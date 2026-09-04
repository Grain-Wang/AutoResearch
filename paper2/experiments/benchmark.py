"""Matched measurement helpers for BlockStamp component and M2 probes."""

from __future__ import annotations

import json
import platform
import resource
import time
from dataclasses import asdict, dataclass
from typing import Any

from experiments.blockstamp_operator import OperatorStatus
from experiments.checkers import (
    CheckerResult,
    CheckerVerdict,
    SlabCheckResult,
    SlabMethod,
    build_slab_problem,
    check_slab,
    pointwise_krawczyk,
    sparse_solve_adapter,
)
from experiments.interval_backend import Interval
from experiments.mna import Circuit, MnaStatus, interval_be_residual_jacobian
from experiments.producers import TraceResult, TraceStep
from experiments.provenance import canonical_sha256

METHODS = (
    "dense_slab_generic",
    "device_local_pointwise_b2",
    "temporal_only",
    "temporal_device_blockstamp",
)

RESULT_COLUMNS = (
    "run_id",
    "circuit_id",
    "instance_id",
    "producer_id",
    "producer_precision",
    "producer_tolerance",
    "step_size",
    "steps",
    "slab_length",
    "replicate",
    "method",
    "input_sha256",
    "producer_trace_sha256",
    "candidate_sha256",
    "tube_sha256",
    "backend_sha256",
    "semantics_sha256",
    "scaling_sha256",
    "ordering_sha256",
    "factor_sha256",
    "threads",
    "hardware_id",
    "checker_verdict",
    "failure_code",
    "oracle_root_in_tube",
    "confirmed_false_accept",
    "certification_rate",
    "certified_prefix_steps",
    "tube_max_relative_width",
    "tube_growth_rate",
    "inclusion_margin_min",
    "assembly_seconds",
    "verified_solve_seconds",
    "operator_propagation_seconds",
    "certificate_generation_seconds",
    "check_seconds",
    "fallback_seconds",
    "end_to_end_seconds",
    "peak_rss_bytes",
    "certificate_bytes",
    "raw_trajectory_bytes",
)


@dataclass(frozen=True, slots=True)
class SharedHashes:
    """Hashes that must agree for every method on one matched input."""

    input_sha256: str
    producer_trace_sha256: str
    candidate_sha256: str
    tube_sha256: str
    backend_sha256: str
    semantics_sha256: str
    scaling_sha256: str
    ordering_sha256: str
    factor_sha256: str
    hardware_id: str


@dataclass(frozen=True, slots=True)
class MethodMeasurements:
    """Aggregated unfiltered verdict and resource observations."""

    verdict: CheckerVerdict
    failure_code: str | None
    accepted_steps: int
    certified_prefix_steps: int
    inclusion_margin_min: float | None
    assembly_seconds: float
    verified_solve_seconds: float
    operator_propagation_seconds: float
    check_seconds: float
    peak_rss_bytes: int


@dataclass(frozen=True, slots=True)
class ContractivePathMeasurements:
    """Prefix obtained by propagating checker-produced interface enclosures."""

    verdict: CheckerVerdict
    failure_code: str | None
    certified_prefix_steps: int
    obligation_attempts: int
    accepted_obligations: int
    segment_lengths: tuple[int, ...]
    accepted_boundaries: tuple[int, ...]
    outgoing_interfaces: tuple[tuple[Interval, ...], ...]
    inclusion_margin_min: float | None
    check_seconds: float


def _interval_payload(value: Interval) -> dict[str, str]:
    return value.to_dict()


def trace_payload(trace: TraceResult) -> dict[str, Any]:
    """Return stable trace content without timing or post-hoc reference values."""

    return {
        "circuit_id": trace.circuit_id,
        "instance": trace.instance_name,
        "precision": trace.precision.value,
        "tolerance": trace.tolerance,
        "steps": trace.steps_requested,
        "step_size": trace.step_size,
        "radius_multiplier": trace.radius_multiplier,
        "records": [
            {
                "step": record.step_index,
                "center": record.center,
                "tube": (
                    [_interval_payload(value) for value in record.tube]
                    if record.tube is not None
                    else None
                ),
                "producer_converged": record.producer_converged,
                "producer_iterations": record.producer_iterations,
                "producer_raw_residual_inf": record.producer_raw_residual_inf,
                "producer_failure_code": record.producer_failure_code,
            }
            for record in trace.records
        ],
    }


def build_shared_hashes(
    trace: TraceResult,
    *,
    backend_sha256: str,
    semantics_sha256: str,
) -> SharedHashes:
    """Build method-independent hashes for one frozen candidate/tube trace."""

    payload = trace_payload(trace)
    candidates = [record.center for record in trace.records]
    tubes = [
        (
            [_interval_payload(value) for value in record.tube]
            if record.tube is not None
            else None
        )
        for record in trace.records
    ]
    hardware = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "threads": 1,
    }
    return SharedHashes(
        canonical_sha256(
            {
                "circuit_id": trace.circuit_id,
                "instance": trace.instance_name,
                "precision": trace.precision.value,
                "tolerance": trace.tolerance,
                "steps": trace.steps_requested,
                "step_size": trace.step_size,
                "radius_multiplier": trace.radius_multiplier,
            }
        ),
        canonical_sha256(payload),
        canonical_sha256(candidates),
        canonical_sha256(tubes),
        backend_sha256,
        semantics_sha256,
        canonical_sha256({"scaling": "identity"}),
        canonical_sha256({"ordering": "normalized-state-layout"}),
        canonical_sha256(
            {
                "midpoint_operator": "interval-endpoint-midpoint-clamped-v1",
                "factor_quality": "verified-partial-pivot-no-dropping-v1",
                "candidate_sha256": canonical_sha256(candidates),
                "tube_sha256": canonical_sha256(tubes),
            }
        ),
        canonical_sha256(hardware),
    )


def _peak_rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    multiplier = 1 if platform.system() == "Darwin" else 1024
    return int(usage * multiplier)


def _combine_verdicts(verdicts: list[CheckerVerdict]) -> CheckerVerdict:
    if len(verdicts) == 0 or CheckerVerdict.UNSUPPORTED in verdicts:
        return CheckerVerdict.UNSUPPORTED
    if CheckerVerdict.UNKNOWN in verdicts:
        return CheckerVerdict.UNKNOWN
    return CheckerVerdict.ACCEPT


def _pointwise_obligation(
    record: TraceStep,
    circuit: Circuit,
    incoming_state: tuple[Interval, ...],
    step_size: float,
) -> tuple[CheckerResult, float, float]:
    if record.tube is None:
        return (
            CheckerResult(
                CheckerVerdict.UNSUPPORTED,
                None,
                None,
                "producer tube is missing",
            ),
            0.0,
            0.0,
        )
    point_box = tuple(Interval.point(value) for value in record.center)
    started = time.perf_counter()
    center_evaluation = interval_be_residual_jacobian(
        circuit, point_box, incoming_state, step_size
    )
    tube_evaluation = interval_be_residual_jacobian(
        circuit, record.tube, incoming_state, step_size
    )
    assembly_seconds = time.perf_counter() - started
    if (
        center_evaluation.status is not MnaStatus.OK
        or center_evaluation.residual is None
        or tube_evaluation.status is not MnaStatus.OK
        or tube_evaluation.jacobian is None
    ):
        return (
            CheckerResult(
                CheckerVerdict.UNSUPPORTED,
                None,
                None,
                center_evaluation.reason
                or tube_evaluation.reason
                or "MNA reconstruction failed",
            ),
            assembly_seconds,
            0.0,
        )
    started = time.perf_counter()
    checked = pointwise_krawczyk(
        record.center,
        record.tube,
        center_evaluation.residual,
        tube_evaluation.jacobian,
        linear_solver=sparse_solve_adapter,
    )
    solve_seconds = time.perf_counter() - started
    return checked, assembly_seconds, solve_seconds


def _slab_obligation(
    records: tuple[TraceStep, ...],
    circuit: Circuit,
    incoming_state: tuple[Interval, ...],
    step_size: float,
    method: str,
) -> tuple[SlabCheckResult, float, float]:
    if not records or any(record.tube is None for record in records):
        return (
            SlabCheckResult(
                CheckerVerdict.UNSUPPORTED,
                None,
                None,
                0,
                "producer tube is missing",
            ),
            0.0,
            0.0,
        )
    centers = tuple(record.center for record in records)
    tubes = tuple(record.tube for record in records if record.tube is not None)
    started = time.perf_counter()
    built = build_slab_problem(
        circuit,
        centers,
        tubes,
        incoming_state,
        step_size,
        streamed_remainder=method == "temporal_device_blockstamp",
    )
    assembly_seconds = time.perf_counter() - started
    if built.status is not OperatorStatus.OK or built.problem is None:
        return (
            SlabCheckResult(
                CheckerVerdict.UNSUPPORTED,
                None,
                None,
                0,
                built.reason or "slab reconstruction failed",
            ),
            assembly_seconds,
            0.0,
        )
    started = time.perf_counter()
    checked = check_slab(built.problem, SlabMethod(method))
    operator_seconds = time.perf_counter() - started
    return checked, assembly_seconds, operator_seconds


def _pointwise_measurements(
    trace: TraceResult,
    circuit: Circuit,
    initial_state: tuple[float, ...],
) -> MethodMeasurements:
    verdicts: list[CheckerVerdict] = []
    margins: list[float] = []
    accepted_steps = 0
    certified_prefix = 0
    prefix_open = True
    assembly_seconds = 0.0
    solve_seconds = 0.0
    previous_tube = tuple(Interval.point(value) for value in initial_state)
    failure_code = trace.failure_code
    for record in trace.records:
        checked, assembly, solve = _pointwise_obligation(
            record, circuit, previous_tube, trace.step_size
        )
        assembly_seconds += assembly
        solve_seconds += solve
        verdict = checked.verdict
        margin = checked.inclusion_margin
        if verdict is not CheckerVerdict.ACCEPT:
            failure_code = failure_code or (
                "B2_STRICT_INCLUSION_FAILED"
                if verdict is CheckerVerdict.UNKNOWN
                else (
                    "MISSING_PRODUCER_TUBE"
                    if record.tube is None
                    else "B2_SPARSE_SOLVE_UNSUPPORTED"
                )
            )
        verdicts.append(verdict)
        if margin is not None:
            margins.append(margin)
        if verdict is CheckerVerdict.ACCEPT:
            accepted_steps += 1
            if prefix_open:
                certified_prefix += 1
        else:
            prefix_open = False
        if record.tube is not None:
            previous_tube = record.tube
    if len(trace.records) < trace.steps_requested:
        verdicts.append(CheckerVerdict.UNSUPPORTED)
        failure_code = failure_code or "INCOMPLETE_PRODUCER_TRACE"
    return MethodMeasurements(
        _combine_verdicts(verdicts),
        failure_code,
        accepted_steps,
        certified_prefix,
        min(margins) if margins else None,
        assembly_seconds,
        solve_seconds,
        0.0,
        assembly_seconds + solve_seconds,
        _peak_rss_bytes(),
    )


def _slab_measurements(
    trace: TraceResult,
    circuit: Circuit,
    initial_state: tuple[float, ...],
    method: str,
    slab_length: int,
) -> MethodMeasurements:
    records = trace.records
    verdicts: list[CheckerVerdict] = []
    margins: list[float] = []
    accepted_steps = 0
    certified_prefix = 0
    prefix_open = True
    assembly_seconds = 0.0
    operator_seconds = 0.0
    failure_code = trace.failure_code
    for start in range(0, len(records), slab_length):
        slab = records[start : start + slab_length]
        incoming = (
            tuple(Interval.point(value) for value in initial_state)
            if start == 0
            else records[start - 1].tube
        )
        if incoming is None:
            verdicts.append(CheckerVerdict.UNSUPPORTED)
            prefix_open = False
            failure_code = failure_code or "MISSING_INCOMING_TUBE"
            continue
        checked, assembly, operator = _slab_obligation(
            slab, circuit, incoming, trace.step_size, method
        )
        assembly_seconds += assembly
        operator_seconds += operator
        verdict = checked.verdict
        margin = checked.inclusion_margin
        if verdict is not CheckerVerdict.ACCEPT:
            failure_code = failure_code or (
                "SLAB_STRICT_INCLUSION_FAILED"
                if verdict is CheckerVerdict.UNKNOWN
                else (
                    "MISSING_PRODUCER_TUBE"
                    if any(record.tube is None for record in slab)
                    else "SLAB_SOLVE_UNSUPPORTED"
                )
            )
        verdicts.append(verdict)
        if margin is not None:
            margins.append(margin)
        if verdict is CheckerVerdict.ACCEPT:
            accepted_steps += len(slab)
            if prefix_open:
                certified_prefix += len(slab)
        else:
            prefix_open = False
    if len(records) < trace.steps_requested:
        verdicts.append(CheckerVerdict.UNSUPPORTED)
        failure_code = failure_code or "INCOMPLETE_PRODUCER_TRACE"
    return MethodMeasurements(
        _combine_verdicts(verdicts),
        failure_code,
        accepted_steps,
        certified_prefix,
        min(margins) if margins else None,
        assembly_seconds,
        0.0,
        operator_seconds,
        assembly_seconds + operator_seconds,
        _peak_rss_bytes(),
    )


def measure_method(
    trace: TraceResult,
    circuit: Circuit,
    initial_state: tuple[float, ...],
    method: str,
    slab_length: int,
) -> MethodMeasurements:
    """Measure one registered method on one complete, unfiltered trace."""

    if method not in METHODS:
        raise ValueError(f"unsupported component method: {method}")
    if slab_length <= 0:
        raise ValueError("slab length must be positive")
    if method == "device_local_pointwise_b2":
        return _pointwise_measurements(trace, circuit, initial_state)
    return _slab_measurements(trace, circuit, initial_state, method, slab_length)


def _contractive_result(
    trace: TraceResult,
    *,
    verdict: CheckerVerdict,
    failure_code: str | None,
    prefix: int,
    attempts: int,
    segments: list[int],
    boundaries: list[int],
    interfaces: list[tuple[Interval, ...]],
    margins: list[float],
    check_seconds: float,
) -> ContractivePathMeasurements:
    if prefix == trace.steps_requested and len(trace.records) == trace.steps_requested:
        verdict = CheckerVerdict.ACCEPT
        failure_code = None
    return ContractivePathMeasurements(
        verdict,
        failure_code,
        prefix,
        attempts,
        len(segments),
        tuple(segments),
        tuple(boundaries),
        tuple(interfaces),
        min(margins) if margins else None,
        check_seconds,
    )


def measure_contractive_pointwise_prefix(
    trace: TraceResult,
    circuit: Circuit,
    initial_state: tuple[float, ...],
) -> ContractivePathMeasurements:
    """Check the valid prefix while propagating each accepted pointwise image."""

    incoming = tuple(Interval.point(value) for value in initial_state)
    segments: list[int] = []
    boundaries: list[int] = []
    interfaces: list[tuple[Interval, ...]] = []
    margins: list[float] = []
    check_seconds = 0.0
    attempts = 0
    for index, record in enumerate(trace.records):
        attempts += 1
        checked, assembly, solve = _pointwise_obligation(
            record, circuit, incoming, trace.step_size
        )
        check_seconds += assembly + solve
        if checked.inclusion_margin is not None:
            margins.append(checked.inclusion_margin)
        if checked.verdict is not CheckerVerdict.ACCEPT or checked.image is None:
            failure = (
                "CONTRACTIVE_B2_STRICT_INCLUSION_FAILED"
                if checked.verdict is CheckerVerdict.UNKNOWN
                else "CONTRACTIVE_B2_UNSUPPORTED"
            )
            return _contractive_result(
                trace,
                verdict=checked.verdict,
                failure_code=trace.failure_code or failure,
                prefix=index,
                attempts=attempts,
                segments=segments,
                boundaries=boundaries,
                interfaces=interfaces,
                margins=margins,
                check_seconds=check_seconds,
            )
        incoming = checked.image
        segments.append(1)
        boundaries.append(index + 1)
        interfaces.append(incoming)
    verdict = (
        CheckerVerdict.ACCEPT
        if len(trace.records) == trace.steps_requested
        else CheckerVerdict.UNSUPPORTED
    )
    return _contractive_result(
        trace,
        verdict=verdict,
        failure_code=(
            None
            if verdict is CheckerVerdict.ACCEPT
            else trace.failure_code or "INCOMPLETE_PRODUCER_TRACE"
        ),
        prefix=len(trace.records),
        attempts=attempts,
        segments=segments,
        boundaries=boundaries,
        interfaces=interfaces,
        margins=margins,
        check_seconds=check_seconds,
    )


def measure_contractive_slab_prefix(
    trace: TraceResult,
    circuit: Circuit,
    initial_state: tuple[float, ...],
    slab_length: int,
    *,
    method: str = "temporal_only",
) -> ContractivePathMeasurements:
    """Check fixed slabs while feeding each accepted endpoint image forward."""

    if slab_length <= 0:
        raise ValueError("slab length must be positive")
    if method not in {
        "dense_slab_generic",
        "temporal_only",
        "temporal_device_blockstamp",
    }:
        raise ValueError(f"unsupported slab method: {method}")
    incoming = tuple(Interval.point(value) for value in initial_state)
    segments: list[int] = []
    boundaries: list[int] = []
    interfaces: list[tuple[Interval, ...]] = []
    margins: list[float] = []
    check_seconds = 0.0
    attempts = 0
    prefix = 0
    while prefix < len(trace.records):
        length = min(slab_length, len(trace.records) - prefix)
        slab = trace.records[prefix : prefix + length]
        attempts += 1
        checked, assembly, operator = _slab_obligation(
            slab, circuit, incoming, trace.step_size, method
        )
        check_seconds += assembly + operator
        if checked.inclusion_margin is not None:
            margins.append(checked.inclusion_margin)
        if checked.verdict is not CheckerVerdict.ACCEPT or checked.image_blocks is None:
            failure = (
                "CONTRACTIVE_SLAB_STRICT_INCLUSION_FAILED"
                if checked.verdict is CheckerVerdict.UNKNOWN
                else "CONTRACTIVE_SLAB_UNSUPPORTED"
            )
            return _contractive_result(
                trace,
                verdict=checked.verdict,
                failure_code=trace.failure_code or failure,
                prefix=prefix,
                attempts=attempts,
                segments=segments,
                boundaries=boundaries,
                interfaces=interfaces,
                margins=margins,
                check_seconds=check_seconds,
            )
        incoming = checked.image_blocks[-1]
        prefix += length
        segments.append(length)
        boundaries.append(prefix)
        interfaces.append(incoming)
    verdict = (
        CheckerVerdict.ACCEPT
        if len(trace.records) == trace.steps_requested
        else CheckerVerdict.UNSUPPORTED
    )
    return _contractive_result(
        trace,
        verdict=verdict,
        failure_code=(
            None
            if verdict is CheckerVerdict.ACCEPT
            else trace.failure_code or "INCOMPLETE_PRODUCER_TRACE"
        ),
        prefix=prefix,
        attempts=attempts,
        segments=segments,
        boundaries=boundaries,
        interfaces=interfaces,
        margins=margins,
        check_seconds=check_seconds,
    )


def measure_greedy_contractive_prefix(
    trace: TraceResult,
    circuit: Circuit,
    initial_state: tuple[float, ...],
    slab_lengths: tuple[int, ...] = (16, 8, 4, 2, 1),
) -> ContractivePathMeasurements:
    """Try the largest available slab and back off to pointwise certification."""

    lengths = tuple(sorted(set(slab_lengths), reverse=True))
    if not lengths or lengths[-1] != 1 or any(length <= 0 for length in lengths):
        raise ValueError("greedy slab lengths must be positive and include one")
    incoming = tuple(Interval.point(value) for value in initial_state)
    segments: list[int] = []
    boundaries: list[int] = []
    interfaces: list[tuple[Interval, ...]] = []
    margins: list[float] = []
    check_seconds = 0.0
    attempts = 0
    prefix = 0
    while prefix < len(trace.records):
        attempted_verdicts: list[CheckerVerdict] = []
        accepted = False
        for length in lengths:
            if prefix + length > len(trace.records):
                continue
            attempts += 1
            if length == 1:
                checked, assembly, solve = _pointwise_obligation(
                    trace.records[prefix], circuit, incoming, trace.step_size
                )
                check_seconds += assembly + solve
                verdict = checked.verdict
                image = checked.image
                margin = checked.inclusion_margin
            else:
                slab_checked, assembly, operator = _slab_obligation(
                    trace.records[prefix : prefix + length],
                    circuit,
                    incoming,
                    trace.step_size,
                    "temporal_only",
                )
                check_seconds += assembly + operator
                verdict = slab_checked.verdict
                image = (
                    None
                    if slab_checked.image_blocks is None
                    else slab_checked.image_blocks[-1]
                )
                margin = slab_checked.inclusion_margin
            attempted_verdicts.append(verdict)
            if margin is not None:
                margins.append(margin)
            if verdict is not CheckerVerdict.ACCEPT or image is None:
                continue
            incoming = image
            prefix += length
            segments.append(length)
            boundaries.append(prefix)
            interfaces.append(incoming)
            accepted = True
            break
        if not accepted:
            verdict = (
                CheckerVerdict.UNKNOWN
                if CheckerVerdict.UNKNOWN in attempted_verdicts
                else CheckerVerdict.UNSUPPORTED
            )
            return _contractive_result(
                trace,
                verdict=verdict,
                failure_code=trace.failure_code or "GREEDY_NO_ACCEPTED_SLAB",
                prefix=prefix,
                attempts=attempts,
                segments=segments,
                boundaries=boundaries,
                interfaces=interfaces,
                margins=margins,
                check_seconds=check_seconds,
            )
    verdict = (
        CheckerVerdict.ACCEPT
        if len(trace.records) == trace.steps_requested
        else CheckerVerdict.UNSUPPORTED
    )
    return _contractive_result(
        trace,
        verdict=verdict,
        failure_code=(
            None
            if verdict is CheckerVerdict.ACCEPT
            else trace.failure_code or "INCOMPLETE_PRODUCER_TRACE"
        ),
        prefix=prefix,
        attempts=attempts,
        segments=segments,
        boundaries=boundaries,
        interfaces=interfaces,
        margins=margins,
        check_seconds=check_seconds,
    )


def _tube_diagnostics(trace: TraceResult) -> tuple[float, float]:
    widths: list[float] = []
    per_step: list[float] = []
    for record in trace.records:
        if record.tube is None:
            continue
        relative = [
            (interval.upper - interval.lower) / max(1e-15, abs(center), 1.0)
            for interval, center in zip(record.tube, record.center, strict=True)
        ]
        widths.extend(relative)
        per_step.append(max(relative))
    growth = per_step[-1] / per_step[0] if per_step and per_step[0] > 0.0 else 0.0
    return max(widths, default=0.0), growth


def _serialized_sizes(trace: TraceResult) -> tuple[int, int]:
    candidates = [record.center for record in trace.records]
    certificate = {
        "candidate": candidates,
        "tubes": [
            (
                [value.to_dict() for value in record.tube]
                if record.tube is not None
                else None
            )
            for record in trace.records
        ],
    }
    certificate_encoding = json.dumps(
        certificate, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    candidate_encoding = json.dumps(
        candidates, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return len(certificate_encoding), len(candidate_encoding)


def result_row(
    trace: TraceResult,
    measurements: MethodMeasurements,
    shared: SharedHashes,
    *,
    method: str,
    slab_length: int,
    replicate: int,
    fallback_seconds: float = 0.0,
) -> dict[str, object]:
    """Create one schema-complete matched result row."""

    tube_width, tube_growth = _tube_diagnostics(trace)
    certificate_bytes, raw_bytes = _serialized_sizes(trace)
    reference_flags = [
        record.reference_in_tube
        for record in trace.records
        if record.reference_in_tube is not None
    ]
    reference_inside = all(reference_flags) if reference_flags else None
    generation_seconds = sum(
        record.generation_seconds + record.tube_seconds for record in trace.records
    )
    run_identity = {
        "input": shared.input_sha256,
        "method": method,
        "slab": slab_length,
        "replicate": replicate,
    }
    row: dict[str, object] = {
        "run_id": canonical_sha256(run_identity)[:20],
        "circuit_id": trace.circuit_id,
        "instance_id": trace.instance_name,
        "producer_id": "residual-stopped-damped-newton-v1",
        "producer_precision": trace.precision.value,
        "producer_tolerance": trace.tolerance,
        "step_size": trace.step_size,
        "steps": trace.steps_requested,
        "slab_length": slab_length,
        "replicate": replicate,
        "method": method,
        **asdict(shared),
        "threads": 1,
        "checker_verdict": measurements.verdict.value,
        "failure_code": measurements.failure_code or "",
        "oracle_root_in_tube": reference_inside,
        "confirmed_false_accept": False,
        "certification_rate": (measurements.accepted_steps / trace.steps_requested),
        "certified_prefix_steps": measurements.certified_prefix_steps,
        "tube_max_relative_width": tube_width,
        "tube_growth_rate": tube_growth,
        "inclusion_margin_min": measurements.inclusion_margin_min,
        "assembly_seconds": measurements.assembly_seconds,
        "verified_solve_seconds": measurements.verified_solve_seconds,
        "operator_propagation_seconds": measurements.operator_propagation_seconds,
        "certificate_generation_seconds": generation_seconds,
        "check_seconds": measurements.check_seconds,
        "fallback_seconds": fallback_seconds,
        "end_to_end_seconds": generation_seconds
        + measurements.check_seconds
        + fallback_seconds,
        "peak_rss_bytes": measurements.peak_rss_bytes,
        "certificate_bytes": certificate_bytes,
        "raw_trajectory_bytes": raw_bytes,
    }
    missing = set(RESULT_COLUMNS) - row.keys()
    if missing:
        raise AssertionError(f"result row is missing columns: {sorted(missing)}")
    return row
