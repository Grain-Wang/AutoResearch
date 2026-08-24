from __future__ import annotations

import hashlib

import pytest
from paper1.experiments.covol.audit_annotation_coverage import (
    RELATIVE_GAP_DEFINITION,
    CoverageThresholds,
    build_coverage_audit,
    relative_median_depth_gap,
    summarize_dataset_coverage,
    validate_image_record,
)
from paper1.experiments.covol.build_nyuv2_source_manifest import (
    NYUV2_EVAL_PROTOCOL_SHA256,
)
from paper1.experiments.covol.build_vkitti2_source_manifest import (
    VKITTI2_EVAL_PROTOCOL_SHA256,
)

_ANNOTATION_HASH = "a" * 64
_DEPTH_HASH = "d" * 64


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record(
    *,
    dataset: str,
    image_id: str,
    entities: list[dict[str, object]],
    annotation_available: bool = True,
    depth_available: bool = True,
):
    raw = {
        "dataset": dataset,
        "image_id": image_id,
        "scene_id": f"scene-{image_id}",
        "sequence_id": f"sequence-{image_id}",
        "cluster_id": _sha(f"cluster-{image_id}"),
        "rgb_sha256": "f" * 64,
        "official_split": "train",
        "split": "internal_test",
        "selection_hash": "e" * 64,
        "manifest_scope": "training_pilot_step003",
        "official_test_audit_status": "DEFERRED_FROZEN",
        "selection_stage": "PILOT_V1",
        "annotation_available": annotation_available,
        "annotation_source": "instances.json" if annotation_available else None,
        "annotation_sha256": _ANNOTATION_HASH if annotation_available else None,
        "depth_available": depth_available,
        "depth_source": "depth.bin" if depth_available else None,
        "depth_sha256": _DEPTH_HASH if depth_available else None,
        "entities": entities,
    }
    if entities:
        raw["eval_protocol_sha256"] = (
            NYUV2_EVAL_PROTOCOL_SHA256
            if dataset == "NYUv2"
            else (
                VKITTI2_EVAL_PROTOCOL_SHA256
                if dataset == "Virtual KITTI 2"
                else _sha(f"eval-protocol-{dataset}")
            )
        )
    return validate_image_record(raw, line_number=1)


def _entity(entity_id: str, median_depth: float) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "class_name": entity_id,
        "reliable_mask": True,
        "eval_mask_area_pixels": 64,
        "eval_valid_depth_count": 48,
        "eval_median_depth": median_depth,
    }


def test_coverage_uses_mask_depth_and_conservative_pair_gap() -> None:
    records = [
        _record(
            dataset="NYUv2",
            image_id="one",
            entities=[_entity("a", 1.0), _entity("b", 2.0)],
        ),
        _record(
            dataset="NYUv2",
            image_id="two",
            entities=[_entity("a", 1.0), _entity("b", 1.1)],
        ),
    ]
    result = summarize_dataset_coverage(
        "NYUv2",
        records,
        thresholds=CoverageThresholds(
            minimum_eligible_images=2,
            minimum_eligible_pairs=1,
            minimum_images_with_eligible_pair=1,
            minimum_independent_clusters_with_eligible_pair=1,
        ),
    )

    assert relative_median_depth_gap(1.0, 1.1) == pytest.approx(1.0 / 11.0)
    assert result["relative_gap_definition"] == RELATIVE_GAP_DEFINITION
    assert result["eligible_image_count"] == 2
    assert result["pair_candidate_count"] == 2
    assert result["eligible_pair_count"] == 1
    assert result["gate_pass"] is True


def test_missing_kitti_masks_are_zero_coverage_and_stop_local_gate() -> None:
    record = _record(
        dataset="KITTI",
        image_id="frame-0",
        entities=[],
        annotation_available=False,
        depth_available=True,
    )
    result = summarize_dataset_coverage("KITTI", [record])

    assert result["image_count"] == 1
    assert result["eligible_image_count"] == 0
    assert result["eligible_pair_count"] == 0
    assert result["gate_pass"] is False
    assert result["decision"] == "STOP_INSUFFICIENT_LOCAL_ANNOTATION_COVERAGE"


def test_passing_virtual_kitti_does_not_resolve_kitti_inferential_gate() -> None:
    kitti = _record(
        dataset="KITTI",
        image_id="kitti-frame",
        entities=[],
        annotation_available=False,
        depth_available=False,
    )
    virtual_kitti = _record(
        dataset="Virtual KITTI 2",
        image_id="virtual-frame",
        entities=[_entity("car", 10.0), _entity("road-sign", 20.0)],
    )
    nyuv2 = _record(
        dataset="NYUv2",
        image_id="nyuv2-frame",
        entities=[_entity("chair", 1.0), _entity("table", 2.0)],
    )

    audit = build_coverage_audit(
        [kitti, nyuv2, virtual_kitti],
        input_manifest_sha256="0" * 64,
        thresholds=CoverageThresholds(
            minimum_eligible_images=1,
            minimum_eligible_pairs=1,
            minimum_images_with_eligible_pair=1,
            minimum_independent_clusters_with_eligible_pair=1,
        ),
    )

    by_dataset = {row["dataset"]: row for row in audit["datasets"]}
    assert audit["status"] == "FAIL"
    assert audit["claim_dataset_decision"] == {
        "decision": "STOP_TWO_DATASET_CLAIM",
        "local_claim_datasets": ["NYUv2"],
        "kitti_role": "image_level_sensitivity_only",
        "virtual_kitti2_role": "synthetic_structured_auxiliary_only",
    }
    assert by_dataset["KITTI"]["gate_pass"] is False
    assert by_dataset["KITTI"]["fallback_resolved"] is False
    assert by_dataset["KITTI"]["inferential_requirement_pass"] is False
    assert by_dataset["Virtual KITTI 2"]["evidence_role"] == (
        "synthetic_structured_auxiliary_only"
    )


def test_precomputed_entities_require_annotation_and_depth_provenance() -> None:
    with pytest.raises(ValueError, match="entities require annotation provenance"):
        _record(
            dataset="KITTI",
            image_id="frame-0",
            entities=[_entity("car", 10.0)],
            annotation_available=False,
            depth_available=True,
        )

    with pytest.raises(ValueError, match="valid depth summaries require depth"):
        _record(
            dataset="NYUv2",
            image_id="frame-1",
            entities=[_entity("chair", 2.0)],
            annotation_available=True,
            depth_available=False,
        )


def test_nested_adapter_provenance_is_accepted() -> None:
    record = validate_image_record(
        {
            "dataset": "NYUv2",
            "image_id": "frame-1",
            "scene_id": "scene-1",
            "sequence_id": "sequence-1",
            "cluster_id": _sha("cluster-1"),
            "rgb_sha256": "f" * 64,
            "official_split": "train",
            "split": "internal_test",
            "selection_hash": "e" * 64,
            "manifest_scope": "training_pilot_step003",
            "official_test_audit_status": "DEFERRED_FROZEN",
            "selection_stage": "PILOT_V1",
            "eval_protocol_sha256": NYUV2_EVAL_PROTOCOL_SHA256,
            "annotation_source": {
                "path": "nyu_depth_v2_labeled.mat",
                "sha256": _ANNOTATION_HASH,
                "labels_key": "labels",
            },
            "depth_source": {
                "path": "nyu_depth_v2_labeled.mat",
                "sha256": _DEPTH_HASH,
                "dataset_key": "rawDepths",
            },
            "entities": [_entity("chair", 2.0)],
        },
        line_number=1,
    )

    assert record.annotation_available is True
    assert record.annotation_source == "nyu_depth_v2_labeled.mat"
    assert record.annotation_sha256 == _ANNOTATION_HASH
    assert record.depth_available is True
    assert record.depth_sha256 == _DEPTH_HASH


def test_target_requires_both_mask_area_and_valid_depth_thresholds() -> None:
    record = _record(
        dataset="NYUv2",
        image_id="one",
        entities=[
            {
                **_entity("small-mask", 1.0),
                "eval_mask_area_pixels": 31,
                "eval_valid_depth_count": 31,
            },
            {
                **_entity("sparse-depth", 2.0),
                "eval_mask_area_pixels": 64,
                "eval_valid_depth_count": 31,
            },
            _entity("eligible", 3.0),
        ],
    )
    result = summarize_dataset_coverage(
        "NYUv2",
        [record],
        thresholds=CoverageThresholds(
            minimum_eligible_images=1,
            minimum_eligible_pairs=1,
            minimum_images_with_eligible_pair=1,
            minimum_independent_clusters_with_eligible_pair=1,
        ),
    )

    assert result["eligible_target_count"] == 1
    assert result["eligible_pair_count"] == 0
    assert result["image_gate_pass"] is True
    assert result["pair_gate_pass"] is False


def test_many_pairs_in_one_image_cannot_satisfy_independent_unit_gate() -> None:
    record = _record(
        dataset="NYUv2",
        image_id="one",
        entities=[_entity(f"entity-{index}", float(index + 1)) for index in range(25)],
    )

    result = summarize_dataset_coverage(
        "NYUv2",
        [record],
        thresholds=CoverageThresholds(
            minimum_relative_median_depth_gap=0.0,
            minimum_eligible_images=1,
            minimum_eligible_pairs=300,
            minimum_images_with_eligible_pair=2,
            minimum_independent_clusters_with_eligible_pair=2,
        ),
    )

    assert result["eligible_pair_count"] == 300
    assert result["images_with_eligible_pair"] == 1
    assert result["scenes_with_eligible_pair"] == 1
    assert result["pair_gate_pass"] is False


def test_entity_requires_languageable_class_name() -> None:
    entity = _entity("opaque-instance", 2.0)
    entity.pop("class_name")

    with pytest.raises(ValueError, match="class_name is required"):
        _record(
            dataset="NYUv2",
            image_id="one",
            entities=[entity],
        )
