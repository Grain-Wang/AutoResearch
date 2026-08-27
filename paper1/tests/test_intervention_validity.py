from __future__ import annotations

from copy import deepcopy

from paper1.experiments.covol.audit_intervention_validity import (
    audit_caption_surface_form,
    audit_intervention_validity,
    audit_text_artifacts,
)
from paper1.experiments.covol.build_interventions import (
    build_diagnostic_interventions,
)
from paper1.tests.test_build_interventions import _source_rows


def test_realistic_templates_pass_pre_model_validity_controls() -> None:
    rows, _, _ = build_diagnostic_interventions(_source_rows())

    result = audit_intervention_validity(rows)

    assert result["status"] == ("PASS_AUTOMATED_VALIDITY_HUMAN_NATURALNESS_UNASSESSED")
    assert result["predicate"]["predicate_precision"] == 1.0
    assert result["text_artifact"]["aggregate"]["macro_f1"] <= 0.60
    assert len(result["text_artifact"]["folds"]) == 3
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


def test_surface_form_does_not_claim_human_naturalness() -> None:
    rows, _, _ = build_diagnostic_interventions(_source_rows())
    result = audit_caption_surface_form(rows)
    assert result["human_naturalness_status"] == "NOT_ASSESSED"

    malformed = deepcopy(rows)
    for row in malformed[:13]:
        row["intervention"] = "unresolved {near}"
    stopped = audit_caption_surface_form(malformed)
    assert stopped["status"] == "STOP_AUTOMATED_SURFACE_FORM"
