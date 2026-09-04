"""Run the frozen nonlinear M2 grid in independent worker processes."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from experiments.benchmark import (
    METHODS,
    RESULT_COLUMNS,
    build_shared_hashes,
    measure_method,
    result_row,
)
from experiments.checkers import CheckerVerdict
from experiments.interval_backend import Interval
from experiments.mna import (
    DIODE_RC_INSTANCES,
    RING_INSTANCES,
    Circuit,
    transient_workload,
)
from experiments.producers import (
    ProducerPrecision,
    TraceResult,
    TraceStep,
    build_test_reference,
    produce_trace,
)
from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    sha256_file,
    source_file_hashes,
)

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _PAPER_ROOT / "configs/blockstamp/minimal_probe.yaml"
_RESULT_ROOT = _PAPER_ROOT / "results/blockstamp"
_DEFAULT_OUTPUT = _RESULT_ROOT / "minimal_probe.csv"
_DEFAULT_CHECKPOINT_DIR = _RESULT_ROOT / "minimal_probe_parts"
_FAIRNESS = _RESULT_ROOT / "b2_fairness.json"
_BACKEND = _PAPER_ROOT / "experiments/rigorous_backend.py"
_SEMANTICS_FILES = (
    _PAPER_ROOT / "experiments/devices/stamps.py",
    _PAPER_ROOT / "experiments/mna/fixed_be.py",
)
_SOURCE_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "experiments/__init__.py",
    _PAPER_ROOT / "experiments/benchmark.py",
    _PAPER_ROOT / "experiments/blockstamp_operator.py",
    _PAPER_ROOT / "experiments/interval_backend.py",
    _PAPER_ROOT / "experiments/provenance.py",
    _PAPER_ROOT / "experiments/rigorous_backend.py",
    _PAPER_ROOT / "experiments/checkers/__init__.py",
    _PAPER_ROOT / "experiments/checkers/be_step.py",
    _PAPER_ROOT / "experiments/checkers/pointwise_krawczyk.py",
    _PAPER_ROOT / "experiments/checkers/slab_krawczyk.py",
    _PAPER_ROOT / "experiments/checkers/verified_sparse.py",
    _PAPER_ROOT / "experiments/devices/__init__.py",
    _PAPER_ROOT / "experiments/devices/stamps.py",
    _PAPER_ROOT / "experiments/mna/__init__.py",
    _PAPER_ROOT / "experiments/mna/fixed_be.py",
    _PAPER_ROOT / "experiments/mna/minimal_circuits.py",
    _PAPER_ROOT / "experiments/mna/oracles.py",
    _PAPER_ROOT / "experiments/producers/__init__.py",
    _PAPER_ROOT / "experiments/producers/config.py",
    _PAPER_ROOT / "experiments/producers/nonlinear.py",
    _PAPER_ROOT / "experiments/producers/precision.py",
    _PAPER_ROOT / "experiments/producers/trace.py",
    _PAPER_ROOT / "experiments/producers/transient.py",
    _PAPER_ROOT / "experiments/producers/tube.py",
)
_PRIMARY_METHODS = METHODS
_ALL_METHODS = (*METHODS, "strict_mpfr_rerun")
_FROZEN_PRIMARY_METHODS = (
    "dense_slab_generic",
    "device_local_pointwise_b2",
    "temporal_only",
    "temporal_device_blockstamp",
)
_FROZEN_METHODS = (*_FROZEN_PRIMARY_METHODS, "strict_mpfr_rerun")
_FROZEN_STEPS = (100, 300, 1000)
_FROZEN_SLAB_LENGTHS = (1, 2, 4, 8, 16)
_FROZEN_REPLICATES = 5
_FROZEN_WORKLOADS = {
    "diode_rc": ("nominal", "fast_load", "slow_hot_start"),
    "nmos_ring_3stage": ("balanced", "light_load", "slow_load"),
}
_FROZEN_TOLERANCE = 1.0e-10
_FROZEN_RADIUS_MULTIPLIER = 4.0
_CHECKPOINT_SCHEMA_VERSION = 1
_CHECKPOINT_QUEUE = "minimal-probe-m2-v1"
_RESOURCE_METRICS = ("check_seconds", "peak_rss_bytes", "certificate_bytes")
_SHARED_HASH_COLUMNS = (
    "input_sha256",
    "producer_trace_sha256",
    "candidate_sha256",
    "tube_sha256",
    "backend_sha256",
    "semantics_sha256",
    "scaling_sha256",
    "ordering_sha256",
    "factor_sha256",
    "hardware_id",
)


def _load_config() -> dict[str, Any]:
    payload = json.loads(_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("minimal-probe configuration must be a JSON object")
    return payload


def _semantics_sha256() -> str:
    return canonical_sha256({path.name: sha256_file(path) for path in _SEMANTICS_FILES})


def _execution_contract() -> dict[str, object]:
    """Return the immutable source/config contract attached to every queue item."""

    return {
        "config_sha256": sha256_file(_CONFIG),
        "source_files_sha256": source_file_hashes(_PAPER_ROOT, _SOURCE_FILES),
        "backend_sha256": sha256_file(_BACKEND),
        "semantics_sha256": _semantics_sha256(),
    }


def _frozen_request_errors(
    *,
    steps_grid: tuple[int, ...],
    slab_lengths: tuple[int, ...],
    replicates: int,
    workers: int,
    run_warmups: bool,
) -> list[str]:
    config = _load_config()
    tolerance = float(config["producer"]["ring_tolerance_by_precision"]["float64"])
    radius_multiplier = float(config["ring_canary"]["radius_multiplier"])
    actual_workloads = {
        "diode_rc": tuple(item.name for item in DIODE_RC_INSTANCES),
        "nmos_ring_3stage": tuple(item.name for item in RING_INSTANCES),
    }
    checks = (
        (steps_grid == _FROZEN_STEPS, f"steps must equal {_FROZEN_STEPS}"),
        (
            slab_lengths == _FROZEN_SLAB_LENGTHS,
            f"slab lengths must equal {_FROZEN_SLAB_LENGTHS}",
        ),
        (replicates == _FROZEN_REPLICATES, "replicates must equal 5"),
        (workers == 1, "checkpointed M2 must use exactly one worker"),
        (run_warmups, "all frozen warmups must run"),
        (METHODS == _FROZEN_PRIMARY_METHODS, "primary method order changed"),
        (_ALL_METHODS == _FROZEN_METHODS, "M2 method order changed"),
        (actual_workloads == _FROZEN_WORKLOADS, "frozen workload matrix changed"),
        (tolerance == _FROZEN_TOLERANCE, "float64 tolerance changed"),
        (
            radius_multiplier == _FROZEN_RADIUS_MULTIPLIER,
            "radius multiplier changed",
        ),
    )
    return [message for passed, message in checks if not passed]


def _validate_frozen_request(
    *,
    steps_grid: tuple[int, ...],
    slab_lengths: tuple[int, ...],
    replicates: int,
    workers: int,
    run_warmups: bool,
) -> None:
    errors = _frozen_request_errors(
        steps_grid=steps_grid,
        slab_lengths=slab_lengths,
        replicates=replicates,
        workers=workers,
        run_warmups=run_warmups,
    )
    if errors:
        raise ValueError("invalid frozen M2 request: " + "; ".join(errors))


def _workload(
    circuit_id: str, instance_name: str
) -> tuple[Circuit, tuple[float, ...], float]:
    return transient_workload(circuit_id, instance_name)


def _reference_interval(center: float, reference: Decimal, radius: float) -> Interval:
    lower = math.nextafter(center - radius, -math.inf)
    upper = math.nextafter(center + radius, math.inf)
    while Decimal.from_float(lower) > reference:
        lower = math.nextafter(lower, -math.inf)
    while Decimal.from_float(upper) < reference:
        upper = math.nextafter(upper, math.inf)
    return Interval(lower, upper)


def _strict_trace(
    source: TraceResult,
    references: tuple[tuple[Decimal, ...], ...],
    reference_generation_seconds: float,
) -> TraceResult:
    records: list[TraceStep] = []
    per_step_generation = reference_generation_seconds / len(references)
    for index, reference in enumerate(references):
        center = tuple(float(value) for value in reference)
        source_record = source.records[index] if index < len(source.records) else None
        radii = (
            source_record.radii
            if source_record is not None and source_record.radii is not None
            else tuple(
                1e-12 if item < len(center) - 1 else 1e-15
                for item in range(len(center))
            )
        )
        tube = tuple(
            _reference_interval(value, exact, radius)
            for value, exact, radius in zip(center, reference, radii, strict=True)
        )
        records.append(
            TraceStep(
                step_index=index,
                center=center,
                tube=tube,
                radii=radii,
                producer_converged=True,
                producer_iterations=0,
                producer_raw_residual_inf=0.0,
                producer_scaled_residual_inf=0.0,
                producer_failure_code=None,
                reference=center,
                reference_error_inf=0.0,
                reference_in_tube=True,
                checker_verdict=CheckerVerdict.UNKNOWN,
                checker_inclusion_margin=None,
                checker_reason="verdict reconstructed by strict-rerun worker",
                generation_seconds=per_step_generation,
                tube_seconds=0.0,
                check_seconds=0.0,
                reference_seconds=0.0,
                incoming_reference_in_tube=True,
            )
        )
    return replace(
        source,
        precision=ProducerPrecision.FLOAT64,
        records=tuple(records),
        failure_code=None,
        test_reference_method=(
            "Decimal-160 candidate generation followed by MPFR-256 directed "
            "Krawczyk verification"
        ),
    )


def _queue_key(spec: dict[str, Any]) -> dict[str, object]:
    return {
        "circuit_id": str(spec["circuit_id"]),
        "instance_id": str(spec["instance"]),
        "producer_precision": str(spec["precision"]),
        "producer_tolerance": float(spec["tolerance"]),
        "step_size": float(spec["step_size"]),
        "radius_multiplier": float(spec["radius_multiplier"]),
        "steps": int(spec["steps"]),
        "slab_length": int(spec["slab_length"]),
        "replicate": int(spec["replicate"]),
        "method": str(spec["method"]),
    }


def _producer_completion(trace: TraceResult) -> dict[str, object]:
    records = len(trace.records)
    tubes = sum(record.tube is not None for record in trace.records)
    converged = sum(record.producer_converged for record in trace.records)
    return {
        "records": records,
        "steps_requested": trace.steps_requested,
        "trace_complete": records == trace.steps_requested,
        "tube_records": tubes,
        "tube_complete": tubes == trace.steps_requested,
        "converged_records": converged,
        "all_records_converged": converged == trace.steps_requested,
        "failure_code": trace.failure_code,
    }


def _worker_envelope(spec: dict[str, Any]) -> dict[str, object]:
    worker_started = time.perf_counter()
    contract = _execution_contract()
    for name in (
        "config_sha256",
        "source_files_sha256",
        "backend_sha256",
        "semantics_sha256",
    ):
        if name in spec and spec[name] != contract[name]:
            raise RuntimeError(f"worker {name} differs from the parent contract")
    circuit_id = str(spec["circuit_id"])
    instance = str(spec["instance"])
    circuit, initial_state, default_step_size = _workload(circuit_id, instance)
    step_size = float(spec.get("step_size", default_step_size))
    steps = int(spec["steps"])
    started = time.perf_counter()
    references = build_test_reference(circuit_id, instance, steps, step_size)
    reference_generation_seconds = time.perf_counter() - started
    started = time.perf_counter()
    trace = produce_trace(
        circuit_id,
        instance,
        ProducerPrecision(str(spec["precision"])),
        float(spec["tolerance"]),
        steps,
        step_size,
        float(spec["radius_multiplier"]),
        test_reference=references,
    )
    trace_construction_seconds = time.perf_counter() - started
    method = str(spec["method"])
    timing_breakdown: dict[str, float] = {
        "reference_generation_seconds": reference_generation_seconds,
        "source_trace_construction_seconds": trace_construction_seconds,
    }
    if method == "strict_mpfr_rerun":
        started = time.perf_counter()
        measured_trace = _strict_trace(trace, references, 0.0)
        strict_trace_construction_seconds = time.perf_counter() - started
        measurements = measure_method(
            measured_trace,
            circuit,
            initial_state,
            "device_local_pointwise_b2",
            1,
        )
        shared = build_shared_hashes(
            measured_trace,
            backend_sha256=str(spec["backend_sha256"]),
            semantics_sha256=str(spec["semantics_sha256"]),
        )
        started = time.perf_counter()
        row = result_row(
            measured_trace,
            measurements,
            shared,
            method=method,
            slab_length=int(spec["slab_length"]),
            replicate=int(spec["replicate"]),
        )
        certificate_serialization_seconds = time.perf_counter() - started
        strict_generation_seconds = (
            reference_generation_seconds
            + trace_construction_seconds
            + strict_trace_construction_seconds
            + certificate_serialization_seconds
        )
        row["certificate_generation_seconds"] = strict_generation_seconds
        row["end_to_end_seconds"] = strict_generation_seconds + float(
            row["check_seconds"]
        )
        row["producer_id"] = "decimal160-candidate+mpfr256-verified-rerun-v1"
        timing_breakdown.update(
            {
                "strict_trace_construction_seconds": (
                    strict_trace_construction_seconds
                ),
                "certificate_serialization_seconds": (
                    certificate_serialization_seconds
                ),
                "accounted_strict_generation_seconds": strict_generation_seconds,
            }
        )
        certificate_trace = measured_trace
    else:
        measurements = measure_method(
            trace,
            circuit,
            initial_state,
            method,
            int(spec["slab_length"]),
        )
        shared = build_shared_hashes(
            trace,
            backend_sha256=str(spec["backend_sha256"]),
            semantics_sha256=str(spec["semantics_sha256"]),
        )
        row = result_row(
            trace,
            measurements,
            shared,
            method=method,
            slab_length=int(spec["slab_length"]),
            replicate=int(spec["replicate"]),
        )
        certificate_trace = trace

    row["confirmed_false_accept"] = bool(
        row["checker_verdict"] == "ACCEPT" and row["oracle_root_in_tube"] is False
    )

    queue_kind = str(spec.get("_queue_kind", "measured"))
    queue_index = int(spec.get("_queue_index", -1))
    return {
        "schema_version": _CHECKPOINT_SCHEMA_VERSION,
        "status": "COMPLETE",
        "stage": "M2-FROZEN-CONFIGURATION",
        "queue": _CHECKPOINT_QUEUE,
        "queue_kind": queue_kind,
        "queue_index": queue_index,
        "queue_key": _queue_key(spec),
        **contract,
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": (
            "python3 -m experiments.run_minimal_probe --worker-json "
            "<canonical-queue-spec>"
        ),
        "random_seeds": {},
        "producer_completion": _producer_completion(trace),
        "certificate_trace_records": len(certificate_trace.records),
        "certificate_trace_complete": (
            len(certificate_trace.records) == certificate_trace.steps_requested
        ),
        "timing_breakdown": timing_breakdown,
        "worker_elapsed_seconds": time.perf_counter() - worker_started,
        "success_only_filtering": False,
        "row": row,
    }


def _worker_row(spec: dict[str, Any]) -> dict[str, object]:
    """Compatibility helper returning only the result row."""

    envelope = _worker_envelope(spec)
    row = envelope["row"]
    if not isinstance(row, dict):
        raise AssertionError("worker envelope row must be an object")
    return row


def _run_subprocess(spec: dict[str, Any]) -> dict[str, object]:
    command = [
        sys.executable,
        "-m",
        "experiments.run_minimal_probe",
        "--worker-json",
        json.dumps(spec, sort_keys=True, separators=(",", ":")),
    ]
    environment = os.environ.copy()
    result = subprocess.run(
        command,
        cwd=_PAPER_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"M2 worker failed ({result.returncode}): {result.stderr.strip()}"
        )
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("M2 worker did not return a JSON envelope")
    if payload.get("status") != "COMPLETE" or not isinstance(payload.get("row"), dict):
        raise RuntimeError("M2 worker returned an incomplete metadata envelope")
    return payload


def _median_rows(
    rows: list[dict[str, object]],
) -> dict[tuple[object, ...], dict[str, float]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            row["circuit_id"],
            row["instance_id"],
            row["steps"],
            row["slab_length"],
            row["method"],
        )
        grouped.setdefault(key, []).append(row)
    output: dict[tuple[object, ...], dict[str, float]] = {}
    numeric = (
        *_RESOURCE_METRICS,
        "certification_rate",
        "certified_prefix_steps",
        "tube_max_relative_width",
    )
    for key, records in grouped.items():
        output[key] = {
            name: statistics.median(float(record[name]) for record in records)
            for name in numeric
        }
    return output


def _bootstrap_ratio(
    paired: list[tuple[str, float, float]], seed: int, samples: int = 2_000
) -> dict[str, float | int]:
    if not paired:
        return {"ratio": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "samples": 0}
    by_cluster: dict[str, list[tuple[float, float]]] = {}
    for cluster, baseline, candidate in paired:
        by_cluster.setdefault(cluster, []).append((baseline, candidate))
    clusters = sorted(by_cluster)

    def ratio(selected: list[str]) -> float:
        baseline_total = sum(
            baseline for cluster in selected for baseline, _ in by_cluster[cluster]
        )
        candidate_total = sum(
            candidate for cluster in selected for _, candidate in by_cluster[cluster]
        )
        return baseline_total / candidate_total if candidate_total > 0.0 else math.inf

    observed = ratio(clusters)
    generator = random.Random(seed)
    draws = sorted(
        ratio([generator.choice(clusters) for _ in clusters]) for _ in range(samples)
    )
    return {
        "ratio": observed,
        "ci_lower": draws[int(0.025 * (samples - 1))],
        "ci_upper": draws[int(0.975 * (samples - 1))],
        "samples": samples,
    }


def _stable_resource_signal(
    medians: dict[tuple[object, ...], dict[str, float]],
    baseline_method: str,
    metric: str,
) -> dict[str, object]:
    paired: list[tuple[str, float, float]] = []
    instance_ratios: dict[str, dict[str, float]] = {}
    no_quality_regression = True
    for key, baseline in medians.items():
        circuit, instance, steps, slab, method = key
        if method != baseline_method or int(slab) not in {8, 16}:
            continue
        candidate_key = (
            circuit,
            instance,
            steps,
            slab,
            "temporal_device_blockstamp",
        )
        if candidate_key not in medians:
            continue
        candidate = medians[candidate_key]
        baseline_value = baseline[metric]
        candidate_value = candidate[metric]
        ratio = baseline_value / candidate_value if candidate_value > 0.0 else math.inf
        cluster = f"{circuit}/{instance}"
        paired.append((cluster, baseline_value, candidate_value))
        instance_ratios.setdefault(cluster, {}).setdefault(str(slab), []).append(ratio)
        no_quality_regression = no_quality_regression and (
            candidate["certification_rate"] >= baseline["certification_rate"]
            and candidate["certified_prefix_steps"]
            >= baseline["certified_prefix_steps"]
        )
    summarized = {
        cluster: {
            slab: statistics.median(values) for slab, values in slab_values.items()
        }
        for cluster, slab_values in instance_ratios.items()
    }
    counts = {
        circuit: {
            slab: sum(
                ratios.get(slab, 0.0) > 1.0
                for cluster, ratios in summarized.items()
                if cluster.startswith(f"{circuit}/")
            )
            for slab in ("8", "16")
        }
        for circuit in ("diode_rc", "nmos_ring_3stage")
    }
    instance_rule = all(
        counts[circuit][slab] >= 2 for circuit in counts for slab in ("8", "16")
    )
    bootstrap = _bootstrap_ratio(paired, seed=20260901)
    stable = (
        instance_rule and float(bootstrap["ci_lower"]) > 1.0 and no_quality_regression
    )
    return {
        "stable": stable,
        "baseline": baseline_method,
        "metric": metric,
        "instance_slab_ratios": summarized,
        "passing_instance_counts": counts,
        "instance_rule": instance_rule,
        "no_quality_regression": no_quality_regression,
        "clustered_bootstrap": bootstrap,
    }


def _mechanism_signal(
    medians: dict[tuple[object, ...], dict[str, float]], baseline_method: str
) -> dict[str, object]:
    slabs: dict[str, dict[str, int]] = {}
    for slab in (2, 4, 8, 16):
        counts = {"diode_rc": 0, "nmos_ring_3stage": 0}
        for circuit in counts:
            instances: set[object] = set()
            for key, baseline in medians.items():
                row_circuit, instance, steps, row_slab, method = key
                if (
                    row_circuit != circuit
                    or int(row_slab) != slab
                    or method != baseline_method
                ):
                    continue
                candidate = medians.get(
                    (
                        row_circuit,
                        instance,
                        steps,
                        row_slab,
                        "temporal_device_blockstamp",
                    )
                )
                if candidate is None:
                    continue
                improved = (
                    candidate["certification_rate"] > baseline["certification_rate"]
                    or candidate["certified_prefix_steps"]
                    > baseline["certified_prefix_steps"]
                )
                width_ok = (
                    candidate["tube_max_relative_width"]
                    <= baseline["tube_max_relative_width"]
                )
                if improved and width_ok:
                    instances.add(instance)
            counts[circuit] = len(instances)
        slabs[str(slab)] = counts
    passing_slabs = [
        slab
        for slab, counts in slabs.items()
        if all(value >= 2 for value in counts.values())
    ]
    return {
        "passes": bool(passing_slabs),
        "baseline": baseline_method,
        "passing_slabs": passing_slabs,
        "passing_instance_counts": slabs,
    }


def evaluate_claims(rows: list[dict[str, object]]) -> dict[str, object]:
    """Apply the frozen W/D/E rules to a complete result table."""

    medians = _median_rows(rows)
    resource = {
        baseline: {
            metric: _stable_resource_signal(medians, baseline, metric)
            for metric in _RESOURCE_METRICS
        }
        for baseline in (
            "device_local_pointwise_b2",
            "dense_slab_generic",
            "temporal_only",
        )
    }
    w = _mechanism_signal(medians, "device_local_pointwise_b2")
    d_mechanism = _mechanism_signal(medians, "temporal_only")
    e_metrics = [
        metric
        for metric in _RESOURCE_METRICS
        if resource["device_local_pointwise_b2"][metric]["stable"]
        and resource["dense_slab_generic"][metric]["stable"]
    ]
    d_metrics = [
        metric
        for metric in _RESOURCE_METRICS
        if resource["temporal_only"][metric]["stable"]
    ]
    return {
        "W": "PASS" if w["passes"] else "STOP",
        "E": "PASS" if e_metrics else "STOP",
        "D": "PASS" if d_metrics or d_mechanism["passes"] else "STOP",
        "claim_w_mechanism": w,
        "claim_e_passing_metrics": e_metrics,
        "claim_d_passing_metrics": d_metrics,
        "claim_d_mechanism": d_mechanism,
        "resource_signals": resource,
    }


def _apply_fallback_costs(rows: list[dict[str, object]]) -> None:
    strict: dict[tuple[object, ...], dict[str, object]] = {}
    for row in rows:
        if row["method"] == "strict_mpfr_rerun":
            key = (
                row["input_sha256"],
                row["circuit_id"],
                row["instance_id"],
                row["steps"],
                row["slab_length"],
                row["replicate"],
            )
            if key in strict:
                raise RuntimeError(f"duplicate strict fallback comparator: {key}")
            strict[key] = row
    for row in rows:
        if row["method"] == "strict_mpfr_rerun" or row["checker_verdict"] == "ACCEPT":
            continue
        key = (
            row["input_sha256"],
            row["circuit_id"],
            row["instance_id"],
            row["steps"],
            row["slab_length"],
            row["replicate"],
        )
        fallback = float(strict[key]["end_to_end_seconds"])
        row["fallback_seconds"] = fallback
        row["end_to_end_seconds"] = (
            float(row["certificate_generation_seconds"])
            + float(row["check_seconds"])
            + fallback
        )


def _primary_hashes_match(rows: list[dict[str, object]]) -> bool:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        if row["method"] not in _PRIMARY_METHODS:
            continue
        key = (
            row["circuit_id"],
            row["instance_id"],
            row["steps"],
            row["slab_length"],
            row["replicate"],
        )
        grouped.setdefault(key, []).append(row)
    return all(
        len(records) == len(_PRIMARY_METHODS)
        and all(
            len({str(record[column]) for record in records}) == 1
            for column in _SHARED_HASH_COLUMNS
        )
        for records in grouped.values()
    )


def _strict_comparator_hashes_valid(rows: list[dict[str, object]]) -> bool:
    """Validate the frozen, explicitly limited strict-comparator exception."""

    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            row["circuit_id"],
            row["instance_id"],
            row["steps"],
            row["slab_length"],
            row["replicate"],
        )
        grouped.setdefault(key, []).append(row)
    required_equal = (
        "input_sha256",
        "backend_sha256",
        "semantics_sha256",
        "scaling_sha256",
        "ordering_sha256",
        "hardware_id",
        "threads",
    )
    return bool(grouped) and all(
        len(records) == len(_ALL_METHODS)
        and sum(record["method"] == "strict_mpfr_rerun" for record in records) == 1
        and all(
            len({str(record[column]) for record in records}) == 1
            for column in required_equal
        )
        for records in grouped.values()
    )


def _specs(
    *,
    steps_grid: tuple[int, ...],
    slab_lengths: tuple[int, ...],
    replicates: int,
    contract: dict[str, object],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    config = _load_config()
    tolerance = float(config["producer"]["ring_tolerance_by_precision"]["float64"])
    radius_multiplier = float(config["ring_canary"]["radius_multiplier"])
    workloads = [
        ("diode_rc", item.name, item.step_size) for item in DIODE_RC_INSTANCES
    ] + [("nmos_ring_3stage", item.name, item.step_size) for item in RING_INSTANCES]
    common_specs: list[dict[str, Any]] = []
    warmups: list[dict[str, Any]] = []
    for circuit_id, instance, step_size in workloads:
        for steps in steps_grid:
            for slab_length in slab_lengths:
                for method in _ALL_METHODS:
                    base = {
                        "circuit_id": circuit_id,
                        "instance": instance,
                        "precision": "float64",
                        "tolerance": tolerance,
                        "steps": steps,
                        "step_size": step_size,
                        "radius_multiplier": radius_multiplier,
                        "slab_length": slab_length,
                        "method": method,
                        **contract,
                    }
                    warmups.append({**base, "replicate": -1})
                    for replicate in range(replicates):
                        common_specs.append({**base, "replicate": replicate})
    for queue_index, spec in enumerate(warmups):
        spec["_queue_kind"] = "warmup"
        spec["_queue_index"] = queue_index
    for queue_index, spec in enumerate(common_specs):
        spec["_queue_kind"] = "measured"
        spec["_queue_index"] = queue_index
    return warmups, common_specs


def _checkpoint_path(checkpoint_dir: Path, spec: dict[str, Any]) -> Path:
    queue_kind = str(spec["_queue_kind"])
    directory = "warmups" if queue_kind == "warmup" else "measured"
    return checkpoint_dir / directory / f"{int(spec['_queue_index']):06d}.json"


def _row_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        row["circuit_id"],
        row["instance_id"],
        int(row["steps"]),
        int(row["slab_length"]),
        str(row["method"]),
        int(row["replicate"]),
    )


def _spec_key(spec: dict[str, Any]) -> tuple[object, ...]:
    return (
        str(spec["circuit_id"]),
        str(spec["instance"]),
        int(spec["steps"]),
        int(spec["slab_length"]),
        str(spec["method"]),
        int(spec["replicate"]),
    )


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_result_row(row: dict[str, object], spec: dict[str, Any]) -> None:
    missing = set(RESULT_COLUMNS) - row.keys()
    if missing:
        raise RuntimeError(f"checkpoint row is missing columns: {sorted(missing)}")
    expected = {
        "circuit_id": str(spec["circuit_id"]),
        "instance_id": str(spec["instance"]),
        "producer_precision": str(spec["precision"]),
        "producer_tolerance": float(spec["tolerance"]),
        "step_size": float(spec["step_size"]),
        "steps": int(spec["steps"]),
        "slab_length": int(spec["slab_length"]),
        "replicate": int(spec["replicate"]),
        "method": str(spec["method"]),
        "backend_sha256": str(spec["backend_sha256"]),
        "semantics_sha256": str(spec["semantics_sha256"]),
    }
    mismatches = [name for name, value in expected.items() if row.get(name) != value]
    if mismatches:
        raise RuntimeError(
            f"checkpoint row differs from queue spec: {sorted(mismatches)}"
        )

    required_strings = (
        "run_id",
        "circuit_id",
        "instance_id",
        "producer_id",
        "producer_precision",
        "method",
        *_SHARED_HASH_COLUMNS,
        "checker_verdict",
    )
    if any(
        not isinstance(row[name], str) or not row[name] for name in required_strings
    ):
        raise RuntimeError("checkpoint row has an empty or non-string identity field")
    if not isinstance(row["failure_code"], str):
        raise RuntimeError("checkpoint row failure_code must be a string")
    if row["checker_verdict"] not in {"ACCEPT", "UNKNOWN", "UNSUPPORTED"}:
        raise RuntimeError("checkpoint row has an invalid checker verdict")
    if row["oracle_root_in_tube"] not in {True, False, None}:
        raise RuntimeError("checkpoint row oracle_root_in_tube must be bool or null")
    if not isinstance(row["confirmed_false_accept"], bool):
        raise RuntimeError("checkpoint row confirmed_false_accept must be bool")

    integer_fields = (
        "steps",
        "slab_length",
        "replicate",
        "threads",
        "certified_prefix_steps",
        "peak_rss_bytes",
        "certificate_bytes",
        "raw_trajectory_bytes",
    )
    if any(
        not isinstance(row[name], int) or isinstance(row[name], bool)
        for name in integer_fields
    ):
        raise RuntimeError("checkpoint row has a non-integer count field")
    if int(row["threads"]) != 1:
        raise RuntimeError("checkpoint row must declare one thread")
    if not 0 <= int(row["certified_prefix_steps"]) <= int(row["steps"]):
        raise RuntimeError("checkpoint row has an invalid certified prefix")
    resource_counts = ("peak_rss_bytes", "certificate_bytes", "raw_trajectory_bytes")
    if any(int(row[name]) < 0 for name in resource_counts):
        raise RuntimeError("checkpoint row has a negative resource count")

    finite_fields = (
        "producer_tolerance",
        "step_size",
        "certification_rate",
        "tube_max_relative_width",
        "tube_growth_rate",
        "assembly_seconds",
        "verified_solve_seconds",
        "operator_propagation_seconds",
        "certificate_generation_seconds",
        "check_seconds",
        "fallback_seconds",
        "end_to_end_seconds",
    )
    if any(
        not _number(row[name]) or not math.isfinite(float(row[name]))
        for name in finite_fields
    ):
        raise RuntimeError("checkpoint row has a non-finite numeric field")
    if not 0.0 <= float(row["certification_rate"]) <= 1.0:
        raise RuntimeError("checkpoint row has an invalid certification rate")
    nonnegative_fields = tuple(
        name
        for name in finite_fields
        if name not in {"producer_tolerance", "step_size"}
    )
    if any(float(row[name]) < 0.0 for name in nonnegative_fields):
        raise RuntimeError("checkpoint row has a negative timing/diagnostic field")
    margin = row["inclusion_margin_min"]
    if margin is not None and (not _number(margin) or not math.isfinite(float(margin))):
        raise RuntimeError("checkpoint row has an invalid inclusion margin")


def _validate_checkpoint(
    payload: dict[str, object],
    spec: dict[str, Any],
    contract: dict[str, object],
) -> dict[str, object]:
    expected_metadata = {
        "schema_version": _CHECKPOINT_SCHEMA_VERSION,
        "status": "COMPLETE",
        "stage": "M2-FROZEN-CONFIGURATION",
        "queue": _CHECKPOINT_QUEUE,
        "queue_kind": str(spec["_queue_kind"]),
        "queue_index": int(spec["_queue_index"]),
        "queue_key": _queue_key(spec),
        **contract,
    }
    mismatches = [
        name for name, value in expected_metadata.items() if payload.get(name) != value
    ]
    if mismatches:
        raise RuntimeError(
            "checkpoint metadata differs from current queue/contract: "
            + ", ".join(sorted(mismatches))
        )
    if payload.get("success_only_filtering") is not False:
        raise RuntimeError("checkpoint does not preserve unfiltered outcomes")
    completion = payload.get("producer_completion")
    if not isinstance(completion, dict):
        raise RuntimeError("checkpoint lacks producer completion metadata")
    required_completion = {
        "records",
        "steps_requested",
        "trace_complete",
        "tube_records",
        "tube_complete",
        "converged_records",
        "all_records_converged",
        "failure_code",
    }
    if required_completion - completion.keys():
        raise RuntimeError("checkpoint has incomplete producer completion metadata")
    if completion["steps_requested"] != int(spec["steps"]):
        raise RuntimeError("checkpoint producer step count differs from queue spec")
    for name in ("records", "steps_requested", "tube_records", "converged_records"):
        if not isinstance(completion[name], int) or isinstance(completion[name], bool):
            raise RuntimeError("checkpoint producer count must be an integer")
    for name in ("trace_complete", "tube_complete", "all_records_converged"):
        if not isinstance(completion[name], bool):
            raise RuntimeError("checkpoint producer completion flag must be boolean")
    if completion["failure_code"] is not None and not isinstance(
        completion["failure_code"], str
    ):
        raise RuntimeError("checkpoint producer failure code must be string or null")
    if not isinstance(payload.get("certificate_trace_records"), int) or not isinstance(
        payload.get("certificate_trace_complete"), bool
    ):
        raise RuntimeError("checkpoint lacks certificate trace completion metadata")
    row = payload.get("row")
    if not isinstance(row, dict):
        raise RuntimeError("checkpoint row must be an object")
    _validate_result_row(row, spec)
    return row


def _read_checkpoint(
    path: Path, spec: dict[str, Any], contract: dict[str, object]
) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"corrupt M2 checkpoint: {path}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"M2 checkpoint is not an object: {path}")
    _validate_checkpoint(payload, spec, contract)
    return payload


def _write_checkpoint_atomic(
    path: Path,
    payload: dict[str, object],
    spec: dict[str, Any],
    contract: dict[str, object],
) -> dict[str, object]:
    if path.exists():
        raise FileExistsError(f"refusing to replace completed M2 checkpoint: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise RuntimeError(f"stale M2 checkpoint temporary file: {temporary}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return _read_checkpoint(path, spec, contract)


def _scan_checkpoint_tree(
    checkpoint_dir: Path,
    warmups: list[dict[str, Any]],
    specs: list[dict[str, Any]],
) -> None:
    if not checkpoint_dir.exists():
        return
    expected = {
        _checkpoint_path(checkpoint_dir, spec).resolve() for spec in (*warmups, *specs)
    }
    found = {path.resolve() for path in checkpoint_dir.rglob("*.json")}
    extras = sorted(str(path) for path in found - expected)
    temporaries = sorted(str(path) for path in checkpoint_dir.rglob("*.tmp"))
    if extras or temporaries:
        details = []
        if extras:
            details.append(f"unexpected JSON files={extras}")
        if temporaries:
            details.append(f"stale temporary files={temporaries}")
        raise RuntimeError("invalid M2 checkpoint tree: " + "; ".join(details))


def _execute_checkpointed(
    *,
    checkpoint_dir: Path,
    warmups: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    contract: dict[str, object],
    resume: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
    _scan_checkpoint_tree(checkpoint_dir, warmups, specs)
    envelopes: list[dict[str, object]] = []
    counts = {
        "warmups_executed": 0,
        "warmups_reused": 0,
        "measured_executed": 0,
        "measured_reused": 0,
    }
    for spec in (*warmups, *specs):
        path = _checkpoint_path(checkpoint_dir, spec)
        queue_kind = str(spec["_queue_kind"])
        prefix = "warmups" if queue_kind == "warmup" else "measured"
        if path.exists():
            if not resume:
                raise FileExistsError(
                    f"M2 checkpoint exists; use --resume to reuse it: {path}"
                )
            envelope = _read_checkpoint(path, spec, contract)
            counts[f"{prefix}_reused"] += 1
        else:
            print(
                json.dumps(
                    {
                        "event": "M2_START",
                        "queue_kind": queue_kind,
                        "queue_index": int(spec["_queue_index"]),
                        "queue_size": (
                            len(warmups) if queue_kind == "warmup" else len(specs)
                        ),
                        "queue_key": _queue_key(spec),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            envelope = _run_subprocess(spec)
            _validate_checkpoint(envelope, spec, contract)
            envelope = _write_checkpoint_atomic(path, envelope, spec, contract)
            counts[f"{prefix}_executed"] += 1
            row = envelope["row"]
            if not isinstance(row, dict):
                raise AssertionError("validated M2 row changed type")
            print(
                json.dumps(
                    {
                        "event": "M2_CHECKPOINT",
                        "queue_kind": queue_kind,
                        "queue_index": int(spec["_queue_index"]),
                        "queue_size": (
                            len(warmups) if queue_kind == "warmup" else len(specs)
                        ),
                        "checker_verdict": row["checker_verdict"],
                        "producer_trace_complete": envelope["producer_completion"][
                            "trace_complete"
                        ],
                        "path": str(path.resolve().relative_to(_PAPER_ROOT)),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        envelopes.append(envelope)
    warmup_count = len(warmups)
    measured_envelopes = envelopes[warmup_count:]
    rows = [envelope["row"] for envelope in measured_envelopes]
    if any(not isinstance(row, dict) for row in rows):
        raise AssertionError("validated M2 checkpoint row changed type")
    return rows, envelopes, counts


def _integrity_report(
    rows: list[dict[str, object]],
    specs: list[dict[str, Any]],
    warmups: list[dict[str, Any]],
    envelopes: list[dict[str, object]],
    contract: dict[str, object],
) -> dict[str, object]:
    expected_counter = Counter(_spec_key(spec) for spec in specs)
    observed_counter = Counter(_row_key(row) for row in rows)
    expected_unique = len(expected_counter) == len(specs) and all(
        count == 1 for count in expected_counter.values()
    )
    duplicate_rows = sum(max(0, count - 1) for count in observed_counter.values())
    missing_rows = sum((expected_counter - observed_counter).values())
    extra_rows = sum((observed_counter - expected_counter).values())

    grouped_methods: dict[tuple[object, ...], Counter[str]] = {}
    for row in rows:
        key = (
            row["circuit_id"],
            row["instance_id"],
            row["steps"],
            row["slab_length"],
            row["replicate"],
        )
        grouped_methods.setdefault(key, Counter())[str(row["method"])] += 1
    expected_methods = Counter(_ALL_METHODS)
    five_methods_per_group = bool(grouped_methods) and all(
        methods == expected_methods for methods in grouped_methods.values()
    )

    run_ids = [str(row["run_id"]) for row in rows]
    run_ids_unique = len(set(run_ids)) == len(run_ids)
    checkpoints_complete = len(envelopes) == len(warmups) + len(specs)
    checkpoint_contract_match = all(
        all(envelope.get(name) == value for name, value in contract.items())
        for envelope in envelopes
    )
    primary_hashes_match = _primary_hashes_match(rows)
    strict_comparator_hashes_valid = _strict_comparator_hashes_valid(rows)
    exact_counter_match = observed_counter == expected_counter
    all_pass = (
        expected_unique
        and exact_counter_match
        and duplicate_rows == 0
        and missing_rows == 0
        and extra_rows == 0
        and five_methods_per_group
        and run_ids_unique
        and checkpoints_complete
        and checkpoint_contract_match
        and primary_hashes_match
        and strict_comparator_hashes_valid
    )
    return {
        "all_pass": all_pass,
        "expected_queue_keys_unique": expected_unique,
        "exact_key_counter_match": exact_counter_match,
        "missing_rows": missing_rows,
        "extra_rows": extra_rows,
        "duplicate_rows": duplicate_rows,
        "run_ids_unique": run_ids_unique,
        "five_methods_per_matched_group": five_methods_per_group,
        "all_checkpoints_complete": checkpoints_complete,
        "all_checkpoint_contract_hashes_match": checkpoint_contract_match,
        "all_primary_shared_hashes_match": primary_hashes_match,
        "strict_comparator_hashes_valid": strict_comparator_hashes_valid,
        "strict_comparator_exception": (
            "strict_mpfr_rerun deliberately regenerates its Decimal-160 candidate "
            "and oracle-centered tube; it is excluded from primary shared-hash equality"
        ),
    }


def _fallback_report(rows: list[dict[str, object]]) -> dict[str, object]:
    strict: dict[tuple[object, ...], dict[str, object]] = {}
    strict_unique = True
    for row in rows:
        if row["method"] != "strict_mpfr_rerun":
            continue
        key = (
            row["input_sha256"],
            row["circuit_id"],
            row["instance_id"],
            row["steps"],
            row["slab_length"],
            row["replicate"],
        )
        strict_unique = strict_unique and key not in strict
        strict[key] = row
    triggered = 0
    recovered_accept_rows = 0
    accounting_match = True
    total_seconds = 0.0
    for row in rows:
        if row["method"] == "strict_mpfr_rerun" or row["checker_verdict"] == "ACCEPT":
            continue
        triggered += 1
        key = (
            row["input_sha256"],
            row["circuit_id"],
            row["instance_id"],
            row["steps"],
            row["slab_length"],
            row["replicate"],
        )
        comparator = strict.get(key)
        if comparator is None:
            accounting_match = False
            continue
        recovered_accept_rows += comparator["checker_verdict"] == "ACCEPT"
        expected = float(comparator["end_to_end_seconds"])
        observed = float(row["fallback_seconds"])
        total_seconds += observed
        accounting_match = accounting_match and math.isclose(
            observed, expected, rel_tol=0.0, abs_tol=0.0
        )
        accounting_match = accounting_match and math.isclose(
            float(row["end_to_end_seconds"]),
            float(row["certificate_generation_seconds"])
            + float(row["check_seconds"])
            + observed,
            rel_tol=1.0e-15,
            abs_tol=1.0e-15,
        )
    return {
        "policy": (
            "every non-ACCEPT primary row adds its matched strict-rerun "
            "end-to-end cost"
        ),
        "triggered_rows": triggered,
        "recovered_accept_rows": recovered_accept_rows,
        "recovery_rate": recovered_accept_rows / triggered if triggered else 0.0,
        "total_fallback_seconds": total_seconds,
        "strict_comparators_unique": strict_unique,
        "complete_cost_accounting": accounting_match and strict_unique,
    }


def run_minimal_probe(
    *,
    steps_grid: tuple[int, ...],
    slab_lengths: tuple[int, ...],
    replicates: int,
    workers: int,
    run_warmups: bool = True,
    checkpoint_dir: Path = _DEFAULT_CHECKPOINT_DIR,
    resume: bool = False,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Run or resume the exact frozen M2 queue, one fresh process at a time."""

    _validate_frozen_request(
        steps_grid=steps_grid,
        slab_lengths=slab_lengths,
        replicates=replicates,
        workers=workers,
        run_warmups=run_warmups,
    )
    contract = _execution_contract()
    warmups, specs = _specs(
        steps_grid=steps_grid,
        slab_lengths=slab_lengths,
        replicates=replicates,
        contract=contract,
    )
    rows, envelopes, checkpoint_counts = _execute_checkpointed(
        checkpoint_dir=checkpoint_dir,
        warmups=warmups,
        specs=specs,
        contract=contract,
        resume=resume,
    )
    _apply_fallback_costs(rows)
    rows.sort(
        key=lambda row: (
            str(row["circuit_id"]),
            str(row["instance_id"]),
            int(row["steps"]),
            int(row["slab_length"]),
            str(row["method"]),
            int(row["replicate"]),
        )
    )
    integrity = _integrity_report(rows, specs, warmups, envelopes, contract)
    expected_rows = len(specs)
    expected_warmups = len(warmups)
    grid_complete = bool(integrity["all_pass"])
    observed_workloads = {
        circuit: sorted(
            {str(row["instance_id"]) for row in rows if row["circuit_id"] == circuit}
        )
        for circuit in _FROZEN_WORKLOADS
    }
    workloads_complete_details = {
        circuit: observed_workloads[circuit] == sorted(instances)
        for circuit, instances in _FROZEN_WORKLOADS.items()
    }
    workloads_complete = all(workloads_complete_details.values())
    fallback = _fallback_report(rows)
    primary_hashes_match = bool(integrity["all_primary_shared_hashes_match"])
    strict_hashes_valid = bool(integrity["strict_comparator_hashes_valid"])
    measured_envelopes = [
        envelope for envelope in envelopes if envelope["queue_kind"] == "measured"
    ]
    warmup_envelopes = [
        envelope for envelope in envelopes if envelope["queue_kind"] == "warmup"
    ]
    producer_completion = {
        "measured_trace_complete": sum(
            bool(envelope["producer_completion"]["trace_complete"])
            for envelope in measured_envelopes
        ),
        "measured_tube_complete": sum(
            bool(envelope["producer_completion"]["tube_complete"])
            for envelope in measured_envelopes
        ),
        "warmup_trace_complete": sum(
            bool(envelope["producer_completion"]["trace_complete"])
            for envelope in warmup_envelopes
        ),
        "warmup_tube_complete": sum(
            bool(envelope["producer_completion"]["tube_complete"])
            for envelope in warmup_envelopes
        ),
        "expected_measured": expected_rows,
        "expected_warmups": expected_warmups,
    }
    strict_generation_accounted = all(
        isinstance(envelope.get("timing_breakdown"), dict)
        and "accounted_strict_generation_seconds" in envelope["timing_breakdown"]
        for envelope in measured_envelopes
        if envelope["queue_key"]["method"] == "strict_mpfr_rerun"
    )
    checkpoint_paths = [
        _checkpoint_path(checkpoint_dir, spec) for spec in (*warmups, *specs)
    ]
    checkpoint_sha256 = canonical_sha256(
        {
            str(path.relative_to(checkpoint_dir)): sha256_file(path)
            for path in checkpoint_paths
        }
    )
    queue_execution_complete = (
        grid_complete
        and workloads_complete
        and bool(fallback["complete_cost_accounting"])
        and strict_generation_accounted
    )
    claims = (
        evaluate_claims(rows)
        if queue_execution_complete
        else {
            "W": "UNVERIFIED",
            "E": "UNVERIFIED",
            "D": "UNVERIFIED",
        }
    )
    fairness = (
        json.loads(_FAIRNESS.read_text(encoding="utf-8")) if _FAIRNESS.exists() else {}
    )
    fairness_pass = (
        fairness.get("status") == "PASS"
        and fairness.get("strong_baseline_status") == "IMPLEMENTED"
        and fairness.get("all_required_hashes_present") is True
        and fairness.get("all_shared_hashes_match") is True
    )
    false_accepts = sum(bool(row["confirmed_false_accept"]) for row in rows)
    promotion_signal = claims.get("W") == "PASS" or claims.get("E") == "PASS"
    protocol_complete = queue_execution_complete and fairness_pass
    scientific_evidence_valid = protocol_complete and false_accepts == 0
    status = (
        "PASS"
        if scientific_evidence_valid and promotion_signal
        else ("STOP" if protocol_complete else "INCOMPLETE")
    )
    failure_distribution = Counter(
        str(row["failure_code"]) if row["failure_code"] else "NONE" for row in rows
    )
    first_non_accept = next(
        (row for row in rows if row["checker_verdict"] != "ACCEPT"), None
    )
    manifest: dict[str, object] = {
        "schema_version": 2,
        "status": status,
        "claim_scope": (
            "frozen nonlinear M2 probe; strict comparator uses Decimal-160 candidate "
            "generation plus MPFR-256 directed certificate checking"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": (
            "python3 -m experiments.run_minimal_probe --steps-grid "
            + " ".join(str(value) for value in steps_grid)
            + " --slab-lengths "
            + " ".join(str(value) for value in slab_lengths)
            + f" --replicates {replicates} --workers {workers} "
            + f"--checkpoint-dir {checkpoint_dir} --resume"
        ),
        **contract,
        "input_sha256": canonical_sha256(
            {
                "steps": steps_grid,
                "slabs": slab_lengths,
                "replicates": replicates,
                "methods": _ALL_METHODS,
            }
        ),
        "row_count": len(rows),
        "expected_row_count": expected_rows,
        "attempted_cases": len(rows),
        "supported_cases": sum(row["checker_verdict"] != "UNSUPPORTED" for row in rows),
        "unsupported_cases": sum(
            row["checker_verdict"] == "UNSUPPORTED" for row in rows
        ),
        "failure_codes": sorted(
            code for code in failure_distribution if code != "NONE"
        ),
        "failure_code_distribution": dict(sorted(failure_distribution.items())),
        "first_failure": (
            {
                "run_id": first_non_accept["run_id"],
                "circuit_id": first_non_accept["circuit_id"],
                "instance_id": first_non_accept["instance_id"],
                "steps": first_non_accept["steps"],
                "slab_length": first_non_accept["slab_length"],
                "replicate": first_non_accept["replicate"],
                "method": first_non_accept["method"],
                "checker_verdict": first_non_accept["checker_verdict"],
                "failure_code": first_non_accept["failure_code"],
            }
            if first_non_accept is not None
            else None
        ),
        "execution_complete": queue_execution_complete,
        "protocol_complete": protocol_complete,
        "scientific_evidence_valid": scientific_evidence_valid,
        "requested_coverage_complete": grid_complete,
        "frozen_grid_requested": True,
        "grid_complete": grid_complete,
        "integrity": integrity,
        "independent_processes": True,
        "workers": workers,
        "warmups_excluded": True,
        "warmup_processes": expected_warmups,
        "expected_warmup_processes": 450,
        "checkpoint_counts": checkpoint_counts,
        "checkpoint_dir": str(checkpoint_dir),
        "checkpoint_set_sha256": checkpoint_sha256,
        "producer_completion": producer_completion,
        "replicates": replicates,
        "steps_grid": list(steps_grid),
        "slab_lengths": list(slab_lengths),
        "methods": list(_ALL_METHODS),
        "workloads_complete": workloads_complete,
        "workloads_complete_details": workloads_complete_details,
        "observed_instances": observed_workloads,
        "success_only_filtering": False,
        "required_columns": list(RESULT_COLUMNS),
        "allowed_methods": list(_ALL_METHODS),
        "allowed_verdicts": ["ACCEPT", "UNKNOWN", "UNSUPPORTED"],
        "all_primary_shared_hashes_match": primary_hashes_match,
        "strict_comparator_hashes_valid": strict_hashes_valid,
        "strict_rerun_allowed_difference": {
            "role": (
                "predeclared utility/fallback comparator; not a fifth primary "
                "matched checker"
            ),
            "different": [
                "producer_trace_sha256",
                "candidate_sha256",
                "tube_sha256",
                "factor_sha256",
            ],
            "reason": (
                "Decimal-160 candidate generation and oracle-centered strict tube"
            ),
            "required_equal": [
                "input_sha256",
                "backend_sha256",
                "semantics_sha256",
                "scaling_sha256",
                "ordering_sha256",
                "hardware_id",
                "threads",
            ],
        },
        "strict_comparator_scope": (
            "Decimal-160 reference candidate followed by MPFR-256 directed B2 "
            "certificate checking; not an independent full transient solver"
        ),
        "fairness_pass": fairness_pass,
        "fairness_artifact_sha256": (
            sha256_file(_FAIRNESS) if _FAIRNESS.exists() else None
        ),
        "confirmed_false_accepts": false_accepts,
        "observed_reference_exclusions": sum(
            row["oracle_root_in_tube"] is False for row in rows
        ),
        "complete_cost_accounting": bool(fallback["complete_cost_accounting"])
        and strict_generation_accounted,
        "strict_generation_accounted": strict_generation_accounted,
        "fallback_and_recovery": fallback,
        "fallback_policy": fallback["policy"],
        "claims": claims,
        "stable_signal": {
            "clustered_bootstrap_95ci_complete": grid_complete,
            "decision_rule": (
                "paper2/steps/008_next_round_gate.md" "#54-stable-signal-definition"
            ),
        },
        "verdict_counts": {
            verdict: sum(row["checker_verdict"] == verdict for row in rows)
            for verdict in ("ACCEPT", "UNKNOWN", "UNSUPPORTED")
        },
        "rss_measurement_scope": "fresh-worker process high-water mark",
        "timing_aggregation": "five-process median per configuration",
        "bootstrap": {
            "unit": "circuit-instance",
            "confidence": 0.95,
            "samples": 2_000,
            "seed": 20260901,
        },
        "random_seeds": {"clustered_bootstrap": 20260901},
        "confirmed_false_accept_definition": (
            "checker ACCEPT and independent Decimal-160 test reference outside tube; "
            "the Decimal reference is high precision but not a directed root proof"
        ),
        "certificate_size_scope": (
            "candidate and tube serialization only; method-specific factor/witness "
            "bytes are not represented"
        ),
    }
    return rows, manifest


def write_minimal_probe(
    output: Path,
    manifest_output: Path,
    rows: list[dict[str, object]],
    manifest: dict[str, object],
) -> None:
    """Write M2 CSV and its machine-readable decision manifest."""

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        **manifest,
        "artifact_sha256": sha256_file(output),
        "row_content_sha256": canonical_sha256(rows),
    }
    manifest_output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-json", help=argparse.SUPPRESS)
    parser.add_argument("--steps-grid", type=int, nargs="+", default=(100, 300, 1000))
    parser.add_argument("--slab-lengths", type=int, nargs="+", default=(1, 2, 4, 8, 16))
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--skip-warmups", action="store_true")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--checkpoint-dir", type=Path, default=_DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.worker_json:
        spec = json.loads(arguments.worker_json)
        print(json.dumps(_worker_envelope(spec), sort_keys=True))
        return
    manifest_output = arguments.manifest_output or arguments.output.with_suffix(
        ".manifest.json"
    )
    rows, manifest = run_minimal_probe(
        steps_grid=tuple(arguments.steps_grid),
        slab_lengths=tuple(arguments.slab_lengths),
        replicates=arguments.replicates,
        workers=arguments.workers,
        run_warmups=not arguments.skip_warmups,
        checkpoint_dir=arguments.checkpoint_dir,
        resume=arguments.resume,
    )
    write_minimal_probe(arguments.output, manifest_output, rows, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if manifest["status"] == "INCOMPLETE":
        sys.exit(1)


if __name__ == "__main__":
    main()
