from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from paper1.experiments.covol.cache_oof_experts import (
    FORMAL_CANDIDATE_IDS,
    FORMAL_CONTROL_TYPES,
    FORMAL_TRAINING_SEEDS,
    build_stacking_plan,
    validate_expert_cache_manifest,
    validate_stacking_plan,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifests() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    official = [
        {
            "dataset": "toy",
            "image_id": f"official-{index}",
            "scene_id": f"scene-{index}",
            "cluster_id": f"cluster-{index}",
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
                "cluster_id": f"cluster-{index}",
                "split": "train",
            }
        )
    for index in range(10, 12):
        router.append(
            {
                "dataset": "toy",
                "image_id": f"dev-{index}",
                "scene_id": f"scene-{index}",
                "cluster_id": f"cluster-{index}",
                "split": "dev",
            }
        )
    for index in range(12, 14):
        router.append(
            {
                "dataset": "toy",
                "image_id": f"test-{index}",
                "scene_id": f"scene-{index}",
                "cluster_id": f"cluster-{index}",
                "split": "internal_test",
            }
        )
    return router, official


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _materialize_cache_manifest(
    tmp_path: Path,
    plan: dict[str, object],
    *,
    seeds: tuple[int, ...],
    candidate_ids: tuple[str, ...],
    control_types: tuple[str, ...],
) -> dict[str, object]:
    code_commit = "a" * 40
    experts = {item["expert_id"]: item for item in plan["experts"]}
    rows: list[dict[str, object]] = []
    for prediction in plan["predictions"]:
        expert = experts[prediction["expert_id"]]
        for seed in seeds:
            for candidate_id in candidate_ids:
                for control_type in control_types:
                    identity = (
                        f"{prediction['expert_id'].replace(':', '-')}-{seed}-"
                        f"{candidate_id}-{control_type}"
                    )
                    training_path = tmp_path / "training" / f"{identity}.jsonl"
                    if not training_path.exists():
                        training_rows = [
                            json.dumps(
                                {"dataset": "toy", "cluster_id": cluster_id},
                                sort_keys=True,
                            )
                            for cluster_id in expert["training_cluster_ids"]
                        ]
                        training_path.parent.mkdir(parents=True, exist_ok=True)
                        training_path.write_text(
                            "\n".join(training_rows) + "\n", encoding="utf-8"
                        )
                    checkpoint_path = tmp_path / "checkpoints" / f"{identity}.bin"
                    if not checkpoint_path.exists():
                        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                        checkpoint_path.write_bytes(identity.encode())
                    config_path = tmp_path / "configs" / f"{identity}.json"
                    config = {
                        "dataset": "toy",
                        "seed": seed,
                        "candidate_id": candidate_id,
                        "control_type": control_type,
                        "expert_id": prediction["expert_id"],
                        "code_commit": code_commit,
                        "checkpoint_sha256": _sha256(checkpoint_path),
                        "training_manifest_sha256": _sha256(training_path),
                    }
                    _write_json(config_path, config)
                    cache_path = (
                        tmp_path / "cache" / f"{identity}-{prediction['image_id']}.json"
                    )
                    cache = {
                        "dataset": "toy",
                        "image_id": prediction["image_id"],
                        "cluster_id": prediction["cluster_id"],
                        "seed": seed,
                        "candidate_id": candidate_id,
                        "control_type": control_type,
                        "expert_id": prediction["expert_id"],
                        "checkpoint_sha256": _sha256(checkpoint_path),
                        "prediction": [0.1, 0.2],
                    }
                    _write_json(cache_path, cache)
                    rows.append(
                        {
                            **cache,
                            "cluster_hash": prediction["cluster_hash"],
                            "checkpoint_path": checkpoint_path.relative_to(
                                tmp_path
                            ).as_posix(),
                            "checkpoint_sha256": _sha256(checkpoint_path),
                            "config_path": config_path.relative_to(tmp_path).as_posix(),
                            "config_sha256": _sha256(config_path),
                            "training_manifest_path": training_path.relative_to(
                                tmp_path
                            ).as_posix(),
                            "training_manifest_sha256": _sha256(training_path),
                            "cache_path": cache_path.relative_to(tmp_path).as_posix(),
                            "cache_sha256": _sha256(cache_path),
                        }
                    )
    return {
        "schema_version": "covol-expert-cache-v2",
        "plan_sha256": plan["plan_sha256"],
        "code_commit": code_commit,
        "predictions": rows,
    }


def test_builds_cluster_disjoint_oof_and_final_expert_plan() -> None:
    router, official = _manifests()
    plan = build_stacking_plan(router, official, n_folds=5)

    validate_stacking_plan(plan)
    assert plan["version"] == 2
    assert plan["status"] == "PLANNED_NOT_TRAINED"
    assert len(plan["predictions"]) == len(router)
    assert (
        sum(
            prediction["prediction_scope"] == "oof"
            for prediction in plan["predictions"]
        )
        == 10
    )


def test_same_cluster_cannot_cross_router_splits_even_with_different_scenes() -> None:
    router, official = _manifests()
    router[10]["cluster_id"] = router[0]["cluster_id"]
    router[10]["scene_id"] = "a-different-scene-label"

    with pytest.raises(ValueError, match="cluster crosses splits"):
        build_stacking_plan(router, official, n_folds=5)


def test_rejects_training_cluster_in_prediction_scope() -> None:
    router, official = _manifests()
    plan = build_stacking_plan(router, official, n_folds=5)
    corrupted = deepcopy(plan)
    first_prediction = corrupted["predictions"][0]
    expert = next(
        item
        for item in corrupted["experts"]
        if item["expert_id"] == first_prediction["expert_id"]
    )
    expert["training_cluster_hashes"].append(first_prediction["cluster_hash"])

    with pytest.raises(ValueError, match="disagree|leakage"):
        validate_stacking_plan(corrupted)


def test_entity_cache_covers_three_seeds_candidates_and_controls(
    tmp_path: Path,
) -> None:
    router, official = _manifests()
    plan = build_stacking_plan(router, official, n_folds=5)
    cache_manifest = _materialize_cache_manifest(
        tmp_path,
        plan,
        seeds=FORMAL_TRAINING_SEEDS,
        candidate_ids=FORMAL_CANDIDATE_IDS,
        control_types=FORMAL_CONTROL_TYPES,
    )

    validate_expert_cache_manifest(
        plan,
        cache_manifest,
        repository_root=tmp_path,
    )
    assert len(cache_manifest["predictions"]) == len(plan["predictions"]) * 18


def test_tampered_checkpoint_and_missing_seed_hard_fail(tmp_path: Path) -> None:
    router, official = _manifests()
    plan = build_stacking_plan(router, official, n_folds=5)
    cache_manifest = _materialize_cache_manifest(
        tmp_path,
        plan,
        seeds=(17,),
        candidate_ids=("D0", "D1"),
        control_types=("main",),
    )
    row = cache_manifest["predictions"][0]
    (tmp_path / row["checkpoint_path"]).write_bytes(b"tampered")

    with pytest.raises(ValueError, match="checkpoint file SHA256 mismatch"):
        validate_expert_cache_manifest(
            plan,
            cache_manifest,
            repository_root=tmp_path,
            training_seeds=(17,),
            candidate_ids=("D0", "D1"),
            control_types=("main",),
        )

    cache_manifest = _materialize_cache_manifest(
        tmp_path / "fresh",
        plan,
        seeds=(17, 29),
        candidate_ids=("D0",),
        control_types=("main",),
    )
    cache_manifest["predictions"].pop()
    with pytest.raises(ValueError, match="missing"):
        validate_expert_cache_manifest(
            plan,
            cache_manifest,
            repository_root=tmp_path / "fresh",
            training_seeds=(17, 29),
            candidate_ids=("D0",),
            control_types=("main",),
        )
