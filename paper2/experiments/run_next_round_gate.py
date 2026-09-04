"""Evaluate the machine-checkable M0/M1/M2 evidence state without overclaiming."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    sha256_file,
    source_file_hashes,
)

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_RESULT_ROOT = _PAPER_ROOT / "results/blockstamp"
_DEFAULT_OUTPUT = _RESULT_ROOT / "next_round_gate.json"
_ARITHMETIC = _RESULT_ROOT / "rigorous_backend_summary.json"
_MNA = _RESULT_ROOT / "mna_canary.json"
_OPERATOR = _RESULT_ROOT / "operator_canary.json"
_OPERATOR_STRESS = _RESULT_ROOT / "operator_stress.json"
_FAIRNESS = _RESULT_ROOT / "b2_fairness.json"
_COMPONENT_LADDER = _RESULT_ROOT / "component_ladder.manifest.json"
_MINIMAL_PROBE = _RESULT_ROOT / "minimal_probe.manifest.json"
_INTERFACE_CONTRACTION = _RESULT_ROOT / "interface_contraction_canary.json"
_PRIOR_ART = _PAPER_ROOT / "steps/004_theorem_prior_art_closure.md"
_SOURCE_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "steps/003_formal_soundness_contract.md",
    _PRIOR_ART,
    _PAPER_ROOT / "steps/007_blockstamp_operator_spec.md",
    _PAPER_ROOT / "steps/008_next_round_gate.md",
    _PAPER_ROOT / "steps/009_m2_result_gate.md",
)
_EXPECTED_OPERATIONS = {"add", "sub", "mul", "div", "exp", "expm1", "log", "sqrt"}
_EXPECTED_OPERATOR_GRIDS = {
    (dimension, slabs) for dimension in (1, 2, 4, 8) for slabs in (2, 4, 8)
}
_EXPECTED_STRESS_GRIDS = {
    (dimension, slabs) for dimension in (1, 2, 4, 8) for slabs in (2, 4, 8, 16)
}
_EXPECTED_CONDITION_BUCKETS = {"1e0-1e2", "1e2-1e4", "1e4-1e6", "1e6-1e8"}
_REQUIRED_COMPONENT_METHODS = {
    "dense_slab_generic",
    "device_local_pointwise_b2",
    "temporal_only",
    "temporal_device_blockstamp",
}
_REQUIRED_NEGATIVE_CASES = {
    "root-excluding-tube",
    "state-permutation-mismatch",
    "singular-midpoint-operator",
    "invalid-node-mapping",
    "malformed-state-layout",
    "unsupported-diode-domain-box",
    "mos-region-branch-crossing",
}
_PRIOR_ART_PREFIX = "Prior-art gate: "
_PRIOR_ART_DECISIONS = {"CONTINUE-ALGORITHM", "REFRAME-SYSTEM"}
_PRIOR_ART_REFRAME_CLOSURE_MARKER = "Prior-art reframe closure: COMPLETE"
_MINIMAL_EVIDENCE_CHECKS = {
    "artifact_present",
    "artifact_status_reported",
    "grid_complete",
    "independent_processes",
    "warmups_excluded",
    "five_replicates",
    "both_workloads_complete",
    "unfiltered",
    "fairness_pass",
    "zero_confirmed_false_accepts",
    "complete_cost_accounting",
    "clustered_bootstrap_ci_present",
    "claim_w_reported",
    "claim_e_reported",
    "claim_d_reported_independently",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return payload


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return _load_json(path)


def _integer_at_least(value: object, minimum: int) -> bool:
    try:
        return int(value) >= minimum
    except (TypeError, ValueError, OverflowError):
        return False


def _integer_equals(value: object, expected: int) -> bool:
    try:
        return int(value) == expected
    except (TypeError, ValueError, OverflowError):
        return False


def _integer_values_equal(left: object, right: object) -> bool:
    try:
        return int(left) == int(right)
    except (TypeError, ValueError, OverflowError):
        return False


def _arithmetic_checks(payload: dict[str, Any]) -> dict[str, bool]:
    operations = payload.get("operations", {})
    if not isinstance(operations, dict):
        operations = {}
    return {
        "artifact_pass": payload.get("status") == "PASS",
        "mpfr_256_or_stronger": (
            isinstance(payload.get("backend"), dict)
            and payload["backend"].get("name") == "MPFR"
            and _integer_at_least(payload["backend"].get("precision_bits"), 256)
        ),
        "directed_rounding_declared": payload.get("rounding_modes")
        == {"lower": "RNDD", "upper": "RNDU"},
        "all_operations_present": set(operations) == _EXPECTED_OPERATIONS,
        "random_budget_met": all(
            isinstance(operations.get(name), dict)
            and _integer_at_least(operations[name].get("random_cases"), 50_000)
            for name in _EXPECTED_OPERATIONS
        ),
        "edge_budget_met": all(
            isinstance(operations.get(name), dict)
            and _integer_at_least(operations[name].get("edge_cases"), 7)
            for name in _EXPECTED_OPERATIONS
        ),
        "zero_containment_violations": _integer_equals(
            payload.get("containment_violations"), 0
        ),
    }


def _mna_checks(payload: dict[str, Any]) -> dict[str, bool]:
    circuits = payload.get("circuits", {})
    if not isinstance(circuits, dict):
        circuits = {}
    negative = payload.get("negative_cases", {})
    if not isinstance(negative, dict):
        negative = {}
    records = negative.get("records", [])
    if not isinstance(records, list):
        records = []
    case_ids = {record.get("case_id") for record in records if isinstance(record, dict)}
    circuit_checks = []
    for name in ("rc", "diode_rc"):
        record = circuits.get(name, {})
        if not isinstance(record, dict):
            circuit_checks.append(False)
            continue
        try:
            steps = int(record.get("steps", 0))
        except (TypeError, ValueError, OverflowError):
            steps = 0
        circuit_checks.append(
            steps >= 100
            and _integer_equals(record.get("accepted"), steps)
            and _integer_equals(record.get("root_contained_steps"), steps)
            and _integer_equals(record.get("root_excluded_steps"), 0)
            and _integer_equals(record.get("jacobian_containment_violations"), 0)
            and _integer_equals(record.get("checker_false_accepts"), 0)
        )
    return {
        "artifact_pass": payload.get("status") == "PASS",
        "rc_and_diode_rc_100_steps": all(circuit_checks),
        "required_negative_families_present": _REQUIRED_NEGATIVE_CASES <= case_ids,
        "wrong_history_sweep_present": sum(
            str(case_id).startswith("wrong-history-") for case_id in case_ids
        )
        >= 10,
        "zero_negative_false_accepts": _integer_equals(
            negative.get("false_accepts"), 0
        ),
    }


def _operator_checks(payload: dict[str, Any]) -> dict[str, bool]:
    grids = payload.get("grids", [])
    if not isinstance(grids, list):
        grids = []
    by_key: dict[tuple[int, int], dict[str, Any]] = {}
    for grid in grids:
        if not isinstance(grid, dict):
            continue
        try:
            key = (int(grid.get("block_dimension")), int(grid.get("slab_length")))
        except (TypeError, ValueError, OverflowError):
            continue
        by_key[key] = grid
    required_cells_pass = all(
        key in by_key
        and _integer_at_least(by_key[key].get("attempted_cases"), 200)
        and _integer_at_least(by_key[key].get("supported_cases"), 200)
        and _integer_equals(by_key[key].get("containment_violations"), 0)
        for key in _EXPECTED_OPERATOR_GRIDS
    )
    singular = payload.get("singular_cases", {})
    if not isinstance(singular, dict):
        singular = {}
    return {
        "artifact_pass": payload.get("status") == "PASS",
        "all_12_grid_cells_pass": required_cells_pass,
        "zero_recursive_containment_violations": _integer_equals(
            payload.get("total_recursive_containment_violations"), 0
        ),
        "singular_case_fails_closed": (
            _integer_at_least(singular.get("attempted_cases"), 1)
            and _integer_equals(singular.get("false_supported_count"), 0)
        ),
    }


def _operator_stress_checks(payload: dict[str, Any] | None) -> dict[str, bool]:
    if payload is None:
        return {
            "artifact_present": False,
            "artifact_pass": False,
            "all_16_interval_rhs_cells_pass": False,
            "all_condition_buckets_present": False,
            "difficult_cases_present": False,
            "zero_containment_violations": False,
            "expected_unsupported_fail_closed": False,
        }
    grids = payload.get("grids", [])
    if not isinstance(grids, list):
        grids = []
    by_key: dict[tuple[int, int], dict[str, Any]] = {}
    for grid in grids:
        if not isinstance(grid, dict):
            continue
        try:
            key = (int(grid.get("block_dimension")), int(grid.get("slab_length")))
        except (TypeError, ValueError, OverflowError):
            continue
        by_key[key] = grid

    def bucket_labels(grid: dict[str, Any]) -> set[str]:
        records = grid.get("conditioning_and_pivot_growth_buckets", [])
        if not isinstance(records, list):
            return set()
        return {
            str(record.get("bucket")) for record in records if isinstance(record, dict)
        }

    required_cells_pass = all(
        key in by_key
        and _integer_at_least(by_key[key].get("attempted_cases"), 200)
        and _integer_at_least(by_key[key].get("interval_rhs_cases"), 200)
        and _integer_equals(by_key[key].get("violations"), 0)
        and _integer_equals(by_key[key].get("containment_violation_coordinates"), 0)
        for key in _EXPECTED_STRESS_GRIDS
    )
    condition_buckets_pass = all(
        key in by_key and _EXPECTED_CONDITION_BUCKETS <= bucket_labels(by_key[key])
        for key in _EXPECTED_STRESS_GRIDS
    )
    difficult_cases_present = all(
        key in by_key
        and _integer_at_least(by_key[key].get("strong_subdiagonal_cases"), 1)
        and _integer_at_least(by_key[key].get("nonnormal_global_matrix_cases"), 1)
        and _integer_at_least(by_key[key].get("near_singular_supported_cases"), 1)
        for key in _EXPECTED_STRESS_GRIDS
    )
    expected_unsupported = payload.get("expected_unsupported", {})
    if not isinstance(expected_unsupported, dict):
        expected_unsupported = {}
    attempted_unsupported = expected_unsupported.get("attempted_cases")
    return {
        "artifact_present": True,
        "artifact_pass": payload.get("status") == "PASS",
        "all_16_interval_rhs_cells_pass": required_cells_pass,
        "all_condition_buckets_present": condition_buckets_pass,
        "difficult_cases_present": difficult_cases_present,
        "zero_containment_violations": (
            _integer_equals(payload.get("containment_violations"), 0)
            and _integer_equals(payload.get("containment_violation_coordinates"), 0)
        ),
        "expected_unsupported_fail_closed": (
            _integer_at_least(attempted_unsupported, 32)
            and _integer_equals(expected_unsupported.get("false_OK"), 0)
            and _integer_values_equal(
                expected_unsupported.get("UNKNOWN"), attempted_unsupported
            )
        ),
    }


def _fairness_checks(payload: dict[str, Any]) -> dict[str, bool]:
    return {
        "artifact_pass": payload.get("status") == "PASS",
        "strong_baseline_implemented": payload.get("strong_baseline_status")
        == "IMPLEMENTED",
        "all_required_hashes_present": payload.get("all_required_hashes_present")
        is True,
        "all_shared_hashes_match": payload.get("all_shared_hashes_match") is True,
        "known_bad_cases_present": _integer_at_least(payload.get("known_bad_cases"), 1),
        "zero_confirmed_false_accepts": _integer_equals(
            payload.get("confirmed_false_accepts"), 0
        ),
    }


def _component_ladder_checks(payload: dict[str, Any] | None) -> dict[str, bool]:
    if payload is None:
        return {
            "artifact_present": False,
            "artifact_pass": False,
            "coverage_complete": False,
            "all_methods_present": False,
            "unfiltered": False,
            "all_required_hashes_present": False,
            "all_shared_hashes_match": False,
            "zero_confirmed_false_accepts": False,
        }
    methods = payload.get("methods", [])
    if not isinstance(methods, list):
        methods = []
    return {
        "artifact_present": True,
        "artifact_pass": payload.get("status") == "PASS",
        "coverage_complete": payload.get("coverage_complete") is True,
        "all_methods_present": set(methods) == _REQUIRED_COMPONENT_METHODS,
        "unfiltered": payload.get("success_only_filtering") is False,
        "all_required_hashes_present": payload.get("all_required_hashes_present")
        is True,
        "all_shared_hashes_match": payload.get("all_shared_hashes_match") is True,
        "zero_confirmed_false_accepts": _integer_equals(
            payload.get("confirmed_false_accepts"), 0
        ),
    }


def _claim_status(claims: object, name: str) -> str:
    if not isinstance(claims, dict):
        return "UNVERIFIED"
    value = claims.get(name, claims.get(f"Claim {name}"))
    if isinstance(value, dict):
        value = value.get("status", value.get("decision"))
    if not isinstance(value, str):
        return "UNVERIFIED"
    normalized = value.strip().upper()
    return normalized if normalized in {"PASS", "STOP", "UNVERIFIED"} else "UNVERIFIED"


def _minimal_probe_checks(payload: dict[str, Any] | None) -> dict[str, bool]:
    if payload is None:
        return {
            "artifact_present": False,
            "artifact_status_reported": False,
            "artifact_pass": False,
            "grid_complete": False,
            "independent_processes": False,
            "warmups_excluded": False,
            "five_replicates": False,
            "both_workloads_complete": False,
            "unfiltered": False,
            "fairness_pass": False,
            "zero_confirmed_false_accepts": False,
            "complete_cost_accounting": False,
            "clustered_bootstrap_ci_present": False,
            "claim_w_reported": False,
            "claim_w_pass": False,
            "claim_e_reported": False,
            "claim_e_pass": False,
            "claim_w_or_e_pass": False,
            "claim_d_reported_independently": False,
        }
    claims = payload.get("claims", {})
    claim_w = _claim_status(claims, "W")
    claim_e = _claim_status(claims, "E")
    claim_d = _claim_status(claims, "D")
    complete_cost_accounting = payload.get(
        "complete_cost_accounting", payload.get("cost_accounting_complete")
    )
    stable_signal = payload.get("stable_signal", {})
    clustered_ci = False
    if isinstance(stable_signal, dict):
        clustered_ci = (
            stable_signal.get(
                "clustered_bootstrap_95ci_complete",
                stable_signal.get("clustered_bootstrap_ci_complete"),
            )
            is True
        )
    workloads_complete = payload.get("workloads_complete")
    if isinstance(workloads_complete, dict):
        both_workloads_complete = all(
            workloads_complete.get(name) is True
            for name in ("diode_rc", "nmos_ring_3stage")
        )
    else:
        both_workloads_complete = workloads_complete is True
    return {
        "artifact_present": True,
        "artifact_status_reported": payload.get("status") in {"PASS", "STOP"},
        "artifact_pass": payload.get("status") == "PASS",
        "grid_complete": payload.get("grid_complete") is True,
        "independent_processes": payload.get("independent_processes") is True,
        "warmups_excluded": payload.get("warmups_excluded") is True,
        "five_replicates": _integer_at_least(payload.get("replicates"), 5),
        "both_workloads_complete": both_workloads_complete,
        "unfiltered": payload.get("success_only_filtering") is False,
        "fairness_pass": payload.get("fairness_pass") is True,
        "zero_confirmed_false_accepts": _integer_equals(
            payload.get("confirmed_false_accepts"), 0
        ),
        "complete_cost_accounting": complete_cost_accounting is True,
        "clustered_bootstrap_ci_present": clustered_ci,
        "claim_w_reported": claim_w in {"PASS", "STOP"},
        "claim_w_pass": claim_w == "PASS",
        "claim_e_reported": claim_e in {"PASS", "STOP"},
        "claim_e_pass": claim_e == "PASS",
        "claim_w_or_e_pass": "PASS" in {claim_w, claim_e},
        "claim_d_reported_independently": claim_d in {"PASS", "STOP"},
    }


def _interface_contraction_checks(
    payload: dict[str, Any] | None,
) -> dict[str, bool]:
    if payload is None:
        return {
            "artifact_present": False,
            "artifact_pass_canary": False,
            "protocol_complete": False,
            "six_registered_traces": False,
            "unfiltered": False,
            "claim_w_result_reported": False,
            "algorithm_novelty_reported": False,
        }
    claim_w = payload.get("claim_w_killer_baseline", {})
    if not isinstance(claim_w, dict):
        claim_w = {}
    return {
        "artifact_present": True,
        "artifact_pass_canary": payload.get("status") in {"PASS-CANARY", "PASS"},
        "protocol_complete": payload.get("protocol_complete") is True,
        "six_registered_traces": (
            _integer_equals(payload.get("attempted_traces"), 6)
            and _integer_equals(payload.get("completed_traces"), 6)
        ),
        "unfiltered": payload.get("success_only_filtering") is False,
        "claim_w_result_reported": claim_w.get("status")
        in {"PASS", "KILLER-BASELINE-CANARY-FAIL"},
        "algorithm_novelty_reported": payload.get("algorithmic_novelty")
        in {"ESTABLISHED", "NOT-ESTABLISHED"},
    }


def _interface_claim_w_status(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return "NOT-RUN"
    claim = payload.get("claim_w_killer_baseline", {})
    if not isinstance(claim, dict) or not isinstance(claim.get("status"), str):
        return "UNVERIFIED"
    return str(claim["status"])


def _prior_art_decision(document: str | None) -> str:
    if document is None:
        return "UNRESOLVED"
    direct = document.strip()
    if direct in _PRIOR_ART_DECISIONS:
        return direct
    decisions = {
        line.strip().removeprefix(_PRIOR_ART_PREFIX)
        for line in document.splitlines()
        if line.strip().startswith(_PRIOR_ART_PREFIX)
    }
    if len(decisions) != 1:
        return "UNRESOLVED"
    decision = decisions.pop()
    return decision if decision in _PRIOR_ART_DECISIONS else "UNRESOLVED"


def _prior_art_reframe_complete(document: str | None) -> bool:
    """Return whether the exact system-reframe action marker is present."""

    if document is None:
        return False
    return any(
        line.strip() == _PRIOR_ART_REFRAME_CLOSURE_MARKER
        for line in document.splitlines()
    )


def _all(checks: dict[str, bool]) -> bool:
    return all(checks.values())


def evaluate_gate(
    arithmetic: dict[str, Any],
    mna: dict[str, Any],
    operator: dict[str, Any],
    fairness: dict[str, Any],
    operator_stress: dict[str, Any] | None = None,
    component_ladder: dict[str, Any] | None = None,
    minimal_probe: dict[str, Any] | None = None,
    prior_art: str | None = None,
    interface_contraction: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Return evidence-derived claim decisions.

    The first four parameters preserve the original public call. New evidence is
    optional so an older checkout fails closed as ``NOT-STARTED`` instead of raising.
    """

    arithmetic_checks = _arithmetic_checks(arithmetic)
    mna_checks = _mna_checks(mna)
    operator_checks = _operator_checks(operator)
    stress_checks = _operator_stress_checks(operator_stress)
    fairness_checks = _fairness_checks(fairness)
    component_checks = _component_ladder_checks(component_ladder)
    minimal_checks = _minimal_probe_checks(minimal_probe)
    interface_checks = _interface_contraction_checks(interface_contraction)
    interface_claim_w_status = _interface_claim_w_status(interface_contraction)
    prior_art_decision = _prior_art_decision(prior_art)
    prior_art_reframe_complete = _prior_art_reframe_complete(prior_art)

    arithmetic_pass = _all(arithmetic_checks)
    mna_pass = _all(mna_checks)
    operator_pass = _all(operator_checks)
    stress_pass = _all(stress_checks)
    fairness_pass = _all(fairness_checks)
    component_pass = _all(component_checks)
    interface_canary_complete = _all(interface_checks)
    minimal_evidence_complete = all(
        minimal_checks[name] for name in _MINIMAL_EVIDENCE_CHECKS
    )
    contractive_w_cleared = (
        interface_canary_complete
        and interface_contraction is not None
        and interface_contraction.get("status") == "PASS"
        and interface_claim_w_status == "PASS"
    )
    effective_w_pass = minimal_checks["claim_w_pass"] and contractive_w_cleared
    effective_signal_pass = minimal_checks["claim_e_pass"] or effective_w_pass
    minimal_scientific_pass = (
        minimal_evidence_complete
        and minimal_checks["artifact_pass"]
        and effective_signal_pass
    )
    minimal_scientific_stop = minimal_evidence_complete and (
        not minimal_checks["artifact_pass"] or not minimal_checks["claim_w_or_e_pass"]
    )
    interface_killer_canary_failure = (
        interface_canary_complete
        and interface_claim_w_status == "KILLER-BASELINE-CANARY-FAIL"
    )
    m0_canary_pass = arithmetic_pass and mna_pass
    prior_art_ready = prior_art_decision == "CONTINUE-ALGORITHM"
    known_bad_cases_safe = (
        fairness_checks["zero_confirmed_false_accepts"]
        and (
            component_ladder is None or component_checks["zero_confirmed_false_accepts"]
        )
        and (minimal_probe is None or minimal_checks["zero_confirmed_false_accepts"])
    )

    blockers: list[str] = []
    if not m0_canary_pass:
        blockers.append("M0_MACHINE_CANARY_INCOMPLETE")
    if not operator_pass:
        blockers.append("CLAIM_I_OPERATOR_CANARY_INCOMPLETE")
    if operator_stress is None:
        blockers.append("OPERATOR_STRESS_NOT_RUN")
    elif not stress_pass:
        blockers.append("OPERATOR_STRESS_INCOMPLETE")
    if prior_art_decision == "UNRESOLVED":
        blockers.append("THEOREM_LEVEL_NOVELTY_UNRESOLVED")
    elif prior_art_decision == "REFRAME-SYSTEM" and not prior_art_reframe_complete:
        blockers.append("PRIOR_ART_REFRAME_SYSTEM")
    elif prior_art_decision == "REFRAME-SYSTEM":
        blockers.append("ALGORITHMIC_NOVELTY_NOT_ESTABLISHED")
    if fairness.get("strong_baseline_status") != "IMPLEMENTED":
        blockers.append("B2_STRONG_UNIMPLEMENTED")
    elif not fairness_pass:
        blockers.append("B2_FAIRNESS_INCOMPLETE")
    if component_ladder is None:
        blockers.append("COMPONENT_LADDER_NOT_RUN")
    elif not component_pass:
        blockers.append("COMPONENT_LADDER_INCOMPLETE")
    if minimal_probe is None:
        blockers.append("MATCHED_NONLINEAR_M2_NOT_RUN")
    elif not minimal_evidence_complete:
        blockers.append("MATCHED_NONLINEAR_M2_INCOMPLETE")
    elif minimal_scientific_stop and not interface_killer_canary_failure:
        blockers.append("M2_FROZEN_CRITERIA_STOP")
    if interface_contraction is None:
        blockers.append("CONTRACTIVE_INTERFACE_BASELINE_NOT_RUN")
    elif not interface_canary_complete:
        blockers.append("CONTRACTIVE_INTERFACE_BASELINE_INCOMPLETE")
    elif interface_killer_canary_failure:
        blockers.append("CLAIM_W_CONTRACTIVE_KILLER_CANARY_FAIL")
    if not known_bad_cases_safe:
        blockers.append("CONFIRMED_FALSE_ACCEPT_PRESENT")

    pre_paper_candidate = all(
        (
            m0_canary_pass,
            operator_pass,
            stress_pass,
            fairness_pass,
            component_pass,
            minimal_scientific_pass,
            contractive_w_cleared or minimal_checks["claim_e_pass"],
            prior_art_ready,
            known_bad_cases_safe,
        )
    )
    if not m0_canary_pass or not known_bad_cases_safe:
        m2_status = "STOP-S"
    elif minimal_probe is None:
        m2_status = "NOT-STARTED"
    elif pre_paper_candidate:
        m2_status = "PRE_PAPER_CANDIDATE"
    elif minimal_scientific_stop and not interface_killer_canary_failure:
        m2_status = "STOP"
    else:
        m2_status = "ITERATE"

    if not operator_pass or (operator_stress is not None and not stress_pass):
        m1_status = "STOP"
    elif prior_art_decision == "REFRAME-SYSTEM":
        m1_status = "REFRAME-SYSTEM"
    elif prior_art_decision == "CONTINUE-ALGORITHM":
        m1_status = "CONTINUE-ALGORITHM"
    else:
        m1_status = "ITERATE"

    return {
        "m0": {
            "status": "PASS-CANARY" if m0_canary_pass else "ITERATE",
            "arithmetic_checks": arithmetic_checks,
            "mna_checks": mna_checks,
            "scope": "machine implementation evidence; theorem remains conditional",
        },
        "m1": {
            "status": m1_status,
            "claim_i": "IMPLEMENTATION-CANARY-PASS" if operator_pass else "FAILED",
            "operator_checks": operator_checks,
            "operator_stress_checks": stress_checks,
            "novelty": prior_art_decision,
            "prior_art_gate": prior_art_decision,
            "prior_art_reframe_closure": (
                "COMPLETE" if prior_art_reframe_complete else "INCOMPLETE"
            ),
            "algorithm_novelty": (
                "ABANDONED-AS-PAPER-HEADLINE"
                if prior_art_decision == "REFRAME-SYSTEM"
                else (
                    "CONTINUE-ALGORITHM"
                    if prior_art_decision == "CONTINUE-ALGORITHM"
                    else "UNRESOLVED"
                )
            ),
            "efficiency": (
                "M2-STABLE-SIGNAL-PASS"
                if minimal_scientific_pass
                else (
                    "KILLER-BASELINE-CANARY-FAIL"
                    if interface_killer_canary_failure
                    else "UNVERIFIED"
                )
            ),
        },
        "m2": {
            "status": m2_status,
            "b2_strong_ready": fairness_pass,
            "fairness_checks": fairness_checks,
            "component_ladder": "PASS" if component_pass else "NOT-READY",
            "component_ladder_checks": component_checks,
            "matched_nonlinear_probe": (
                "PASS"
                if minimal_scientific_pass
                else (
                    "PASS-INVALIDATED-BY-KILLER-CANARY"
                    if interface_killer_canary_failure
                    else "COMPLETE-STOP" if minimal_scientific_stop else "NOT-READY"
                )
            ),
            "minimal_probe_checks": minimal_checks,
            "minimal_probe_evidence_complete": minimal_evidence_complete,
            "minimal_probe_scientific_pass": minimal_scientific_pass,
            "interface_contraction_checks": interface_checks,
            "interface_contraction_canary_complete": interface_canary_complete,
            "claim_w_after_contractive_baseline": (
                "PASS"
                if effective_w_pass
                else (
                    "FAIL-CANARY" if interface_killer_canary_failure else "UNVERIFIED"
                )
            ),
            "contractive_w_cleared": contractive_w_cleared,
            "prior_art_ready": prior_art_ready,
            "prior_art_reframe_complete": prior_art_reframe_complete,
            "known_bad_cases_safe": known_bad_cases_safe,
        },
        "blockers": blockers,
        "pre_paper_candidate": "PASS" if pre_paper_candidate else "FAIL-UNVERIFIED",
        "paper_candidate": "FAIL-UNVERIFIED",
        "research_opportunity": "PASS",
    }


def run_gate() -> dict[str, object]:
    """Load frozen artifacts, evaluate the gate, and attach provenance."""

    required_paths = {
        "arithmetic": _ARITHMETIC,
        "mna": _MNA,
        "operator": _OPERATOR,
        "b2_fairness": _FAIRNESS,
    }
    optional_paths = {
        "operator_stress": _OPERATOR_STRESS,
        "component_ladder": _COMPONENT_LADDER,
        "minimal_probe": _MINIMAL_PROBE,
        "interface_contraction": _INTERFACE_CONTRACTION,
    }
    evidence = {name: _load_json(path) for name, path in required_paths.items()}
    optional_evidence = {
        name: _load_optional_json(path) for name, path in optional_paths.items()
    }
    prior_art = _PRIOR_ART.read_text(encoding="utf-8") if _PRIOR_ART.is_file() else None
    decision = evaluate_gate(
        evidence["arithmetic"],
        evidence["mna"],
        evidence["operator"],
        evidence["b2_fairness"],
        operator_stress=optional_evidence["operator_stress"],
        component_ladder=optional_evidence["component_ladder"],
        minimal_probe=optional_evidence["minimal_probe"],
        prior_art=prior_art,
        interface_contraction=optional_evidence["interface_contraction"],
    )
    all_paths = {**required_paths, **optional_paths, "prior_art": _PRIOR_ART}
    artifact_hashes = {
        name: sha256_file(path) for name, path in all_paths.items() if path.is_file()
    }
    missing_evidence = sorted(
        name for name, path in optional_paths.items() if not path.is_file()
    )
    if prior_art is None:
        missing_evidence.append("prior_art")
    source_hashes = source_file_hashes(_PAPER_ROOT, _SOURCE_FILES)
    m2_status = str(decision["m2"]["status"])
    top_status = (
        "PRE_PAPER_CANDIDATE"
        if m2_status == "PRE_PAPER_CANDIDATE"
        else "STOP-S" if m2_status == "STOP-S" else "ITERATE"
    )
    return {
        "schema_version": 2,
        "status": top_status,
        "claim_scope": "claim-separated next-round decision; no paper-candidate claim",
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": "python3 -m experiments.run_next_round_gate",
        "config_sha256": sha256_file(_PAPER_ROOT / "steps/008_next_round_gate.md"),
        "input_sha256": canonical_sha256(artifact_hashes),
        "source_files_sha256": source_hashes,
        "artifact_sha256": artifact_hashes,
        "missing_optional_evidence": missing_evidence,
        "backend": evidence["arithmetic"].get("backend", {}),
        "random_seeds": {},
        "attempted_cases": len(all_paths),
        "supported_cases": len(artifact_hashes),
        "unsupported_cases": len(all_paths) - len(artifact_hashes),
        "failure_codes": (
            ["MACHINE_SOUNDNESS_GATE_FAILED"] if m2_status == "STOP-S" else []
        ),
        "first_failure": (
            {"blocker": decision["blockers"][0]}
            if m2_status == "STOP-S" and decision["blockers"]
            else None
        ),
        **decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = run_gate()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["m0"]["status"] != "PASS-CANARY" or result["status"] == "STOP-S":
        sys.exit(1)


if __name__ == "__main__":
    main()
