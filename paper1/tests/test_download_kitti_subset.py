from __future__ import annotations

import hashlib
import json
from pathlib import Path

from paper1.experiments.covol import download_kitti_subset as downloader


def test_downloads_revision_locked_plan_and_writes_hash_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan = tmp_path / "plan.jsonl"
    records = [
        {
            "dataset": "KITTI",
            "image_id": f"drive/image_02/{index:010d}",
            "repository_path": f"raw_data/date/drive/image_02/data/{index:010d}.png",
            "rgb_relative_path": f"date/drive/image_02/data/{index:010d}.png",
        }
        for index in range(2)
    ]
    plan.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    payloads = {
        f"{index:010d}.png": downloader.PNG_SIGNATURE + bytes([index]) * 10
        for index in range(2)
    }

    def fake_download(url: str, *, timeout: float) -> bytes:
        assert timeout == 3.0
        return payloads[url.rsplit("/", maxsplit=1)[-1]]

    monkeypatch.setattr(downloader, "_download_bytes", fake_download)
    output_manifest = tmp_path / "downloads.jsonl"
    output_root = tmp_path / "rgb"

    completed = downloader.download_kitti_subset(
        plan,
        output_root=output_root,
        output_manifest=output_manifest,
        repository_id="example/kitti",
        repository_revision="a" * 40,
        workers=2,
        timeout=3.0,
        max_retries=0,
    )

    assert len(completed) == 2
    manifest = [json.loads(line) for line in output_manifest.read_text().splitlines()]
    for index, record in enumerate(manifest):
        assert record["repository_revision"] == "a" * 40
        assert (
            record["rgb_sha256"]
            == hashlib.sha256(payloads[f"{index:010d}.png"]).hexdigest()
        )
