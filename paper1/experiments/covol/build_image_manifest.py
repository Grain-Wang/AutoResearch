"""Run the Step-008 official-test integrity audit after method freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SPLIT_ORDER = ("train", "dev", "internal_test")


def _stable_hash(*parts: object) -> str:
    payload = "/".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


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


def _validated_records(
    path: Path,
    *,
    dataset: str,
    required_split: str,
) -> list[dict[str, Any]]:
    records = _read_jsonl(path)
    seen_images: set[str] = set()
    seen_rgb_hashes: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        image_id = str(record.get("image_id", "")).strip()
        scene_id = str(record.get("scene_id", "")).strip()
        official_split = str(record.get("official_split", "")).strip()
        record_dataset = str(record.get("dataset", dataset)).strip()
        rgb_sha256 = str(record.get("rgb_sha256", "")).strip().lower()
        sequence_id = str(record.get("sequence_id", "")).strip()
        frame_index_raw = record.get("frame_index")

        if not image_id or not scene_id or not sequence_id:
            raise ValueError(
                f"{path}: record {index} lacks image_id, scene_id, or sequence_id"
            )
        if not _valid_sha256(rgb_sha256):
            raise ValueError(f"{path}: record {index} has invalid rgb_sha256")
        try:
            frame_index = int(frame_index_raw)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{path}: record {index} has invalid frame_index"
            ) from error
        if record_dataset != dataset:
            raise ValueError(
                f"{path}: dataset {record_dataset!r} does not match {dataset!r}"
            )
        if official_split != required_split:
            raise ValueError(
                f"{path}: {image_id} is {official_split!r}, "
                f"expected {required_split!r}"
            )
        if image_id in seen_images:
            raise ValueError(f"{path}: duplicate image_id {image_id!r}")
        if rgb_sha256 in seen_rgb_hashes:
            raise ValueError(f"{path}: duplicate RGB content hash {rgb_sha256!r}")

        seen_images.add(image_id)
        seen_rgb_hashes.add(rgb_sha256)
        normalized.append(
            {
                **record,
                "dataset": dataset,
                "image_id": image_id,
                "scene_id": scene_id,
                "sequence_id": sequence_id,
                "frame_index": frame_index,
                "rgb_sha256": rgb_sha256,
                "official_split": official_split,
            }
        )

    return normalized


def _assert_no_benchmark_overlap(
    training_records: Iterable[Mapping[str, Any]],
    test_records: Iterable[Mapping[str, Any]],
    *,
    dataset: str,
) -> tuple[set[str], set[str], set[str], set[str]]:
    train_images = {str(record["image_id"]) for record in training_records}
    train_scenes = {str(record["scene_id"]) for record in training_records}
    train_sequences = {str(record["sequence_id"]) for record in training_records}
    train_rgb_hashes = {str(record["rgb_sha256"]) for record in training_records}
    test_images = {str(record["image_id"]) for record in test_records}
    test_scenes = {str(record["scene_id"]) for record in test_records}
    test_sequences = {str(record["sequence_id"]) for record in test_records}
    test_rgb_hashes = {str(record["rgb_sha256"]) for record in test_records}
    image_overlap = train_images & test_images
    scene_overlap = train_scenes & test_scenes
    sequence_overlap = train_sequences & test_sequences
    rgb_overlap = train_rgb_hashes & test_rgb_hashes

    if image_overlap or scene_overlap or sequence_overlap or rgb_overlap:
        raise ValueError(
            f"{dataset}: official-test leakage detected; "
            f"image_overlap={sorted(image_overlap)[:5]}, "
            f"scene_overlap={sorted(scene_overlap)[:5]}, "
            f"sequence_overlap={sorted(sequence_overlap)[:5]}, "
            f"rgb_overlap={sorted(rgb_overlap)[:5]}"
        )
    return image_overlap, scene_overlap, sequence_overlap, rgb_overlap


def _select_scene_grouped(
    records: list[dict[str, Any]],
    *,
    dataset: str,
    split_counts: Mapping[str, int],
    seed: int,
    max_images_per_component: Mapping[str, int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if set(split_counts) != set(SPLIT_ORDER):
        raise ValueError(f"split_counts must contain exactly {SPLIT_ORDER}")
    if any(count <= 0 for count in split_counts.values()):
        raise ValueError("all split counts must be positive")
    component_caps = (
        {split: int(split_counts[split]) for split in SPLIT_ORDER}
        if max_images_per_component is None
        else {
            split: int(max_images_per_component.get(split, 0)) for split in SPLIT_ORDER
        }
    )
    if any(cap <= 0 for cap in component_caps.values()):
        raise ValueError("all max_images_per_component values must be positive")

    parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(node: tuple[str, str]) -> tuple[str, str]:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: tuple[str, str], right: tuple[str, str]) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    for record in records:
        union(
            ("scene", str(record["scene_id"])),
            ("sequence", str(record["sequence_id"])),
        )

    component_nodes: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for node in parent:
        component_nodes[find(node)].append(node)
    component_key_by_root = {
        root: hashlib.sha256(
            "\n".join(
                f"{kind}:{identifier}" for kind, identifier in sorted(nodes)
            ).encode("utf-8")
        ).hexdigest()
        for root, nodes in component_nodes.items()
    }
    by_component: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        root = find(("scene", str(record["scene_id"])))
        by_component[component_key_by_root[root]].append(record)

    component_ids = sorted(
        by_component,
        key=lambda component: _stable_hash(
            dataset,
            seed,
            "scene-sequence-component",
            component,
        ),
    )
    component_cursor = 0
    selected: list[dict[str, Any]] = []
    selected_cluster_counts: dict[str, int] = {}

    for split in SPLIT_ORDER:
        remaining = int(split_counts[split])
        while remaining:
            if component_cursor >= len(component_ids):
                raise ValueError(
                    f"{dataset}: insufficient scene/sequence-disjoint training "
                    "images "
                    f"for split {split!r}; {remaining} still required"
                )
            component_id = component_ids[component_cursor]
            component_cursor += 1
            component_records = sorted(
                by_component[component_id],
                key=lambda record: _stable_hash(
                    dataset,
                    seed,
                    "image",
                    record["image_id"],
                ),
            )
            take = min(
                remaining,
                len(component_records),
                component_caps[split],
            )
            for record in component_records[:take]:
                selected.append(
                    {
                        **record,
                        "cluster_id": component_id,
                        "split": split,
                        "selection_hash": _stable_hash(
                            dataset,
                            seed,
                            split,
                            record["image_id"],
                        ),
                    }
                )
            remaining -= take
        selected_cluster_counts[split] = len(
            {
                str(record["cluster_id"])
                for record in selected
                if record["split"] == split
            }
        )

    return selected, selected_cluster_counts


def build_dataset_manifest(
    spec: Mapping[str, Any],
    *,
    config_dir: Path,
    default_seed: int,
    allow_official_test_read: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not allow_official_test_read:
        raise PermissionError(
            "official benchmark test manifests are frozen until Step 008; "
            "use build_training_pilot_manifest.py during Step 003"
        )
    dataset = str(spec["name"])
    training_path = (config_dir / str(spec["training_manifest"])).resolve()
    test_path = (config_dir / str(spec["official_test_manifest"])).resolve()
    split_counts = {split: int(spec["split_counts"][split]) for split in SPLIT_ORDER}
    select_count = int(spec.get("select_count", sum(split_counts.values())))
    seed = int(spec.get("seed", default_seed))

    if sum(split_counts.values()) != select_count:
        raise ValueError(
            f"{dataset}: split counts do not sum to select_count={select_count}"
        )

    training_records = _validated_records(
        training_path,
        dataset=dataset,
        required_split="train",
    )
    test_records = _validated_records(
        test_path,
        dataset=dataset,
        required_split="test",
    )
    (
        image_overlap,
        scene_overlap,
        sequence_overlap,
        rgb_overlap,
    ) = _assert_no_benchmark_overlap(
        training_records,
        test_records,
        dataset=dataset,
    )
    selected, cluster_counts = _select_scene_grouped(
        training_records,
        dataset=dataset,
        split_counts=split_counts,
        seed=seed,
    )

    selected_scenes: dict[str, set[str]] = defaultdict(set)
    selected_sequences: dict[str, set[str]] = defaultdict(set)
    for record in selected:
        selected_scenes[str(record["split"])].add(str(record["scene_id"]))
        selected_sequences[str(record["split"])].add(str(record["sequence_id"]))
    for left_index, left in enumerate(SPLIT_ORDER):
        for right in SPLIT_ORDER[left_index + 1 :]:
            if selected_scenes[left] & selected_scenes[right]:
                raise AssertionError(
                    f"{dataset}: internal scene leakage between {left} and {right}"
                )
            if selected_sequences[left] & selected_sequences[right]:
                raise AssertionError(
                    f"{dataset}: internal sequence leakage between {left} and {right}"
                )

    audit = {
        "dataset": dataset,
        "status": "PASS",
        "seed": seed,
        "input": {
            "official_training_count": len(training_records),
            "official_test_count": len(test_records),
            "training_manifest_sha256": _file_sha256(training_path),
            "official_test_manifest_sha256": _file_sha256(test_path),
        },
        "selected_counts": {
            split: sum(record["split"] == split for record in selected)
            for split in SPLIT_ORDER
        },
        "selected_cluster_counts": cluster_counts,
        "official_test_overlap": {
            "image_count": len(image_overlap),
            "scene_count": len(scene_overlap),
            "sequence_count": len(sequence_overlap),
            "rgb_sha256_count": len(rgb_overlap),
        },
    }
    return selected, audit


def build_manifests(
    config_path: Path,
    output_path: Path,
    audit_path: Path,
    *,
    allow_official_test_read: bool = False,
) -> None:
    if not allow_official_test_read:
        raise PermissionError(
            "official benchmark test manifests are frozen until Step 008; "
            "pass --allow-official-test-read only after the method is frozen"
        )
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("datasets"), list):
        raise ValueError("config must contain a datasets list")

    default_seed = int(config.get("seed", 20260821))
    all_records: list[dict[str, Any]] = []
    dataset_audits: list[dict[str, Any]] = []
    for spec in config["datasets"]:
        if not isinstance(spec, dict):
            raise ValueError("each dataset spec must be a JSON object")
        records, audit = build_dataset_manifest(
            spec,
            config_dir=config_path.parent,
            default_seed=default_seed,
            allow_official_test_read=True,
        )
        all_records.extend(records)
        dataset_audits.append(audit)

    all_records.sort(
        key=lambda record: (
            str(record["dataset"]),
            SPLIT_ORDER.index(str(record["split"])),
            str(record["selection_hash"]),
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in all_records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    audit_payload = {
        "status": "PASS",
        "config_sha256": _file_sha256(config_path),
        "record_count": len(all_records),
        "manifest_sha256": _file_sha256(output_path),
        "datasets": dataset_audits,
    }
    audit_path.write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument(
        "--allow-official-test-read",
        action="store_true",
        help="Step-008-only unlock after every method and threshold is frozen",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_manifests(
        args.config,
        args.output,
        args.audit,
        allow_official_test_read=args.allow_official_test_read,
    )


if __name__ == "__main__":
    main()
