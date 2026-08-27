"""Plan and audit cluster-OOF expert caches with entity-level file lineage."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from paper1.experiments.covol.scientific_gate import (
        DEFAULT_SCIENTIFIC_GATE,
        require_covol_action_authorized,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from scientific_gate import (  # type: ignore
        DEFAULT_SCIENTIFIC_GATE,
        require_covol_action_authorized,
    )

ROUTER_SPLITS = frozenset({"train", "dev", "internal_test"})
FORMAL_TRAINING_SEEDS = (17, 29, 43)
FORMAL_CANDIDATE_IDS = ("D0", "D1")
FORMAL_CONTROL_TYPES = ("main", "twin", "shuffled")


def _stable_hash(*parts: object) -> str:
    encoded = "/".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _cluster_hash(dataset: str, cluster_id: str) -> str:
    return _stable_hash("cluster", dataset, cluster_id)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    cluster_splits: dict[tuple[str, str], str] = {}
    for index, record in enumerate(records):
        dataset = str(record.get("dataset", "")).strip()
        image_id = str(record.get("image_id", "")).strip()
        scene_id = str(record.get("scene_id", "")).strip()
        cluster_id = str(record.get("cluster_id", scene_id)).strip()
        split = str(record.get("split", "")).strip()
        if (
            not dataset
            or not image_id
            or not scene_id
            or not cluster_id
            or split not in ROUTER_SPLITS
        ):
            raise ValueError(f"router record {index} has invalid required fields")
        image_key = (dataset, image_id)
        if image_key in seen_images:
            raise ValueError(f"duplicate router image: {image_key}")
        cluster_key = (dataset, cluster_id)
        prior_split = cluster_splits.setdefault(cluster_key, split)
        if prior_split != split:
            raise ValueError(f"router cluster crosses splits: {cluster_key}")
        seen_images.add(image_key)
        normalized.append(
            {
                "dataset": dataset,
                "image_id": image_id,
                "scene_id": scene_id,
                "cluster_id": cluster_id,
                "split": split,
            }
        )
    if not normalized:
        raise ValueError("router manifest must not be empty")
    return normalized


def _official_training_clusters(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, set[str]]:
    clusters: dict[str, set[str]] = defaultdict(set)
    for index, record in enumerate(records):
        dataset = str(record.get("dataset", "")).strip()
        scene_id = str(record.get("scene_id", "")).strip()
        cluster_id = str(record.get("cluster_id", scene_id)).strip()
        official_split = str(record.get("official_split", "")).strip()
        if not dataset or not cluster_id or official_split != "train":
            raise ValueError(f"official training record {index} is invalid")
        clusters[dataset].add(cluster_id)
    if not clusters:
        raise ValueError("official training manifest must not be empty")
    return clusters


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
    """Build cluster-disjoint OOF and final expert prediction scopes."""

    if n_folds < 2:
        raise ValueError("n_folds must be at least 2")
    router = _router_records(router_manifest)
    official_clusters = _official_training_clusters(official_training_manifest)
    by_dataset: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in router:
        by_dataset[record["dataset"]].append(record)

    experts: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    for dataset in sorted(by_dataset):
        if dataset not in official_clusters:
            raise ValueError(f"{dataset}: no official training clusters")
        records = by_dataset[dataset]
        split_clusters = {
            split: {
                record["cluster_id"] for record in records if record["split"] == split
            }
            for split in ROUTER_SPLITS
        }
        router_clusters = set().union(*split_clusters.values())
        missing = router_clusters - official_clusters[dataset]
        if missing:
            raise ValueError(
                f"{dataset}: router clusters absent from official training pool"
            )
        train_clusters = split_clusters["train"]
        if len(train_clusters) < n_folds:
            raise ValueError(
                f"{dataset}: {len(train_clusters)} train clusters cannot fill "
                f"{n_folds} folds"
            )
        forbidden_final = split_clusters["dev"] | split_clusters["internal_test"]
        available_training = official_clusters[dataset] - forbidden_final
        ordered_train_clusters = sorted(
            train_clusters,
            key=lambda cluster: _stable_hash(dataset, seed, "oof-fold", cluster),
        )
        fold_clusters = {
            fold: set(ordered_train_clusters[fold::n_folds]) for fold in range(n_folds)
        }

        for fold in range(n_folds):
            prediction_clusters = fold_clusters[fold]
            training_clusters = available_training - prediction_clusters
            expert_id = f"{dataset}:oof:{fold}"
            training_hashes = sorted(
                _cluster_hash(dataset, cluster) for cluster in training_clusters
            )
            experts.append(
                {
                    "dataset": dataset,
                    "expert_id": expert_id,
                    "prediction_scope": "oof",
                    "fold": fold,
                    "training_cluster_ids": sorted(training_clusters),
                    "training_cluster_hashes": training_hashes,
                    "training_cluster_set_sha256": _hash_set(training_hashes),
                    "prediction_cluster_hashes": sorted(
                        _cluster_hash(dataset, cluster)
                        for cluster in prediction_clusters
                    ),
                    "prediction_cluster_ids": sorted(prediction_clusters),
                }
            )

        final_expert_id = f"{dataset}:final"
        final_training_hashes = sorted(
            _cluster_hash(dataset, cluster) for cluster in available_training
        )
        experts.append(
            {
                "dataset": dataset,
                "expert_id": final_expert_id,
                "prediction_scope": "final",
                "fold": None,
                "training_cluster_ids": sorted(available_training),
                "training_cluster_hashes": final_training_hashes,
                "training_cluster_set_sha256": _hash_set(final_training_hashes),
                "prediction_cluster_hashes": sorted(
                    _cluster_hash(dataset, cluster) for cluster in forbidden_final
                ),
                "prediction_cluster_ids": sorted(forbidden_final),
            }
        )

        cluster_to_fold = {
            cluster: fold
            for fold, clusters in fold_clusters.items()
            for cluster in clusters
        }
        for record in records:
            if record["split"] == "train":
                fold = cluster_to_fold[record["cluster_id"]]
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
                    "cluster_hash": _cluster_hash(dataset, record["cluster_id"]),
                }
            )

    payload = {
        "version": 2,
        "status": "PLANNED_NOT_TRAINED",
        "fold_assignment_seed": seed,
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
    """Hard-fail on expert/router cluster leakage or duplicate predictions."""

    if plan.get("version") != 2:
        raise ValueError("stacking plan must use version 2")
    experts_raw = plan.get("experts")
    predictions_raw = plan.get("predictions")
    if not isinstance(experts_raw, list) or not isinstance(predictions_raw, list):
        raise ValueError("plan must contain experts and predictions lists")
    experts: dict[str, Mapping[str, Any]] = {}
    for expert in experts_raw:
        expert_id = str(expert.get("expert_id", ""))
        if not expert_id or expert_id in experts:
            raise ValueError("expert IDs must be unique and nonempty")
        training = set(expert.get("training_cluster_hashes", []))
        prediction = set(expert.get("prediction_cluster_hashes", []))
        expected_training_hashes = {
            _cluster_hash(str(expert.get("dataset", "")), str(cluster))
            for cluster in expert.get("training_cluster_ids", [])
        }
        expected_prediction_hashes = {
            _cluster_hash(str(expert.get("dataset", "")), str(cluster))
            for cluster in expert.get("prediction_cluster_ids", [])
        }
        if training != expected_training_hashes or prediction != (
            expected_prediction_hashes
        ):
            raise ValueError(f"{expert_id}: raw cluster IDs and hashes disagree")
        if training & prediction:
            raise ValueError(f"{expert_id}: training/prediction cluster leakage")
        if str(expert.get("training_cluster_set_sha256", "")) != _hash_set(training):
            raise ValueError(f"{expert_id}: training cluster hash-set mismatch")
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
        cluster_hash = str(prediction.get("cluster_hash", ""))
        if cluster_hash in set(expert.get("training_cluster_hashes", [])):
            raise ValueError(f"{image_key}: predicted cluster was used for training")
        if cluster_hash not in set(expert.get("prediction_cluster_hashes", [])):
            raise ValueError(f"{image_key}: cluster absent from prediction scope")
        split = str(prediction.get("split", ""))
        expected_scope = "oof" if split == "train" else "final"
        if prediction.get("prediction_scope") != expected_scope:
            raise ValueError(f"{image_key}: incorrect prediction scope")
        seen_images.add(image_key)

    payload = {key: value for key, value in plan.items() if key != "plan_sha256"}
    expected_hash = _with_plan_hash(dict(payload))["plan_sha256"]
    if plan.get("plan_sha256") != expected_hash:
        raise ValueError("plan_sha256 mismatch")


def _resolve_bound_file(
    repository_root: Path,
    row: Mapping[str, Any],
    *,
    prefix: str,
) -> Path:
    relative = Path(str(row.get(f"{prefix}_path", "")).strip())
    if not str(relative) or relative.is_absolute():
        raise ValueError(f"{prefix}_path must be repository-relative")
    root = repository_root.resolve(strict=True)
    resolved = (root / relative).resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{prefix}_path escapes repository root") from error
    if not resolved.is_file():
        raise ValueError(f"missing {prefix} file: {relative}")
    expected = str(row.get(f"{prefix}_sha256", ""))
    if _file_sha256(resolved) != expected:
        raise ValueError(f"{prefix} file SHA256 mismatch")
    return resolved


def _json_object(path: Path, *, name: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{name} file must contain a JSON object")
    return value


def _validate_identity(
    value: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
    fields: Sequence[str],
    name: str,
) -> None:
    for field in fields:
        if value.get(field) != expected.get(field):
            raise ValueError(f"{name} identity mismatch for {field}")


def validate_expert_cache_manifest(
    plan: Mapping[str, Any],
    cache_manifest: Mapping[str, Any],
    *,
    repository_root: Path,
    training_seeds: Sequence[int] = FORMAL_TRAINING_SEEDS,
    candidate_ids: Sequence[str] = FORMAL_CANDIDATE_IDS,
    control_types: Sequence[str] = FORMAL_CONTROL_TYPES,
) -> None:
    """Open and hash every entity-level checkpoint/config/cache dependency."""

    validate_stacking_plan(plan)
    if cache_manifest.get("schema_version") != "covol-expert-cache-v2":
        raise ValueError("cache manifest must use covol-expert-cache-v2")
    if cache_manifest.get("plan_sha256") != plan.get("plan_sha256"):
        raise ValueError("cache manifest references a different stacking plan")
    code_commit = str(cache_manifest.get("code_commit", ""))
    if len(code_commit) != 40 or any(
        char not in "0123456789abcdef" for char in code_commit
    ):
        raise ValueError("cache manifest requires a full lowercase code commit")
    rows = cache_manifest.get("predictions")
    if not isinstance(rows, list):
        raise ValueError("cache manifest predictions must be a list")
    planned = {(row["dataset"], row["image_id"]): row for row in plan["predictions"]}
    expected_keys = {
        (dataset, image_id, seed, candidate_id, control_type)
        for dataset, image_id in planned
        for seed in training_seeds
        for candidate_id in candidate_ids
        for control_type in control_types
    }
    experts = {row["expert_id"]: row for row in plan["experts"]}
    seen: set[tuple[str, str, int, str, str]] = set()
    identity_fields = (
        "dataset",
        "seed",
        "candidate_id",
        "control_type",
        "expert_id",
    )
    for row in rows:
        seed = row.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("cache seed must be an integer")
        key = (
            str(row.get("dataset", "")),
            str(row.get("image_id", "")),
            seed,
            str(row.get("candidate_id", "")),
            str(row.get("control_type", "")),
        )
        if key in seen or key not in expected_keys:
            raise ValueError("cache entity key is duplicate or outside frozen coverage")
        prediction = planned[(key[0], key[1])]
        for field in ("expert_id", "cluster_id", "cluster_hash"):
            if row.get(field) != prediction.get(field):
                raise ValueError(f"{key}: cache {field} mismatch")

        checkpoint_path = _resolve_bound_file(repository_root, row, prefix="checkpoint")
        config_path = _resolve_bound_file(repository_root, row, prefix="config")
        training_path = _resolve_bound_file(
            repository_root, row, prefix="training_manifest"
        )
        cache_path = _resolve_bound_file(repository_root, row, prefix="cache")
        config = _json_object(config_path, name="config")
        _validate_identity(config, expected=row, fields=identity_fields, name="config")
        if config.get("code_commit") != code_commit:
            raise ValueError("config code commit mismatch")
        if config.get("checkpoint_sha256") != _file_sha256(checkpoint_path):
            raise ValueError("config/checkpoint lineage mismatch")
        if config.get("training_manifest_sha256") != _file_sha256(training_path):
            raise ValueError("config/training-manifest lineage mismatch")

        training_rows = _read_jsonl(training_path)
        training_cluster_hashes = {
            _cluster_hash(key[0], str(item.get("cluster_id", "")).strip())
            for item in training_rows
            if str(item.get("dataset", "")).strip() == key[0]
            and str(item.get("cluster_id", "")).strip()
        }
        expected_training = set(
            experts[str(row["expert_id"])]["training_cluster_hashes"]
        )
        if training_cluster_hashes != expected_training:
            raise ValueError("training manifest cluster set differs from frozen plan")
        if str(row["cluster_hash"]) in training_cluster_hashes:
            raise ValueError("prediction cluster appears in expert training manifest")

        cache = _json_object(cache_path, name="cache")
        _validate_identity(
            cache,
            expected=row,
            fields=(*identity_fields, "image_id", "cluster_id"),
            name="cache",
        )
        if cache.get("checkpoint_sha256") != _file_sha256(checkpoint_path):
            raise ValueError("cache/checkpoint lineage mismatch")
        seen.add(key)
    if seen != expected_keys:
        raise ValueError("cache manifest is missing frozen entity predictions")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--scientific-gate", type=Path, default=DEFAULT_SCIENTIFIC_GATE)
    parser.add_argument("--router-manifest", type=Path, required=True)
    parser.add_argument("--official-training-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260821)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    require_covol_action_authorized(
        step003_authorization_path=args.authorization,
        scientific_gate_path=args.scientific_gate,
        scientific_action="step005",
        step003_action="step005",
    )
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
