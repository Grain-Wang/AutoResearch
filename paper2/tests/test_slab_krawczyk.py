from experiments.blockstamp_operator import OperatorStatus
from experiments.checkers import (
    CheckerVerdict,
    SlabMethod,
    be_history_jacobian,
    build_slab_problem,
    check_slab,
)
from experiments.interval_backend import Interval
from experiments.mna import rc_closed_form_next, rc_source_circuit, rc_state


def _rc_slab(length: int = 4) -> tuple:
    circuit = rc_source_circuit()
    previous = rc_state(0.0)
    centers = []
    tubes = []
    radii = (1e-9, 1e-12, 1e-12)
    for _ in range(length):
        current = rc_state(rc_closed_form_next(previous[0], 1e-5))
        centers.append(current)
        tubes.append(
            tuple(
                Interval(value - radius, value + radius)
                for value, radius in zip(current, radii, strict=True)
            )
        )
        previous = current
    return circuit, tuple(centers), tuple(tubes)


def test_history_jacobian_matches_rc_capacitor_stamp() -> None:
    matrix = be_history_jacobian(rc_source_circuit())
    assert matrix == (
        (-1e-6, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )


def test_dense_and_temporal_slab_paths_certify_same_rc_trace() -> None:
    circuit, centers, tubes = _rc_slab()
    incoming = tuple(Interval.point(value) for value in rc_state(0.0))
    materialized = build_slab_problem(
        circuit,
        centers,
        tubes,
        incoming,
        1e-5,
        streamed_remainder=False,
    )
    streamed = build_slab_problem(
        circuit,
        centers,
        tubes,
        incoming,
        1e-5,
        streamed_remainder=True,
    )
    assert materialized.status is OperatorStatus.OK
    assert streamed.status is OperatorStatus.OK
    assert materialized.problem is not None
    assert streamed.problem is not None
    dense = check_slab(materialized.problem, SlabMethod.DENSE_SLAB_GENERIC)
    temporal = check_slab(materialized.problem, SlabMethod.TEMPORAL_ONLY)
    blockstamp = check_slab(streamed.problem, SlabMethod.TEMPORAL_DEVICE_BLOCKSTAMP)
    assert dense.verdict is CheckerVerdict.ACCEPT
    assert temporal.verdict is CheckerVerdict.ACCEPT
    assert blockstamp.verdict is CheckerVerdict.ACCEPT
    assert dense.verified_pivots == temporal.verified_pivots == 12


def test_root_excluding_slab_tube_does_not_accept() -> None:
    circuit, centers, tubes = _rc_slab(length=2)
    wrong_centers = tuple((center[0] + 0.1, center[1], center[2]) for center in centers)
    wrong_tubes = tuple(
        tuple(
            Interval(
                value - (1e-9 if index == 0 else 1e-12),
                value + (1e-9 if index == 0 else 1e-12),
            )
            for index, value in enumerate(center)
        )
        for center in wrong_centers
    )
    built = build_slab_problem(
        circuit,
        wrong_centers,
        wrong_tubes,
        tuple(Interval.point(value) for value in rc_state(0.0)),
        1e-5,
        streamed_remainder=False,
    )
    assert built.status is OperatorStatus.OK
    assert built.problem is not None
    result = check_slab(built.problem, SlabMethod.TEMPORAL_ONLY)
    assert result.verdict is not CheckerVerdict.ACCEPT
