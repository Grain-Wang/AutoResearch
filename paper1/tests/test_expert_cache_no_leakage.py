from __future__ import annotations

from copy import deepcopy

import pytest
from paper1.experiments.covol.cache_oof_experts import (
    build_stacking_plan,
    validate_expert_cache_manifest,
    validate_stacking_plan,
)


def _manifests() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    official = [
        {
            "dataset": "toy",
            "image_id": f"official-{index}",
            "scene_id": f"scene-{index}",
            "official_split": "train",
        }
        for index in range(20)
    ]
    router: list[dict[str, object]] = []
    for index in range(10):
        router.append(
            {
                "dataset": "toy",
                "image_id": f"train-{index}",
                "scene_id": f"scene-{index}",
                "split": "train",
            }
        )
    for index in range(10, 12):
        router.append(
            {
                "dataset": "toy",
                "image_id": f"dev-{index}",
                "scene_id": f"scene-{index}",
                "split": "dev",
            }
        )
    for index in range(12, 14):
        router.append(
            {
                "dataset": "toy",
                "image_id": f"test-{index}",
                "scene_id": f"scene-{index}",
                "split": "internal_test",
            }
        )
    return router, official


def test_builds_scene_disjoint_oof_and_final_expert_plan() -> None:
    router, official = _manifests()
    plan = build_stacking_plan(router, official, n_folds=5)

    validate_stacking_plan(plan)
    assert plan["status"] == "PLANNED_NOT_TRAINED"
    assert len(plan["predictions"]) == len(router)
    assert (
        sum(
            prediction["prediction_scope"] == "oof"
            for prediction in plan["predictions"]
        )
        == 10
    )


def test_rejects_training_scene_in_prediction_scope() -> None:
    router, official = _manifests()
    plan = build_stacking_plan(router, official, n_folds=5)
    corrupted = deepcopy(plan)
    first_prediction = corrupted["predictions"][0]
    expert = next(
        item
        for item in corrupted["experts"]
        if item["expert_id"] == first_prediction["expert_id"]
    )
    expert["training_scene_hashes"].append(first_prediction["scene_hash"])

    with pytest.raises(ValueError, match="leakage"):
        validate_stacking_plan(corrupted)


def test_cache_manifest_must_match_every_planned_prediction_once() -> None:
    router, official = _manifests()
    plan = build_stacking_plan(router, official, n_folds=5)
    cache_manifest = {
        "plan_sha256": plan["plan_sha256"],
        "predictions": [
            {
                "dataset": prediction["dataset"],
                "image_id": prediction["image_id"],
                "expert_id": prediction["expert_id"],
                "scene_hash": prediction["scene_hash"],
                "d0_cache_sha256": "a" * 64,
                "d1_cache_sha256": "b" * 64,
            }
            for prediction in plan["predictions"]
        ],
    }

    validate_expert_cache_manifest(plan, cache_manifest)
    cache_manifest["predictions"].pop()
    with pytest.raises(ValueError, match="missing"):
        validate_expert_cache_manifest(plan, cache_manifest)
