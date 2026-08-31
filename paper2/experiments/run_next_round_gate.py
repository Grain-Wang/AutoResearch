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
_FAIRNESS = _RESULT_ROOT / "b2_fairness.json"
_SOURCE_FILES = (
    Path(__file__).resolve(),
    _PAPER_ROOT / "steps/003_formal_soundness_contract.md",
    _PAPER_ROOT / "steps/007_blockstamp_operator_spec.md",
    _PAPER_ROOT / "steps/008_next_round_gate.md",
)
_EXPECTED_OPERATIONS = {"add", "sub", "mul", "div", "exp", "expm1", "log", "sqrt"}
_EXPECTED_GRIDS = {
    (dimension, slabs) for dimension in (1, 2, 4, 8) for slabs in (2, 4, 8)
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return payload


def _arithmetic_checks(payload: dict[str, Any]) -> dict[str, bool]:
    operations = payload.get("operations", {})
    return {
        "artifact_pass": payload.get("status") == "PASS",
        "mpfr_256_or_stronger": (
            payload.get("backend", {}).get("name") == "MPFR"
            and int(payload.get("backend", {}).get("precision_bits", 0)) >= 256
        ),
        "directed_rounding_declared": payload.get("rounding_modes")
        == {"lower": "RNDD", "upper": "RNDU"},
        "all_operations_present": set(operations) == _EXPECTED_OPERATIONS,
        "random_budget_met": all(
            int(operations.get(name, {}).get("random_cases", 0)) >= 50_000
            for name in _EXPECTED_OPERATIONS
        ),
        "edge_budget_met": all(
            int(operations.get(name, {}).get("edge_cases", 0)) >= 7
            for name in _EXPECTED_OPERATIONS
        ),
        "zero_containment_violations": int(payload.get("containment_violations", -1))
        == 0,
    }


def _mna_checks(payload: dict[str, Any]) -> dict[str, bool]:
    circuits = payload.get("circuits", {})
    negative = payload.get("negative_cases", {})
    records = negative.get("records", [])
    case_ids = {record.get("case_id") for record in records}
    circuit_checks = []
    for name in ("rc", "diode_rc"):
        record = circuits.get(name, {})
        steps = int(record.get("steps", 0))
        circuit_checks.append(
            steps >= 100
            and int(record.get("accepted", -1)) == steps
            and int(record.get("root_contained_steps", -1)) == steps
            and int(record.get("root_excluded_steps", -1)) == 0
            and int(record.get("jacobian_containment_violations", -1)) == 0
            and int(record.get("checker_false_accepts", -1)) == 0
        )
    return {
        "artifact_pass": payload.get("status") == "PASS",
        "rc_and_diode_rc_100_steps": all(circuit_checks),
        "required_negative_families_present": _REQUIRED_NEGATIVE_CASES <= case_ids,
        "wrong_history_sweep_present": sum(
            str(case_id).startswith("wrong-history-") for case_id in case_ids
        )
        >= 10,
        "zero_negative_false_accepts": int(negative.get("false_accepts", -1)) == 0,
    }


def _operator_checks(payload: dict[str, Any]) -> dict[str, bool]:
    grids = payload.get("grids", [])
    by_key = {
        (int(grid.get("block_dimension", -1)), int(grid.get("slab_length", -1))): grid
        for grid in grids
    }
    required_cells_pass = all(
        key in by_key
        and int(by_key[key].get("attempted_cases", 0)) >= 200
        and int(by_key[key].get("supported_cases", 0)) >= 200
        and int(by_key[key].get("containment_violations", -1)) == 0
        for key in _EXPECTED_GRIDS
    )
    singular = payload.get("singular_cases", {})
    return {
        "artifact_pass": payload.get("status") == "PASS",
        "all_12_grid_cells_pass": required_cells_pass,
        "zero_recursive_containment_violations": int(
            payload.get("total_recursive_containment_violations", -1)
        )
        == 0,
        "singular_case_fails_closed": (
            int(singular.get("attempted_cases", 0)) >= 1
            and int(singular.get("false_supported_count", -1)) == 0
        ),
    }


def evaluate_gate(
    arithmetic: dict[str, Any],
    mna: dict[str, Any],
    operator: dict[str, Any],
    fairness: dict[str, Any],
) -> dict[str, object]:
    """Return claim-separated gate decisions from existing evidence payloads."""

    arithmetic_checks = _arithmetic_checks(arithmetic)
    mna_checks = _mna_checks(mna)
    operator_checks = _operator_checks(operator)
    arithmetic_pass = all(arithmetic_checks.values())
    mna_pass = all(mna_checks.values())
    operator_pass = all(operator_checks.values())
    m0_canary_pass = arithmetic_pass and mna_pass
    b2_strong_ready = (
        fairness.get("status") == "PASS"
        and fairness.get("strong_baseline_status") == "IMPLEMENTED"
        and fairness.get("all_required_hashes_present") is True
        and fairness.get("all_shared_hashes_match") is True
    )
    blockers = []
    if not m0_canary_pass:
        blockers.append("M0_MACHINE_CANARY_INCOMPLETE")
    if not operator_pass:
        blockers.append("CLAIM_I_OPERATOR_CANARY_INCOMPLETE")
    blockers.extend(
        [
            "THEOREM_LEVEL_NOVELTY_UNRESOLVED",
            "B2_STRONG_UNIMPLEMENTED",
            "COMPONENT_LADDER_NOT_RUN",
            "MATCHED_NONLINEAR_M2_NOT_RUN",
        ]
    )
    return {
        "m0": {
            "status": "PASS-CANARY" if m0_canary_pass else "ITERATE",
            "arithmetic_checks": arithmetic_checks,
            "mna_checks": mna_checks,
            "scope": "machine implementation evidence; theorem remains conditional",
        },
        "m1": {
            "status": "ITERATE" if operator_pass else "STOP",
            "claim_i": "IMPLEMENTATION-CANARY-PASS" if operator_pass else "FAILED",
            "operator_checks": operator_checks,
            "novelty": "UNRESOLVED",
            "efficiency": "UNVERIFIED",
        },
        "m2": {
            "status": "NOT-STARTED",
            "b2_strong_ready": b2_strong_ready,
            "component_ladder": "NOT-RUN",
            "matched_nonlinear_probe": "NOT-RUN",
        },
        "blockers": blockers,
        "paper_candidate": "FAIL-UNVERIFIED",
        "research_opportunity": "PASS",
    }


def run_gate() -> dict[str, object]:
    """Load frozen artifacts, evaluate the gate, and attach provenance."""

    evidence_paths = {
        "arithmetic": _ARITHMETIC,
        "mna": _MNA,
        "operator": _OPERATOR,
        "b2_fairness": _FAIRNESS,
    }
    evidence = {name: _load_json(path) for name, path in evidence_paths.items()}
    artifact_hashes = {name: sha256_file(path) for name, path in evidence_paths.items()}
    decision = evaluate_gate(
        evidence["arithmetic"],
        evidence["mna"],
        evidence["operator"],
        evidence["b2_fairness"],
    )
    source_hashes = source_file_hashes(_PAPER_ROOT, _SOURCE_FILES)
    return {
        "schema_version": 1,
        "status": "ITERATE",
        "claim_scope": "claim-separated next-round decision; no performance claim",
        **git_state(_PAPER_ROOT.parent, "paper2"),
        **runtime_provenance(),
        "command": "python3 -m experiments.run_next_round_gate",
        "config_sha256": sha256_file(_PAPER_ROOT / "steps/008_next_round_gate.md"),
        "input_sha256": canonical_sha256(artifact_hashes),
        "source_files_sha256": source_hashes,
        "artifact_sha256": artifact_hashes,
        "backend": evidence["arithmetic"].get("backend", {}),
        "random_seeds": {},
        "attempted_cases": len(evidence_paths),
        "supported_cases": len(evidence_paths),
        "unsupported_cases": 0,
        "failure_codes": [],
        "first_failure": None,
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
    if result["m0"]["status"] != "PASS-CANARY":
        sys.exit(1)


if __name__ == "__main__":
    main()
