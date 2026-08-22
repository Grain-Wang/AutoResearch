from __future__ import annotations

import json

import pytest
from paper1.experiments.covol.bootstrap import (
    PolicyImageOutcome,
    cluster_bootstrap_constrained_risk_difference,
)
from paper1.experiments.covol.constrained_evaluation import (
    select_constrained_operating_point,
    write_operating_point_artifact,
)


def _outcome(
    image_id: str,
    cluster_id: str,
    *,
    clean_losses: tuple[float, ...],
    variant_losses: tuple[float, ...],
) -> PolicyImageOutcome:
    return PolicyImageOutcome(
        image_id=image_id,
        cluster_id=cluster_id,
        d0_clean_loss=1.0,
        d1_clean_loss=0.8,
        routed_clean_losses=clean_losses,
        routed_variant_losses=tuple((loss, loss, loss) for loss in variant_losses),
    )


def test_selects_minimum_dev_cvar_only_among_feasible_thresholds(tmp_path) -> None:
    dev = [
        _outcome(
            "a",
            "cluster-a",
            clean_losses=(0.84, 0.82, 0.90),
            variant_losses=(1.10, 1.20, 0.90),
        ),
        _outcome(
            "b",
            "cluster-b",
            clean_losses=(0.84, 0.82, 0.90),
            variant_losses=(1.10, 1.20, 0.90),
        ),
    ]

    point = select_constrained_operating_point(
        "main_pr",
        dev,
        threshold_ids=("q00", "q01", "q02"),
        minimum_retention=0.80,
        minimum_clean_gain=0.01,
    )

    assert point.threshold_id == "q00"
    assert point.threshold_index == 0
    assert point.retention == pytest.approx(0.80)
    artifact = write_operating_point_artifact(
        point,
        tmp_path / "threshold.json",
        dev_manifest_sha256="a" * 64,
        method_config_sha256="b" * 64,
    )
    assert artifact["selection_scope"] == "DEV_ONLY_INTERNAL_TEST_UNREAD"
    assert (
        json.loads((tmp_path / "threshold.json").read_text())["artifact_sha256"]
        == artifact["artifact_sha256"]
    )


def test_internal_test_changes_cannot_reselect_dev_threshold() -> None:
    dev = [
        _outcome(
            "dev-a",
            "cluster-a",
            clean_losses=(0.84, 0.82),
            variant_losses=(1.10, 1.20),
        ),
        _outcome(
            "dev-b",
            "cluster-b",
            clean_losses=(0.84, 0.82),
            variant_losses=(1.10, 1.20),
        ),
    ]
    point = select_constrained_operating_point(
        "main_pr",
        dev,
        threshold_ids=("q00", "q01"),
        minimum_clean_gain=0.01,
    )
    internal_left = [
        _outcome(
            "a",
            "cluster-a",
            clean_losses=(0.84, 0.82),
            variant_losses=(1.10, 5.00),
        ),
        _outcome(
            "b",
            "cluster-b",
            clean_losses=(0.84, 0.82),
            variant_losses=(1.10, 5.00),
        ),
    ]
    internal_right = [
        _outcome(
            "a",
            "cluster-a",
            clean_losses=(0.84, 0.82),
            variant_losses=(1.30, 0.10),
        ),
        _outcome(
            "b",
            "cluster-b",
            clean_losses=(0.84, 0.82),
            variant_losses=(1.30, 0.10),
        ),
    ]

    result = cluster_bootstrap_constrained_risk_difference(
        internal_left,
        internal_right,
        left_threshold_index=point.threshold_index,
        right_threshold_index=0,
        minimum_clean_gain=0.01,
        replicates=100,
        seed=17,
    )

    assert point.threshold_id == "q00"
    assert result.status == "PASS"
    assert result.cvar_estimate == pytest.approx(-0.20)
    assert result.cvar_ci_lower == pytest.approx(-0.20)
    assert result.cvar_ci_upper == pytest.approx(-0.20)
    assert result.worst_of_n_estimate == pytest.approx(-0.20)
    assert result.cluster_count == 2
