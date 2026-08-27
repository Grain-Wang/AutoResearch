"""Audit drive/camera/frame intersections for proposed KITTI depth/mask sources."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

try:
    from paper1.experiments.covol.scientific_gate import (
        DEFAULT_SCIENTIFIC_GATE,
        require_covol_action_authorized,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from scientific_gate import (  # type: ignore
        DEFAULT_SCIENTIFIC_GATE,
        require_covol_action_authorized,
    )

FrameKey = tuple[str, str, int]


@dataclass(frozen=True)
class OracleSource:
    """One proposed source manifest and the directory resolving its arrays."""

    name: str
    manifest_path: Path
    rows: tuple[Mapping[str, Any], ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(value)
    return tuple(rows)


def _frame_key(row: Mapping[str, Any]) -> FrameKey:
    sequence_id = str(row.get("sequence_id", "")).strip()
    camera_id = str(row.get("camera_id", "")).strip()
    frame_index = row.get("frame_index")
    if (
        not sequence_id
        or not camera_id
        or isinstance(frame_index, bool)
        or not isinstance(frame_index, int)
        or frame_index < 0
    ):
        raise ValueError("source row lacks a valid drive/camera/frame key")
    return sequence_id, camera_id, frame_index


def _index_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    name: str,
) -> dict[FrameKey, Mapping[str, Any]]:
    indexed: dict[FrameKey, Mapping[str, Any]] = {}
    for row in rows:
        if str(row.get("dataset", "")) != "KITTI":
            raise ValueError(f"{name}: every row must name KITTI")
        key = _frame_key(row)
        if key in indexed:
            raise ValueError(f"{name}: duplicate drive/camera/frame key {key}")
        indexed[key] = row
    return indexed


def _array(source: OracleSource, row: Mapping[str, Any], *, kind: str) -> np.ndarray:
    relative = Path(str(row.get(f"{kind}_path", "")).strip())
    if not str(relative) or relative.is_absolute():
        raise ValueError(f"{source.name}: {kind}_path must be manifest-relative")
    root = source.manifest_path.parent.resolve(strict=True)
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{source.name}: {kind}_path escapes source root") from error
    if path.suffix != ".npy" or not path.is_file():
        raise ValueError(f"{source.name}: {kind} must be an existing .npy file")
    if _sha256(path) != str(row.get(f"{kind}_sha256", "")):
        raise ValueError(f"{source.name}: {kind} SHA256 mismatch")
    array = np.load(path, allow_pickle=False)
    if array.ndim != 2:
        raise ValueError(f"{source.name}: {kind} array must be two-dimensional")
    return array


def _eligible_entities_and_pairs(
    depth: np.ndarray,
    mask: np.ndarray,
    *,
    minimum_pixels: int,
    minimum_relative_gap: float,
) -> tuple[int, int]:
    if depth.shape != mask.shape:
        raise ValueError("aligned depth and mask arrays must have the same shape")
    valid_depth = np.isfinite(depth) & (depth > 0.0)
    medians: list[float] = []
    for label in sorted(int(value) for value in np.unique(mask) if int(value) > 0):
        values = depth[(mask == label) & valid_depth]
        if values.size >= minimum_pixels:
            medians.append(float(np.median(values)))
    eligible_pairs = sum(
        abs(left - right) / max(left, right) >= minimum_relative_gap
        for left, right in combinations(medians, 2)
    )
    return len(medians), eligible_pairs


def audit_kitti_sources(
    pilot_rows: Sequence[Mapping[str, Any]],
    depth_sources: Sequence[OracleSource],
    mask_sources: Sequence[OracleSource],
    *,
    minimum_pixels: int = 32,
    minimum_relative_gap: float = 0.10,
    minimum_eligible_images: int = 150,
    minimum_eligible_pairs: int = 300,
    minimum_clusters: int = 20,
) -> list[dict[str, Any]]:
    """Report every preregistered depth/mask intersection on the frozen pilot."""

    pilot = _index_rows(pilot_rows, name="frozen-pilot")
    if not pilot or not depth_sources or not mask_sources:
        raise ValueError("pilot, depth sources, and mask sources must be nonempty")
    cluster_by_key = {
        key: str(row.get("cluster_id", "")).strip() for key, row in pilot.items()
    }
    if any(not cluster for cluster in cluster_by_key.values()):
        raise ValueError("every frozen pilot row must contain cluster_id")

    depth_indices = {
        source.name: _index_rows(source.rows, name=source.name)
        for source in depth_sources
    }
    mask_indices = {
        source.name: _index_rows(source.rows, name=source.name)
        for source in mask_sources
    }
    results: list[dict[str, Any]] = []
    for depth_source in depth_sources:
        depth_index = depth_indices[depth_source.name]
        depth_keys = set(pilot) & set(depth_index)
        for mask_source in mask_sources:
            mask_index = mask_indices[mask_source.name]
            mask_keys = set(pilot) & set(mask_index)
            joint_keys = sorted(depth_keys & mask_keys)
            eligible_images = 0
            eligible_pairs = 0
            eligible_entities = 0
            eligible_clusters: set[str] = set()
            for key in joint_keys:
                depth = _array(depth_source, depth_index[key], kind="depth")
                mask = _array(mask_source, mask_index[key], kind="mask")
                entity_count, pair_count = _eligible_entities_and_pairs(
                    depth,
                    mask,
                    minimum_pixels=minimum_pixels,
                    minimum_relative_gap=minimum_relative_gap,
                )
                if entity_count > 0:
                    eligible_images += 1
                    eligible_entities += entity_count
                    eligible_pairs += pair_count
                    eligible_clusters.add(cluster_by_key[key])
            gate_pass = (
                eligible_images >= minimum_eligible_images
                and eligible_pairs >= minimum_eligible_pairs
                and len(eligible_clusters) >= minimum_clusters
            )
            results.append(
                {
                    "depth_source": depth_source.name,
                    "mask_source": mask_source.name,
                    "pilot_images": len(pilot),
                    "depth_only_intersection": len(depth_keys),
                    "mask_only_intersection": len(mask_keys),
                    "joint_frame_intersection": len(joint_keys),
                    "eligible_depth_mask_images": eligible_images,
                    "eligible_entities": eligible_entities,
                    "eligible_pairs": eligible_pairs,
                    "independent_eligible_clusters": len(eligible_clusters),
                    "minimum_valid_depth_mask_pixels": minimum_pixels,
                    "minimum_relative_median_depth_gap": minimum_relative_gap,
                    "status": "PASS_UPDATE_ADAPTER" if gate_pass else "FAIL_COVERAGE",
                }
            )
    return results


def _named_source(value: str) -> OracleSource:
    name, separator, raw_path = value.partition("=")
    if not separator or not name.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("source must use NAME=MANIFEST.jsonl")
    path = Path(raw_path).resolve(strict=True)
    return OracleSource(name.strip(), path, _read_jsonl(path))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--scientific-gate", type=Path, default=DEFAULT_SCIENTIFIC_GATE)
    parser.add_argument("--pilot-manifest", type=Path, required=True)
    parser.add_argument(
        "--depth-source", type=_named_source, action="append", required=True
    )
    parser.add_argument(
        "--mask-source", type=_named_source, action="append", required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    require_covol_action_authorized(
        step003_authorization_path=args.authorization,
        scientific_gate_path=args.scientific_gate,
        scientific_action="second_dataset_recovery",
        step003_action="kitti_oracle_gap_audit",
    )
    results = audit_kitti_sources(
        _read_jsonl(args.pilot_manifest),
        args.depth_source,
        args.mask_source,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(results[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    main()
