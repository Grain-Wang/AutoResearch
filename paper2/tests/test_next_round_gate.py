from typing import Any

from experiments.run_next_round_gate import evaluate_gate, run_gate


def _complete_evidence() -> tuple[dict[str, Any], ...]:
    operations = {
        name: {"random_cases": 50_000, "edge_cases": 7}
        for name in ("add", "sub", "mul", "div", "exp", "expm1", "log", "sqrt")
    }
    arithmetic = {
        "status": "PASS",
        "backend": {"name": "MPFR", "precision_bits": 256},
        "rounding_modes": {"lower": "RNDD", "upper": "RNDU"},
        "operations": operations,
        "containment_violations": 0,
    }
    negative_case_ids = {
        "root-excluding-tube",
        "state-permutation-mismatch",
        "singular-midpoint-operator",
        "invalid-node-mapping",
        "malformed-state-layout",
        "unsupported-diode-domain-box",
        "mos-region-branch-crossing",
        *(f"wrong-history-{index}" for index in range(10)),
    }
    circuit = {
        "steps": 100,
        "accepted": 100,
        "root_contained_steps": 100,
        "root_excluded_steps": 0,
        "jacobian_containment_violations": 0,
        "checker_false_accepts": 0,
    }
    mna = {
        "status": "PASS",
        "circuits": {"rc": circuit, "diode_rc": circuit},
        "negative_cases": {
            "false_accepts": 0,
            "records": [{"case_id": case_id} for case_id in negative_case_ids],
        },
    }
    operator = {
        "status": "PASS",
        "total_recursive_containment_violations": 0,
        "singular_cases": {"attempted_cases": 1, "false_supported_count": 0},
        "grids": [
            {
                "block_dimension": dimension,
                "slab_length": slabs,
                "attempted_cases": 200,
                "supported_cases": 200,
                "containment_violations": 0,
            }
            for dimension in (1, 2, 4, 8)
            for slabs in (2, 4, 8)
        ],
    }
    buckets = [
        {"bucket": label} for label in ("1e0-1e2", "1e2-1e4", "1e4-1e6", "1e6-1e8")
    ]
    stress = {
        "status": "PASS",
        "containment_violations": 0,
        "containment_violation_coordinates": 0,
        "expected_unsupported": {
            "attempted_cases": 32,
            "UNKNOWN": 32,
            "false_OK": 0,
        },
        "grids": [
            {
                "block_dimension": dimension,
                "slab_length": slabs,
                "attempted_cases": 200,
                "interval_rhs_cases": 200,
                "violations": 0,
                "containment_violation_coordinates": 0,
                "strong_subdiagonal_cases": 1,
                "nonnormal_global_matrix_cases": 1,
                "near_singular_supported_cases": 1,
                "conditioning_and_pivot_growth_buckets": buckets,
            }
            for dimension in (1, 2, 4, 8)
            for slabs in (2, 4, 8, 16)
        ],
    }
    fairness = {
        "status": "PASS",
        "strong_baseline_status": "IMPLEMENTED",
        "all_required_hashes_present": True,
        "all_shared_hashes_match": True,
        "known_bad_cases": 17,
        "confirmed_false_accepts": 0,
    }
    component = {
        "status": "PASS",
        "coverage_complete": True,
        "methods": [
            "dense_slab_generic",
            "device_local_pointwise_b2",
            "temporal_only",
            "temporal_device_blockstamp",
        ],
        "success_only_filtering": False,
        "all_required_hashes_present": True,
        "all_shared_hashes_match": True,
        "confirmed_false_accepts": 0,
    }
    minimal = {
        "status": "PASS",
        "grid_complete": True,
        "independent_processes": True,
        "warmups_excluded": True,
        "replicates": 5,
        "workloads_complete": True,
        "success_only_filtering": False,
        "fairness_pass": True,
        "confirmed_false_accepts": 0,
        "complete_cost_accounting": True,
        "stable_signal": {"clustered_bootstrap_95ci_complete": True},
        "claims": {"W": "PASS", "E": "STOP", "D": "STOP"},
    }
    return arithmetic, mna, operator, fairness, stress, component, minimal


def _complete_interface_evidence() -> dict[str, Any]:
    return {
        "status": "PASS",
        "protocol_complete": True,
        "attempted_traces": 6,
        "completed_traces": 6,
        "success_only_filtering": False,
        "claim_w_killer_baseline": {"status": "PASS"},
        "algorithmic_novelty": "ESTABLISHED",
    }


def test_current_repository_evidence_records_killer_baseline_failure() -> None:
    result = run_gate()
    assert result["m0"]["status"] == "PASS-CANARY"
    assert result["m1"]["claim_i"] == "IMPLEMENTATION-CANARY-PASS"
    assert result["m2"]["status"] == "ITERATE"
    assert result["m2"]["claim_w_after_contractive_baseline"] == "FAIL-CANARY"
    assert result["paper_candidate"] == "FAIL-UNVERIFIED"
    assert "CLAIM_W_CONTRACTIVE_KILLER_CANARY_FAIL" in result["blockers"]


def test_legacy_evaluate_gate_call_fails_closed_on_new_evidence() -> None:
    arithmetic, mna, operator, fairness, *_ = _complete_evidence()
    result = evaluate_gate(arithmetic, mna, operator, fairness)
    assert result["m2"]["status"] == "NOT-STARTED"
    assert "OPERATOR_STRESS_NOT_RUN" in result["blockers"]
    assert "COMPONENT_LADDER_NOT_RUN" in result["blockers"]
    assert "MATCHED_NONLINEAR_M2_NOT_RUN" in result["blockers"]
    assert "CONTRACTIVE_INTERFACE_BASELINE_NOT_RUN" in result["blockers"]


def test_synthetic_complete_evidence_reaches_pre_paper_candidate() -> None:
    arithmetic, mna, operator, fairness, stress, component, minimal = (
        _complete_evidence()
    )
    result = evaluate_gate(
        arithmetic,
        mna,
        operator,
        fairness,
        operator_stress=stress,
        component_ladder=component,
        minimal_probe=minimal,
        prior_art="Prior-art gate: CONTINUE-ALGORITHM",
        interface_contraction=_complete_interface_evidence(),
    )
    assert result["m1"]["status"] == "CONTINUE-ALGORITHM"
    assert result["m2"]["status"] == "PRE_PAPER_CANDIDATE"
    assert result["pre_paper_candidate"] == "PASS"
    assert result["paper_candidate"] == "FAIL-UNVERIFIED"
    assert result["blockers"] == []


def test_unclosed_prior_art_reframe_blocks_otherwise_complete_evidence() -> None:
    arithmetic, mna, operator, fairness, stress, component, minimal = (
        _complete_evidence()
    )
    result = evaluate_gate(
        arithmetic,
        mna,
        operator,
        fairness,
        operator_stress=stress,
        component_ladder=component,
        minimal_probe=minimal,
        prior_art="Prior-art gate: REFRAME-SYSTEM",
        interface_contraction=_complete_interface_evidence(),
    )
    assert result["m1"]["status"] == "REFRAME-SYSTEM"
    assert result["m2"]["status"] == "ITERATE"
    assert result["pre_paper_candidate"] == "FAIL-UNVERIFIED"
    assert "PRIOR_ART_REFRAME_SYSTEM" in result["blockers"]


def test_closed_prior_art_reframe_closes_action_but_not_algorithm_gate() -> None:
    arithmetic, mna, operator, fairness, stress, component, minimal = (
        _complete_evidence()
    )
    result = evaluate_gate(
        arithmetic,
        mna,
        operator,
        fairness,
        operator_stress=stress,
        component_ladder=component,
        minimal_probe=minimal,
        prior_art=(
            "Prior-art gate: REFRAME-SYSTEM\n" "Prior-art reframe closure: COMPLETE\n"
        ),
        interface_contraction=_complete_interface_evidence(),
    )
    assert result["m1"]["novelty"] == "REFRAME-SYSTEM"
    assert result["m1"]["prior_art_reframe_closure"] == "COMPLETE"
    assert result["m1"]["algorithm_novelty"] == "ABANDONED-AS-PAPER-HEADLINE"
    assert result["m2"]["prior_art_reframe_complete"] is True
    assert result["m2"]["prior_art_ready"] is False
    assert result["m2"]["status"] == "ITERATE"
    assert result["pre_paper_candidate"] == "FAIL-UNVERIFIED"
    assert "PRIOR_ART_REFRAME_SYSTEM" not in result["blockers"]
    assert "ALGORITHMIC_NOVELTY_NOT_ESTABLISHED" in result["blockers"]


def test_runner_schema_workload_mapping_is_complete() -> None:
    arithmetic, mna, operator, fairness, stress, component, minimal = (
        _complete_evidence()
    )
    minimal["workloads_complete"] = {
        "diode_rc": True,
        "nmos_ring_3stage": True,
    }
    result = evaluate_gate(
        arithmetic,
        mna,
        operator,
        fairness,
        operator_stress=stress,
        component_ladder=component,
        minimal_probe=minimal,
        prior_art="Prior-art gate: CONTINUE-ALGORITHM",
        interface_contraction=_complete_interface_evidence(),
    )
    assert result["m2"]["minimal_probe_checks"]["both_workloads_complete"] is True
    assert result["m2"]["minimal_probe_evidence_complete"] is True
    assert result["m2"]["status"] == "PRE_PAPER_CANDIDATE"


def test_complete_negative_m2_is_stop_not_incomplete() -> None:
    arithmetic, mna, operator, fairness, stress, component, minimal = (
        _complete_evidence()
    )
    minimal["status"] = "STOP"
    minimal["workloads_complete"] = {
        "diode_rc": True,
        "nmos_ring_3stage": True,
    }
    minimal["claims"] = {"W": "STOP", "E": "STOP", "D": "STOP"}
    result = evaluate_gate(
        arithmetic,
        mna,
        operator,
        fairness,
        operator_stress=stress,
        component_ladder=component,
        minimal_probe=minimal,
        prior_art="Prior-art gate: CONTINUE-ALGORITHM",
        interface_contraction=_complete_interface_evidence(),
    )
    assert result["m2"]["minimal_probe_evidence_complete"] is True
    assert result["m2"]["minimal_probe_scientific_pass"] is False
    assert result["m2"]["matched_nonlinear_probe"] == "COMPLETE-STOP"
    assert result["m2"]["status"] == "STOP"
    assert result["pre_paper_candidate"] == "FAIL-UNVERIFIED"
    assert result["paper_candidate"] == "FAIL-UNVERIFIED"
    assert "M2_FROZEN_CRITERIA_STOP" in result["blockers"]
    assert "MATCHED_NONLINEAR_M2_INCOMPLETE" not in result["blockers"]


def test_confirmed_false_accept_stops_soundness_gate() -> None:
    arithmetic, mna, operator, fairness, stress, component, minimal = (
        _complete_evidence()
    )
    minimal["confirmed_false_accepts"] = 1
    result = evaluate_gate(
        arithmetic,
        mna,
        operator,
        fairness,
        operator_stress=stress,
        component_ladder=component,
        minimal_probe=minimal,
        prior_art="CONTINUE-ALGORITHM",
        interface_contraction=_complete_interface_evidence(),
    )
    assert result["m2"]["status"] == "STOP-S"
    assert "CONFIRMED_FALSE_ACCEPT_PRESENT" in result["blockers"]


def test_killer_interface_canary_revokes_w_only_promotion() -> None:
    arithmetic, mna, operator, fairness, stress, component, minimal = (
        _complete_evidence()
    )
    interface = _complete_interface_evidence()
    interface["status"] = "PASS-CANARY"
    interface["claim_w_killer_baseline"] = {"status": "KILLER-BASELINE-CANARY-FAIL"}
    interface["algorithmic_novelty"] = "NOT-ESTABLISHED"
    result = evaluate_gate(
        arithmetic,
        mna,
        operator,
        fairness,
        operator_stress=stress,
        component_ladder=component,
        minimal_probe=minimal,
        prior_art="Prior-art gate: CONTINUE-ALGORITHM",
        interface_contraction=interface,
    )
    assert result["m2"]["status"] == "ITERATE"
    assert result["m2"]["minimal_probe_evidence_complete"] is True
    assert result["m2"]["claim_w_after_contractive_baseline"] == "FAIL-CANARY"
    assert result["m2"]["matched_nonlinear_probe"] == (
        "PASS-INVALIDATED-BY-KILLER-CANARY"
    )
    assert "CLAIM_W_CONTRACTIVE_KILLER_CANARY_FAIL" in result["blockers"]
