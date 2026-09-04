"""Run the four-method matched BlockStamp component ladder."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.benchmark import (
    METHODS,
    RESULT_COLUMNS,
    build_shared_hashes,
    measure_method,
    result_row,
)
from experiments.mna import (
    DIODE_RC_INSTANCES,
    RING_INSTANCES,
    Circuit,
    diode_rc_circuit,
    diode_rc_state,
    nmos_ring_3stage,
    ring_initial_state,
)
from experiments.producers import ProducerPrecision, produce_trace
from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    sha256_file,
    source_file_hashes,
)

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _PAPER_ROOT / "configs/blockstamp/minimal_probe.yaml"
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/component_ladder.csv"
_DEFAULT_FAIRNESS = _PAPER_ROOT / "results/blockstamp/b2_fairness.json"
_BACKEND = _PAPER_ROOT / "experiments/rigorous_backend.py"
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
    _PAPER_ROOT / "experiments/producers/trace.py",
    *_SEMANTICS_FILES,
)
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


def _workloads(
    circuit_filter: str,
) -> tuple[tuple[str, str, Circuit, tuple[float, ...], float], ...]:
    workloads: list[tuple[str, str, Circuit, tuple[float, ...], float]] = []
    if circuit_filter in {"all", "diode_rc"}:
        for instance in DIODE_RC_INSTANCES:
            workloads.append(
                (
                    "diode_rc",
                    instance.name,
                    diode_rc_circuit(instance),
                    diode_rc_state(instance.initial_voltage, instance),
                    instance.step_size,
                )
            )
    if circuit_filter in {"all", "nmos_ring_3stage"}:
        for instance in RING_INSTANCES:
            workloads.append(
                (
                    "nmos_ring_3stage",
                    instance.name,
                    nmos_ring_3stage(instance),
                    ring_initial_state(instance),
                    instance.step_size,
                )
            )
    if not workloads:
        raise ValueError(f"unknown circuit filter: {circuit_filter}")
    return tuple(workloads)


def _shared_hashes_match(rows: list[dict[str, object]]) -> bool:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (
            row["circuit_id"],
            row["instance_id"],
            row["producer_precision"],
            row["producer_tolerance"],
            row["step_size"],
            row["steps"],
            row["slab_length"],
            row["replicate"],
        )
        grouped[key].append(row)
    return all(
        len(records) == len(METHODS)
        and all(
            len({str(record[column]) for record in records}) == 1
            for column in _SHARED_HASH_COLUMNS
        )
        for records in grouped.values()
    )


def _named_workload(
    circuit_id: str, instance_name: str
) -> tuple[str, str, Circuit, tuple[float, ...], float]:
    matches = tuple(
        workload for workload in _workloads(circuit_id) if workload[1] == instance_name
    )
    if len(matches) != 1:
        available = ", ".join(workload[1] for workload in _workloads(circuit_id))
        raise ValueError(
            f"unknown instance {instance_name!r} for {circuit_id}; "
            f"available: {available}"
        )
    return matches[0]


def run_component_configuration(
    *,
    circuit_id: str,
    instance_name: str,
    steps: int,
    slab_length: int,
    replicate: int,
    method: str,
) -> dict[str, object]:
    """Run exactly one component-ladder configuration without filtering its result."""

    if steps <= 0:
        raise ValueError("steps must be positive")
    if slab_length <= 0:
        raise ValueError("slab length must be positive")
    if replicate < 0:
        raise ValueError("replicate must be nonnegative")
    if method not in METHODS:
        raise ValueError(f"unsupported component method: {method}")

    config = _load_config()
    tolerance = float(config["producer"]["ring_tolerance_by_precision"]["float64"])
    radius_multiplier = float(config["ring_canary"]["radius_multiplier"])
    (
        selected_circuit_id,
        selected_instance_name,
        circuit,
        initial_state,
        step_size,
    ) = _named_workload(circuit_id, instance_name)
    trace = produce_trace(
        selected_circuit_id,
        selected_instance_name,
        ProducerPrecision.FLOAT64,
        tolerance,
        steps,
        step_size,
        radius_multiplier,
    )
    backend_sha256 = sha256_file(_BACKEND)
    semantics_sha256 = canonical_sha256(
        {path.name: sha256_file(path) for path in _SEMANTICS_FILES}
    )
    shared = build_shared_hashes(
        trace,
        backend_sha256=backend_sha256,
        semantics_sha256=semantics_sha256,
    )
    measurements = measure_method(trace, circuit, initial_state, method, slab_length)
    row = result_row(
        trace,
        measurements,
        shared,
        method=method,
        slab_length=slab_length,
        replicate=replicate,
    )
    return {
        "schema_version": 1,
        "status": "COMPLETE",
        "stage": "COMPONENT-LADDER-CONFIGURATION",
        "queue": "component-ladder-v1",
        "queue_key": {
            "circuit_id": selected_circuit_id,
            "instance_id": selected_instance_name,
            "producer_precision": ProducerPrecision.FLOAT64.value,
            "producer_tolerance": tolerance,
            "radius_multiplier": radius_multiplier,
            "steps": steps,
            "slab_length": slab_length,
            "replicate": replicate,
            "method": method,
        },
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "config_sha256": sha256_file(_CONFIG),
        "source_files_sha256": source_file_hashes(_PAPER_ROOT, _SOURCE_FILES),
        "backend_sha256": backend_sha256,
        "semantics_sha256": semantics_sha256,
        "producer_records": len(trace.records),
        "producer_steps_requested": trace.steps_requested,
        "producer_trace_complete": len(trace.records) == trace.steps_requested,
        "producer_failure_code": trace.failure_code,
        "success_only_filtering": False,
        "row": row,
        "command": (
            "python3 -m experiments.run_component_ladder "
            f"--circuit {selected_circuit_id} --steps {steps} "
            f"--single-instance {selected_instance_name} "
            f"--single-method {method} --single-slab-length {slab_length} "
            f"--single-replicate {replicate}"
        ),
    }


def write_component_checkpoint(output: Path, payload: dict[str, object]) -> None:
    """Write one completed queue item without permitting accidental replacement."""

    if output.exists():
        raise FileExistsError(f"component checkpoint already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_component_ladder(
    *,
    steps: int,
    slab_lengths: tuple[int, ...],
    replicates: int,
    circuit_filter: str = "all",
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    """Return rows, component manifest, and B2 fairness evidence."""

    if steps <= 0 or replicates <= 0:
        raise ValueError("steps and replicates must be positive")
    if not slab_lengths or any(length <= 0 for length in slab_lengths):
        raise ValueError("slab lengths must be nonempty and positive")
    config = _load_config()
    tolerance = float(config["producer"]["ring_tolerance_by_precision"]["float64"])
    radius_multiplier = float(config["ring_canary"]["radius_multiplier"])
    backend_sha256 = sha256_file(_BACKEND)
    semantics_sha256 = canonical_sha256(
        {path.name: sha256_file(path) for path in _SEMANTICS_FILES}
    )
    rows: list[dict[str, object]] = []
    trace_hashes: dict[str, str] = {}
    for circuit_id, instance_name, circuit, initial_state, step_size in _workloads(
        circuit_filter
    ):
        trace = produce_trace(
            circuit_id,
            instance_name,
            ProducerPrecision.FLOAT64,
            tolerance,
            steps,
            step_size,
            radius_multiplier,
        )
        shared = build_shared_hashes(
            trace,
            backend_sha256=backend_sha256,
            semantics_sha256=semantics_sha256,
        )
        trace_hashes[f"{circuit_id}/{instance_name}"] = shared.producer_trace_sha256
        for slab_length in slab_lengths:
            for replicate in range(replicates):
                for method in METHODS:
                    measurements = measure_method(
                        trace, circuit, initial_state, method, slab_length
                    )
                    rows.append(
                        result_row(
                            trace,
                            measurements,
                            shared,
                            method=method,
                            slab_length=slab_length,
                            replicate=replicate,
                        )
                    )

    expected_rows = (
        len(_workloads(circuit_filter)) * len(slab_lengths) * replicates * len(METHODS)
    )
    coverage_complete = len(rows) == expected_rows
    hashes_present = all(
        all(str(row.get(column, "")) for column in _SHARED_HASH_COLUMNS) for row in rows
    )
    hashes_match = _shared_hashes_match(rows)
    false_accepts = sum(bool(row["confirmed_false_accept"]) for row in rows)
    source_hashes = source_file_hashes(_PAPER_ROOT, _SOURCE_FILES)
    common = {
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "config_sha256": sha256_file(_CONFIG),
        "source_files_sha256": source_hashes,
        "backend_sha256": backend_sha256,
        "semantics_sha256": semantics_sha256,
        "trace_sha256": trace_hashes,
    }
    component_status = (
        "PASS" if coverage_complete and hashes_match and false_accepts == 0 else "STOP"
    )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "status": component_status,
        "claim_scope": (
            "four-method component-matched implementation probe; timings are "
            "same-process canary observations"
        ),
        **common,
        "command": (
            "python3 -m experiments.run_component_ladder "
            f"--steps {steps} --slab-lengths "
            + " ".join(str(value) for value in slab_lengths)
            + f" --replicates {replicates} --circuit {circuit_filter}"
        ),
        "row_count": len(rows),
        "expected_row_count": expected_rows,
        "coverage_complete": coverage_complete,
        "methods": list(METHODS),
        "slab_lengths": list(slab_lengths),
        "replicates": replicates,
        "success_only_filtering": False,
        "verdict_counts": {
            verdict: sum(row["checker_verdict"] == verdict for row in rows)
            for verdict in ("ACCEPT", "UNKNOWN", "UNSUPPORTED")
        },
        "confirmed_false_accepts": false_accepts,
        "all_required_hashes_present": hashes_present,
        "all_shared_hashes_match": hashes_match,
        "rss_measurement_scope": "same-process high-water mark; not causal RSS",
        "timing_scope": "same-process canary; M2 requires independent processes",
        "streamed_remainder_scope": (
            "streams globally assembled Jacobian rows; direct device-stamp remainder "
            "is not yet implemented"
        ),
    }
    b2_rows = [row for row in rows if row["method"] == "device_local_pointwise_b2"]
    fairness_status = (
        "PASS"
        if component_status == "PASS" and hashes_present and hashes_match
        else "ITERATE"
    )
    fairness: dict[str, object] = {
        "schema_version": 2,
        "status": fairness_status,
        "stage": "B2-STRONG-COMPONENT-MATCHED",
        "strong_baseline_status": "IMPLEMENTED",
        "strong_baseline_kernel": (
            "sparse-row outward-rounded interval Gaussian elimination with verified "
            "partial pivots and no dropping"
        ),
        "strong_baseline_scope": (
            "auditable correctness-oriented verified-sparse kernel; not an optimized "
            "third-party sparse package"
        ),
        **common,
        "input_sha256": canonical_sha256(trace_hashes),
        "attempted_cases": len(b2_rows),
        "supported_cases": sum(
            row["checker_verdict"] != "UNSUPPORTED" for row in b2_rows
        ),
        "unsupported_cases": sum(
            row["checker_verdict"] == "UNSUPPORTED" for row in b2_rows
        ),
        "failure_codes": sorted(
            {str(row["failure_code"]) for row in b2_rows if row["failure_code"]}
        ),
        "all_required_hashes_present": hashes_present,
        "all_shared_hashes_match": hashes_match,
        "required_shared_hashes": list(_SHARED_HASH_COLUMNS),
        "allowed_method_differences": [
            "verification organization",
            "dense versus verified-sparse factor storage",
            "materialized versus streamed remainder traversal",
        ],
        "easy_case_accepts": sum(
            int(row["certified_prefix_steps"])
            for row in b2_rows
            if row["checker_verdict"] == "ACCEPT"
        ),
        "known_bad_cases": 17,
        "confirmed_false_accepts": false_accepts,
        "component_ladder_status": component_status,
        "missing_for_b2_strong": [],
    }
    return rows, manifest, fairness


def write_component_ladder(
    output: Path,
    manifest_output: Path,
    fairness_output: Path,
    rows: list[dict[str, object]],
    manifest: dict[str, object],
    fairness: dict[str, object],
) -> None:
    """Write schema-stable CSV and JSON evidence artifacts."""

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
    fairness_output.write_text(
        json.dumps(fairness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--slab-lengths", type=int, nargs="+", default=(1, 2, 4, 8, 16))
    parser.add_argument("--replicates", type=int, default=1)
    parser.add_argument(
        "--circuit",
        choices=("all", "diode_rc", "nmos_ring_3stage"),
        default="all",
    )
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--fairness-output", type=Path, default=_DEFAULT_FAIRNESS)
    parser.add_argument("--single-instance")
    parser.add_argument("--single-method", choices=METHODS)
    parser.add_argument("--single-slab-length", type=int)
    parser.add_argument("--single-replicate", type=int, default=0)
    parser.add_argument("--checkpoint-output", type=Path)
    arguments = parser.parse_args()
    single_arguments = (
        arguments.single_instance,
        arguments.single_method,
        arguments.single_slab_length,
        arguments.checkpoint_output,
    )
    if any(value is not None for value in single_arguments):
        if any(value is None for value in single_arguments):
            parser.error(
                "single-configuration mode requires --single-instance, "
                "--single-method, --single-slab-length, and --checkpoint-output"
            )
        if arguments.circuit == "all":
            parser.error("single-configuration mode requires one explicit --circuit")
        if arguments.checkpoint_output.exists():
            parser.error(
                f"checkpoint already exists; refusing to rerun: "
                f"{arguments.checkpoint_output}"
            )
        payload = run_component_configuration(
            circuit_id=arguments.circuit,
            instance_name=arguments.single_instance,
            steps=arguments.steps,
            slab_length=arguments.single_slab_length,
            replicate=arguments.single_replicate,
            method=arguments.single_method,
        )
        payload["command"] = (
            f"{payload['command']} --checkpoint-output {arguments.checkpoint_output}"
        )
        write_component_checkpoint(arguments.checkpoint_output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    manifest_output = arguments.manifest_output or arguments.output.with_suffix(
        ".manifest.json"
    )
    rows, manifest, fairness = run_component_ladder(
        steps=arguments.steps,
        slab_lengths=tuple(arguments.slab_lengths),
        replicates=arguments.replicates,
        circuit_filter=arguments.circuit,
    )
    write_component_ladder(
        arguments.output,
        manifest_output,
        arguments.fairness_output,
        rows,
        manifest,
        fairness,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if manifest["status"] != "PASS" or fairness["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
