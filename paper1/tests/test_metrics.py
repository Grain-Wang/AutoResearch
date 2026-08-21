from __future__ import annotations

import pytest
from paper1.experiments.covol.metrics import (
    NoCleanGainError,
    advantage_tie_band,
    clean_gain_retention,
    corruption_metrics,
    coverage,
    fixed_reference_cvar,
    pareto_hypervolume,
)


def test_corruption_metrics_aggregate_variants_within_image() -> None:
    metrics = corruption_metrics(
        [1.0, 2.0],
        [
            [1.1, 0.9, 1.3],
            [2.2, 2.4, 1.8],
        ],
        tail_fraction=0.5,
    )

    assert metrics.mean_regret == pytest.approx(7.0 / 60.0)
    assert metrics.worst_of_n == pytest.approx(0.35)
    assert metrics.cvar == pytest.approx(0.4)


def test_coverage_uses_only_eligible_regions() -> None:
    result = coverage(
        [[True, True, False], [True, False, True]],
        [[True, False, True], [True, True, True]],
    )

    assert result.micro == pytest.approx(3.0 / 5.0)
    assert result.macro == pytest.approx((0.5 + 2.0 / 3.0) / 2.0)


def test_clean_gain_retention_and_stop_rule() -> None:
    retention = clean_gain_retention(
        [1.0, 2.0],
        [0.8, 1.8],
        [0.9, 1.9],
        clean_gain_ci_lower=0.01,
    )
    assert retention == pytest.approx(0.5)

    with pytest.raises(NoCleanGainError, match="STOP_NO_CLEAN_GAIN"):
        clean_gain_retention(
            [1.0, 2.0],
            [0.8, 1.8],
            [0.9, 1.9],
            clean_gain_ci_lower=0.0,
        )


def test_pareto_hypervolume_has_fixed_orientation() -> None:
    result = pareto_hypervolume(
        [(0.5, 0.4), (0.8, 0.5), (0.7, 0.3)],
        reference_retention=0.0,
        reference_cvar=1.0,
    )
    assert result == pytest.approx(0.54)


def test_advantage_tie_band_uses_nearest_rank_95th_percentile() -> None:
    assert advantage_tie_band([0.001, -0.002, 0.003, 0.004]) == 0.004


def test_hypervolume_reference_uses_only_always_d1_dev_risk() -> None:
    reference = fixed_reference_cvar(0.4)

    assert reference == pytest.approx(0.42)
    base = pareto_hypervolume(
        [(0.5, 0.3), (0.8, 0.35)],
        reference_retention=0.0,
        reference_cvar=reference,
    )
    with_dominated_candidate = pareto_hypervolume(
        [(0.5, 0.3), (0.8, 0.35), (0.1, 0.41)],
        reference_retention=0.0,
        reference_cvar=reference,
    )

    assert with_dominated_candidate == pytest.approx(base, abs=1e-12)


def test_hypervolume_handles_duplicate_retention_and_dominated_points() -> None:
    base = pareto_hypervolume(
        [(0.5, 0.4), (0.8, 0.5), (0.7, 0.3)],
        reference_retention=0.0,
        reference_cvar=1.0,
    )
    augmented = pareto_hypervolume(
        [
            (0.5, 0.4),
            (0.8, 0.5),
            (0.7, 0.3),
            (0.7, 0.6),
            (0.1, 0.9),
        ],
        reference_retention=0.0,
        reference_cvar=1.0,
    )

    assert augmented == pytest.approx(base)
