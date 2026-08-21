from __future__ import annotations

import pytest
from paper1.experiments.covol.bootstrap import (
    PolicyImageOutcome,
    cluster_bootstrap_hypervolume_difference,
    cluster_bootstrap_indices,
)


def _outcome(
    image_id: str,
    scene_id: str,
    *,
    clean_loss: float,
    corrupt_loss: float,
    d1_clean_loss: float = 0.8,
) -> PolicyImageOutcome:
    return PolicyImageOutcome(
        image_id=image_id,
        scene_id=scene_id,
        d0_clean_loss=1.0,
        d1_clean_loss=d1_clean_loss,
        routed_clean_losses=(clean_loss,),
        routed_variant_losses=((corrupt_loss, corrupt_loss, corrupt_loss),),
    )


def test_cluster_resampling_keeps_all_scene_members_together() -> None:
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
