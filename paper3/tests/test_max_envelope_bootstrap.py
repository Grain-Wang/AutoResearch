from __future__ import annotations

import numpy as np
from paper3.experiments.bar_depth.analyze_budget_baselines import confidence_interval
from paper3.experiments.bar_depth.analyze_budget_baselines_v2 import (
    replicate_wise_max_envelope,
)
from paper3.experiments.bar_depth.analyze_direct_resolution_accuracy_v2 import (
    direct_accuracy_envelope,
)
from paper3.experiments.bar_depth.analyze_matched_latency_v2 import (
    candidate_range_is_closed,
    select_best_feasible_candidate,
    session_relative_difference,
)


def test_crossing_baselines_require_replicate_wise_envelope() -> None:
    oracle = np.ones(200, dtype=np.float64)
    first = np.full(200, 0.8, dtype=np.float64)
    second = np.full(200, 0.79, dtype=np.float64)
    first[:4] = 1.1
    second[4:8] = 1.1

    fixed_winner_margin = oracle - first
    assert confidence_interval(fixed_winner_margin.tolist(), 0.95)["lower"] > 0

    margin, envelope, winners = replicate_wise_max_envelope(
        oracle, {"first": first, "second": second}
    )
    assert confidence_interval(margin.tolist(), 0.95)["lower"] < 0
    assert np.all(envelope[:8] == 1.1)
    assert winners[:4] == ["first"] * 4
    assert winners[4:8] == ["second"] * 4


def test_envelope_rejects_mismatched_replicate_shapes() -> None:
    oracle = np.ones(2, dtype=np.float64)
    try:
        replicate_wise_max_envelope(oracle, {"bad": np.ones(3)})
    except ValueError as error:
        assert "share the oracle shape" in str(error)
    else:
        raise AssertionError("Mismatched bootstrap arrays were accepted")


def test_direct_accuracy_envelope_reselects_size_per_replicate() -> None:
    oracle = np.asarray([0.10, 0.10, 0.10], dtype=np.float64)
    margins, envelope, winners = direct_accuracy_envelope(
        oracle,
        {
            518: np.asarray([0.00, 0.03, 0.01], dtype=np.float64),
            574: np.asarray([0.02, 0.01, 0.01], dtype=np.float64),
        },
    )

    assert np.allclose(envelope, [0.02, 0.03, 0.01])
    assert np.allclose(margins, [0.08, 0.07, 0.09])
    assert winners == [574, 518, 518]


def test_matched_latency_reselects_only_within_replicate_feasible_set() -> None:
    best, feasible = select_best_feasible_candidate(
        direct_accuracy={518: 0.01, 574: 0.03, 630: 0.05},
        direct_latency={518: (1.0, 2.0), 574: (2.0, 3.0), 630: (4.0, 8.0)},
        regional_latency=(3.0, 5.0),
    )
    assert feasible == [518, 574]
    assert best == 574


def test_direct_candidate_range_closes_only_at_frozen_boundary() -> None:
    sizes = [518, 574, 630, 686]
    regional = (5.0, 10.0)
    latency = {
        518: (1.0, 2.0),
        574: (4.0, 8.0),
        630: (6.0, 11.0),
        686: (7.0, 12.0),
    }
    assert candidate_range_is_closed(
        input_sizes=sizes,
        direct_latency=latency,
        regional_latency=regional,
        oom_sizes=set(),
        required_consecutive=2,
    )
    assert not candidate_range_is_closed(
        input_sizes=sizes[:3],
        direct_latency={size: latency[size] for size in sizes[:3]},
        regional_latency=regional,
        oom_sizes=set(),
        required_consecutive=2,
    )


def test_direct_candidate_range_accepts_only_contiguous_oom_suffix() -> None:
    sizes = [518, 574, 630, 686]
    assert candidate_range_is_closed(
        input_sizes=sizes,
        direct_latency={518: (1.0, 2.0), 574: (2.0, 3.0)},
        regional_latency=(5.0, 10.0),
        oom_sizes={630, 686},
        required_consecutive=2,
    )
    assert not candidate_range_is_closed(
        input_sizes=sizes,
        direct_latency={518: (1.0, 2.0), 630: (2.0, 3.0)},
        regional_latency=(5.0, 10.0),
        oom_sizes={574, 686},
        required_consecutive=2,
    )


def test_session_relative_difference_is_symmetric() -> None:
    assert np.isclose(session_relative_difference(95.0, 105.0), 0.1)
    assert np.isclose(
        session_relative_difference(95.0, 105.0),
        session_relative_difference(105.0, 95.0),
    )
