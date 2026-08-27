from __future__ import annotations

from copy import deepcopy

from paper1.experiments.covol.audit_intervention_validity import (
    audit_caption_surface_form,
    audit_intervention_validity,
    audit_text_artifacts,
    audit_text_artifacts_per_family,
)
from paper1.experiments.covol.build_interventions import (
    build_diagnostic_interventions,
)
from paper1.tests.test_build_interventions import _source_rows


def test_realistic_templates_expose_per_family_artifacts() -> None:
    rows, _, _ = build_diagnostic_interventions(_source_rows())

    result = audit_intervention_validity(rows)

    assert result["status"] == (
        "LIMITED_BY_FAMILY_TEXT_ARTIFACTS_HUMAN_NATURALNESS_UNASSESSED"
    )
    assert result["predicate"]["predicate_precision"] == 1.0
    assert result["text_artifact"]["aggregate"]["macro_f1"] <= 0.60
    assert len(result["text_artifact"]["folds"]) == 3
    assert result["text_artifact_per_family"]["status"] == "FAMILY_ARTIFACT_DETECTED"
    assert result["text_artifact_per_family"]["families_exceeding_threshold"]
    assert result["surface_form"]["pass_rate"] == 1.0


def test_text_artifact_control_stops_obvious_family_tokens() -> None:
    rows, _, _ = build_diagnostic_interventions(_source_rows())
    leaked = deepcopy(rows)
    for row in leaked:
        row["intervention"] = (
            f"The image shows marker{row['error_type'].replace('_', '')} object."
        )

    result = audit_text_artifacts(leaked)

    assert result["aggregate"]["macro_f1"] == 1.0
    assert result["status"] == "STOP_TEXT_TEMPLATE_ARTIFACT"

    per_family = audit_text_artifacts_per_family(leaked)
    assert per_family["status"] == "FAMILY_ARTIFACT_DETECTED"
    assert set(per_family["families_exceeding_threshold"]) == {
        "semantic_preserving",
        "target_deletion",
        "local_entity_conflict",
        "depth_relation_conflict",
    }


def test_surface_form_does_not_claim_human_naturalness() -> None:
    rows, _, _ = build_diagnostic_interventions(_source_rows())
    result = audit_caption_surface_form(rows)
    assert result["human_naturalness_status"] == "NOT_ASSESSED"

    malformed = deepcopy(rows)
    for row in malformed[:13]:
        row["intervention"] = "unresolved {near}"
    stopped = audit_caption_surface_form(malformed)
    assert stopped["status"] == "STOP_AUTOMATED_SURFACE_FORM"
