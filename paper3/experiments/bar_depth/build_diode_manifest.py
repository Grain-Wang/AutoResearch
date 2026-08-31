"""Build the preregistered 200-image DIODE validation manifest."""

from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image

from .io_utils import (
    canonical_json_digest,
    file_digest,
    read_json,
    write_json_atomic,
    write_jsonl_atomic,
)


def _stable_priority(seed: int, relative_path: str) -> str:
    return hashlib.sha256(f"{seed}:{relative_path}".encode()).hexdigest()


def _metadata_from_path(relative_path: Path, partition: str) -> tuple[str, str, str]:
    parts = relative_path.parts
    try:
        partition_index = parts.index(partition)
    except ValueError as error:
        raise ValueError(
            f"Path does not contain partition {partition!r}: {relative_path}"
        ) from error
    suffix = parts[partition_index + 1 :]
    if len(suffix) < 4:
        raise ValueError(f"Unexpected DIODE path layout: {relative_path}")
    domain, scene_id, scan_id = suffix[:3]
    return domain, scene_id, scan_id


def enumerate_diode_records(dataset_root: Path, partition: str) -> list[dict[str, str]]:
    """Enumerate complete DIODE RGB/depth/mask triples."""
    records: list[dict[str, str]] = []
    for depth_path in sorted(dataset_root.rglob("*_depth.npy")):
        if depth_path.name.endswith("_depth_mask.npy"):
            continue
        image_path = depth_path.with_name(
            depth_path.name.removesuffix("_depth.npy") + ".png"
        )
        mask_path = depth_path.with_name(
            depth_path.name.removesuffix("_depth.npy") + "_depth_mask.npy"
        )
        if not image_path.is_file() or not mask_path.is_file():
            continue
        image_relative = image_path.relative_to(dataset_root)
        domain, scene_id, scan_id = _metadata_from_path(image_relative, partition)
        records.append(
            {
                "domain": domain,
                "scene_id": scene_id,
                "scan_id": f"{domain}/{scene_id}/{scan_id}",
                "image_relpath": image_relative.as_posix(),
                "depth_relpath": depth_path.relative_to(dataset_root).as_posix(),
                "mask_relpath": mask_path.relative_to(dataset_root).as_posix(),
            }
        )
    return records


def select_manifest_records(
    records: list[dict[str, str]], samples_per_scan: int, seed: int
) -> list[dict[str, str]]:
    """Select a fixed number of images per scan using stable hash priorities."""
    by_scan: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        by_scan[record["scan_id"]].append(record)

    selected: list[dict[str, str]] = []
    for scan_id in sorted(by_scan):
        candidates = sorted(
            by_scan[scan_id],
            key=lambda row: (
                _stable_priority(seed, row["image_relpath"]),
                row["image_relpath"],
            ),
        )
        if len(candidates) < samples_per_scan:
            raise ValueError(
                f"Scan {scan_id} has {len(candidates)} images; need {samples_per_scan}"
            )
        selected.extend(candidates[:samples_per_scan])
    return sorted(selected, key=lambda row: (row["scan_id"], row["image_relpath"]))


def materialize_manifest(
    selected: list[dict[str, str]], dataset_root: Path
) -> list[dict[str, Any]]:
    """Attach dimensions and content hashes to selected records."""
    materialized: list[dict[str, Any]] = []
    for index, record in enumerate(selected):
        image_path = dataset_root / record["image_relpath"]
        depth_path = dataset_root / record["depth_relpath"]
        mask_path = dataset_root / record["mask_relpath"]
        with Image.open(image_path) as image:
            width, height = image.size
        materialized.append(
            {
                "sample_index": index,
                "dataset": "DIODE",
                "partition": "val",
                **record,
                "width": width,
                "height": height,
                "image_sha256": file_digest(image_path),
                "depth_sha256": file_digest(depth_path),
                "mask_sha256": file_digest(mask_path),
            }
        )
    return materialized


def build_manifest(
    *,
    dataset_root: Path,
    archive_path: Path,
    config_path: Path,
    output_manifest: Path,
    output_audit: Path,
) -> dict[str, Any]:
    """Build and validate the frozen DIODE canary manifest."""
    config = read_json(config_path)
    dataset_config = config["dataset"]
    archive_md5 = file_digest(archive_path, "md5")
    if archive_md5 != dataset_config["archive_md5"]:
        raise ValueError(
            f"DIODE archive MD5 mismatch: expected {dataset_config['archive_md5']}, "
            f"got {archive_md5}"
        )

    records = enumerate_diode_records(dataset_root, dataset_config["partition"])
    selected = select_manifest_records(
        records,
        int(dataset_config["samples_per_scan"]),
        int(config["seed"]),
    )
    manifest = materialize_manifest(selected, dataset_root)

    scan_ids = sorted({row["scan_id"] for row in manifest})
    domains = sorted({row["domain"] for row in manifest})
    dimensions = sorted({(row["width"], row["height"]) for row in manifest})
    expected_dimensions = {
        (int(dataset_config["expected_width"]), int(dataset_config["expected_height"]))
    }
    failures: list[str] = []
    if len(scan_ids) != int(dataset_config["expected_scan_count"]):
        failures.append("unexpected_scan_count")
    if len(manifest) != int(dataset_config["expected_sample_count"]):
        failures.append("unexpected_sample_count")
    if set(dimensions) != expected_dimensions:
        failures.append("unexpected_image_dimensions")
    scan_counts = {
        scan_id: sum(row["scan_id"] == scan_id for row in manifest)
        for scan_id in scan_ids
    }
    if any(
        count != int(dataset_config["samples_per_scan"])
        for count in scan_counts.values()
    ):
        failures.append("unbalanced_scan_sample_count")

    manifest_digest = canonical_json_digest(manifest)
    audit: dict[str, Any] = {
        "schema_version": 1,
        "status": "PASS" if not failures else "INVALID_CANARY",
        "failures": failures,
        "config_sha256": file_digest(config_path),
        "archive": {
            "name": archive_path.name,
            "md5": archive_md5,
            "size_bytes": archive_path.stat().st_size,
        },
        "enumerated_record_count": len(records),
        "selected_record_count": len(manifest),
        "scan_count": len(scan_ids),
        "domain_counts": {
            domain: sum(row["domain"] == domain for row in manifest)
            for domain in domains
        },
        "scan_counts": scan_counts,
        "dimensions": [list(pair) for pair in dimensions],
        "manifest_canonical_sha256": manifest_digest,
        "source_root_role": "external_diode_validation_root",
    }
    if failures:
        raise ValueError(f"Manifest contract failed: {', '.join(failures)}")
    write_jsonl_atomic(output_manifest, manifest)
    write_json_atomic(output_audit, audit)
    return audit


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    audit = build_manifest(
        dataset_root=args.dataset_root,
        archive_path=args.archive,
        config_path=args.config,
        output_manifest=args.output_manifest,
        output_audit=args.output_audit,
    )
    print(f"{audit['status']}: {audit['selected_record_count']} images")


if __name__ == "__main__":
    main()
