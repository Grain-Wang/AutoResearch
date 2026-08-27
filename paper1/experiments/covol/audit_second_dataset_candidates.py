"""Audit the three preregistered second-dataset candidates without model results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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

FROZEN_DATASET_ORDER = ("Cityscapes", "ScanNet_v2", "Matterport3D")
_CSV_FIELDS = (
    "dataset",
    "order",
    "status",
    "source_revision_lock",
    "license_contract",
    "manifest_sha256",
    "sample_size",
    "eligible_images",
    "eligible_pairs",
    "independent_eligible_clusters",
    "projected_full_pilot_eligible_images",
    "projected_full_pilot_eligible_pairs",
    "failure_counts_json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            rows.append(value)
    return rows


def _resolve_source_file(manifest_path: Path, raw_path: object) -> Path:
    value = Path(str(raw_path).strip())
    if not str(value):
        raise ValueError("source file path must be nonempty")
    resolved = value if value.is_absolute() else manifest_path.parent / value
    resolved = resolved.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"source path is not a file: {resolved}")
    return resolved


def _validate_source_file(
    row: Mapping[str, Any],
    *,
    prefix: str,
    manifest_path: Path,
) -> None:
    path = _resolve_source_file(manifest_path, row.get(f"{prefix}_path", ""))
    expected = str(row.get(f"{prefix}_sha256", ""))
    if _sha256(path) != expected:
        raise ValueError(f"{prefix} file hash mismatch for {row.get('image_id')}")


def _audit_manifest(
    candidate: Mapping[str, Any],
    manifest_path: Path,
    *,
    sample_size: int,
    projected_size: int,
    minimum_images: int,
    minimum_pairs: int,
    minimum_clusters: int,
    minimum_pixels: int,
) -> dict[str, Any]:
    rows = _read_jsonl(manifest_path)
    dataset = str(candidate["dataset"])
    if len(rows) != sample_size:
        raise ValueError(f"{dataset}: dry-run manifest must contain {sample_size} rows")
    seen_images: set[str] = set()
    seen_ranks: set[int] = set()
    eligible_images = 0
    eligible_pairs = 0
    eligible_clusters: set[str] = set()
    failure_counts = {
        "rgb": 0,
        "metric_depth": 0,
        "local_mask": 0,
        "frame_alignment": 0,
        "license": 0,
        "depth_mask_pixels": 0,
    }
    for index, row in enumerate(rows):
        if str(row.get("dataset", "")) != dataset:
            raise ValueError(f"{dataset}: row {index} names another dataset")
        image_id = str(row.get("image_id", "")).strip()
        cluster_id = str(row.get("cluster_id", "")).strip()
        if not image_id or not cluster_id or image_id in seen_images:
            raise ValueError(f"{dataset}: invalid or duplicate image/cluster identity")
        rank = row.get("selection_rank")
        if isinstance(rank, bool) or not isinstance(rank, int):
            raise ValueError(f"{dataset}: selection_rank must be an integer")
        seen_images.add(image_id)
        seen_ranks.add(rank)
        for prefix in ("rgb", "depth", "mask"):
            _validate_source_file(row, prefix=prefix, manifest_path=manifest_path)
        frame_keys = {
            str(row.get(field, "")).strip()
            for field in ("rgb_frame_key", "depth_frame_key", "mask_frame_key")
        }
        frame_alignment = len(frame_keys) == 1 and "" not in frame_keys
        checks = {
            "rgb": bool(row.get("rgb_available")),
            "metric_depth": bool(row.get("metric_depth_available")),
            "local_mask": bool(row.get("local_mask_available")),
            "frame_alignment": frame_alignment,
            "license": bool(row.get("license_pass")),
            "depth_mask_pixels": int(row.get("valid_depth_mask_pixels", 0))
            >= minimum_pixels,
        }
        for name, passed in checks.items():
            failure_counts[name] += int(not passed)
        pair_count = int(row.get("eligible_pair_count", 0))
        is_eligible = all(checks.values()) and pair_count > 0
        if is_eligible:
            eligible_images += 1
            eligible_pairs += pair_count
            eligible_clusters.add(cluster_id)
    if seen_ranks != set(range(sample_size)):
        raise ValueError(
            f"{dataset}: selection_rank must be exactly 0..{sample_size - 1}"
        )

    scale = projected_size / sample_size
    projected_images = eligible_images * scale
    projected_pairs = eligible_pairs * scale
    status = (
        "PASS"
        if projected_images >= minimum_images
        and projected_pairs >= minimum_pairs
        and len(eligible_clusters) >= minimum_clusters
        else "FAIL_COVERAGE"
    )
    return {
        "dataset": dataset,
        "order": int(candidate["order"]),
        "status": status,
        "manifest_path": manifest_path.as_posix(),
        "manifest_sha256": _sha256(manifest_path),
        "sample_size": sample_size,
        "eligible_images": eligible_images,
        "eligible_pairs": eligible_pairs,
        "independent_eligible_clusters": len(eligible_clusters),
        "projected_full_pilot_eligible_images": projected_images,
        "projected_full_pilot_eligible_pairs": projected_pairs,
        "failure_counts": failure_counts,
    }


def audit_candidates(
    config: Mapping[str, Any],
    *,
    config_path: Path,
) -> dict[str, Any]:
    """Evaluate exactly the frozen candidates and choose the first coverage PASS."""

    candidates = config.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise ValueError("config must contain exactly three candidates")
    names = tuple(str(candidate.get("dataset", "")) for candidate in candidates)
    orders = tuple(candidate.get("order") for candidate in candidates)
    if names != FROZEN_DATASET_ORDER or orders != (1, 2, 3):
        raise ValueError("candidate names and order differ from the frozen contract")
    if config.get("selection_rule") != "FIRST_PASS_IN_FROZEN_ORDER":
        raise ValueError("selection rule must remain FIRST_PASS_IN_FROZEN_ORDER")
    if config.get("frozen_before_method_results") is not True:
        raise ValueError("candidate audit must be frozen before method results")

    sample_size = int(config["dry_run_sample_size"])
    projected_size = int(config["projected_full_pilot_size"])
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        manifest_value = candidate.get("dry_run_manifest")
        if manifest_value is None:
            results.append(
                {
                    "dataset": candidate["dataset"],
                    "order": candidate["order"],
                    "status": "PENDING_SOURCE_ACCESS",
                    "source_revision_lock": candidate["source_revision_lock"],
                    "license_contract": candidate["license_contract"],
                }
            )
            continue
        manifest_path = Path(str(manifest_value))
        if not manifest_path.is_absolute():
            manifest_path = config_path.parent / manifest_path
        results.append(
            _audit_manifest(
                candidate,
                manifest_path.resolve(strict=True),
                sample_size=sample_size,
                projected_size=projected_size,
                minimum_images=int(config["minimum_projected_eligible_images"]),
                minimum_pairs=int(config["minimum_projected_eligible_pairs"]),
                minimum_clusters=int(config["minimum_independent_clusters"]),
                minimum_pixels=int(config["minimum_valid_depth_mask_pixels"]),
            )
        )
    selected = next(
        (result["dataset"] for result in results if result["status"] == "PASS"),
        None,
    )
    pending = any(result["status"] == "PENDING_SOURCE_ACCESS" for result in results)
    if selected is not None:
        status = "PASS_DRY_RUN"
        decision = f"SELECT_{selected.upper()}_FOR_FULL_PILOT"
    elif pending:
        status = "BLOCKED_SOURCE_ACCESS"
        decision = "WAIT_FOR_PREREGISTERED_SOURCE_ACCESS"
    else:
        status = "FAIL_ALL_CANDIDATES"
        decision = "STOPPED_NO_SECOND_REAL_DATASET"
    return {
        "schema_version": "covol-second-dataset-audit-v1",
        "status": status,
        "decision": decision,
        "scientific_evidence": "SOURCE_AND_COVERAGE_ONLY_NO_MODEL_RESULTS",
        "config_path": config_path.as_posix(),
        "config_sha256": _sha256(config_path),
        "selected_candidate": selected,
        "candidates": results,
    }


def write_candidate_audit_csv(path: Path, result: Mapping[str, Any]) -> None:
    """Write a portable row per frozen candidate, including blocked sources."""

    candidates = result.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidate audit result lacks candidate rows")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            row = {field: candidate.get(field, "") for field in _CSV_FIELDS}
            failures = candidate.get("failure_counts")
            row["failure_counts_json"] = (
                ""
                if failures is None
                else json.dumps(failures, sort_keys=True, separators=(",", ":"))
            )
            writer.writerow(row)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--scientific-gate", type=Path, default=DEFAULT_SCIENTIFIC_GATE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    require_covol_action_authorized(
        step003_authorization_path=args.authorization,
        scientific_gate_path=args.scientific_gate,
        scientific_action="second_dataset_recovery",
        step003_action="second_dataset_audit",
    )
    result = audit_candidates(_read_json(args.config), config_path=args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if args.csv_output is not None:
        write_candidate_audit_csv(args.csv_output, result)


if __name__ == "__main__":
    main()
