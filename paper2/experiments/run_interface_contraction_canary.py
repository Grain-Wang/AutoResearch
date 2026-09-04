"""Audit Claim W against a pointwise checker that propagates contracted interfaces."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from experiments.benchmark import (
    ContractivePathMeasurements,
    measure_contractive_pointwise_prefix,
    measure_contractive_slab_prefix,
    measure_greedy_contractive_prefix,
    measure_method,
    trace_payload,
)
from experiments.mna import DIODE_RC_INSTANCES, RING_INSTANCES, transient_workload
from experiments.producers import (
    ProducerPrecision,
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
from experiments.rigorous_backend import backend_info

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _PAPER_ROOT / "configs/blockstamp/minimal_probe.yaml"
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/interface_contraction_canary.json"
_SLAB_LENGTHS = (1, 2, 4, 8, 16)
_GREEDY_LENGTHS = tuple(reversed(_SLAB_LENGTHS))
_SEMANTICS_FILES = (
    _PAPER_ROOT / "experiments/devices/stamps.py",
    _PAPER_ROOT / "experiments/mna/fixed_be.py",
)
_SOURCE_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "experiments/benchmark.py",
    _PAPER_ROOT / "experiments/blockstamp_operator.py",
    _PAPER_ROOT / "experiments/checkers/pointwise_krawczyk.py",
    _PAPER_ROOT / "experiments/checkers/slab_krawczyk.py",
    _PAPER_ROOT / "experiments/checkers/verified_sparse.py",
    _PAPER_ROOT / "experiments/devices/stamps.py",
    _PAPER_ROOT / "experiments/mna/fixed_be.py",
    _PAPER_ROOT / "experiments/mna/minimal_circuits.py",
    _PAPER_ROOT / "experiments/producers/nonlinear.py",
    _PAPER_ROOT / "experiments/producers/precision.py",
    _PAPER_ROOT / "experiments/producers/trace.py",
    _PAPER_ROOT / "experiments/producers/transient.py",
    _PAPER_ROOT / "experiments/producers/tube.py",
    _PAPER_ROOT / "experiments/provenance.py",
    _PAPER_ROOT / "experiments/rigorous_backend.py",
)


def _reference_inside(reference: tuple[Decimal, ...], interface: tuple) -> bool:
    return all(
        Decimal.from_float(interval.lower)
        <= value
        <= Decimal.from_float(interval.upper)
        for value, interval in zip(reference, interface, strict=True)
    )


def _contractive_payload(
    measurement: ContractivePathMeasurements,
    references: tuple[tuple[Decimal, ...], ...],
    steps: int,
) -> dict[str, object]:
    reference_flags = [
        _reference_inside(references[boundary - 1], interface)
        for boundary, interface in zip(
            measurement.accepted_boundaries,
            measurement.outgoing_interfaces,
            strict=True,
        )
    ]
    return {
        "verdict": measurement.verdict.value,
        "failure_code": measurement.failure_code,
        "certified_prefix_steps": measurement.certified_prefix_steps,
        "certification_rate": measurement.certified_prefix_steps / steps,
        "obligation_attempts": measurement.obligation_attempts,
        "accepted_obligations": measurement.accepted_obligations,
        "segment_lengths": list(measurement.segment_lengths),
        "accepted_boundaries": list(measurement.accepted_boundaries),
        "minimum_inclusion_margin": measurement.inclusion_margin_min,
        "check_seconds": measurement.check_seconds,
        "reference_in_all_accepted_interfaces": all(reference_flags),
        "reference_excluding_accepted_interfaces": sum(
            not flag for flag in reference_flags
        ),
    }


def _instances(circuit_filter: str | None) -> tuple[tuple[str, str], ...]:
    registered = (
        *(("diode_rc", instance.name) for instance in DIODE_RC_INSTANCES),
        *(("nmos_ring_3stage", instance.name) for instance in RING_INSTANCES),
    )
    if circuit_filter is None:
        return registered
    if circuit_filter not in {"diode_rc", "nmos_ring_3stage"}:
        raise ValueError(f"unknown circuit filter: {circuit_filter}")
    return tuple(item for item in registered if item[0] == circuit_filter)


def run_interface_contraction_canary(
    *,
    steps: int = 100,
    circuit_filter: str | None = None,
) -> dict[str, object]:
    """Run a deterministic strengthened-baseline canary on registered workloads."""

    if steps <= 0:
        raise ValueError("steps must be positive")
    info = backend_info()
    if info is None:
        raise RuntimeError("the MPFR checker backend is unavailable")
    config = json.loads(_CONFIG.read_text(encoding="utf-8"))
    tolerance = float(config["producer"]["ring_tolerance_by_precision"]["float64"])
    radius_multiplier = float(config["ring_canary"]["radius_multiplier"])
    semantics_sha256 = canonical_sha256(
        {path.name: sha256_file(path) for path in _SEMANTICS_FILES}
    )
    backend_sha256 = sha256_file(_PAPER_ROOT / "experiments/rigorous_backend.py")
    records: list[dict[str, object]] = []
    for circuit_id, instance_name in _instances(circuit_filter):
        circuit, initial_state, step_size = transient_workload(
            circuit_id, instance_name
        )
        references = build_test_reference(circuit_id, instance_name, steps, step_size)
        trace = produce_trace(
            circuit_id,
            instance_name,
            ProducerPrecision.FLOAT64,
            tolerance,
            steps,
            step_size,
            radius_multiplier,
            test_reference=references,
        )
        legacy = measure_method(
            trace,
            circuit,
            initial_state,
            "device_local_pointwise_b2",
            1,
        )
        pointwise = measure_contractive_pointwise_prefix(trace, circuit, initial_state)
        fixed = {
            str(length): measure_contractive_slab_prefix(
                trace,
                circuit,
                initial_state,
                length,
                method="temporal_only",
            )
            for length in _SLAB_LENGTHS
        }
        greedy = measure_greedy_contractive_prefix(
            trace, circuit, initial_state, _GREEDY_LENGTHS
        )
        pointwise_prefix = pointwise.certified_prefix_steps
        records.append(
            {
                "circuit_id": circuit_id,
                "instance_id": instance_name,
                "steps": steps,
                "step_size": step_size,
                "producer_precision": "float64",
                "producer_tolerance": tolerance,
                "radius_multiplier": radius_multiplier,
                "trace_complete": len(trace.records) == steps,
                "trace_failure_code": trace.failure_code,
                "trace_sha256": canonical_sha256(trace_payload(trace)),
                "legacy_noncontractive_pointwise": {
                    "verdict": legacy.verdict.value,
                    "certified_prefix_steps": legacy.certified_prefix_steps,
                    "certification_rate": legacy.certified_prefix_steps / steps,
                    "check_seconds": legacy.check_seconds,
                },
                "contractive_pointwise_b2": _contractive_payload(
                    pointwise, references, steps
                ),
                "contractive_fixed_slabs": {
                    length: _contractive_payload(measurement, references, steps)
                    for length, measurement in fixed.items()
                },
                "greedy_largest_first": _contractive_payload(greedy, references, steps),
                "pointwise_prefix_gain_over_legacy": (
                    pointwise_prefix - legacy.certified_prefix_steps
                ),
                "fixed_slab_prefix_advantage_over_pointwise": {
                    length: measurement.certified_prefix_steps - pointwise_prefix
                    for length, measurement in fixed.items()
                },
                "greedy_prefix_advantage_over_pointwise": (
                    greedy.certified_prefix_steps - pointwise_prefix
                ),
            }
        )

    nontrivial_counts = {
        str(length): {
            circuit_id: sum(
                int(
                    record["fixed_slab_prefix_advantage_over_pointwise"][str(length)]
                    > 0
                )
                for record in records
                if record["circuit_id"] == circuit_id
            )
            for circuit_id in {record["circuit_id"] for record in records}
        }
        for length in _SLAB_LENGTHS
        if length > 1
    }
    workload_complete = len(records) == len(_instances(circuit_filter)) and all(
        record["trace_complete"] is True for record in records
    )
    protocol_failure_codes = [] if workload_complete else ["INCOMPLETE_TRACE"]
    criterion_applicable = circuit_filter is None
    passing_lengths = [
        length
        for length, counts in nontrivial_counts.items()
        if criterion_applicable
        and all(counts.get(circuit_id, 0) >= 2 for circuit_id in counts)
        and set(counts) == {"diode_rc", "nmos_ring_3stage"}
    ]
    reference_exclusions = sum(
        int(
            record["contractive_pointwise_b2"][
                "reference_excluding_accepted_interfaces"
            ]
        )
        + sum(
            int(payload["reference_excluding_accepted_interfaces"])
            for payload in record["contractive_fixed_slabs"].values()
        )
        + int(record["greedy_largest_first"]["reference_excluding_accepted_interfaces"])
        for record in records
    )
    pointwise_dominates = all(
        all(
            int(advantage) <= 0
            for advantage in record[
                "fixed_slab_prefix_advantage_over_pointwise"
            ].values()
        )
        for record in records
    )
    greedy_beats = sum(
        int(record["greedy_prefix_advantage_over_pointwise"] > 0) for record in records
    )
    return {
        "schema_version": 1,
        "status": "PASS-CANARY" if not protocol_failure_codes else "STOP",
        "claim_scope": (
            "strengthened Claim-W killer-baseline canary; fixed-step discrete-MNA "
            "prefix evidence only, not a novelty, full-grid, or rigorous-oracle claim"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": (
            "python3 -m experiments.run_interface_contraction_canary "
            f"--steps {steps}"
        ),
        "config": _CONFIG.relative_to(_PAPER_ROOT).as_posix(),
        "config_sha256": sha256_file(_CONFIG),
        "input_sha256": canonical_sha256(
            {
                "instances": _instances(circuit_filter),
                "steps": steps,
                "slab_lengths": _SLAB_LENGTHS,
                "precision": "float64",
                "tolerance": tolerance,
                "radius_multiplier": radius_multiplier,
            }
        ),
        "source_files_sha256": source_file_hashes(_PAPER_ROOT, _SOURCE_FILES),
        "backend_sha256": backend_sha256,
        "semantics_sha256": semantics_sha256,
        "backend": asdict(info),
        "random_seeds": {},
        "randomness_used": False,
        "test_reference": config["test_reference"],
        "reference_audit": {
            "confirmed_false_accepts": None,
            "reason": "the Decimal-160 test reference is not a rigorous oracle",
            "reference_excluding_accepted_interfaces": reference_exclusions,
        },
        "attempted_traces": len(_instances(circuit_filter)),
        "completed_traces": sum(record["trace_complete"] is True for record in records),
        "protocol_complete": workload_complete,
        "success_only_filtering": False,
        "slab_lengths": list(_SLAB_LENGTHS),
        "contractive_pointwise_dominates_or_ties_all_fixed_slabs": (
            pointwise_dominates
        ),
        "contractive_pointwise_improves_legacy_instances": sum(
            int(record["pointwise_prefix_gain_over_legacy"] > 0) for record in records
        ),
        "greedy_beats_contractive_pointwise_instances": greedy_beats,
        "claim_w_killer_baseline": {
            "criterion_applicable": criterion_applicable,
            "passing_slab_lengths": passing_lengths,
            "slab_win_counts_by_workload": nontrivial_counts,
            "status": (
                "PASS"
                if passing_lengths
                else (
                    "KILLER-BASELINE-CANARY-FAIL"
                    if criterion_applicable
                    else "REDUCED-TEST-ONLY"
                )
            ),
        },
        "adaptive_partition_canary": {
            "method": "largest-first slab selection with pointwise backoff",
            "status": "NO-PREFIX-GAIN" if greedy_beats == 0 else "ITERATE",
            "instances_beating_contractive_pointwise": greedy_beats,
        },
        "algorithmic_novelty": "NOT-ESTABLISHED",
        "failure_codes": protocol_failure_codes,
        "first_failure": (
            None
            if not protocol_failure_codes
            else next(
                record for record in records if record["trace_complete"] is not True
            )
        ),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--circuit-filter", choices=("diode_rc", "nmos_ring_3stage"))
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = run_interface_contraction_canary(
        steps=arguments.steps, circuit_filter=arguments.circuit_filter
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    summary = {key: value for key, value in result.items() if key != "records"}
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    if result["status"] == "STOP":
        sys.exit(1)


if __name__ == "__main__":
    main()
