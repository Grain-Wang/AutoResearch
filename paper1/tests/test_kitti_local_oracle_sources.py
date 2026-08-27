from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
from paper1.experiments.covol.audit_kitti_local_oracle_sources import (
    OracleSource,
    audit_kitti_sources,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(
    tmp_path: Path,
    name: str,
    *,
    kind: str,
    keys: range,
) -> OracleSource:
    manifest_path = tmp_path / f"{name}.jsonl"
    rows = []
    for index in keys:
        path = tmp_path / f"{name}-{index}.npy"
        if kind == "depth":
            array = np.vstack((np.full((4, 8), 1.0), np.full((4, 8), 2.0)))
        else:
            array = np.vstack((np.full((4, 8), 1), np.full((4, 8), 2)))
        np.save(path, array)
        rows.append(
            {
                "dataset": "KITTI",
                "sequence_id": f"drive-{index}",
                "camera_id": "image_02",
                "frame_index": index,
                f"{kind}_path": path.name,
                f"{kind}_sha256": _sha256(path),
            }
        )
    return OracleSource(name, manifest_path, tuple(rows))


def _pilot(count: int) -> list[dict[str, object]]:
    return [
        {
            "dataset": "KITTI",
            "sequence_id": f"drive-{index}",
            "camera_id": "image_02",
            "frame_index": index,
            "cluster_id": f"drive-{index}",
        }
        for index in range(count)
    ]


def test_reports_depth_mask_joint_and_pixel_eligible_intersections(
    tmp_path: Path,
) -> None:
    depth = _source(tmp_path, "depth", kind="depth", keys=range(3))
    mask = _source(tmp_path, "mask", kind="mask", keys=range(1, 4))

    result = audit_kitti_sources(
        _pilot(4),
        [depth],
        [mask],
        minimum_pixels=32,
        minimum_eligible_images=2,
        minimum_eligible_pairs=2,
        minimum_clusters=2,
    )[0]

    assert result["depth_only_intersection"] == 3
    assert result["mask_only_intersection"] == 3
    assert result["joint_frame_intersection"] == 2
    assert result["eligible_depth_mask_images"] == 2
    assert result["eligible_pairs"] == 2
    assert result["independent_eligible_clusters"] == 2
    assert result["status"] == "PASS_UPDATE_ADAPTER"


def test_actual_array_hash_and_frame_shape_are_enforced(tmp_path: Path) -> None:
    depth = _source(tmp_path, "depth", kind="depth", keys=range(1))
    mask = _source(tmp_path, "mask", kind="mask", keys=range(1))
    depth_path = tmp_path / "depth-0.npy"
    depth_path.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        audit_kitti_sources(_pilot(1), [depth], [mask])
