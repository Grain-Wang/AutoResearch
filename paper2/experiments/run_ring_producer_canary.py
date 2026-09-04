"""Run the real-producer canary on the executable three-stage smooth-NMOS ring."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from experiments.checkers import CheckerVerdict
from experiments.mna import RING_INSTANCES, nmos_ring_3stage
from experiments.producers import (
    ProducerPrecision,
    TraceResult,
    build_test_reference,
    load_minimal_probe_config,
    produce_trace,
)
from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    sha256_file,
    source_file_hashes,
)
from experiments.rigorous_backend import backend_info

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG = _PAPER_ROOT / "configs/blockstamp/minimal_probe.yaml"
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/ring_producer_canary.json"
_PROVENANCE_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "experiments/checkers/be_step.py",
    _PAPER_ROOT / "experiments/checkers/pointwise_krawczyk.py",
    _PAPER_ROOT / "experiments/devices/stamps.py",
    _PAPER_ROOT / "experiments/mna/fixed_be.py",
    _PAPER_ROOT / "experiments/mna/minimal_circuits.py",
    _PAPER_ROOT / "experiments/mna/oracles.py",
    _PAPER_ROOT / "experiments/producers/config.py",
    _PAPER_ROOT / "experiments/producers/nonlinear.py",
    _PAPER_ROOT / "experiments/producers/precision.py",
    _PAPER_ROOT / "experiments/producers/trace.py",
    _PAPER_ROOT / "experiments/producers/transient.py",
    _PAPER_ROOT / "experiments/producers/tube.py",
    _PAPER_ROOT / "experiments/provenance.py",
    _PAPER_ROOT / "experiments/rigorous_backend.py",
)


def _serialize_step(record: Any) -> dict[str, object]:
    tube = (
        None
        if record.tube is None
        else [
            {"lower": interval.lower.hex(), "upper": interval.upper.hex()}
            for interval in record.tube
        ]
    )
    return {
        "step_index": record.step_index,
        "center": list(record.center),
        "tube": tube,
        "radii": None if record.radii is None else list(record.radii),
        "producer_converged": record.producer_converged,
        "producer_iterations": record.producer_iterations,
        "producer_raw_residual_inf": record.producer_raw_residual_inf,
        "producer_scaled_residual_inf": record.producer_scaled_residual_inf,
        "producer_failure_code": record.producer_failure_code,
        "incoming_reference_in_tube": record.incoming_reference_in_tube,
        "reference": None if record.reference is None else list(record.reference),
        "reference_error_inf": record.reference_error_inf,
        "reference_in_tube": record.reference_in_tube,
        "checker_verdict": record.checker_verdict.value,
        "checker_inclusion_margin": record.checker_inclusion_margin,
        "checker_reason": record.checker_reason,
        "generation_seconds": record.generation_seconds,
        "tube_seconds": record.tube_seconds,
        "check_seconds": record.check_seconds,
        "reference_lookup_seconds": record.reference_seconds,
    }


def _trace_summary(
    trace: TraceResult, reference_generation_seconds: float
) -> dict[str, object]:
    records = trace.records
    accepted = sum(
        record.checker_verdict is CheckerVerdict.ACCEPT for record in records
    )
    unknown = sum(
        record.checker_verdict is CheckerVerdict.UNKNOWN for record in records
    )
    unsupported = sum(
        record.checker_verdict is CheckerVerdict.UNSUPPORTED for record in records
    )
    prefix = 0
    for record in records:
        if (
            record.checker_verdict is CheckerVerdict.ACCEPT
            and record.reference_in_tube is True
        ):
            prefix += 1
        else:
            break
    finite_margins = [
        record.checker_inclusion_margin
        for record in records
        if record.checker_inclusion_margin is not None
    ]
    errors = [
        record.reference_error_inf
        for record in records
        if record.reference_error_inf is not None
    ]
    radii = [
        radius
        for record in records
        if record.radii is not None
        for radius in record.radii
    ]
    voltage_columns = [
        [record.center[index] for record in records] for index in range(3)
    ]
    eligible_reference_excluding_accepts = sum(
        record.checker_verdict is CheckerVerdict.ACCEPT
        and record.incoming_reference_in_tube
        and record.reference_in_tube is False
        for record in records
    )
    detached_reference_accepts = sum(
        record.checker_verdict is CheckerVerdict.ACCEPT
        and not record.incoming_reference_in_tube
        and record.reference_in_tube is False
        for record in records
    )
    return {
        "circuit_id": trace.circuit_id,
        "instance": trace.instance_name,
        "precision": trace.precision.value,
        "producer_precision_semantics": (
            "round every operation through IEEE-754 binary32"
            if trace.precision is ProducerPrecision.FLOAT32
            else "CPython IEEE-754 binary64 (C double) operations"
        ),
        "producer_tolerance": trace.tolerance,
        "steps_requested": trace.steps_requested,
        "steps_completed": len(records),
        "step_size": trace.step_size,
        "radius_multiplier": trace.radius_multiplier,
        "tube_rule": asdict(trace.tube_rule),
        "test_reference": trace.test_reference_method,
        "trace_failure_code": trace.failure_code,
        "producer_converged_steps": sum(
            record.producer_converged for record in records
        ),
        "producer_failed_steps": sum(
            not record.producer_converged for record in records
        ),
        "producer_total_iterations": sum(
            record.producer_iterations for record in records
        ),
        "maximum_scaled_residual": max(
            (record.producer_scaled_residual_inf for record in records), default=None
        ),
        "maximum_reference_error_inf": max(errors, default=None),
        "reference_in_tube_steps": sum(
            record.reference_in_tube is True for record in records
        ),
        "eligible_reference_excluding_accepts": (eligible_reference_excluding_accepts),
        "detached_reference_accepts": detached_reference_accepts,
        "checker_accept": accepted,
        "checker_unknown": unknown,
        "checker_unsupported": unsupported,
        "certified_reference_containing_prefix": prefix,
        "minimum_inclusion_margin": min(finite_margins, default=None),
        "maximum_tube_radius": max(radii, default=None),
        "output_voltage_ranges": [
            {"minimum": min(column), "maximum": max(column)}
            for column in voltage_columns
            if column
        ],
        "timing_seconds": {
            "producer": sum(record.generation_seconds for record in records),
            "tube": sum(record.tube_seconds for record in records),
            "checker": sum(record.check_seconds for record in records),
            "reference_generation": reference_generation_seconds,
            "reference_lookup": sum(record.reference_seconds for record in records),
        },
        "step_records": [_serialize_step(record) for record in records],
    }


def run_ring_canary(
    config_path: Path = _DEFAULT_CONFIG,
    *,
    step_counts: tuple[int, ...] | None = None,
) -> dict[str, object]:
    """Run the frozen instance/length/precision grid and return its artifact."""

    info = backend_info()
    if info is None:
        raise RuntimeError("the MPFR checker backend is unavailable")
    config = load_minimal_probe_config(config_path)
    ring_config = config["ring_canary"]
    producer_config = config["producer"]
    declared_steps = tuple(ring_config["steps"] if step_counts is None else step_counts)
    if not declared_steps or any(steps <= 0 for steps in declared_steps):
        raise ValueError("ring canary step counts must be positive")
    radius_multiplier = float(ring_config["radius_multiplier"])
    traces: list[dict[str, object]] = []
    for instance in RING_INSTANCES:
        for steps in declared_steps:
            started = time.perf_counter()
            reference = build_test_reference(
                "nmos_ring_3stage", instance.name, steps, instance.step_size
            )
            reference_seconds = time.perf_counter() - started
            for precision in (
                ProducerPrecision(value) for value in producer_config["precisions"]
            ):
                trace = produce_trace(
                    "nmos_ring_3stage",
                    instance.name,
                    precision,
                    float(
                        producer_config["ring_tolerance_by_precision"][precision.value]
                    ),
                    steps,
                    instance.step_size,
                    radius_multiplier,
                    test_reference=reference,
                )
                traces.append(_trace_summary(trace, reference_seconds))
    attempted_steps = sum(int(trace["steps_requested"]) for trace in traces)
    completed_steps = sum(int(trace["steps_completed"]) for trace in traces)
    eligible_reference_excluding_accepts = sum(
        int(trace["eligible_reference_excluding_accepts"]) for trace in traces
    )
    detached_reference_accepts = sum(
        int(trace["detached_reference_accepts"]) for trace in traces
    )
    incomplete = attempted_steps - completed_steps
    topology_payload = {
        instance.name: asdict(nmos_ring_3stage(instance)) for instance in RING_INSTANCES
    }
    sources = source_file_hashes(_PAPER_ROOT, _PROVENANCE_FILES)
    failure_codes = []
    if incomplete:
        failure_codes.append("INCOMPLETE_TRACE")
    if eligible_reference_excluding_accepts:
        failure_codes.append("REFERENCE_EXCLUDING_ACCEPT")
    return {
        "schema_version": 1,
        "status": "PASS-CANARY" if not failure_codes else "STOP",
        "claim_scope": (
            "real binary producer and oracle-free tube canary on a declared smooth-"
            "NMOS ring; not a BSIM/industrial-model or performance claim"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": "python3 -m experiments.run_ring_producer_canary",
        "config": config_path.relative_to(_PAPER_ROOT).as_posix(),
        "config_sha256": sha256_file(config_path),
        "input_sha256": canonical_sha256(
            {
                "topologies": topology_payload,
                "steps": declared_steps,
                "precisions": producer_config["precisions"],
                "tolerances": producer_config["ring_tolerance_by_precision"],
                "radius_multiplier": radius_multiplier,
            }
        ),
        "topology_sha256": canonical_sha256(topology_payload),
        "source_files_sha256": sources,
        "random_seeds": {},
        "randomness_used": False,
        "backend": {
            "name": info.name,
            "version": info.version,
            "precision_bits": info.precision_bits,
            "library": info.library,
        },
        "producer_checker_independence": {
            "producer": "experiments/producers/transient.py",
            "checker_semantics": "experiments/mna/fixed_be.py",
            "test_reference": "experiments/mna/oracles.py",
            "tube_reference_access": False,
        },
        "test_reference": config["test_reference"],
        "reference_audit": {
            "eligible_reference_excluding_accept": (
                "checker ACCEPT while the incoming tube contained the Decimal test "
                "reference but the current tube did not"
            ),
            "detached_reference_accept": (
                "checker ACCEPT after the Decimal test trajectory had already left "
                "the incoming tube; this is not a checker contradiction"
            ),
            "confirmed_false_accepts": None,
            "confirmed_false_accepts_reason": (
                "the Decimal-160 test reference is not a rigorous oracle"
            ),
        },
        "attempted_traces": len(traces),
        "attempted_steps": attempted_steps,
        "completed_steps": completed_steps,
        "checker_accept": sum(int(trace["checker_accept"]) for trace in traces),
        "checker_unknown": sum(int(trace["checker_unknown"]) for trace in traces),
        "checker_unsupported": sum(
            int(trace["checker_unsupported"]) for trace in traces
        ),
        "eligible_reference_excluding_accepts": (eligible_reference_excluding_accepts),
        "detached_reference_accepts": detached_reference_accepts,
        "failure_codes": failure_codes,
        "first_failure": next(
            (
                {
                    "instance": trace["instance"],
                    "precision": trace["precision"],
                    "steps": trace["steps_requested"],
                    "failure_code": trace["trace_failure_code"],
                }
                for trace in traces
                if trace["trace_failure_code"] is not None
            ),
            None,
        ),
        "traces": traces,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--steps",
        type=int,
        nargs="+",
        help="optional positive step-count override for test/canary replays",
    )
    arguments = parser.parse_args()
    result = run_ring_canary(
        arguments.config,
        step_counts=None if arguments.steps is None else tuple(arguments.steps),
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    summary = {key: value for key, value in result.items() if key != "traces"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    if result["status"] == "STOP":
        sys.exit(1)


if __name__ == "__main__":
    main()
