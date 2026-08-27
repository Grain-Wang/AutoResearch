from __future__ import annotations

import pytest
from paper1.experiments.covol.bootstrap import (
    PolicyImageOutcome,
    cluster_bootstrap_hypervolume_difference,
    cluster_bootstrap_indices,
    cluster_bootstrap_retention,
    summarize_fixed_seed_estimates,
)


def _outcome(
    image_id: str,
    cluster_id: str,
    *,
    clean_loss: float,
    corrupt_loss: float,
    d1_clean_loss: float = 0.8,
) -> PolicyImageOutcome:
    return PolicyImageOutcome(
        image_id=image_id,
        cluster_id=cluster_id,
        training_seed=17,
        d0_clean_loss=1.0,
        d1_clean_loss=d1_clean_loss,
        routed_clean_losses=(clean_loss,),
        routed_variant_losses=((corrupt_loss, corrupt_loss, corrupt_loss),),
    )


def test_cluster_resampling_keeps_all_cluster_members_together() -> None:
    samples = cluster_bootstrap_indices(
        ["scene-a", "scene-a", "scene-b"],
        replicates=20,
        seed=17,
    )

    for indices in samples:
        assert indices.count(0) == indices.count(1)


def test_two_scene_hand_calculated_hypervolume_difference() -> None:
    left = [
        _outcome("a", "scene-a", clean_loss=0.8, corrupt_loss=1.0),
        _outcome("b", "scene-b", clean_loss=0.8, corrupt_loss=1.0),
    ]
    right = [
        _outcome("a", "scene-a", clean_loss=0.9, corrupt_loss=1.2),
        _outcome("b", "scene-b", clean_loss=0.9, corrupt_loss=1.2),
    ]

    result = cluster_bootstrap_hypervolume_difference(
        left,
        right,
        reference_cvar=1.0,
        replicates=100,
        seed=29,
        minimum_clean_gain=0.01,
    )

    assert result.status == "PASS"
    assert result.estimate == pytest.approx(0.6, abs=1e-8)
    assert result.ci_lower == pytest.approx(0.6, abs=1e-8)
    assert result.ci_upper == pytest.approx(0.6, abs=1e-8)
    assert result.cluster_count == 2
    assert result.valid_replicates == 100
    assert result.invalid_replicates == 0


def test_mixed_clean_gain_replicates_stop_without_crashing() -> None:
    left = [
        _outcome(
            "a",
            "scene-a",
            clean_loss=0.8,
            corrupt_loss=1.0,
            d1_clean_loss=0.6,
        ),
        _outcome(
            "b",
            "scene-b",
            clean_loss=0.8,
            corrupt_loss=1.0,
            d1_clean_loss=1.1,
        ),
    ]
    right = [
        _outcome(
            "a",
            "scene-a",
            clean_loss=0.9,
            corrupt_loss=1.2,
            d1_clean_loss=0.6,
        ),
        _outcome(
            "b",
            "scene-b",
            clean_loss=0.9,
            corrupt_loss=1.2,
            d1_clean_loss=1.1,
        ),
    ]

    result = cluster_bootstrap_hypervolume_difference(
        left,
        right,
        reference_cvar=1.5,
        replicates=200,
        seed=17,
        minimum_clean_gain=0.01,
    )

    assert result.status == "STOP_UNSTABLE_CLEAN_GAIN"
    assert result.estimate is not None
    assert result.ci_lower is None
    assert result.ci_upper is None
    assert result.invalid_replicates > 0
    assert result.invalid_fraction > 0.05


def test_retention_bootstrap_reports_one_sided_cluster_lower_bound() -> None:
    outcomes = [
        _outcome("a", "scene-a", clean_loss=0.8, corrupt_loss=1.0),
        _outcome("b", "scene-b", clean_loss=0.8, corrupt_loss=1.0),
    ]

    result = cluster_bootstrap_retention(
        outcomes,
        threshold_index=0,
        minimum_clean_gain=0.01,
        replicates=100,
        seed=17,
    )

    assert result.status == "PASS"
    assert result.estimate == pytest.approx(1.0)
    assert result.one_sided_lower == pytest.approx(1.0)
    assert result.training_seed == 17


def test_three_training_seeds_are_fixed_repeats_not_bootstrap_population() -> None:
    result = summarize_fixed_seed_estimates(
        {17: -0.3, 29: -0.1, 43: -0.2},
        favorable_direction="negative",
    )

    assert result.mean == pytest.approx(-0.2)
    assert result.sample_sd == pytest.approx(0.1)
    assert result.direction_pass is True

    reversed_seed = summarize_fixed_seed_estimates(
        {17: -0.3, 29: 0.01, 43: -0.2},
        favorable_direction="negative",
    )
    assert reversed_seed.direction_pass is False
