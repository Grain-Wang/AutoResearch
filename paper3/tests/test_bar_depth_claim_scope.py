from __future__ import annotations

from pathlib import Path


def test_active_bar_depth_claims_use_round2_scope() -> None:
    active_paths = [
        Path("paper3/ideas/candidates/01_budget_adaptive_regional_depth.md"),
        *[
            Path(f"paper3/steps/{number:03d}_{suffix}")
            for number, suffix in (
                (22, "bar_depth_router_probe_protocol.md"),
                (23, "bar_depth_killer_selector_result.md"),
                (24, "bar_depth_merge_ablation_protocol.md"),
                (25, "bar_depth_matched_latency_protocol.md"),
                (26, "bar_depth_novelty_audit.md"),
                (27, "bar_depth_objective_contract.md"),
                (28, "bar_depth_generic_novelty_audit.md"),
                (29, "bar_depth_formal_latency_result.md"),
            )
        ],
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in active_paths)
    assert "Boosting MDE 2021" not in combined
    assert "GO_PATCH_INFORMATION_NECESSARY" not in combined
    assert "absolute metric depth" not in combined.lower()
    assert "absolute metric-depth" not in combined.lower()
    assert "STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER" in combined


def test_shared_latency_is_explicitly_non_formal() -> None:
    protocol = Path("paper3/steps/025_bar_depth_matched_latency_protocol.md").read_text(
        encoding="utf-8"
    )
    assert "PROVISIONAL / NOT_FORMAL" in protocol
    assert "two-session v2 protocol" in protocol


def test_correction_ledger_preserves_historical_mapping() -> None:
    ledger = Path("paper3/steps/031_bar_depth_claim_scope_corrections.md").read_text(
        encoding="utf-8"
    )
    assert "Boosting MDE 2021" in ledger
    assert "Boosting-MDE edge-density selector adapted to frozen BAR actions" in ledger
    assert "GO_PATCH_INFORMATION_NECESSARY" in ledger
    assert "GO_PATCH_INFORMATION_BEYOND_TWO_FROZEN_CONTROLS" in ledger
