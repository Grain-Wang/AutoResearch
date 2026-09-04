import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from experiments.benchmark import RESULT_COLUMNS
from experiments.checkers import CheckerVerdict
from experiments.interval_backend import Interval
from experiments.producers import ProducerPrecision, TraceResult, TraceStep
from experiments.producers.tube import TubeRule
from experiments.run_minimal_probe import (
    _ALL_METHODS,
    _DEFAULT_CHECKPOINT_DIR,
    _FROZEN_SLAB_LENGTHS,
    _FROZEN_STEPS,
    _apply_fallback_costs,
    _checkpoint_path,
    _execution_contract,
    _fallback_report,
    _frozen_request_errors,
    _integrity_report,
    _queue_key,
    _read_checkpoint,
    _specs,
    _strict_trace,
    _write_checkpoint_atomic,
)


def _row(spec: dict[str, Any], run_id: str) -> dict[str, object]:
    row: dict[str, object] = {name: "" for name in RESULT_COLUMNS}
    row.update(
        {
            "run_id": run_id,
            "circuit_id": spec["circuit_id"],
            "instance_id": spec["instance"],
            "producer_id": "test-producer",
            "producer_precision": spec["precision"],
            "producer_tolerance": spec["tolerance"],
            "step_size": spec["step_size"],
            "steps": spec["steps"],
            "slab_length": spec["slab_length"],
            "replicate": spec["replicate"],
            "method": spec["method"],
            "input_sha256": "input",
            "producer_trace_sha256": "trace",
            "candidate_sha256": "candidate",
            "tube_sha256": "tube",
            "backend_sha256": spec["backend_sha256"],
            "semantics_sha256": spec["semantics_sha256"],
            "scaling_sha256": "scaling",
            "ordering_sha256": "ordering",
            "factor_sha256": "factor",
            "threads": 1,
            "hardware_id": "hardware",
            "checker_verdict": "UNKNOWN",
            "failure_code": "STRICT_INCLUSION_FAILED",
            "oracle_root_in_tube": True,
            "confirmed_false_accept": False,
            "certification_rate": 0.0,
            "certified_prefix_steps": 0,
            "tube_max_relative_width": 1.0e-12,
            "tube_growth_rate": 1.0,
            "inclusion_margin_min": -1.0e-12,
            "assembly_seconds": 0.1,
            "verified_solve_seconds": 0.1,
            "operator_propagation_seconds": 0.1,
            "certificate_generation_seconds": 0.1,
            "check_seconds": 0.2,
            "fallback_seconds": 0.0,
            "end_to_end_seconds": 0.3,
            "peak_rss_bytes": 1024,
            "certificate_bytes": 100,
            "raw_trajectory_bytes": 50,
        }
    )
    return row


def _envelope(
    spec: dict[str, Any], contract: dict[str, object], run_id: str
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "COMPLETE",
        "stage": "M2-FROZEN-CONFIGURATION",
        "queue": "minimal-probe-m2-v1",
        "queue_kind": spec["_queue_kind"],
        "queue_index": spec["_queue_index"],
        "queue_key": _queue_key(spec),
        **contract,
        "producer_completion": {
            "records": spec["steps"],
            "steps_requested": spec["steps"],
            "trace_complete": True,
            "tube_records": spec["steps"],
            "tube_complete": True,
            "converged_records": spec["steps"],
            "all_records_converged": True,
            "failure_code": None,
        },
        "certificate_trace_records": spec["steps"],
        "certificate_trace_complete": True,
        "success_only_filtering": False,
        "row": _row(spec, run_id),
    }


def test_frozen_request_is_exact_not_set_or_lower_bound() -> None:
    valid = {
        "steps_grid": _FROZEN_STEPS,
        "slab_lengths": _FROZEN_SLAB_LENGTHS,
        "replicates": 5,
        "workers": 1,
        "run_warmups": True,
    }
    assert _frozen_request_errors(**valid) == []
    for change in (
        {"steps_grid": (300, 100, 1000)},
        {"slab_lengths": (1, 2, 4, 8, 16, 16)},
        {"replicates": 6},
        {"workers": 4},
        {"run_warmups": False},
    ):
        request = {**valid, **change}
        assert _frozen_request_errors(**request)


def test_checkpoint_round_trip_is_atomic_and_fail_closed(tmp_path: Path) -> None:
    contract = _execution_contract()
    warmups, _ = _specs(
        steps_grid=_FROZEN_STEPS,
        slab_lengths=_FROZEN_SLAB_LENGTHS,
        replicates=5,
        contract=contract,
    )
    spec = warmups[0]
    path = _checkpoint_path(tmp_path, spec)
    payload = _envelope(spec, contract, "warmup-0")
    written = _write_checkpoint_atomic(path, payload, spec, contract)
    assert written["queue_key"] == _queue_key(spec)
    assert _read_checkpoint(path, spec, contract)["status"] == "COMPLETE"
    with pytest.raises(FileExistsError):
        _write_checkpoint_atomic(path, payload, spec, contract)
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="corrupt M2 checkpoint"):
        _read_checkpoint(path, spec, contract)


def test_exact_matrix_integrity_rejects_missing_or_duplicate_rows() -> None:
    contract = _execution_contract()
    warmups, specs = _specs(
        steps_grid=_FROZEN_STEPS,
        slab_lengths=_FROZEN_SLAB_LENGTHS,
        replicates=5,
        contract=contract,
    )
    rows = [_row(spec, f"run-{index}") for index, spec in enumerate(specs)]
    envelopes = [
        _envelope(spec, contract, f"warmup-{index}")
        for index, spec in enumerate(warmups)
    ] + [_envelope(spec, contract, f"run-{index}") for index, spec in enumerate(specs)]
    report = _integrity_report(rows, specs, warmups, envelopes, contract)
    assert report["all_pass"] is True
    assert report["missing_rows"] == 0
    assert report["duplicate_rows"] == 0
    broken = rows[:-1] + [dict(rows[0])]
    report = _integrity_report(broken, specs, warmups, envelopes, contract)
    assert report["all_pass"] is False
    assert report["missing_rows"] == 1
    assert report["duplicate_rows"] == 1


def test_fallback_uses_unique_matched_strict_cost() -> None:
    contract = _execution_contract()
    _, specs = _specs(
        steps_grid=_FROZEN_STEPS,
        slab_lengths=_FROZEN_SLAB_LENGTHS,
        replicates=5,
        contract=contract,
    )
    primary_spec = specs[0]
    strict_spec = next(
        spec
        for spec in specs
        if spec["circuit_id"] == primary_spec["circuit_id"]
        and spec["instance"] == primary_spec["instance"]
        and spec["steps"] == primary_spec["steps"]
        and spec["slab_length"] == primary_spec["slab_length"]
        and spec["replicate"] == primary_spec["replicate"]
        and spec["method"] == "strict_mpfr_rerun"
    )
    primary = _row(primary_spec, "primary")
    strict = _row(strict_spec, "strict")
    strict["checker_verdict"] = "ACCEPT"
    strict["failure_code"] = ""
    strict["end_to_end_seconds"] = 2.0
    rows = [primary, strict]
    _apply_fallback_costs(rows)
    assert primary["fallback_seconds"] == 2.0
    report = _fallback_report(rows)
    assert report["complete_cost_accounting"] is True
    assert report["recovered_accept_rows"] == 1
    assert report["recovery_rate"] == 1.0


def test_strict_trace_uses_typed_trace_step_fields() -> None:
    source_step = TraceStep(
        step_index=0,
        center=(0.5,),
        tube=(Interval(0.4, 0.6),),
        radii=(0.1,),
        producer_converged=True,
        producer_iterations=1,
        producer_raw_residual_inf=0.0,
        producer_scaled_residual_inf=0.0,
        producer_failure_code=None,
        reference=(0.5,),
        reference_error_inf=0.0,
        reference_in_tube=True,
        checker_verdict=CheckerVerdict.UNKNOWN,
        checker_inclusion_margin=None,
        checker_reason=None,
        generation_seconds=0.1,
        tube_seconds=0.1,
        check_seconds=0.0,
        reference_seconds=0.0,
    )
    source = TraceResult(
        circuit_id="synthetic",
        instance_name="one-step",
        precision=ProducerPrecision.FLOAT64,
        tolerance=1.0e-10,
        steps_requested=1,
        step_size=1.0,
        radius_multiplier=4.0,
        tube_rule=TubeRule((0.1,), (1.0,), 4.0),
        test_reference_method="synthetic",
        records=(source_step,),
        failure_code=None,
    )
    strict = _strict_trace(source, ((Decimal("0.5"),),), 0.25)
    record = strict.records[0]
    assert record.reference == (0.5,)
    assert record.reference_in_tube is True
    assert record.checker_verdict is CheckerVerdict.UNKNOWN
    assert record.generation_seconds == 0.25


def test_default_checkpoint_path_is_inside_results_tree() -> None:
    assert _DEFAULT_CHECKPOINT_DIR.name == "minimal_probe_parts"
    assert json.loads('{"ok": true}')["ok"] is True
    assert set(_ALL_METHODS) == {
        "dense_slab_generic",
        "device_local_pointwise_b2",
        "temporal_only",
        "temporal_device_blockstamp",
        "strict_mpfr_rerun",
    }
