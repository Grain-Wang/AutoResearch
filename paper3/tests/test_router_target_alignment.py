from __future__ import annotations

from typing import Any

import numpy as np
from paper3.experiments.bar_depth.audit_router_target_alignment import (
    aggregate_alignment,
    build_image_alignment_rows,
    kendall_tau_b,
)


def _image_rows() -> list[dict[str, Any]]:
    utilities = [9.0, 8.0, 1.0]
    weights = [9.0, 1.0, 1.0]
    return [
        {
            "sample_index": 0,
            "domain": "indoor",
            "scene_id": "scene-0",
            "scan_id": "scan-0",
            "region_id": region_id,
            "primary_utility_sum": utility,
            "weight_sum": weight,
            "base_primary_error_sum": 10.0,
        }
        for region_id, (utility, weight) in enumerate(
            zip(utilities, weights, strict=True)
        )
    ]


def test_region_denominator_can_change_top_k_ordering() -> None:
    rows = build_image_alignment_rows([_image_rows()], budgets=(1,))
    assert rows[0]["raw_topk_region_ids"] == "0"
    assert rows[0]["normalized_topk_region_ids"] == "1"
    assert rows[0]["top_k_set_jaccard"] == 0.0
    assert rows[0]["selected_set_disagreement"] == 1.0
    assert aggregate_alignment(rows)["normalized_target_raw_oracle_recovery"] == 8 / 9


def test_image_constant_denominator_preserves_ranking() -> None:
    utility = np.asarray([9.0, 8.0, 1.0])
    image_denominator = 30.0
    assert (
        np.argsort(-utility, kind="stable").tolist()
        == np.argsort(-(utility / image_denominator), kind="stable").tolist()
    )


def test_kendall_tau_b_handles_ties() -> None:
    assert kendall_tau_b(np.asarray([2.0, 1.0]), np.asarray([20.0, 10.0])) == 1.0
    assert kendall_tau_b(np.asarray([2.0, 1.0]), np.asarray([10.0, 20.0])) == -1.0
