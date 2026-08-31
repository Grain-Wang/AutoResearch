from __future__ import annotations

from typing import Any

from paper3.experiments.bar_depth.analyze_oracle_canary import (
    aggregate_statistics,
    apply_gate,
    build_image_statistics,
)


def _region_row(sample: int, region: int, utility: float) -> dict[str, Any]:
    return {
        "sample_index": sample,
        "region_id": region,
        "scan_id": f"scan-{sample}",
        "domain": "indoors",
        "base_primary_error_sum": 10.0,
        "base_absrel_error_sum": 10.0,
        "primary_utility_sum": utility,
        "absrel_utility_sum": utility,
        "rgb_gradient_score": float(region),
        "base_gradient_score": float(region),
    }


def test_oracle_capture_uses_per_image_budget() -> None:
    rows = []
    for sample in range(2):
        utilities = [7.0, 2.0, 1.0, 0.0]
        rows.extend(
            _region_row(sample, region, utility)
            for region, utility in enumerate(utilities)
        )
    statistics = build_image_statistics(rows, budget_count=1, expected_regions=4)
    aggregate = aggregate_statistics(statistics)
    assert aggregate["oracle_capture_at_budget"] == 0.7
    assert aggregate["positive_headroom_ratio"] == 0.25
    assert aggregate["oracle_primary_reduction_ratio"] == 0.175


def test_gate_requires_lower_confidence_bounds() -> None:
    estimates = {
        "positive_headroom_ratio": 0.05,
        "oracle_capture_at_budget": 0.8,
        "oracle_primary_reduction_ratio": 0.04,
        "oracle_absrel_relative_degradation": 0.0,
    }
    intervals = {
        key: {"lower": value - 0.01, "upper": value + 0.01}
        for key, value in estimates.items()
    }
    gate = apply_gate(
        estimates,
        intervals,
        {
            "min_positive_headroom_ratio": 0.03,
            "min_oracle_capture_at_budget": 0.7,
            "min_oracle_primary_reduction_ratio": 0.02,
            "max_oracle_absrel_relative_degradation": 0.01,
            "require_cluster_ci_lower_bounds": True,
        },
    )
    assert gate["decision"] == "GO_ORACLE_ROUTABILITY_UNVERIFIED"

    intervals["oracle_capture_at_budget"]["lower"] = 0.69
    gate = apply_gate(
        estimates,
        intervals,
        {
            "min_positive_headroom_ratio": 0.03,
            "min_oracle_capture_at_budget": 0.7,
            "min_oracle_primary_reduction_ratio": 0.02,
            "max_oracle_absrel_relative_degradation": 0.01,
            "require_cluster_ci_lower_bounds": True,
        },
    )
    assert gate["decision"] == "STOP_DIFFUSE_UTILITY"


def test_zero_positive_utility_is_a_valid_stop_statistic() -> None:
    rows = [_region_row(0, region, -1.0) for region in range(4)]
    statistics = build_image_statistics(rows, budget_count=1, expected_regions=4)
    aggregate = aggregate_statistics(statistics)
    assert aggregate["positive_headroom_ratio"] == 0.0
    assert aggregate["oracle_capture_at_budget"] == 0.0
    assert aggregate["rgb_gradient_capture_at_budget"] == 0.0
