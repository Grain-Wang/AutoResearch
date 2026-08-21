from __future__ import annotations

import json
from pathlib import Path

import pytest
from paper1.experiments.covol.build_image_manifest import build_manifests


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
            "official_split": "train",
        }
        for index in range(600)
    ]
    official_test = [
        {
            "dataset": "toy",
            "image_id": f"test-{index}",
            "scene_id": f"test-scene-{index}",
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

    build_manifests(config_path, first_output, first_audit)
    build_manifests(config_path, second_output, second_audit)

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

    assert split_counts == {"train": 300, "dev": 100, "internal_test": 100}
    assert split_scenes["train"].isdisjoint(split_scenes["dev"])
    assert split_scenes["train"].isdisjoint(split_scenes["internal_test"])
    assert split_scenes["dev"].isdisjoint(split_scenes["internal_test"])
    assert first_output.read_bytes() == second_output.read_bytes()
    assert json.loads(first_audit.read_text())["datasets"][0][
        "official_test_overlap"
    ] == {"image_count": 0, "scene_count": 0}


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
        )
