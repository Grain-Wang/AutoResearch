from __future__ import annotations

from copy import deepcopy

from paper1.experiments.covol.audit_diagnostic_interventions import (
    audit_diagnostic_predicates,
    independently_verify_predicate,
)
from paper1.experiments.covol.build_interventions import (
    build_diagnostic_interventions,
)
from paper1.tests.test_build_interventions import _source_rows


def test_independent_parser_audits_25_rows_per_family() -> None:
    rows, _, _ = build_diagnostic_interventions(_source_rows())

    result = audit_diagnostic_predicates(rows)

    assert result["audited_row_count"] == 100
    assert result["predicate_precision"] == 1.0
    assert result["naturalness_audit_status"].startswith("PENDING")
    assert result["status"] == "PASS_PREDICATE_PRECISION_NATURALNESS_PENDING"


def test_independent_parser_does_not_trust_generator_pass_flag() -> None:
    rows, _, _ = build_diagnostic_interventions(_source_rows())
    row = deepcopy(rows[0])
    row["machine_check"]["passed"] = True
    row["intervention"] = "No relevant local relation appears."

    assert independently_verify_predicate(row) is False
