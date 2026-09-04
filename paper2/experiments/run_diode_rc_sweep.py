"""Run the unfiltered diode-RC tolerance × precision × tube-radius sweep."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from experiments.checkers import CheckerVerdict
from experiments.mna import DIODE_RC_INSTANCES
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
_DEFAULT_OUTPUT = _PAPER_ROOT / "results/blockstamp/diode_rc_producer_sweep.csv"
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


def _format_float(value: float | None) -> str:
    return "" if value is None else f"{value:.17g}"


def _trace_row(
    trace: TraceResult, reference_generation_seconds: float
) -> dict[str, str]:
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
    errors = [
        record.reference_error_inf
        for record in records
        if record.reference_error_inf is not None
    ]
    margins = [
        record.checker_inclusion_margin
        for record in records
        if record.checker_inclusion_margin is not None
    ]
    radii = [
        radius
        for record in records
        if record.radii is not None
        for radius in record.radii
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
    producer_seconds = sum(record.generation_seconds for record in records)
    tube_seconds = sum(record.tube_seconds for record in records)
    checker_seconds = sum(record.check_seconds for record in records)
    return {
        "schema_version": "1",
        "circuit_id": trace.circuit_id,
        "instance": trace.instance_name,
        "producer_precision": trace.precision.value,
        "producer_tolerance": _format_float(trace.tolerance),
        "radius_multiplier": _format_float(trace.radius_multiplier),
        "tube_rule": "residual-local-inverse-jacobian-frozen-radius-v1",
        "step_size": _format_float(trace.step_size),
        "steps_requested": str(trace.steps_requested),
        "steps_completed": str(len(records)),
        "producer_converged_steps": str(
            sum(record.producer_converged for record in records)
        ),
        "producer_failed_steps": str(
            sum(not record.producer_converged for record in records)
        ),
        "producer_total_iterations": str(
            sum(record.producer_iterations for record in records)
        ),
        "maximum_scaled_residual": _format_float(
            max(
                (record.producer_scaled_residual_inf for record in records),
                default=None,
            )
        ),
        "maximum_reference_error_inf": _format_float(max(errors, default=None)),
        "final_reference_error_inf": _format_float(errors[-1] if errors else None),
        "test_reference": trace.test_reference_method,
        "test_reference_in_tube_steps": str(
            sum(record.reference_in_tube is True for record in records)
        ),
        "eligible_reference_excluding_accepts": str(
            eligible_reference_excluding_accepts
        ),
        "detached_reference_accepts": str(detached_reference_accepts),
        "checker_accept": str(accepted),
        "checker_unknown": str(unknown),
        "checker_unsupported": str(unsupported),
        "certified_reference_containing_prefix": str(prefix),
        "acceptance_rate": _format_float(accepted / len(records) if records else 0.0),
        "minimum_inclusion_margin": _format_float(min(margins, default=None)),
        "maximum_tube_radius": _format_float(max(radii, default=None)),
        "producer_seconds": _format_float(producer_seconds),
        "tube_seconds": _format_float(tube_seconds),
        "checker_seconds": _format_float(checker_seconds),
        "reference_generation_seconds": _format_float(reference_generation_seconds),
        "end_to_end_seconds": _format_float(
            producer_seconds
            + tube_seconds
            + checker_seconds
            + reference_generation_seconds
        ),
        "trace_failure_code": trace.failure_code or "",
    }


def generate_sweep(
    config_path: Path = _DEFAULT_CONFIG,
    *,
    steps_override: int | None = None,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Execute the complete predeclared sweep without success filtering."""

    info = backend_info()
    if info is None:
        raise RuntimeError("the MPFR checker backend is unavailable")
    config = load_minimal_probe_config(config_path)
    sweep = config["diode_rc_sweep"]
    producer = config["producer"]
    steps = int(sweep["steps"] if steps_override is None else steps_override)
    if steps <= 0:
        raise ValueError("sweep steps must be positive")
    rows: list[dict[str, str]] = []
    for instance in DIODE_RC_INSTANCES:
        started = time.perf_counter()
        reference = build_test_reference(
            "diode_rc", instance.name, steps, instance.step_size
        )
        reference_seconds = time.perf_counter() - started
        for precision_value in producer["precisions"]:
            precision = ProducerPrecision(precision_value)
            for tolerance in sweep["tolerances"]:
                for radius_multiplier in sweep["radius_multipliers"]:
                    trace = produce_trace(
                        "diode_rc",
                        instance.name,
                        precision,
                        float(tolerance),
                        steps,
                        instance.step_size,
                        float(radius_multiplier),
                        test_reference=reference,
                    )
                    rows.append(_trace_row(trace, reference_seconds))
    expected_rows = (
        len(DIODE_RC_INSTANCES)
        * len(producer["precisions"])
        * len(sweep["tolerances"])
        * len(sweep["radius_multipliers"])
    )
    failure_codes: list[str] = []
    if len(rows) != expected_rows:
        failure_codes.append("INCOMPLETE_GRID")
    eligible_reference_excluding_accepts = sum(
        int(row["eligible_reference_excluding_accepts"]) for row in rows
    )
    detached_reference_accepts = sum(
        int(row["detached_reference_accepts"]) for row in rows
    )
    if eligible_reference_excluding_accepts:
        failure_codes.append("REFERENCE_EXCLUDING_ACCEPT")
    incomplete_traces = sum(
        row["steps_completed"] != row["steps_requested"] for row in rows
    )
    if incomplete_traces:
        failure_codes.append("INCOMPLETE_TRACE")
    sources = source_file_hashes(_PAPER_ROOT, _PROVENANCE_FILES)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "status": "PASS-CANARY" if not failure_codes else "STOP",
        "claim_scope": (
            "unfiltered producer certification-boundary sweep; Decimal reference is "
            "post-hoc and non-rigorous; no performance or industrial-SPICE claim"
        ),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": "python3 -m experiments.run_diode_rc_sweep",
        "config": config_path.relative_to(_PAPER_ROOT).as_posix(),
        "config_sha256": sha256_file(config_path),
        "input_sha256": canonical_sha256(
            {
                "instances": sweep["instances"],
                "steps": steps,
                "precisions": producer["precisions"],
                "tolerances": sweep["tolerances"],
                "radius_multipliers": sweep["radius_multipliers"],
            }
        ),
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
        "expected_rows": expected_rows,
        "row_count": len(rows),
        "incomplete_traces": incomplete_traces,
        "checker_accept": sum(int(row["checker_accept"]) for row in rows),
        "checker_unknown": sum(int(row["checker_unknown"]) for row in rows),
        "checker_unsupported": sum(int(row["checker_unsupported"]) for row in rows),
        "eligible_reference_excluding_accepts": (eligible_reference_excluding_accepts),
        "detached_reference_accepts": detached_reference_accepts,
        "grid_has_accept_region": any(int(row["checker_accept"]) > 0 for row in rows),
        "grid_has_unknown_region": any(int(row["checker_unknown"]) > 0 for row in rows),
        "failure_codes": failure_codes,
        "first_failure": next(
            (
                {
                    "instance": row["instance"],
                    "precision": row["producer_precision"],
                    "tolerance": row["producer_tolerance"],
                    "radius_multiplier": row["radius_multiplier"],
                    "failure_code": row["trace_failure_code"],
                }
                for row in rows
                if row["trace_failure_code"]
            ),
            None,
        ),
    }
    return rows, manifest


def write_sweep(
    output: Path,
    manifest_output: Path,
    config_path: Path = _DEFAULT_CONFIG,
    *,
    steps_override: int | None = None,
) -> dict[str, object]:
    """Write the sweep CSV and its provenance manifest."""

    rows, manifest = generate_sweep(config_path, steps_override=steps_override)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest["artifact"] = output.name
    manifest["csv_sha256"] = sha256_file(output)
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--steps", type=int, help="optional positive replay override")
    arguments = parser.parse_args()
    manifest_output = arguments.manifest_output or arguments.output.with_suffix(
        ".manifest.json"
    )
    manifest = write_sweep(
        arguments.output,
        manifest_output,
        arguments.config,
        steps_override=arguments.steps,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if manifest["status"] == "STOP":
        sys.exit(1)


if __name__ == "__main__":
    main()
