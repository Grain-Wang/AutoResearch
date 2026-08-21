"""Plan the fixed 500-image KITTI Step-003 subset before downloading RGBs."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from paper1.experiments.covol.build_image_manifest import (
    SPLIT_ORDER,
    _file_sha256,
    _select_scene_grouped,
)
from paper1.experiments.covol.build_training_pilot_manifest import (
    PILOT_COMPONENT_CAPS,
    PILOT_SEED,
    PILOT_SPLIT_COUNTS,
)

_RAW_RGB_PATH_RE = re.compile(
    r"^(?P<date>\d{4}_\d{2}_\d{2})/"
    r"(?P<drive>\d{4}_\d{2}_\d{2}_drive_\d{4}_sync)/"
    r"(?P<camera>image_0[23])/data/(?P<frame>\d{10})\.png$"
)


def _normalized_source_line(line: str, *, line_number: int) -> str | None:
    normalized = line.partition("#")[0].strip()
    if not normalized:
        return None
    token = normalized.split()[0]
    path = PurePosixPath(token.replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"line {line_number}: unsafe RGB path")
    if _RAW_RGB_PATH_RE.fullmatch(path.as_posix()) is None:
        raise ValueError(f"line {line_number}: unsupported KITTI RGB path {token!r}")
    return normalized


def _candidate_record(source_line: str, *, line_number: int) -> dict[str, Any]:
    rgb_relative_path = PurePosixPath(source_line.split()[0]).as_posix()
    match = _RAW_RGB_PATH_RE.fullmatch(rgb_relative_path)
    if match is None:  # Guarded by _normalized_source_line.
        raise AssertionError("validated KITTI path no longer matches")
    date = match.group("date")
    drive = match.group("drive")
    if not drive.startswith(f"{date}_drive_"):
        raise ValueError(f"line {line_number}: drive/date mismatch")
    sequence_id = f"{date}/{drive}"
    frame_index = int(match.group("frame"))
    camera_id = match.group("camera").lower()
    return {
        "dataset": "KITTI",
        "image_id": f"{sequence_id}/{camera_id}/{frame_index:010d}",
        "scene_id": sequence_id,
        "sequence_id": sequence_id,
        "frame_index": frame_index,
        "camera_id": camera_id,
        "rgb_relative_path": rgb_relative_path,
        "repository_path": f"raw_data/{rgb_relative_path}",
        "source_line": source_line,
        "source_line_number": line_number,
    }


def read_kitti_candidates(split_path: Path) -> list[dict[str, Any]]:
    """Parse canonical Eigen-training lines without touching RGB files."""

    candidates: list[dict[str, Any]] = []
    seen_images: set[str] = set()
    with split_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            normalized = _normalized_source_line(line, line_number=line_number)
            if normalized is None:
                continue
            record = _candidate_record(normalized, line_number=line_number)
            image_id = str(record["image_id"])
            if image_id in seen_images:
                raise ValueError(f"duplicate KITTI image_id {image_id!r}")
            seen_images.add(image_id)
            candidates.append(record)
    if not candidates:
        raise ValueError("KITTI split contains no supported training candidates")
    return candidates


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def plan_kitti_training_subset(
    split_path: Path,
    *,
    selected_split_path: Path,
    download_plan_path: Path,
    audit_path: Path,
    repository_id: str,
    repository_revision: str,
) -> dict[str, Any]:
    """Select, materialize, and audit the fixed KITTI download subset."""

    if not repository_id.strip() or not repository_revision.strip():
        raise ValueError("repository_id and repository_revision must be explicit")
    if re.fullmatch(r"[0-9a-f]{40}", repository_revision.strip().lower()) is None:
        raise ValueError("repository_revision must be a full 40-hex commit")
    candidates = read_kitti_candidates(split_path)
    selected, cluster_counts = _select_scene_grouped(
        candidates,
        dataset="KITTI",
        split_counts=PILOT_SPLIT_COUNTS,
        seed=PILOT_SEED,
        max_images_per_component=PILOT_COMPONENT_CAPS,
    )
    selected.sort(
        key=lambda record: (
            SPLIT_ORDER.index(str(record["split"])),
            str(record["selection_hash"]),
        )
    )
    if cluster_counts["internal_test"] < 20:
        raise ValueError("KITTI plan has fewer than 20 internal-test drives")

    selected_split_path.parent.mkdir(parents=True, exist_ok=True)
    with selected_split_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in selected:
            handle.write(str(record["source_line"]))
            handle.write("\n")
    download_records = [
        {
            key: record[key]
            for key in (
                "camera_id",
                "cluster_id",
                "dataset",
                "frame_index",
                "image_id",
                "repository_path",
                "rgb_relative_path",
                "scene_id",
                "selection_hash",
                "sequence_id",
                "split",
            )
        }
        for record in selected
    ]
    _write_jsonl(download_plan_path, download_records)
    selected_counts = {
        split: sum(record["split"] == split for record in selected)
        for split in SPLIT_ORDER
    }
    audit = {
        "status": "PASS_PREFREEZE_NO_TEST_ACCESS",
        "seed": PILOT_SEED,
        "repository_id": repository_id.strip(),
        "repository_revision": repository_revision.strip().lower(),
        "input": {
            "candidate_count": len(candidates),
            "canonical_training_split_sha256": _file_sha256(split_path),
        },
        "selection": {
            "split_counts": selected_counts,
            "cluster_counts": cluster_counts,
            "max_images_per_scene_sequence_component": PILOT_COMPONENT_CAPS,
        },
        "selected_split_sha256": _file_sha256(selected_split_path),
        "download_plan_sha256": _file_sha256(download_plan_path),
        "record_count": len(selected),
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return audit


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-training-split", type=Path, required=True)
    parser.add_argument("--selected-split", type=Path, required=True)
    parser.add_argument("--download-plan", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--repository-revision", required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    plan_kitti_training_subset(
        args.canonical_training_split,
        selected_split_path=args.selected_split,
        download_plan_path=args.download_plan,
        audit_path=args.audit,
        repository_id=args.repository_id,
        repository_revision=args.repository_revision,
    )


if __name__ == "__main__":
    main()
