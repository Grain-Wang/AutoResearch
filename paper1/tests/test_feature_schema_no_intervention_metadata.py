from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from paper1.experiments.covol.features import (
    candidate_features,
    caption_region_features,
    feature_schema_payload,
    image_features,
    sanitize_feature_inputs,
    validate_feature_schema,
)

SOURCE_FILE_PATH = "paper1/experiments/covol/features.py"
VALID_SHA256 = hashlib.sha256(Path(SOURCE_FILE_PATH).read_bytes()).hexdigest()


def _column(
    name: str,
    *,
    source_fields: list[str],
    source_kind: str = "candidate",
) -> dict[str, object]:
    source_function = (
        "paper1.experiments.covol.features.caption_region_features"
        if source_kind == "caption_content"
        else "paper1.experiments.covol.features.candidate_features"
    )
    return {
        "name": name,
        "source_fields": source_fields,
        "source_kind": source_kind,
        "source_function": source_function,
        "source_file_path": SOURCE_FILE_PATH,
        "source_file_sha256": VALID_SHA256,
    }


def test_valid_schema_has_stable_hash_and_provenance() -> None:
    columns = [
        _column("d0_uncertainty", source_fields=["d0_depth"]),
        _column(
            "caption_region_alignment",
            source_fields=["raw_caption", "region_embedding"],
            source_kind="caption_content",
        ),
    ]

    first = feature_schema_payload(columns)
    second = feature_schema_payload(columns)

    assert first == second
    assert len(first["schema_sha256"]) == 64
    assert first["columns"][1]["source_kind"] == "caption_content"


@pytest.mark.parametrize(
    ("name", "source_fields"),
    [
        ("template_id_onehot_3", ["raw_caption"]),
        ("semantic_score", ["error_type"]),
        ("generator_revision_embedding", ["raw_caption"]),
        ("fold_hint", ["split"]),
        ("renamed_gt_embedding", ["ground_truth_depth"]),
        ("benefit_proxy", ["advantage"]),
        ("candidate_loss_pair", ["d0_loss", "d1_loss"]),
        ("oracle_hint", ["oracle_region"]),
    ],
)
def test_rejects_direct_or_derived_intervention_metadata(
    name: str,
    source_fields: list[str],
) -> None:
    with pytest.raises(ValueError, match="denied metadata"):
        validate_feature_schema([_column(name, source_fields=source_fields)])


def test_requires_traceable_source_sha() -> None:
    column = _column("candidate_difference", source_fields=["d0_depth", "d1_depth"])
    column["source_file_sha256"] = "not-a-sha"

    with pytest.raises(ValueError, match="does not match the local file"):
        validate_feature_schema([column])


def test_source_function_and_raw_field_allowlists_block_renamed_gt() -> None:
    column = _column("difficulty", source_fields=["empirical_error"])
    with pytest.raises(ValueError, match="extractor allowlist"):
        validate_feature_schema([column])

    column = _column("difficulty", source_fields=["d0_depth"])
    column["source_function"] = "paper1.example.unreviewed_extractor"
    with pytest.raises(ValueError, match="unregistered source_function"):
        validate_feature_schema([column])


def test_runtime_sanitizer_hides_unrequested_ground_truth_fields() -> None:
    sanitized = sanitize_feature_inputs(
        {
            "d0_depth": [1.0],
            "d1_depth": [2.0],
            "empirical_error": 99.0,
            "ground_truth_depth": [3.0],
        },
        source_function="paper1.experiments.covol.features.candidate_features",
        source_fields=["d0_depth", "d1_depth"],
    )

    assert sanitized == {"d0_depth": [1.0], "d1_depth": [2.0]}
    assert candidate_features(sanitized) == {
        "candidate_depth_disagreement_l1": 1.0,
        "d0_depth_l1_mean": 1.0,
        "d0_depth_mean": 1.0,
        "d1_depth_l1_mean": 2.0,
        "d1_depth_mean": 2.0,
    }


def test_callable_extractors_reject_raw_leakage_and_compute_content_features() -> None:
    with pytest.raises(ValueError, match="outside its allowlist"):
        candidate_features({"d0_depth": [1.0], "ground_truth": [1.0]})

    semantic = caption_region_features(
        {
            "raw_caption": "chair beside table",
            "caption_embedding": [1.0, 0.0],
            "region_embedding": [1.0, 0.0],
            "region_mask": [1, 0, 1, 0],
        }
    )
    visual = image_features(
        {
            "image_embedding": [3.0, 4.0],
            "image_statistics": {"brightness": 0.4},
        }
    )

    assert semantic["caption_region_cosine"] == pytest.approx(1.0)
    assert semantic["region_mask_coverage"] == pytest.approx(0.5)
    assert visual["image_embedding_norm"] == pytest.approx(5.0)
    assert visual["image_stat_brightness"] == pytest.approx(0.4)
