from __future__ import annotations

import pytest
from paper1.experiments.covol.main_pr_objective import (
    image_worst_variant_regret,
    projected_dual_ascent,
    rockafellar_uryasev_cvar,
    standard_lagrangian,
)


def test_objective_matches_reported_worst_complete_variant() -> None:
    risk = image_worst_variant_regret(
        [0.0, 0.0],
        [
            [2.0, 0.0],
            [0.0, 2.0],
        ],
        region_weights=[0.5, 0.5],
    )

    assert risk == pytest.approx(1.0, abs=1e-10)
    assert risk != pytest.approx(2.0)


def test_standard_lagrangian_and_signed_dual_update_are_consistent() -> None:
    multiplier = 0.5
    violating_sequence = []
    for _ in range(20):
        loss = standard_lagrangian(
            1.0,
            2.0,
            0.25,
            beta=0.5,
            multiplier=multiplier,
        )
        multiplier = projected_dual_ascent(
            multiplier,
            0.25,
            learning_rate=0.01,
            maximum=100.0,
        )
        violating_sequence.append((loss, multiplier))

    assert violating_sequence[0] == pytest.approx((2.125, 0.5025))
    assert multiplier == pytest.approx(0.55)

    feasible = projected_dual_ascent(
        0.01,
        -2.0,
        learning_rate=0.01,
        maximum=100.0,
    )
    assert feasible == 0.0


def test_rockafellar_uryasev_estimator_uses_frozen_tail_fraction() -> None:
    value = rockafellar_uryasev_cvar(
        [0.0, 1.0, 2.0, 3.0],
        eta=2.0,
        tail_fraction=0.25,
    )

    assert value == pytest.approx(3.0)
