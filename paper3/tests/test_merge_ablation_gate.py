from __future__ import annotations

from paper3.experiments.bar_depth.analyze_merge_ablation import (
    apply_patch_necessity_gate,
)


def test_patch_necessity_gate_requires_positive_paired_ci() -> None:
    gate = apply_patch_necessity_gate(
        highpass_estimate=0.06,
        cheap_estimate=0.04,
        paired_differences=[-0.01, 0.02, 0.03, 0.04],
        confidence_level=0.95,
        require_ci_lower_above_zero=True,
    )
    assert gate["decision"] == "STOP_PATCH_INFERENCE_NOT_NECESSARY"


def test_patch_necessity_gate_passes_strict_positive_difference() -> None:
    gate = apply_patch_necessity_gate(
        highpass_estimate=0.06,
        cheap_estimate=0.04,
        paired_differences=[0.01, 0.02, 0.03, 0.04],
        confidence_level=0.95,
        require_ci_lower_above_zero=True,
    )
    assert gate["decision"] == "GO_PATCH_INFORMATION_NECESSARY"
