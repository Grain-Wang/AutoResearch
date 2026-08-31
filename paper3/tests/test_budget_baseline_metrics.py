from __future__ import annotations

from typing import Any

import numpy as np
from paper3.experiments.bar_depth.analyze_budget_baselines import (
    aggregate_sufficient,
    build_image_statistic,
    select_region_indices,
)


def _rows(utilities: list[float]) -> list[dict[str, Any]]:
    return [
        {
            "sample_index": 0,
            "scan_id": "scan-0",
            "region_id": region_id,
            "base_primary_error_sum": 10.0,
            "base_absrel_error_sum": 10.0,
            "primary_utility_sum": utility,
            "absrel_utility_sum": utility / 2.0,
            "rgb_gradient_score": float(region_id),
            "base_gradient_score": float(region_id),
        }
        for region_id, utility in enumerate(utilities)
    ]


def _vector(statistic: dict[str, Any]) -> np.ndarray:
    keys = (
        "base_primary",
        "base_absrel",
        "positive_primary",
        "selected_primary",
        "selected_absrel",
        "selected_positive_primary",
        "selected_count",
        "harmful_count",
        "image_count",
    )
    return np.asarray([float(statistic[key]) for key in keys], dtype=np.float64)


def test_signed_metric_does_not_clip_harmful_selection() -> None:
    rows = _rows([7.0, 2.0, 1.0, -4.0])
    selected = select_region_indices(rows, method="base_gradient_topk", budget_count=1)
    oracle = select_region_indices(
        rows, method="oracle_at_most_k_positive", budget_count=1
    )
    metrics = aggregate_sufficient(
        _vector(build_image_statistic(rows, selected)),
        _vector(build_image_statistic(rows, oracle)),
    )
    assert metrics["signed_primary_error_reduction_ratio"] == -0.1
    assert metrics["harmful_selection_rate"] == 1.0
    assert metrics["positive_utility_capture"] == 0.0


def test_oracle_selects_at_most_k_positive_regions() -> None:
    rows = _rows([7.0, -2.0, -1.0, -4.0])
    selected = select_region_indices(
        rows, method="oracle_at_most_k_positive", budget_count=3
    )
    assert selected.tolist() == [0]


def test_random_selector_is_reproducible_and_exact_k() -> None:
    rows = _rows([7.0, 2.0, 1.0, -4.0])
    first = select_region_indices(
        rows, method="random_topk_100_seeds", budget_count=2, random_seed=1000
    )
    second = select_region_indices(
        rows, method="random_topk_100_seeds", budget_count=2, random_seed=1000
    )
    assert first.tolist() == second.tolist()
    assert first.size == 2


def test_fixed_spatial_selector_rejects_duplicate_regions() -> None:
    rows = _rows([7.0, 2.0, 1.0, -4.0])
    try:
        select_region_indices(
            rows,
            method="fixed_spatial_uniform_topk",
            budget_count=2,
            spatial_pattern=[0, 0],
        )
    except ValueError as exc:
        assert "invalid region" in str(exc)
    else:
        raise AssertionError("Duplicate spatial regions were accepted")
