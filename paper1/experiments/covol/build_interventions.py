"""Build the authorized NYUv2 train-only 100-image diagnostic corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

try:
    from paper1.experiments.covol.step003_authorization import (
        require_action_authorized,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from step003_authorization import require_action_authorized  # type: ignore

DIAGNOSTIC_IMAGE_COUNT = 100
LOCAL_FAMILIES = (
    "semantic_preserving",
    "target_deletion",
    "local_entity_conflict",
    "depth_relation_conflict",
)
DISTRACTOR_VOCABULARY = (
    "bicycle",
    "fire hydrant",
    "mailbox",
    "motorcycle",
    "parking meter",
    "sailboat",
    "streetlight",
    "tractor",
)


def _stable_hash(*parts: object) -> str:
    return hashlib.sha256("/".join(map(str, parts)).encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(value)
    return rows


def _eligible_entities(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_entities = record.get("entities")
    if not isinstance(raw_entities, list):
        raise ValueError("source row entities must be a list")
    entities: list[dict[str, Any]] = []
    for value in raw_entities:
        if not isinstance(value, dict):
            raise ValueError("source entity must be an object")
        depth = value.get("eval_median_depth")
        if (
            value.get("reliable_mask") is True
            and int(value.get("eval_mask_area_pixels", 0)) >= 32
            and int(value.get("eval_valid_depth_count", 0)) >= 32
            and isinstance(depth, (int, float))
            and not isinstance(depth, bool)
            and math.isfinite(float(depth))
            and float(depth) > 0.0
            and str(value.get("entity_id", "")).strip()
            and str(value.get("class_name", "")).strip()
        ):
            entities.append(value)
    return entities


def _select_pair(record: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = []
    for left, right in combinations(_eligible_entities(record), 2):
        left_depth = float(left["eval_median_depth"])
        right_depth = float(right["eval_median_depth"])
        relative_gap = abs(left_depth - right_depth) / max(left_depth, right_depth)
        if (
            relative_gap >= 0.10
            and str(left["class_name"]).casefold()
            != str(right["class_name"]).casefold()
        ):
            candidates.append((left, right))
    if not candidates:
        raise ValueError("diagnostic image lacks a depth-separated entity pair")
    selected = min(
        candidates,
        key=lambda pair: _stable_hash(
            "diagnostic-pair-v1", pair[0]["entity_id"], pair[1]["entity_id"]
        ),
    )
    return (
        selected
        if float(selected[0]["eval_median_depth"])
        < float(selected[1]["eval_median_depth"])
        else (selected[1], selected[0])
    )


def _distractor(record: Mapping[str, Any]) -> str:
    present = {
        str(entity.get("class_name", "")).strip().casefold()
        for entity in record.get("entities", [])
        if isinstance(entity, Mapping)
    }
    for value in DISTRACTOR_VOCABULARY:
        if value.casefold() not in present:
            return value
    raise ValueError("no preregistered absent distractor remains")


def _captions(
    near_name: str,
    far_name: str,
    distractor: str,
) -> dict[str, tuple[str, str, str]]:
    return {
        "semantic_preserving": (
            f"The image shows the {near_name} closer to the camera "
            f"than the {far_name}.",
            f"The camera-to-object distance is shorter for the {near_name} "
            f"than for the {far_name}.",
            f"The camera-to-object distance is greater for the {far_name} "
            f"than for the {near_name}.",
        ),
        "target_deletion": (
            f"The image contains the {far_name}.",
            f"The image contains the {near_name}.",
            f"The image contains the {near_name} and the {far_name}.",
        ),
        "local_entity_conflict": (
            f"The image shows the {distractor} closer to the camera "
            f"than the {far_name}.",
            f"The camera-to-object distance is shorter for the {near_name} "
            f"than for the {distractor}.",
            f"The image shows the {distractor} closer to the camera "
            f"than the {near_name}.",
        ),
        "depth_relation_conflict": (
            f"The camera-to-object distance is greater for the {near_name} "
            f"than for the {far_name}.",
            f"The image shows the {near_name} farther from the camera "
            f"than the {far_name}.",
            f"The image shows the {far_name} closer to the camera "
            f"than the {near_name}.",
        ),
    }


def _diagnostic_candidates(
    source_rows: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    candidates = []
    for row in source_rows:
        if (
            row.get("dataset") == "NYUv2"
            and row.get("official_split") == "train"
            and row.get("split") == "train"
        ):
            try:
                _select_pair(row)
            except ValueError:
                continue
            candidates.append(row)
    if len(candidates) < DIAGNOSTIC_IMAGE_COUNT:
        raise ValueError("fewer than 100 eligible NYUv2 router-train images")
    return sorted(
        candidates,
        key=lambda row: _stable_hash("nyuv2-diagnostic-v1", row.get("image_id")),
    )[:DIAGNOSTIC_IMAGE_COUNT]


def build_diagnostic_interventions(
    source_rows: Sequence[Mapping[str, Any]],
    *,
    seed: int = 20260825,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return 1200 local rows plus separately stored null/global diagnostics."""

    selected = _diagnostic_candidates(source_rows)
    local_rows: list[dict[str, Any]] = []
    null_rows: list[dict[str, Any]] = []
    global_rows: list[dict[str, Any]] = []
    for record in selected:
        near, far = _select_pair(record)
        near_name = str(near["class_name"]).strip().replace("_", " ")
        far_name = str(far["class_name"]).strip().replace("_", " ")
        distractor = _distractor(record)
        base_caption = (
            f"The image shows the {near_name} closer to the camera than the {far_name}."
        )
        source_caption_hash = hashlib.sha256(base_caption.encode("utf-8")).hexdigest()
        caption_sets = _captions(near_name, far_name, distractor)
        common = {
            "dataset": "NYUv2",
            "image_id": record["image_id"],
            "scene_id": record["scene_id"],
            "sequence_id": record["sequence_id"],
            "cluster_id": record["cluster_id"],
            "rgb_sha256": record["rgb_sha256"],
            "source_split": "train",
            "diagnostic_split": "diagnostic_only_never_formal",
            "predicate_clean_caption": base_caption,
            "source_caption_hash": source_caption_hash,
            "target_region": {
                "near_entity_id": near["entity_id"],
                "far_entity_id": far["entity_id"],
            },
            "generator": "deterministic_nyuv2_relation_templates",
            "generator_revision": "diagnostic-interventions-v1",
            "seed": seed,
        }
        for family in LOCAL_FAMILIES:
            for variant_id, intervention in enumerate(caption_sets[family]):
                local_rows.append(
                    {
                        **common,
                        "error_type": family,
                        "variant_id": variant_id,
                        "template_id": f"{family}-v{variant_id}",
                        "intervention": intervention,
                        "machine_check": {
                            "predicate": "nyuv2_local_depth_relation_v1",
                            "passed": True,
                            "evidence_source": "official_train_entity_summaries",
                            "evidence_ids": [near["entity_id"], far["entity_id"]],
                            "near_depth_m": near["eval_median_depth"],
                            "far_depth_m": far["eval_median_depth"],
                            "near_class_name": near_name,
                            "far_class_name": far_name,
                            "minimum_valid_depth_pixels": 32,
                            "minimum_relative_depth_gap": 0.10,
                            "absent_distractor": distractor,
                        },
                    }
                )
        null_rows.append(
            {
                **common,
                "diagnostic_type": "null_caption",
                "caption": "",
            }
        )
        global_rows.append(
            {
                **common,
                "diagnostic_type": "global_caption_swap_placeholder",
                "caption": None,
                "status": "PENDING_CROSS_CLUSTER_ASSIGNMENT",
            }
        )
    validate_diagnostic_interventions(local_rows)
    return local_rows, null_rows, global_rows


def validate_diagnostic_interventions(rows: Sequence[Mapping[str, Any]]) -> None:
    """Validate count, uniqueness, family balance, and machine-check completeness."""

    expected_count = DIAGNOSTIC_IMAGE_COUNT * len(LOCAL_FAMILIES) * 3
    if len(rows) != expected_count:
        raise ValueError(f"diagnostic corpus must contain {expected_count} rows")
    keys = {
        (row.get("image_id"), row.get("error_type"), row.get("variant_id"))
        for row in rows
    }
    if len(keys) != expected_count:
        raise ValueError("diagnostic intervention keys must be unique")
    image_ids = {str(row.get("image_id", "")) for row in rows}
    if len(image_ids) != DIAGNOSTIC_IMAGE_COUNT:
        raise ValueError("diagnostic corpus must use exactly 100 images")
    for image_id in image_ids:
        image_rows = [row for row in rows if row.get("image_id") == image_id]
        counts = {
            family: sum(row.get("error_type") == family for row in image_rows)
            for family in LOCAL_FAMILIES
        }
        if any(count != 3 for count in counts.values()):
            raise ValueError("each image must have three variants per local family")
    if any(
        row.get("diagnostic_split") != "diagnostic_only_never_formal"
        or not isinstance(row.get("machine_check"), Mapping)
        or row["machine_check"].get("passed") is not True
        for row in rows
    ):
        raise ValueError("every diagnostic row must pass its machine check")


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_diagnostic_audit(
    local_rows: Sequence[Mapping[str, Any]],
    null_rows: Sequence[Mapping[str, Any]],
    global_rows: Sequence[Mapping[str, Any]],
    *,
    source_manifest_path: Path,
    local_output_path: Path,
    null_output_path: Path,
    global_output_path: Path,
    json_output_path: Path,
    csv_output_path: Path,
) -> dict[str, Any]:
    """Write a portable construction audit without claiming precision or H-effect."""

    validate_diagnostic_interventions(local_rows)
    image_ids = sorted({str(row["image_id"]) for row in local_rows})
    cluster_ids = sorted({str(row["cluster_id"]) for row in local_rows})
    family_counts = Counter(str(row["error_type"]) for row in local_rows)
    machine_pass_count = sum(
        row["machine_check"].get("passed") is True for row in local_rows
    )
    payload: dict[str, Any] = {
        "schema_version": "covol-diagnostic-intervention-audit-v1",
        "status": "PENDING_INDEPENDENT_PRECISION_AND_H_SENSITIVITY",
        "authorization_scope": "NYUV2_OFFICIAL_TRAIN_DIAGNOSTIC_ONLY",
        "scientific_evidence": "CORPUS_CONSTRUCTION_NOT_MODEL_EFFECT",
        "source_manifest_sha256": _file_sha256(source_manifest_path),
        "source_manifest_row_count": sum(
            1
            for line in source_manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ),
        "selected_image_count": len(image_ids),
        "selected_image_set_sha256": _stable_hash(*image_ids),
        "selected_cluster_count": len(cluster_ids),
        "selected_cluster_set_sha256": _stable_hash(*cluster_ids),
        "local_row_count": len(local_rows),
        "family_counts": dict(sorted(family_counts.items())),
        "machine_check_pass_count": machine_pass_count,
        "machine_check_pass_rate": machine_pass_count / len(local_rows),
        "independent_precision_status": "PENDING",
        "formal_train_dev_test_exclusion": True,
        "null_row_count": len(null_rows),
        "global_row_count": len(global_rows),
        "local_output_sha256": _file_sha256(local_output_path),
        "null_output_sha256": _file_sha256(null_output_path),
        "global_output_sha256": _file_sha256(global_output_path),
    }
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    csv_output_path.parent.mkdir(parents=True, exist_ok=True)
    flat = {
        key: json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
        for key, value in payload.items()
    }
    with csv_output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat), lineterminator="\n")
        writer.writeheader()
        writer.writerow(flat)
    return payload


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--null-output", type=Path, required=True)
    parser.add_argument("--global-output", type=Path, required=True)
    parser.add_argument("--audit-json", type=Path, required=True)
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260825)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    require_action_authorized(args.authorization, action="nyuv2_diagnostic_corpus")
    local, null, global_rows = build_diagnostic_interventions(
        _read_jsonl(args.source_manifest),
        seed=args.seed,
    )
    _write_jsonl(args.output, local)
    _write_jsonl(args.null_output, null)
    _write_jsonl(args.global_output, global_rows)
    write_diagnostic_audit(
        local,
        null,
        global_rows,
        source_manifest_path=args.source_manifest,
        local_output_path=args.output,
        null_output_path=args.null_output,
        global_output_path=args.global_output,
        json_output_path=args.audit_json,
        csv_output_path=args.audit_csv,
    )


if __name__ == "__main__":
    main()
