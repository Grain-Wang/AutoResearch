from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from paper1.experiments.covol.audit_provenance import (
    validate_trusted_training_source,
)
from paper1.experiments.covol.build_image_manifest import _select_scene_grouped
from paper1.experiments.covol.build_vkitti2_source_manifest import (
    ARCHIVE_MD5,
    VKITTI2_EVAL_PROTOCOL_SHA256,
    build_vkitti2_source_manifest,
)
from paper1.experiments.covol.power_analysis import load_power_dataset_decision
from PIL import Image


def _write_checksums(path: Path, *, forged_rgb: bool = False) -> None:
    checksums = dict(ARCHIVE_MD5)
    if forged_rgb:
        checksums["vkitti_2.0.3_rgb.tar"] = "0" * 32
    path.write_text(
        "".join(f"{value}  {name}\n" for name, value in sorted(checksums.items())),
        encoding="utf-8",
    )


def _write_frame(
    data_root: Path,
    *,
    scene: str,
    variation: str,
    camera: str,
    frame_index: int,
    rgb_value: int,
) -> None:
    prefix = Path(scene) / variation
    rgb_path = (
        data_root
        / "vkitti_2.0.3_rgb"
        / prefix
        / "frames/rgb"
        / camera
        / f"rgb_{frame_index:05d}.jpg"
    )
    depth_path = (
        data_root
        / "vkitti_2.0.3_depth"
        / prefix
        / "frames/depth"
        / camera
        / f"depth_{frame_index:05d}.png"
    )
    class_path = (
        data_root
        / "vkitti_2.0.3_classSegmentation"
        / prefix
        / "frames/classsegmentation"
        / camera
        / f"classgt_{frame_index:05d}.png"
    )
    instance_path = (
        data_root
        / "vkitti_2.0.3_instanceSegmentation"
        / prefix
        / "frames/instancesegmentation"
        / camera
        / f"instancegt_{frame_index:05d}.png"
    )
    colors_path = data_root / "vkitti_2.0.3_textgt" / prefix / "colors.txt"
    for path in (rgb_path, depth_path, class_path, instance_path, colors_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    rgb = np.full((4, 4, 3), rgb_value, dtype=np.uint8)
    depth = np.array(
        [
            [1_000, 1_000, 2_000, 2_000],
            [1_000, 1_000, 2_000, 2_000],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
        dtype=np.uint16,
    )
    classes = np.zeros((4, 4, 3), dtype=np.uint8)
    classes[:2, :2] = (255, 127, 80)
    classes[:2, 2:] = (160, 60, 60)
    instances = np.zeros((4, 4), dtype=np.uint8)
    instances[:2, :2] = 1
    instances[:2, 2:] = 2
    Image.fromarray(rgb).save(rgb_path, quality=95, subsampling=0)
    Image.fromarray(depth).save(depth_path)
    Image.fromarray(classes).save(class_path)
    Image.fromarray(instances).save(instance_path)
    colors_path.write_text(
        "Category r g b\nCar 255 127 80\nTruck 160 60 60\nUndefined 0 0 0\n",
        encoding="utf-8",
    )


def _write_index(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _build_one(tmp_path: Path) -> tuple[dict[str, object], Path, Path, Path]:
    data_root = tmp_path / "vkitti"
    checksum_path = tmp_path / "checksums.txt"
    index_path = tmp_path / "frames.jsonl"
    output_path = tmp_path / "source.jsonl"
    _write_checksums(checksum_path)
    _write_frame(
        data_root,
        scene="Scene01",
        variation="clone",
        camera="Camera_0",
        frame_index=0,
        rgb_value=10,
    )
    _write_index(
        index_path,
        [
            {
                "scene": "Scene01",
                "variation": "clone",
                "camera": "Camera_0",
                "frame_index": 0,
                "official_split": "train",
            }
        ],
    )
    records = build_vkitti2_source_manifest(
        data_root,
        index_path,
        checksum_path,
        output_path,
    )
    return records[0], data_root, checksum_path, index_path


def test_legal_vkitti2_source_hashes_files_and_decodes_entities(tmp_path: Path) -> None:
    record, _, _, _ = _build_one(tmp_path)

    assert record["image_id"] == "Scene01/clone/Camera_0/00000"
    assert record["scene_id"] == "Scene01"
    assert record["sequence_id"] == "Scene01/clone/Camera_0"
    assert record["eval_protocol_sha256"] == VKITTI2_EVAL_PROTOCOL_SHA256
    assert record["archive_md5"] == ARCHIVE_MD5
    assert [entity["class_name"] for entity in record["entities"]] == [
        "Car",
        "Truck",
    ]
    assert [entity["eval_median_depth"] for entity in record["entities"]] == [
        10.0,
        20.0,
    ]
    assert (
        validate_trusted_training_source(record, context="test")
        == record["source_split_list_sha256"]
    )


def test_rejects_forged_official_archive_checksum(tmp_path: Path) -> None:
    _, data_root, checksum_path, index_path = _build_one(tmp_path)
    _write_checksums(checksum_path, forged_rgb=True)

    with pytest.raises(ValueError, match="official version 2.0.3"):
        build_vkitti2_source_manifest(
            data_root,
            index_path,
            checksum_path,
            tmp_path / "forged.jsonl",
        )


def test_rejects_forged_vkitti2_revision_after_adapter(tmp_path: Path) -> None:
    record, _, _, _ = _build_one(tmp_path)
    record["dataset_version"] = "2.0.4"

    with pytest.raises(ValueError, match="version is not frozen"):
        validate_trusted_training_source(record, context="test")


def test_rejects_rgb_alias_under_two_frame_ids(tmp_path: Path) -> None:
    _, data_root, checksum_path, _ = _build_one(tmp_path)
    _write_frame(
        data_root,
        scene="Scene02",
        variation="clone",
        camera="Camera_0",
        frame_index=1,
        rgb_value=10,
    )
    index_path = tmp_path / "alias-frames.jsonl"
    _write_index(
        index_path,
        [
            {
                "scene": "Scene01",
                "variation": "clone",
                "camera": "Camera_0",
                "frame_index": 0,
            },
            {
                "scene": "Scene02",
                "variation": "clone",
                "camera": "Camera_0",
                "frame_index": 1,
            },
        ],
    )

    with pytest.raises(ValueError, match="duplicate RGB content hash"):
        build_vkitti2_source_manifest(
            data_root,
            index_path,
            checksum_path,
            tmp_path / "alias.jsonl",
        )


def test_scene_variations_cannot_cross_internal_splits() -> None:
    records = [
        {
            "dataset": "Virtual KITTI 2",
            "image_id": "Scene01/clone/Camera_0/00000",
            "scene_id": "Scene01",
            "sequence_id": "Scene01/clone/Camera_0",
        },
        {
            "dataset": "Virtual KITTI 2",
            "image_id": "Scene01/rain/Camera_0/00000",
            "scene_id": "Scene01",
            "sequence_id": "Scene01/rain/Camera_0",
        },
        {
            "dataset": "Virtual KITTI 2",
            "image_id": "Scene02/clone/Camera_0/00000",
            "scene_id": "Scene02",
            "sequence_id": "Scene02/clone/Camera_0",
        },
        {
            "dataset": "Virtual KITTI 2",
            "image_id": "Scene06/clone/Camera_0/00000",
            "scene_id": "Scene06",
            "sequence_id": "Scene06/clone/Camera_0",
        },
    ]

    selected, _ = _select_scene_grouped(
        records,
        dataset="Virtual KITTI 2",
        split_counts={"train": 1, "dev": 1, "internal_test": 1},
        seed=20260821,
    )

    split_by_scene: dict[str, set[str]] = {}
    for record in selected:
        split_by_scene.setdefault(str(record["scene_id"]), set()).add(
            str(record["split"])
        )
    assert all(len(splits) == 1 for splits in split_by_scene.values())


def test_power_fallback_reads_hash_linked_coverage_decision(tmp_path: Path) -> None:
    manifest_hash = hashlib.sha256(b"manifest").hexdigest()
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "schema_version": "covol-annotation-coverage-v1",
                "status": "PASS",
                "input": {"manifest_sha256": manifest_hash},
                "claim_dataset_decision": {
                    "decision": "GO_LOCAL_CLAIMS_NYUV2_VKITTI2",
                    "local_claim_datasets": ["NYUv2", "Virtual KITTI 2"],
                },
                "datasets": [
                    {
                        "dataset": "NYUv2",
                        "structured_requirement_pass": True,
                    },
                    {
                        "dataset": "Virtual KITTI 2",
                        "structured_requirement_pass": True,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    selected, link = load_power_dataset_decision(
        coverage_path,
        manifest_sha256=manifest_hash,
    )

    assert selected == frozenset({"NYUv2", "Virtual KITTI 2"})
    assert link["source"] == "frozen_coverage_audit"
    assert (
        link["coverage_decision_sha256"]
        == hashlib.sha256(coverage_path.read_bytes()).hexdigest()
    )
    with pytest.raises(ValueError, match="bound to the power manifest"):
        load_power_dataset_decision(
            coverage_path,
            manifest_sha256="0" * 64,
        )
