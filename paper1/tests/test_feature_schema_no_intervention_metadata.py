from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from paper1.experiments.covol.features import (
    feature_schema_payload,
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
