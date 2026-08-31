from experiments.checkers import CheckerVerdict, check_be_step
from experiments.interval_backend import Interval
from experiments.mna import (
    Circuit,
    MnaStatus,
    Resistor,
    diode_rc_decimal_root,
    interval_be_residual_jacobian,
    point_be_residual_jacobian,
    rc_closed_form_next,
    rc_source_circuit,
    rc_state,
)


def _tube(state: tuple[float, ...]) -> tuple[Interval, ...]:
    radii = (1e-9, 1e-12, 1e-12)
    return tuple(
        Interval(value - radius, value + radius)
        for value, radius in zip(state, radii, strict=True)
    )


def test_rc_analytic_trajectory_is_assembled_and_certified_for_100_steps() -> None:
    circuit = rc_source_circuit()
    step_size = 1e-5
    previous = rc_state(0.0)
    for _ in range(100):
        voltage = rc_closed_form_next(previous[0], step_size)
        current = rc_state(voltage)
        point = point_be_residual_jacobian(circuit, current, previous, step_size)
        interval = interval_be_residual_jacobian(
            circuit,
            tuple(Interval.point(value) for value in current),
            tuple(Interval.point(value) for value in previous),
            step_size,
        )
        assert point.status is MnaStatus.OK
        assert interval.status is MnaStatus.OK
        assert point.residual is not None
        assert interval.residual is not None
        assert interval.jacobian is not None
        assert point.jacobian is not None
        for point_value, interval_value in zip(
            point.residual, interval.residual, strict=True
        ):
            assert interval_value.contains(point_value)
        for point_row, interval_row in zip(
            point.jacobian, interval.jacobian, strict=True
        ):
            for point_value, interval_value in zip(
                point_row, interval_row, strict=True
            ):
                assert interval_value.contains(point_value)
        checked = check_be_step(
            circuit,
            current,
            _tube(current),
            tuple(Interval.point(value) for value in previous),
            step_size,
        )
        assert checked.verdict is CheckerVerdict.ACCEPT
        previous = current


def test_diode_rc_high_precision_roots_are_certified_for_100_steps() -> None:
    circuit = rc_source_circuit(diode=True)
    step_size = 1e-5
    previous = rc_state(0.0)
    for _ in range(100):
        current = rc_state(diode_rc_decimal_root(previous[0], step_size))
        checked = check_be_step(
            circuit,
            current,
            _tube(current),
            tuple(Interval.point(value) for value in previous),
            step_size,
        )
        assert checked.verdict is CheckerVerdict.ACCEPT
        assert checked.image is not None
        for enclosure, root_value in zip(checked.image, current, strict=True):
            assert enclosure.contains(root_value)
        previous = current


def test_wrong_history_is_not_accepted_in_the_candidate_tube() -> None:
    circuit = rc_source_circuit()
    step_size = 1e-5
    correct_previous = rc_state(0.2)
    voltage = rc_closed_form_next(correct_previous[0], step_size)
    current = rc_state(voltage)
    wrong_previous = rc_state(0.4)
    checked = check_be_step(
        circuit,
        current,
        _tube(current),
        tuple(Interval.point(value) for value in wrong_previous),
        step_size,
    )
    assert checked.verdict is CheckerVerdict.UNKNOWN


def test_invalid_topology_is_structurally_unsupported() -> None:
    circuit = Circuit(node_count=1, resistors=(Resistor(1, 1, 1_000.0),))
    result = point_be_residual_jacobian(circuit, (0.0,), (0.0,), 1e-5)
    assert result.status is MnaStatus.UNSUPPORTED
