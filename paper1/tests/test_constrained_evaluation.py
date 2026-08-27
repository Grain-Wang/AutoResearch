from __future__ import annotations

import json

import pytest
from paper1.experiments.covol.bootstrap import (
    PolicyImageOutcome,
    cluster_bootstrap_constrained_risk_difference,
)
from paper1.experiments.covol.constrained_evaluation import (
    evaluate_internal_test_operating_point,
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
        training_seed=17,
        d0_clean_loss=1.0,
        d1_clean_loss=0.8,
        routed_clean_losses=clean_losses,
        routed_variant_losses=tuple((loss, loss, loss) for loss in variant_losses),
    )


def _write_point_artifact(tmp_path, point) -> tuple[object, list[object]]:
    lineage_paths = []
    for index in range(7):
        path = tmp_path / f"lineage-{index}.json"
        path.write_text(f'{{"index": {index}}}\n', encoding="utf-8")
        lineage_paths.append(path)
    artifact = write_operating_point_artifact(
        point,
        tmp_path / "threshold.json",
        repository_root=tmp_path,
        dev_manifest_path=lineage_paths[0],
        method_config_path=lineage_paths[1],
        raw_outcome_path=lineage_paths[2],
        coverage_grid_path=lineage_paths[3],
        expert_cache_path=lineage_paths[4],
        metric_spec_path=lineage_paths[5],
        minimum_clean_gain_path=lineage_paths[6],
        code_commit="2" * 40,
    )
    return artifact, lineage_paths


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
        bootstrap_replicates=100,
    )

    assert point.threshold_id == "q00"
    assert point.threshold_index == 0
    assert point.retention == pytest.approx(0.80)
    assert point.retention_lcb == pytest.approx(0.80)
    artifact, _ = _write_point_artifact(tmp_path, point)
    assert artifact["schema_version"] == "covol-dev-operating-point-v2"
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
        bootstrap_replicates=100,
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


def test_point_retention_above_threshold_is_rejected_when_lcb_is_below() -> None:
    dev = [
        _outcome(
            f"image-{index}",
            f"cluster-{index}",
            clean_losses=(clean_loss,),
            variant_losses=(1.0,),
        )
        for index, clean_loss in enumerate((0.76, 0.76, 0.916, 0.916))
    ]

    with pytest.raises(ValueError, match="STOP_NO_FEASIBLE_DEV_THRESHOLD"):
        select_constrained_operating_point(
            "main_pr",
            dev,
            threshold_ids=("q00",),
            minimum_retention=0.80,
            minimum_clean_gain=0.01,
            bootstrap_replicates=1_000,
            bootstrap_seed=17,
        )


def test_internal_test_retention_violation_is_a_named_stop(tmp_path) -> None:
    dev = [
        _outcome(
            image_id,
            cluster_id,
            clean_losses=(0.82,),
            variant_losses=(1.0,),
        )
        for image_id, cluster_id in (("a", "cluster-a"), ("b", "cluster-b"))
    ]
    point = select_constrained_operating_point(
        "main_pr",
        dev,
        threshold_ids=("q00",),
        minimum_retention=0.80,
        minimum_clean_gain=0.01,
        bootstrap_replicates=100,
    )
    internal = [
        _outcome(
            image_id,
            cluster_id,
            clean_losses=(0.85,),
            variant_losses=(1.1,),
        )
        for image_id, cluster_id in (("c", "cluster-c"), ("d", "cluster-d"))
    ]

    _write_point_artifact(tmp_path, point)
    result = evaluate_internal_test_operating_point(
        tmp_path / "threshold.json",
        internal,
        repository_root=tmp_path,
        minimum_clean_gain=0.01,
        bootstrap_replicates=100,
    )

    assert result.status == "STOP_TEST_RETENTION_VIOLATION"
    assert result.retention == pytest.approx(0.75)
    assert result.cvar_metric == "CVaR@Dev-LCB-Ret>=0.80"


def test_internal_evaluator_rehashes_lineage_before_using_threshold(tmp_path) -> None:
    dev = [
        _outcome(
            image_id,
            cluster_id,
            clean_losses=(0.82,),
            variant_losses=(1.0,),
        )
        for image_id, cluster_id in (("a", "cluster-a"), ("b", "cluster-b"))
    ]
    point = select_constrained_operating_point(
        "main_pr",
        dev,
        threshold_ids=("q00",),
        minimum_retention=0.80,
        minimum_clean_gain=0.01,
        bootstrap_replicates=100,
    )
    _, lineage_paths = _write_point_artifact(tmp_path, point)
    lineage_paths[2].write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="raw_outcome lineage mismatch"):
        evaluate_internal_test_operating_point(
            tmp_path / "threshold.json",
            dev,
            repository_root=tmp_path,
            minimum_clean_gain=0.01,
            bootstrap_replicates=100,
        )
