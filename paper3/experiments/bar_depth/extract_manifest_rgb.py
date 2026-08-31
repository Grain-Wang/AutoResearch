"""Extract and hash-check only manifest RGB files from a dataset tar archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from .io_utils import file_digest, write_json_atomic


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def _normalized_member_name(name: str) -> str:
    normalized = str(PurePosixPath(name.removeprefix("./")))
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe archive member: {name}")
    return normalized


def extract_manifest_rgb(
    *,
    archive_path: Path,
    expected_archive_md5: str,
    manifest_path: Path,
    output_root: Path,
    output_audit: Path,
) -> dict[str, Any]:
    """Extract manifest RGB members, verify hashes, and write a portable audit."""
    archive_md5 = _md5(archive_path)
    if archive_md5 != expected_archive_md5:
        raise ValueError("Dataset archive MD5 mismatch")
    records = _read_manifest(manifest_path)
    expected = {str(record["image_relpath"]): record for record in records}
    extracted: list[dict[str, Any]] = []
    found: set[str] = set()
    with tarfile.open(archive_path, mode="r|gz") as archive:
        for member in archive:
            relative_path = _normalized_member_name(member.name)
            if not member.isfile() or relative_path not in expected:
                continue
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read archive member {relative_path}")
            payload = source.read()
            payload_sha256 = hashlib.sha256(payload).hexdigest()
            if payload_sha256 != expected[relative_path]["image_sha256"]:
                raise ValueError(f"RGB SHA256 mismatch for {relative_path}")
            target = output_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.tmp")
            temporary.write_bytes(payload)
            temporary.replace(target)
            extracted.append(
                {
                    "image_relpath": relative_path,
                    "image_sha256": payload_sha256,
                    "byte_count": len(payload),
                }
            )
            found.add(relative_path)
    missing = sorted(set(expected) - found)
    if missing:
        raise ValueError(f"Archive is missing {len(missing)} manifest RGB files")
    audit = {
        "schema_version": 1,
        "status": "PASS",
        "archive_md5": archive_md5,
        "manifest_sha256": file_digest(manifest_path),
        "extracted_rgb_count": len(extracted),
        "total_extracted_bytes": sum(row["byte_count"] for row in extracted),
        "records": extracted,
    }
    write_json_atomic(output_audit, audit)
    return audit


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--expected-archive-md5", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Extract the manifest RGB subset from the command line."""
    args = parse_args()
    audit = extract_manifest_rgb(
        archive_path=args.archive,
        expected_archive_md5=args.expected_archive_md5,
        manifest_path=args.manifest,
        output_root=args.output_root,
        output_audit=args.output_audit,
    )
    print(audit["status"])


if __name__ == "__main__":
    main()
