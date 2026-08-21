"""Audit whether local mask/depth annotations support CoVoL interventions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from paper1.experiments.covol.audit_provenance import (
        EXPANDED_SELECTION_STAGE,
        PILOT_SELECTION_STAGE,
        SPLIT_ORDER,
        file_sha256,
        split_audit_link_payload,
        validate_trusted_training_source,
        verify_split_audit,
    )
    from paper1.experiments.covol.build_nyuv2_source_manifest import (
        NYUV2_EVAL_PROTOCOL_SHA256,
    )
except ModuleNotFoundError:  # Direct script execution from the repository root.
    from audit_provenance import (  # type: ignore[no-redef]
        EXPANDED_SELECTION_STAGE,
        PILOT_SELECTION_STAGE,
        SPLIT_ORDER,
        file_sha256,
        split_audit_link_payload,
        validate_trusted_training_source,
        verify_split_audit,
    )
    from build_nyuv2_source_manifest import (  # type: ignore[no-redef]
        NYUV2_EVAL_PROTOCOL_SHA256,
    )

SCHEMA_VERSION = "covol-annotation-coverage-v1"
RELATIVE_GAP_DEFINITION = "abs(depth_a-depth_b)/max(depth_a,depth_b)"
REQUIRED_DATASETS = frozenset({"KITTI", "NYUv2"})
VIRTUAL_KITTI_DATASET = "Virtual KITTI 2"
_SHA256_LENGTH = 64


@dataclass(frozen=True)
class CoverageThresholds:
    """Frozen annotation-coverage thresholds from Step 003."""

    minimum_mask_area_pixels: int = 32
    minimum_valid_depth_pixels: int = 32
    minimum_relative_median_depth_gap: float = 0.10
    minimum_eligible_images: int = 150
    minimum_eligible_pairs: int = 300
    minimum_images_with_eligible_pair: int = 150
    minimum_independent_clusters_with_eligible_pair: int = 20


@dataclass(frozen=True)
class EntitySummary:
    """Validated per-entity mask/depth summary."""

    entity_id: str
    class_name: str
    reliable_mask: bool
    eval_mask_area_pixels: int
    eval_valid_depth_count: int
    eval_median_depth: float | None


@dataclass(frozen=True)
class ImageAnnotationSummary:
    """Validated per-image annotation summary with source provenance."""

    dataset: str
    image_id: str
    scene_id: str
    sequence_id: str
    cluster_id: str
    rgb_sha256: str
    official_split: str
    split: str
    selection_hash: str
    manifest_scope: str
    official_test_audit_status: str
    selection_stage: str
    eval_protocol_sha256: str | None
    annotation_available: bool
    annotation_source: str | None
    annotation_sha256: str | None
    depth_available: bool
    depth_source: str | None
    depth_sha256: str | None
    entities: tuple[EntitySummary, ...]


def _valid_sha256(value: object) -> bool:
    text = str(value).strip().lower()
    return len(text) == _SHA256_LENGTH and all(
        character in "0123456789abcdef" for character in text
    )


def _required_boolean(record: Mapping[str, Any], field: str, *, context: str) -> bool:
    value = record.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{context}: {field} must be a boolean")
    return value


def _availability(
    record: Mapping[str, Any],
    *,
    prefix: str,
    context: str,
) -> bool:
    field = f"{prefix}_available"
    if field in record:
        return _required_boolean(record, field, context=context)
    source = record.get(f"{prefix}_source")
    if isinstance(source, Mapping):
        return bool(str(source.get("path", "")).strip())
    return bool(source)


def _nonnegative_integer(value: object, *, field: str, context: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{context}: {field} must be a nonnegative integer")
    try:
        integer = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{context}: {field} must be a nonnegative integer"
        ) from error
    if integer < 0 or integer != value:
        raise ValueError(f"{context}: {field} must be a nonnegative integer")
    return integer


def _optional_provenance(
    record: Mapping[str, Any],
    *,
    prefix: str,
    available: bool,
    context: str,
) -> tuple[str | None, str | None]:
    raw_source = record.get(f"{prefix}_source")
    raw_sha256 = record.get(f"{prefix}_sha256")
    if isinstance(raw_source, Mapping):
        source = str(raw_source.get("path", "")).strip()
        nested_sha256 = raw_source.get("sha256")
        if raw_sha256 is not None and str(raw_sha256).strip().lower() != str(
            nested_sha256
        ).strip().lower():
            raise ValueError(
                f"{context}: conflicting nested and flat {prefix} SHA256 values"
            )
        raw_sha256 = nested_sha256
    else:
        source = None if raw_source is None else str(raw_source).strip()
    sha256 = None if raw_sha256 is None else str(raw_sha256).strip().lower()
    if available:
        if not source:
            raise ValueError(
                f"{context}: {prefix}_source is required when {prefix} is available"
            )
        if not _valid_sha256(sha256):
            raise ValueError(
                f"{context}: {prefix}_sha256 must be a lowercase SHA256 when "
                f"{prefix} is available"
            )
    elif source or sha256:
        if not source or not _valid_sha256(sha256):
            raise ValueError(
                f"{context}: partial unavailable-{prefix} provenance is not allowed"
            )
    return source or None, sha256 or None


def _validate_entity(
    value: object,
    *,
    context: str,
    annotation_available: bool,
    depth_available: bool,
) -> EntitySummary:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context}: entity must be a JSON object")
    entity_id = str(value.get("entity_id", "")).strip()
    if not entity_id:
        raise ValueError(f"{context}: entity_id must be nonempty")
    class_name = str(value.get("class_name", "")).strip()
    if not class_name:
        raise ValueError(
            f"{context}: class_name is required for language interventions"
        )
    reliable_mask = _required_boolean(value, "reliable_mask", context=context)
    mask_area = _nonnegative_integer(
        value.get("eval_mask_area_pixels"),
        field="eval_mask_area_pixels",
        context=context,
    )
    valid_depth = _nonnegative_integer(
        value.get("eval_valid_depth_count"),
        field="eval_valid_depth_count",
        context=context,
    )
    if valid_depth > mask_area:
        raise ValueError(
            f"{context}: eval_valid_depth_count cannot exceed "
            "eval_mask_area_pixels"
        )
    raw_median = value.get("eval_median_depth")
    median_depth: float | None
    if raw_median is None:
        median_depth = None
    else:
        try:
            median_depth = float(raw_median)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{context}: eval_median_depth must be numeric or null"
            ) from error
        if not math.isfinite(median_depth) or median_depth <= 0.0:
            raise ValueError(
                f"{context}: eval_median_depth must be finite and positive"
            )
        if valid_depth == 0:
            raise ValueError(
                f"{context}: eval_median_depth requires valid eval-depth pixels"
            )
    if not annotation_available:
        raise ValueError(f"{context}: entities require annotation provenance")
    if valid_depth > 0 and not depth_available:
        raise ValueError(f"{context}: valid depth summaries require depth provenance")
    return EntitySummary(
        entity_id=entity_id,
        class_name=class_name,
        reliable_mask=reliable_mask,
        eval_mask_area_pixels=mask_area,
        eval_valid_depth_count=valid_depth,
        eval_median_depth=median_depth,
    )


def validate_image_record(
    record: Mapping[str, Any],
    *,
    line_number: int,
) -> ImageAnnotationSummary:
    """Validate one image-level annotation record.

    Empty ``entities`` is valid and intentionally represents zero local coverage.
    Any nonempty precomputed summary must be tied to auditable annotation and
    depth hashes.
    """

    context = f"record {line_number}"
    dataset = str(record.get("dataset", "")).strip()
    image_id = str(record.get("image_id", "")).strip()
    scene_id = str(record.get("scene_id", "")).strip()
    sequence_id = str(record.get("sequence_id", "")).strip()
    cluster_id = str(record.get("cluster_id", "")).strip().lower()
    if not dataset or not image_id or not scene_id or not sequence_id:
        raise ValueError(
            f"{context}: dataset, image_id, scene_id, and sequence_id are required"
        )
    if not _valid_sha256(cluster_id):
        raise ValueError(f"{context}: cluster_id must be a lowercase SHA256")
    rgb_sha256 = str(record.get("rgb_sha256", "")).strip().lower()
    if not _valid_sha256(rgb_sha256):
        raise ValueError(f"{context}: rgb_sha256 must be a lowercase SHA256")
    official_split = str(record.get("official_split", "")).strip()
    if official_split != "train":
        raise ValueError(f"{context}: coverage input must be official_split=train")
    split = str(record.get("split", "")).strip()
    if split not in SPLIT_ORDER:
        raise ValueError(f"{context}: split must be one of {SPLIT_ORDER}")
    selection_hash = str(record.get("selection_hash", "")).strip().lower()
    if not _valid_sha256(selection_hash):
        raise ValueError(f"{context}: selection_hash must be a lowercase SHA256")
    manifest_scope = str(record.get("manifest_scope", "")).strip()
    if manifest_scope != "training_pilot_step003":
        raise ValueError(
            f"{context}: manifest_scope must be training_pilot_step003"
        )
    official_test_audit_status = str(
        record.get("official_test_audit_status", "")
    ).strip()
    if official_test_audit_status != "DEFERRED_FROZEN":
        raise ValueError(
            f"{context}: official_test_audit_status must be DEFERRED_FROZEN"
        )
    selection_stage = str(record.get("selection_stage", "")).strip()
    if selection_stage not in {PILOT_SELECTION_STAGE, EXPANDED_SELECTION_STAGE}:
        raise ValueError(
            f"{context}: selection_stage must be PILOT_V1 or EXPANDED_FOR_POWER"
        )
    raw_eval_protocol_sha256 = record.get("eval_protocol_sha256")
    eval_protocol_sha256 = (
        None
        if raw_eval_protocol_sha256 is None
        else str(raw_eval_protocol_sha256).strip().lower()
    )
    if eval_protocol_sha256 is not None and not _valid_sha256(
        eval_protocol_sha256
    ):
        raise ValueError(f"{context}: eval_protocol_sha256 must be a SHA256 or null")
    if dataset == "NYUv2" and eval_protocol_sha256 != NYUV2_EVAL_PROTOCOL_SHA256:
        raise ValueError(
            f"{context}: NYUv2 eval_protocol_sha256 does not match the frozen crop"
        )
    annotation_available = _availability(
        record,
        prefix="annotation",
        context=context,
    )
    depth_available = _availability(
        record,
        prefix="depth",
        context=context,
    )
    annotation_source, annotation_sha256 = _optional_provenance(
        record,
        prefix="annotation",
        available=annotation_available,
        context=context,
    )
    depth_source, depth_sha256 = _optional_provenance(
        record,
        prefix="depth",
        available=depth_available,
        context=context,
    )
    raw_entities = record.get("entities")
    if not isinstance(raw_entities, list):
        raise ValueError(f"{context}: entities must be a JSON list")
    if raw_entities and eval_protocol_sha256 is None:
        raise ValueError(
            f"{context}: entity summaries require eval_protocol_sha256"
        )
    entities = tuple(
        _validate_entity(
            entity,
            context=f"{context} entity {index}",
            annotation_available=annotation_available,
            depth_available=depth_available,
        )
        for index, entity in enumerate(raw_entities)
    )
    entity_ids = [entity.entity_id for entity in entities]
    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError(f"{context}: entity_id values must be unique within image")
    return ImageAnnotationSummary(
        dataset=dataset,
        image_id=image_id,
        scene_id=scene_id,
        sequence_id=sequence_id,
        cluster_id=cluster_id,
        rgb_sha256=rgb_sha256,
        official_split=official_split,
        split=split,
        selection_hash=selection_hash,
        manifest_scope=manifest_scope,
        official_test_audit_status=official_test_audit_status,
        selection_stage=selection_stage,
        eval_protocol_sha256=eval_protocol_sha256,
        annotation_available=annotation_available,
        annotation_source=annotation_source,
        annotation_sha256=annotation_sha256,
        depth_available=depth_available,
        depth_source=depth_source,
        depth_sha256=depth_sha256,
        entities=entities,
    )


def read_annotation_manifest(path: Path) -> list[ImageAnnotationSummary]:
    """Read and validate an image-level annotation JSONL manifest."""

    records: list[ImageAnnotationSummary] = []
    seen_images: set[tuple[str, str]] = set()
    seen_selection_hashes: set[tuple[str, str]] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, Mapping):
                raise ValueError(f"{path.name}:{line_number} is not a JSON object")
            validate_trusted_training_source(
                raw,
                context=f"{path.name}:{line_number}",
            )
            record = validate_image_record(raw, line_number=line_number)
            key = (record.dataset, record.image_id)
            if key in seen_images:
                raise ValueError(
                    f"{path.name}:{line_number} duplicates image key {key!r}"
                )
            seen_images.add(key)
            selection_key = (record.dataset, record.selection_hash)
            if selection_key in seen_selection_hashes:
                raise ValueError(
                    f"{path.name}:{line_number} duplicates selection_hash"
                )
            seen_selection_hashes.add(selection_key)
            records.append(record)
    if not records:
        raise ValueError("annotation manifest must contain at least one image")
    for dataset in {record.dataset for record in records}:
        dataset_records = [record for record in records if record.dataset == dataset]
        for field in ("scene_id", "sequence_id"):
            group_clusters: dict[str, set[str]] = defaultdict(set)
            for record in dataset_records:
                group_clusters[str(getattr(record, field))].add(record.cluster_id)
            split_components = sorted(
                group
                for group, clusters in group_clusters.items()
                if len(clusters) > 1
            )
            if split_components:
                raise ValueError(
                    f"{dataset}: {field} maps to multiple cluster_id values: "
                    f"{split_components[:5]}"
                )
        for field in (
            "image_id",
            "cluster_id",
            "scene_id",
            "sequence_id",
            "rgb_sha256",
        ):
            group_splits: dict[str, set[str]] = defaultdict(set)
            for record in dataset_records:
                group_splits[str(getattr(record, field))].add(record.split)
            leaked = sorted(
                group for group, splits in group_splits.items() if len(splits) > 1
            )
            if leaked:
                raise ValueError(
                    f"{dataset}: internal {field} split leakage: {leaked[:5]}"
                )
    return records


def relative_median_depth_gap(left: float, right: float) -> float:
    """Return the preregistered conservative relative median-depth gap."""

    left = float(left)
    right = float(right)
    if not math.isfinite(left) or not math.isfinite(right) or left <= 0 or right <= 0:
        raise ValueError("median depths must be finite and positive")
    return abs(left - right) / max(left, right)


def _canonical_provenance_hash(
    records: Sequence[ImageAnnotationSummary],
    *,
    prefix: str,
) -> str:
    rows = [
        {
            "dataset": record.dataset,
            "image_id": record.image_id,
            "source": getattr(record, f"{prefix}_source"),
            "sha256": getattr(record, f"{prefix}_sha256"),
        }
        for record in sorted(records, key=lambda row: (row.dataset, row.image_id))
    ]
    encoded = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def summarize_dataset_coverage(
    dataset: str,
    records: Sequence[ImageAnnotationSummary],
    *,
    thresholds: CoverageThresholds | None = None,
) -> dict[str, Any]:
    """Summarize target and pair eligibility for one dataset."""

    thresholds = thresholds or CoverageThresholds()
    if not records:
        raise ValueError(f"{dataset}: records must not be empty")
    if any(record.dataset != dataset for record in records):
        raise ValueError(f"{dataset}: records contain a different dataset")

    entity_count = 0
    reliable_mask_count = 0
    sufficient_mask_area_count = 0
    sufficient_valid_depth_count = 0
    eligible_target_count = 0
    pair_candidate_count = 0
    eligible_pair_count = 0
    images_with_reliable_mask = 0
    eligible_image_count = 0
    images_with_pair = 0
    scenes_with_pair: set[str] = set()
    clusters_with_pair: set[str] = set()
    exclusions = defaultdict(int)

    for record in records:
        reliable_in_image = False
        eligible_targets: list[EntitySummary] = []
        for entity in record.entities:
            entity_count += 1
            if entity.reliable_mask:
                reliable_mask_count += 1
                reliable_in_image = True
            else:
                exclusions["unreliable_mask"] += 1
            if (
                entity.eval_mask_area_pixels
                >= thresholds.minimum_mask_area_pixels
            ):
                sufficient_mask_area_count += 1
            else:
                exclusions["mask_area_below_threshold"] += 1
            if (
                entity.eval_valid_depth_count
                >= thresholds.minimum_valid_depth_pixels
            ):
                sufficient_valid_depth_count += 1
            else:
                exclusions["valid_depth_below_threshold"] += 1
            if (
                entity.reliable_mask
                and entity.eval_mask_area_pixels
                >= thresholds.minimum_mask_area_pixels
                and entity.eval_valid_depth_count
                >= thresholds.minimum_valid_depth_pixels
            ):
                eligible_targets.append(entity)
                eligible_target_count += 1
                if entity.eval_median_depth is None:
                    exclusions["eligible_target_missing_median_depth"] += 1

        if reliable_in_image:
            images_with_reliable_mask += 1
        if eligible_targets:
            eligible_image_count += 1

        pair_members = [
            entity
            for entity in eligible_targets
            if entity.eval_median_depth is not None
        ]
        image_has_pair = False
        for left_index, left in enumerate(pair_members):
            for right in pair_members[left_index + 1 :]:
                pair_candidate_count += 1
                assert left.eval_median_depth is not None
                assert right.eval_median_depth is not None
                gap = relative_median_depth_gap(
                    left.eval_median_depth,
                    right.eval_median_depth,
                )
                if gap >= thresholds.minimum_relative_median_depth_gap:
                    eligible_pair_count += 1
                    image_has_pair = True
                else:
                    exclusions["pair_depth_gap_below_threshold"] += 1
        if image_has_pair:
            images_with_pair += 1
            scenes_with_pair.add(record.scene_id)
            clusters_with_pair.add(record.cluster_id)

    image_gate_pass = eligible_image_count >= thresholds.minimum_eligible_images
    pair_gate_pass = (
        eligible_pair_count >= thresholds.minimum_eligible_pairs
        and images_with_pair >= thresholds.minimum_images_with_eligible_pair
        and len(clusters_with_pair)
        >= thresholds.minimum_independent_clusters_with_eligible_pair
    )
    gate_pass = image_gate_pass and pair_gate_pass
    if gate_pass:
        decision = "GO_LOCAL_STRUCTURED_INTERVENTIONS"
    elif dataset.strip().casefold() == "kitti":
        decision = "FALLBACK_VIRTUAL_KITTI_2_FOR_STRUCTURED_OUTDOOR"
    else:
        decision = "STOP_INSUFFICIENT_LOCAL_ANNOTATION_COVERAGE"

    image_count = len(records)
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset": dataset,
        "image_count": image_count,
        "cluster_count": len({record.cluster_id for record in records}),
        "scene_count": len({record.scene_id for record in records}),
        "annotation_available_image_count": sum(
            record.annotation_available for record in records
        ),
        "depth_available_image_count": sum(
            record.depth_available for record in records
        ),
        "entity_count": entity_count,
        "reliable_mask_entity_count": reliable_mask_count,
        "sufficient_mask_area_entity_count": sufficient_mask_area_count,
        "sufficient_valid_depth_entity_count": sufficient_valid_depth_count,
        "eligible_target_count": eligible_target_count,
        "images_with_reliable_mask": images_with_reliable_mask,
        "eligible_image_count": eligible_image_count,
        "eligible_image_fraction": eligible_image_count / image_count,
        "pair_candidate_count": pair_candidate_count,
        "eligible_pair_count": eligible_pair_count,
        "images_with_eligible_pair": images_with_pair,
        "scenes_with_eligible_pair": len(scenes_with_pair),
        "independent_clusters_with_eligible_pair": len(clusters_with_pair),
        "image_gate_pass": image_gate_pass,
        "pair_gate_pass": pair_gate_pass,
        "gate_pass": gate_pass,
        "decision": decision,
        "thresholds": asdict(thresholds),
        "relative_gap_definition": RELATIVE_GAP_DEFINITION,
        "exclusion_counts": dict(sorted(exclusions.items())),
        "provenance": {
            "rgb_identity_sha256": hashlib.sha256(
                json.dumps(
                    [
                        {
                            "image_id": record.image_id,
                            "rgb_sha256": record.rgb_sha256,
                        }
                        for record in sorted(records, key=lambda row: row.image_id)
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "annotation_provenance_sha256": _canonical_provenance_hash(
                records,
                prefix="annotation",
            ),
            "depth_provenance_sha256": _canonical_provenance_hash(
                records,
                prefix="depth",
            ),
            "unique_annotation_source_count": len(
                {
                    record.annotation_source
                    for record in records
                    if record.annotation_source is not None
                }
            ),
            "unique_depth_source_count": len(
                {
                    record.depth_source
                    for record in records
                    if record.depth_source is not None
                }
            ),
        },
    }


def build_coverage_audit(
    records: Sequence[ImageAnnotationSummary],
    *,
    input_manifest_sha256: str,
    thresholds: CoverageThresholds | None = None,
) -> dict[str, Any]:
    """Build the complete deterministic coverage audit payload."""

    thresholds = thresholds or CoverageThresholds()
    if not _valid_sha256(input_manifest_sha256):
        raise ValueError("input_manifest_sha256 must be a valid SHA256")
    by_dataset: dict[str, list[ImageAnnotationSummary]] = defaultdict(list)
    for record in records:
        by_dataset[record.dataset].append(record)
    raw_datasets = [
        summarize_dataset_coverage(
            dataset,
            sorted(by_dataset[dataset], key=lambda row: row.image_id),
            thresholds=thresholds,
        )
        for dataset in sorted(by_dataset)
    ]
    present_datasets = {str(dataset["dataset"]) for dataset in raw_datasets}
    missing_required_datasets = sorted(REQUIRED_DATASETS - present_datasets)
    virtual_kitti_pass = any(
        dataset["dataset"] == VIRTUAL_KITTI_DATASET and dataset["gate_pass"]
        for dataset in raw_datasets
    )
    datasets: list[dict[str, Any]] = []
    for raw_dataset in raw_datasets:
        dataset = dict(raw_dataset)
        fallback_resolved = (
            dataset["dataset"] == "KITTI"
            and not dataset["gate_pass"]
            and virtual_kitti_pass
        )
        dataset["fallback_resolved"] = fallback_resolved
        dataset["structured_requirement_pass"] = (
            bool(dataset["gate_pass"]) or fallback_resolved
        )
        if fallback_resolved:
            dataset["decision"] = "FALLBACK_RESOLVED_BY_VIRTUAL_KITTI_2"
        datasets.append(dataset)
    gate_pass = not missing_required_datasets and all(
        dataset["structured_requirement_pass"] for dataset in datasets
    )
    by_dataset_name = {
        str(dataset["dataset"]): dataset for dataset in datasets
    }
    nyuv2_pass = bool(by_dataset_name.get("NYUv2", {}).get("gate_pass"))
    kitti_pass = bool(by_dataset_name.get("KITTI", {}).get("gate_pass"))
    if nyuv2_pass and kitti_pass:
        claim_dataset_decision = {
            "decision": "GO_LOCAL_CLAIMS_NYUV2_KITTI",
            "local_claim_datasets": ["NYUv2", "KITTI"],
            "kitti_role": "local_primary",
        }
    elif nyuv2_pass and virtual_kitti_pass:
        claim_dataset_decision = {
            "decision": "GO_LOCAL_CLAIMS_NYUV2_VKITTI2",
            "local_claim_datasets": ["NYUv2", VIRTUAL_KITTI_DATASET],
            "kitti_role": "image_level_sensitivity_only",
        }
    elif not nyuv2_pass:
        claim_dataset_decision = {
            "decision": "STOP_LOCAL_CLAIMS",
            "local_claim_datasets": [],
            "kitti_role": "diagnostic_only",
        }
    else:
        claim_dataset_decision = {
            "decision": "STOP_TWO_DATASET_CLAIM_PENDING_VKITTI2",
            "local_claim_datasets": ["NYUv2"],
            "kitti_role": "image_level_sensitivity_only",
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if gate_pass else "FAIL",
        "implementation_sha256": file_sha256(Path(__file__)),
        "input": {
            "manifest_sha256": input_manifest_sha256,
            "image_count": len(records),
        },
        "thresholds": asdict(thresholds),
        "relative_gap_definition": RELATIVE_GAP_DEFINITION,
        "required_datasets": sorted(REQUIRED_DATASETS),
        "missing_required_datasets": missing_required_datasets,
        "claim_dataset_decision": claim_dataset_decision,
        "datasets": datasets,
    }


def _csv_rows(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    input_payload = audit["input"]
    split_audit = audit.get("split_audit")
    for dataset in audit["datasets"]:
        thresholds = dataset["thresholds"]
        provenance = dataset["provenance"]
        exclusions = dataset["exclusion_counts"]
        rows.append(
            {
                "schema_version": audit["schema_version"],
                "run_mode": audit.get("run_mode", "UNLINKED_DIAGNOSTIC"),
                "authorization_scope": audit.get("authorization_scope"),
                "status": (
                    "PASS" if dataset["structured_requirement_pass"] else "FAIL"
                ),
                "dataset": dataset["dataset"],
                "input_manifest_sha256": input_payload["manifest_sha256"],
                "implementation_sha256": audit["implementation_sha256"],
                "split_audit_sha256": (
                    split_audit["split_audit_sha256"]
                    if isinstance(split_audit, Mapping)
                    else None
                ),
                "rgb_identity_sha256": provenance["rgb_identity_sha256"],
                "annotation_provenance_sha256": provenance[
                    "annotation_provenance_sha256"
                ],
                "depth_provenance_sha256": provenance["depth_provenance_sha256"],
                "image_count": dataset["image_count"],
                "cluster_count": dataset["cluster_count"],
                "scene_count": dataset["scene_count"],
                "annotation_available_image_count": dataset[
                    "annotation_available_image_count"
                ],
                "depth_available_image_count": dataset[
                    "depth_available_image_count"
                ],
                "entity_count": dataset["entity_count"],
                "eligible_target_count": dataset["eligible_target_count"],
                "eligible_image_count": dataset["eligible_image_count"],
                "eligible_image_fraction": dataset["eligible_image_fraction"],
                "pair_candidate_count": dataset["pair_candidate_count"],
                "eligible_pair_count": dataset["eligible_pair_count"],
                "images_with_eligible_pair": dataset["images_with_eligible_pair"],
                "scenes_with_eligible_pair": dataset["scenes_with_eligible_pair"],
                "independent_clusters_with_eligible_pair": dataset[
                    "independent_clusters_with_eligible_pair"
                ],
                "minimum_mask_area_pixels": thresholds[
                    "minimum_mask_area_pixels"
                ],
                "minimum_valid_depth_pixels": thresholds[
                    "minimum_valid_depth_pixels"
                ],
                "minimum_relative_median_depth_gap": thresholds[
                    "minimum_relative_median_depth_gap"
                ],
                "minimum_eligible_images": thresholds["minimum_eligible_images"],
                "minimum_eligible_pairs": thresholds["minimum_eligible_pairs"],
                "minimum_images_with_eligible_pair": thresholds[
                    "minimum_images_with_eligible_pair"
                ],
                "minimum_independent_clusters_with_eligible_pair": thresholds[
                    "minimum_independent_clusters_with_eligible_pair"
                ],
                "relative_gap_definition": dataset["relative_gap_definition"],
                "image_gate_pass": dataset["image_gate_pass"],
                "pair_gate_pass": dataset["pair_gate_pass"],
                "gate_pass": dataset["gate_pass"],
                "fallback_resolved": dataset["fallback_resolved"],
                "structured_requirement_pass": dataset[
                    "structured_requirement_pass"
                ],
                "decision": dataset["decision"],
                "exclusion_counts_json": json.dumps(
                    exclusions,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        )
    return rows


def write_coverage_outputs(
    audit: Mapping[str, Any],
    *,
    output_csv: Path,
    output_json: Path,
) -> None:
    """Write deterministic machine-auditable CSV and JSON outputs."""

    rows = _csv_rows(audit)
    if not rows:
        raise ValueError("audit must contain at least one dataset")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    output_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run_coverage_audit(
    input_path: Path,
    *,
    split_audit_path: Path,
    output_csv: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Run the fixed Step-003 coverage audit and write both artifacts."""

    records = read_annotation_manifest(input_path)
    manifest_hash = file_sha256(input_path)
    audit = build_coverage_audit(
        records,
        input_manifest_sha256=manifest_hash,
    )
    split_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {split: 0 for split in SPLIT_ORDER}
    )
    for record in records:
        split_counts[record.dataset][record.split] += 1
    split_link = verify_split_audit(
        split_audit_path,
        manifest_sha256=manifest_hash,
        manifest_record_count=len(records),
        manifest_split_counts=split_counts,
        required_datasets=REQUIRED_DATASETS,
        manifest_path=input_path,
    )
    manifest_stages = {record.selection_stage for record in records}
    if manifest_stages != {split_link.selection_stage}:
        raise ValueError("manifest row selection_stage does not match split audit")
    audit["run_mode"] = "FORMAL"
    audit["split_audit"] = split_audit_link_payload(split_link)
    audit["authorization_scope"] = split_link.authorization_scope
    write_coverage_outputs(
        audit,
        output_csv=output_csv,
        output_json=output_json,
    )
    return audit


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--split-audit", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    audit = run_coverage_audit(
        args.input,
        split_audit_path=args.split_audit,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    if audit["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
