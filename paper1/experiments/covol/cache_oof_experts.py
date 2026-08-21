"""Plan and audit scene-group out-of-fold expert stacking caches."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROUTER_SPLITS = frozenset({"train", "dev", "internal_test"})


def _stable_hash(*parts: object) -> str:
    encoded = "/".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scene_hash(dataset: str, scene_id: str) -> str:
    return _stable_hash("scene", dataset, scene_id)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(value)
    return records


def _router_records(
    records: Iterable[Mapping[str, Any]],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen_images: set[tuple[str, str]] = set()
    scene_splits: dict[tuple[str, str], str] = {}

    for index, record in enumerate(records):
        dataset = str(record.get("dataset", "")).strip()
        image_id = str(record.get("image_id", "")).strip()
        scene_id = str(record.get("scene_id", "")).strip()
        split = str(record.get("split", "")).strip()
        if not dataset or not image_id or not scene_id or split not in ROUTER_SPLITS:
            raise ValueError(f"router record {index} has invalid required fields")
        image_key = (dataset, image_id)
        if image_key in seen_images:
            raise ValueError(f"duplicate router image: {image_key}")
        scene_key = (dataset, scene_id)
        prior_split = scene_splits.setdefault(scene_key, split)
        if prior_split != split:
            raise ValueError(f"router scene crosses splits: {scene_key}")
        seen_images.add(image_key)
        normalized.append(
            {
                "dataset": dataset,
                "image_id": image_id,
                "scene_id": scene_id,
                "split": split,
            }
        )
    if not normalized:
        raise ValueError("router manifest must not be empty")
    return normalized


def _official_training_scenes(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, set[str]]:
    scenes: dict[str, set[str]] = defaultdict(set)
    for index, record in enumerate(records):
        dataset = str(record.get("dataset", "")).strip()
        scene_id = str(record.get("scene_id", "")).strip()
        official_split = str(record.get("official_split", "")).strip()
        if not dataset or not scene_id or official_split != "train":
            raise ValueError(f"official training record {index} is invalid")
        scenes[dataset].add(scene_id)
    if not scenes:
        raise ValueError("official training manifest must not be empty")
    return scenes


def _hash_set(values: Iterable[str]) -> str:
    encoded = "\n".join(sorted(values)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _with_plan_hash(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {**payload, "plan_sha256": hashlib.sha256(encoded).hexdigest()}


def build_stacking_plan(
    router_manifest: Iterable[Mapping[str, Any]],
    official_training_manifest: Iterable[Mapping[str, Any]],
    *,
    n_folds: int = 5,
    seed: int = 20260821,
) -> dict[str, Any]:
    """Build expert-train and prediction scopes for leakage-free stacking."""

    if n_folds < 2:
        raise ValueError("n_folds must be at least 2")
    router = _router_records(router_manifest)
    official_scenes = _official_training_scenes(official_training_manifest)
    by_dataset: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in router:
        by_dataset[record["dataset"]].append(record)

    experts: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    for dataset in sorted(by_dataset):
        if dataset not in official_scenes:
            raise ValueError(f"{dataset}: no official training scenes")
        records = by_dataset[dataset]
        split_scenes = {
            split: {
                record["scene_id"] for record in records if record["split"] == split
            }
            for split in ROUTER_SPLITS
        }
        router_scenes = set().union(*split_scenes.values())
        missing = router_scenes - official_scenes[dataset]
        if missing:
            raise ValueError(
                f"{dataset}: router scenes absent from official training pool"
            )
        train_scenes = split_scenes["train"]
        if len(train_scenes) < n_folds:
            raise ValueError(
                f"{dataset}: {len(train_scenes)} train scenes cannot fill "
                f"{n_folds} folds"
            )
        forbidden_final = split_scenes["dev"] | split_scenes["internal_test"]
        available_training = official_scenes[dataset] - forbidden_final
        ordered_train_scenes = sorted(
            train_scenes,
            key=lambda scene: _stable_hash(dataset, seed, "oof-fold", scene),
        )
        fold_scenes = {
            fold: set(ordered_train_scenes[fold::n_folds]) for fold in range(n_folds)
        }

        for fold in range(n_folds):
            prediction_scenes = fold_scenes[fold]
            training_scenes = available_training - prediction_scenes
            expert_id = f"{dataset}:oof:{fold}"
            experts.append(
                {
                    "dataset": dataset,
                    "expert_id": expert_id,
                    "prediction_scope": "oof",
                    "fold": fold,
                    "training_scene_hashes": sorted(
                        _scene_hash(dataset, scene) for scene in training_scenes
                    ),
                    "training_scene_set_sha256": _hash_set(
                        _scene_hash(dataset, scene) for scene in training_scenes
                    ),
                    "prediction_scene_hashes": sorted(
                        _scene_hash(dataset, scene) for scene in prediction_scenes
                    ),
                }
            )

        final_expert_id = f"{dataset}:final"
        experts.append(
            {
                "dataset": dataset,
                "expert_id": final_expert_id,
                "prediction_scope": "final",
                "fold": None,
                "training_scene_hashes": sorted(
                    _scene_hash(dataset, scene) for scene in available_training
                ),
                "training_scene_set_sha256": _hash_set(
                    _scene_hash(dataset, scene) for scene in available_training
                ),
                "prediction_scene_hashes": sorted(
                    _scene_hash(dataset, scene) for scene in forbidden_final
                ),
            }
        )

        scene_to_fold = {
            scene: fold for fold, scenes in fold_scenes.items() for scene in scenes
        }
        for record in records:
            if record["split"] == "train":
                fold = scene_to_fold[record["scene_id"]]
                expert_id = f"{dataset}:oof:{fold}"
                scope = "oof"
            else:
                expert_id = final_expert_id
                scope = "final"
            predictions.append(
                {
                    **record,
                    "expert_id": expert_id,
                    "prediction_scope": scope,
                    "scene_hash": _scene_hash(dataset, record["scene_id"]),
                }
            )

    payload = {
        "version": 1,
        "status": "PLANNED_NOT_TRAINED",
        "seed": seed,
        "n_folds": n_folds,
        "experts": sorted(experts, key=lambda value: value["expert_id"]),
        "predictions": sorted(
            predictions,
            key=lambda value: (value["dataset"], value["split"], value["image_id"]),
        ),
    }
    plan = _with_plan_hash(payload)
    validate_stacking_plan(plan)
    return plan


def validate_stacking_plan(plan: Mapping[str, Any]) -> None:
    """Hard-fail on expert/router scene leakage or duplicate predictions."""

    experts_raw = plan.get("experts")
    predictions_raw = plan.get("predictions")
    if not isinstance(experts_raw, list) or not isinstance(predictions_raw, list):
        raise ValueError("plan must contain experts and predictions lists")
    experts: dict[str, Mapping[str, Any]] = {}
    for expert in experts_raw:
        expert_id = str(expert.get("expert_id", ""))
        if not expert_id or expert_id in experts:
            raise ValueError("expert IDs must be unique and nonempty")
        training = set(expert.get("training_scene_hashes", []))
        prediction = set(expert.get("prediction_scene_hashes", []))
        if training & prediction:
            raise ValueError(f"{expert_id}: training/prediction scene leakage")
        if str(expert.get("training_scene_set_sha256", "")) != _hash_set(training):
            raise ValueError(f"{expert_id}: training scene hash-set mismatch")
        experts[expert_id] = expert

    seen_images: set[tuple[str, str]] = set()
    for prediction in predictions_raw:
        dataset = str(prediction.get("dataset", ""))
        image_id = str(prediction.get("image_id", ""))
        image_key = (dataset, image_id)
        if not dataset or not image_id or image_key in seen_images:
            raise ValueError("each router image must have exactly one prediction")
        expert_id = str(prediction.get("expert_id", ""))
        if expert_id not in experts:
            raise ValueError(f"{image_key}: unknown expert {expert_id!r}")
        expert = experts[expert_id]
        scene_hash = str(prediction.get("scene_hash", ""))
        if scene_hash in set(expert.get("training_scene_hashes", [])):
            raise ValueError(f"{image_key}: predicted scene was used for training")
        if scene_hash not in set(expert.get("prediction_scene_hashes", [])):
            raise ValueError(f"{image_key}: scene absent from prediction scope")
        split = str(prediction.get("split", ""))
        expected_scope = "oof" if split == "train" else "final"
        if prediction.get("prediction_scope") != expected_scope:
            raise ValueError(f"{image_key}: incorrect prediction scope")
        seen_images.add(image_key)

    payload = {key: value for key, value in plan.items() if key != "plan_sha256"}
    expected_hash = _with_plan_hash(dict(payload))["plan_sha256"]
    if plan.get("plan_sha256") != expected_hash:
        raise ValueError("plan_sha256 mismatch")


def validate_expert_cache_manifest(
    plan: Mapping[str, Any],
    cache_manifest: Mapping[str, Any],
) -> None:
    """Validate actual cache rows against a previously frozen stacking plan."""

    validate_stacking_plan(plan)
    if cache_manifest.get("plan_sha256") != plan.get("plan_sha256"):
        raise ValueError("cache manifest references a different stacking plan")
    rows = cache_manifest.get("predictions")
    if not isinstance(rows, list):
        raise ValueError("cache manifest predictions must be a list")
    expected = {(row["dataset"], row["image_id"]): row for row in plan["predictions"]}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("dataset", "")), str(row.get("image_id", "")))
        if key in seen or key not in expected:
            raise ValueError("cache predictions must match plan exactly once")
        if row.get("expert_id") != expected[key]["expert_id"]:
            raise ValueError(f"{key}: cache used an unexpected expert")
        if row.get("scene_hash") != expected[key]["scene_hash"]:
            raise ValueError(f"{key}: cache scene hash mismatch")
        for field in ("d0_cache_sha256", "d1_cache_sha256"):
            value = str(row.get(field, ""))
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value
            ):
                raise ValueError(f"{key}: invalid {field}")
        seen.add(key)
    if seen != set(expected):
        raise ValueError("cache manifest is missing planned predictions")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--router-manifest", type=Path, required=True)
    parser.add_argument("--official-training-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260821)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    plan = build_stacking_plan(
        _read_jsonl(args.router_manifest),
        _read_jsonl(args.official_training_manifest),
        n_folds=args.folds,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
