from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from paper1.experiments.covol.build_image_manifest import (
    _select_scene_grouped,
    build_manifests,
)


def _rgb_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def _make_config(tmp_path: Path) -> Path:
    training = [
        {
            "dataset": "toy",
            "image_id": f"train-{index}",
            "scene_id": f"scene-{index // 3}",
            "sequence_id": f"scene-{index // 3}",
            "frame_index": index % 3,
            "rgb_sha256": _rgb_hash(f"train-rgb-{index}"),
            "official_split": "train",
        }
        for index in range(600)
    ]
    official_test = [
        {
            "dataset": "toy",
            "image_id": f"test-{index}",
            "scene_id": f"test-scene-{index}",
            "sequence_id": f"test-sequence-{index}",
            "frame_index": index,
            "rgb_sha256": _rgb_hash(f"test-rgb-{index}"),
            "official_split": "test",
        }
        for index in range(30)
    ]
    _write_jsonl(tmp_path / "train.jsonl", training)
    _write_jsonl(tmp_path / "test.jsonl", official_test)
    config = {
        "seed": 20260821,
        "datasets": [
            {
                "name": "toy",
                "training_manifest": "train.jsonl",
                "official_test_manifest": "test.jsonl",
                "select_count": 500,
                "split_counts": {
                    "train": 300,
                    "dev": 100,
                    "internal_test": 100,
                },
            }
        ],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_builds_exact_deterministic_scene_disjoint_splits(tmp_path: Path) -> None:
    config_path = _make_config(tmp_path)
    first_output = tmp_path / "manifest-1.jsonl"
    first_audit = tmp_path / "audit-1.json"
    second_output = tmp_path / "manifest-2.jsonl"
    second_audit = tmp_path / "audit-2.json"

    build_manifests(
        config_path,
        first_output,
        first_audit,
        allow_official_test_read=True,
    )
    build_manifests(
        config_path,
        second_output,
        second_audit,
        allow_official_test_read=True,
    )

    first_records = [json.loads(line) for line in first_output.read_text().splitlines()]
    split_counts = {
        split: sum(record["split"] == split for record in first_records)
        for split in ("train", "dev", "internal_test")
    }
    split_scenes = {
        split: {
            record["scene_id"] for record in first_records if record["split"] == split
        }
        for split in split_counts
    }
    split_sequences = {
        split: {
            record["sequence_id"]
            for record in first_records
            if record["split"] == split
        }
        for split in split_counts
    }

    assert split_counts == {"train": 300, "dev": 100, "internal_test": 100}
    assert split_scenes["train"].isdisjoint(split_scenes["dev"])
    assert split_scenes["train"].isdisjoint(split_scenes["internal_test"])
    assert split_scenes["dev"].isdisjoint(split_scenes["internal_test"])
    assert split_sequences["train"].isdisjoint(split_sequences["dev"])
    assert split_sequences["train"].isdisjoint(split_sequences["internal_test"])
    assert split_sequences["dev"].isdisjoint(split_sequences["internal_test"])
    assert first_output.read_bytes() == second_output.read_bytes()
    assert json.loads(first_audit.read_text())["datasets"][0][
        "official_test_overlap"
    ] == {
        "image_count": 0,
        "scene_count": 0,
        "sequence_count": 0,
        "rgb_sha256_count": 0,
    }


def test_rejects_official_test_scene_leakage(tmp_path: Path) -> None:
    config_path = _make_config(tmp_path)
    test_path = tmp_path / "test.jsonl"
    records = [json.loads(line) for line in test_path.read_text().splitlines()]
    records[0]["scene_id"] = "scene-0"
    _write_jsonl(test_path, records)

    with pytest.raises(ValueError, match="official-test leakage"):
        build_manifests(
            config_path,
            tmp_path / "manifest.jsonl",
            tmp_path / "audit.json",
            allow_official_test_read=True,
        )


def test_rejects_official_test_rgb_alias_with_different_id(tmp_path: Path) -> None:
    config_path = _make_config(tmp_path)
    training_path = tmp_path / "train.jsonl"
    test_path = tmp_path / "test.jsonl"
    training = [json.loads(line) for line in training_path.read_text().splitlines()]
    test = [json.loads(line) for line in test_path.read_text().splitlines()]
    test[0]["rgb_sha256"] = training[0]["rgb_sha256"]
    _write_jsonl(test_path, test)

    with pytest.raises(ValueError, match="official-test leakage"):
        build_manifests(
            config_path,
            tmp_path / "manifest.jsonl",
            tmp_path / "audit.json",
            allow_official_test_read=True,
        )


def test_rejects_official_test_sequence_leakage(tmp_path: Path) -> None:
    config_path = _make_config(tmp_path)
    test_path = tmp_path / "test.jsonl"
    records = [json.loads(line) for line in test_path.read_text().splitlines()]
    records[0]["sequence_id"] = "scene-0"
    _write_jsonl(test_path, records)

    with pytest.raises(ValueError, match="official-test leakage"):
        build_manifests(
            config_path,
            tmp_path / "manifest.jsonl",
            tmp_path / "audit.json",
            allow_official_test_read=True,
        )


def test_official_test_integrity_audit_requires_step008_unlock(
    tmp_path: Path,
) -> None:
    config_path = _make_config(tmp_path)

    with pytest.raises(PermissionError, match="frozen until Step 008"):
        build_manifests(
            config_path,
            tmp_path / "manifest.jsonl",
            tmp_path / "audit.json",
        )


def test_scene_sequence_components_are_indivisible() -> None:
    records = [
        {
            "image_id": f"image-{scene_index}-{sequence_index}",
            "scene_id": f"scene-{scene_index}",
            "sequence_id": f"sequence-{scene_index}-{sequence_index}",
        }
        for scene_index in range(3)
        for sequence_index in range(2)
    ]

    selected, _ = _select_scene_grouped(
        records,
        dataset="toy",
        split_counts={"train": 2, "dev": 2, "internal_test": 2},
        seed=20260821,
    )

    split_by_scene: dict[str, set[str]] = {}
    split_by_cluster: dict[str, set[str]] = {}
    for record in selected:
        split_by_scene.setdefault(record["scene_id"], set()).add(record["split"])
        split_by_cluster.setdefault(record["cluster_id"], set()).add(record["split"])
    assert all(len(splits) == 1 for splits in split_by_scene.values())
    assert all(len(splits) == 1 for splits in split_by_cluster.values())
