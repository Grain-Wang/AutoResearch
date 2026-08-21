from __future__ import annotations

import pytest
from paper1.experiments.covol.features import (
    feature_schema_payload,
    validate_feature_schema,
)

VALID_SHA256 = "a" * 64


def _column(
    name: str,
    *,
    source_fields: list[str],
    source_kind: str = "candidate",
) -> dict[str, object]:
    return {
        "name": name,
        "source_fields": source_fields,
        "source_kind": source_kind,
        "source_function": "paper1.experiments.covol.features.example",
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

    with pytest.raises(ValueError, match="source_file_sha256"):
        validate_feature_schema([column])
