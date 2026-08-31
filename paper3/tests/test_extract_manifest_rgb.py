from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

from paper3.experiments.bar_depth.extract_manifest_rgb import extract_manifest_rgb


def test_extract_manifest_rgb_checks_archive_and_payload(tmp_path: Path) -> None:
    payload = b"portable-rgb-placeholder"
    relative_path = "val/indoors/scene/scan/example.png"
    archive_path = tmp_path / "val.tar.gz"
    with tarfile.open(archive_path, mode="w:gz") as archive:
        info = tarfile.TarInfo(relative_path)
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    archive_md5 = hashlib.md5(
        archive_path.read_bytes(), usedforsecurity=False
    ).hexdigest()
    manifest_path = tmp_path / "manifest.jsonl"
    manifest_path.write_text(
        json.dumps(
            {
                "image_relpath": relative_path,
                "image_sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "extracted"
    audit = extract_manifest_rgb(
        archive_path=archive_path,
        expected_archive_md5=archive_md5,
        manifest_path=manifest_path,
        output_root=output_root,
        output_audit=tmp_path / "audit.json",
    )
    assert audit["status"] == "PASS"
    assert audit["extracted_rgb_count"] == 1
    assert (output_root / relative_path).read_bytes() == payload
