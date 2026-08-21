from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from paper1.experiments.covol.build_kitti_source_manifest import (
    ANONYMOUS_BENCHMARK_SEQUENCE,
    build_kitti_source_manifest,
)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_eigen_rows_map_drive_camera_frame_and_hash_file_bytes(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "kitti"
    drive = "2011_09_26_drive_0001_sync"
    left_path = data_root / "2011_09_26" / drive / "image_02/data/0000000042.png"
    right_path = data_root / "2011_09_26" / drive / "image_03/data/0000000043.png"
    _write_bytes(left_path, b"encoded-left-rgb")
    _write_bytes(right_path, b"encoded-right-rgb")
    split_list = tmp_path / "eigen_train_files.txt"
    split_list.write_text(
        f"2011_09_26/{drive} 43 r\n" f"2011_09_26/{drive} 0000000042 l\n",
        encoding="utf-8",
    )
    output = tmp_path / "source.jsonl"

    returned = build_kitti_source_manifest(
        data_root,
        split_list,
        output,
        official_split="train",
    )
    records = _read_jsonl(output)

    assert records == returned
    assert [record["image_id"] for record in records] == [
        f"2011_09_26/{drive}/image_02/0000000042",
        f"2011_09_26/{drive}/image_03/0000000043",
    ]
    assert {record["scene_id"] for record in records} == {f"2011_09_26/{drive}"}
    assert {record["sequence_id"] for record in records} == {f"2011_09_26/{drive}"}
    assert records[0]["frame_index"] == 42
    assert records[0]["identity_resolution"] == "raw_drive_camera_frame"
    assert records[0]["rgb_sha256"] == hashlib.sha256(b"encoded-left-rgb").hexdigest()
    assert records[0]["rgb_path"] == (
        f"2011_09_26/{drive}/image_02/data/0000000042.png"
    )
    assert records[0]["official_split"] == "train"
    assert records[0]["entities"] == []
    assert records[0]["annotation_available"] is False
    assert records[0]["annotation_source"] is None
    assert records[0]["annotation_sha256"] is None
    assert records[0]["depth_available"] is False
    assert records[0]["depth_source"] is None
    assert records[0]["depth_sha256"] is None
    assert records[0]["annotation_status"] == "instance_masks_unavailable"


def test_direct_raw_and_official_selection_paths_share_canonical_identity(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "kitti"
    drive = "2011_09_26_drive_0002_sync"
    raw_relative = f"2011_09_26/{drive}/image_02/data/0000000005.jpg"
    selection_relative = (
        "val_selection_cropped/image/" f"{drive}_image_0000000006_image_03.png"
    )
    _write_bytes(data_root / raw_relative, b"raw-rgb")
    _write_bytes(data_root / selection_relative, b"cropped-rgb")
    split_list = tmp_path / "paths.txt"
    split_list.write_text(
        f"{selection_relative}\n" f"{raw_relative} ignored/depth/path.png 721.5\n",
        encoding="utf-8",
    )

    records = build_kitti_source_manifest(
        data_root,
        split_list,
        tmp_path / "source.jsonl",
        official_split="test",
        allow_official_test_read=True,
    )

    assert [record["image_id"] for record in records] == [
        f"2011_09_26/{drive}/image_02/0000000005",
        f"2011_09_26/{drive}/image_03/0000000006",
    ]
    assert [record["source_split_format"] for record in records] == [
        "direct_raw_rgb_path",
        "official_selection_rgb_path",
    ]


def test_official_anonymous_index_uses_conservative_shared_sequence(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "kitti"
    rgb_path = (
        data_root
        / "data_depth_selection/test_depth_prediction_anonymous/image/0000000007.png"
    )
    _write_bytes(rgb_path, b"anonymous-rgb")
    split_list = tmp_path / "benchmark_test_files.txt"
    split_list.write_text("image 7\n", encoding="utf-8")

    records = build_kitti_source_manifest(
        data_root,
        split_list,
        tmp_path / "source.jsonl",
        official_split="test",
        allow_official_test_read=True,
    )

    assert records == [
        {
            "adapter": "kitti-source-v1",
            "annotation_available": False,
            "annotation_sha256": None,
            "annotation_source": None,
            "annotation_status": "instance_masks_unavailable",
            "camera_id": "anonymous_camera",
            "dataset": "KITTI",
            "depth_available": False,
            "depth_sha256": None,
            "depth_source": None,
            "entities": [],
            "frame_index": 7,
            "frame_index_semantics": "anonymous_benchmark_index",
            "identity_resolution": "anonymous_index_rgb_hash_only",
            "image_id": (f"{ANONYMOUS_BENCHMARK_SEQUENCE}/anonymous_camera/0000000007"),
            "official_split": "test",
            "rgb_path": (
                "data_depth_selection/test_depth_prediction_anonymous/"
                "image/0000000007.png"
            ),
            "rgb_sha256": hashlib.sha256(b"anonymous-rgb").hexdigest(),
            "scene_id": ANONYMOUS_BENCHMARK_SEQUENCE,
            "sequence_id": ANONYMOUS_BENCHMARK_SEQUENCE,
            "source_split_format": "official_anonymous_index",
            "source_split_list_sha256": hashlib.sha256(
                split_list.read_bytes()
            ).hexdigest(),
        }
    ]


def test_rejects_same_capture_referenced_by_tuple_and_path(tmp_path: Path) -> None:
    data_root = tmp_path / "kitti"
    drive = "2011_09_26_drive_0001_sync"
    relative = f"2011_09_26/{drive}/image_02/data/0000000042.png"
    _write_bytes(data_root / relative, b"rgb")
    split_list = tmp_path / "duplicate.txt"
    split_list.write_text(
        f"2011_09_26/{drive} 42 l\n{relative}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate canonical image_id"):
        build_kitti_source_manifest(
            data_root,
            split_list,
            tmp_path / "source.jsonl",
            official_split="train",
        )


def test_rejects_duplicate_rgb_bytes_under_different_capture_ids(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "kitti"
    drive = "2011_09_26_drive_0001_sync"
    first = data_root / "2011_09_26" / drive / "image_02/data/0000000042.png"
    second = data_root / "2011_09_26" / drive / "image_02/data/0000000043.png"
    _write_bytes(first, b"same-rgb")
    _write_bytes(second, b"same-rgb")
    split_list = tmp_path / "duplicate-rgb.txt"
    split_list.write_text(
        f"2011_09_26/{drive} 42 l\n2011_09_26/{drive} 43 l\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate RGB content hash"):
        build_kitti_source_manifest(
            data_root,
            split_list,
            tmp_path / "source.jsonl",
            official_split="train",
        )


def test_anonymous_benchmark_rows_cannot_enter_training_pool(tmp_path: Path) -> None:
    data_root = tmp_path / "kitti"
    _write_bytes(
        data_root / "test_depth_prediction_anonymous/image/0000000000.png",
        b"benchmark-rgb",
    )
    split_list = tmp_path / "benchmark.txt"
    split_list.write_text("image 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="only valid for official_split=test"):
        build_kitti_source_manifest(
            data_root,
            split_list,
            tmp_path / "source.jsonl",
            official_split="train",
        )


def test_official_test_requires_explicit_step008_unlock(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="frozen until Step 008"):
        build_kitti_source_manifest(
            tmp_path / "missing-data-root",
            tmp_path / "missing-test-list.txt",
            tmp_path / "source.jsonl",
            official_split="test",
        )
