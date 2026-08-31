from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from paper3.experiments.bar_depth.build_diode_manifest import build_manifest
from paper3.experiments.bar_depth.io_utils import read_jsonl
from PIL import Image


def _write_sample(root: Path, scan: str, index: int) -> None:
    directory = root / "val" / "indoors" / "scene_00001" / scan
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"00001_{scan}_{index:06d}"
    Image.new("RGB", (8, 6), (index, index, index)).save(directory / f"{stem}.png")
    np.save(directory / f"{stem}_depth.npy", np.ones((6, 8), dtype=np.float32))
    np.save(directory / f"{stem}_depth_mask.npy", np.ones((6, 8), dtype=bool))


def test_builds_balanced_hash_locked_manifest(tmp_path: Path) -> None:
    dataset_root = tmp_path / "diode"
    for scan in ("scan_00001", "scan_00002"):
        for index in range(4):
            _write_sample(dataset_root, scan, index)
    archive = tmp_path / "val.tar.gz"
    archive.write_bytes(b"frozen archive")
    archive_md5 = hashlib.md5(archive.read_bytes()).hexdigest()
    config = {
        "seed": 7,
        "dataset": {
            "partition": "val",
            "archive_md5": archive_md5,
            "samples_per_scan": 2,
            "expected_scan_count": 2,
            "expected_sample_count": 4,
            "expected_width": 8,
            "expected_height": 6,
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    manifest_path = tmp_path / "manifest.jsonl"
    audit_path = tmp_path / "audit.json"

    audit = build_manifest(
        dataset_root=dataset_root,
        archive_path=archive,
        config_path=config_path,
        output_manifest=manifest_path,
        output_audit=audit_path,
    )
    rows = read_jsonl(manifest_path)

    assert audit["status"] == "PASS"
    assert len(rows) == 4
    assert {row["scan_id"] for row in rows} == {
        "indoors/scene_00001/scan_00001",
        "indoors/scene_00001/scan_00002",
    }
    assert all(len(row["image_sha256"]) == 64 for row in rows)
