from decimal import Decimal
from pathlib import Path

from experiments.checkers import CheckerVerdict
from experiments.interval_backend import Interval
from experiments.mna import (
    RING_INSTANCES,
    MnaStatus,
    interval_be_residual_jacobian,
    nmos_ring_3stage,
    point_be_residual_jacobian,
    ring_decimal_initial_state,
    ring_decimal_next,
    ring_initial_state,
)
from experiments.producers import (
    ProducerPrecision,
    TubeRule,
    initialize_tube,
    load_minimal_probe_config,
    produce_trace,
    ring_evaluator,
    solve_ring_step,
)
from experiments.run_ring_producer_canary import run_ring_canary

_PAPER_ROOT = Path(__file__).resolve().parents[1]


def test_ring_instances_are_distinct_and_configured() -> None:
    assert len(RING_INSTANCES) == 3
    assert len({instance.name for instance in RING_INSTANCES}) == 3
    assert len({instance.load_resistance for instance in RING_INSTANCES}) == 3
    config = load_minimal_probe_config(
        _PAPER_ROOT / "configs/blockstamp/minimal_probe.yaml"
    )
    assert len(config["ring_canary"]["instances"]) == 3


def test_ring_producer_is_independent_but_matches_point_mna() -> None:
    instance = RING_INSTANCES[0]
    previous = ring_initial_state(instance)
    produced = solve_ring_step(
        previous, instance, ProducerPrecision.FLOAT64, residual_tolerance=1e-12
    )
    assert produced.converged
    producer_residual, producer_jacobian = ring_evaluator(
        previous, instance, ProducerPrecision.FLOAT64
    )(produced.center)
    checker_point = point_be_residual_jacobian(
        nmos_ring_3stage(instance), produced.center, previous, instance.step_size
    )
    assert checker_point.status is MnaStatus.OK
    assert checker_point.residual is not None
    assert checker_point.jacobian is not None
    for producer_value, checker_value in zip(
        producer_residual, checker_point.residual, strict=True
    ):
        assert abs(producer_value - checker_value) <= 1e-24
    for producer_row, checker_row in zip(
        producer_jacobian, checker_point.jacobian, strict=True
    ):
        for producer_value, checker_value in zip(
            producer_row, checker_row, strict=True
        ):
            assert abs(producer_value - checker_value) <= 1e-24


def test_ring_interval_assembly_contains_point_evaluation() -> None:
    instance = RING_INSTANCES[1]
    previous = ring_initial_state(instance)
    produced = solve_ring_step(
        previous, instance, ProducerPrecision.FLOAT64, residual_tolerance=1e-12
    )
    tube = tuple(Interval(value - 1e-8, value + 1e-8) for value in produced.center)
    point = point_be_residual_jacobian(
        nmos_ring_3stage(instance), produced.center, previous, instance.step_size
    )
    interval = interval_be_residual_jacobian(
        nmos_ring_3stage(instance),
        tube,
        tuple(Interval.point(value) for value in previous),
        instance.step_size,
    )
    assert point.status is MnaStatus.OK
    assert interval.status is MnaStatus.OK
    assert point.residual is not None
    assert point.jacobian is not None
    assert interval.residual is not None
    assert interval.jacobian is not None
    for point_value, enclosure in zip(point.residual, interval.residual, strict=True):
        assert enclosure.contains(point_value)
    for point_row, interval_row in zip(point.jacobian, interval.jacobian, strict=True):
        for point_value, enclosure in zip(point_row, interval_row, strict=True):
            assert enclosure.contains(point_value)


def test_decimal_ring_reference_has_small_independent_residual() -> None:
    instance = RING_INSTANCES[2]
    previous_decimal = ring_decimal_initial_state(instance)
    current_decimal = ring_decimal_next(previous_decimal, instance)
    previous = tuple(float(value) for value in previous_decimal)
    current = tuple(float(value) for value in current_decimal)
    evaluated = point_be_residual_jacobian(
        nmos_ring_3stage(instance), current, previous, instance.step_size
    )
    assert evaluated.status is MnaStatus.OK
    assert evaluated.residual is not None
    assert max(abs(value) for value in evaluated.residual) < 1e-24
    assert all(isinstance(value, Decimal) for value in current_decimal)


def test_tube_rule_uses_residual_and_precision_without_reference() -> None:
    instance = RING_INSTANCES[0]
    previous = ring_initial_state(instance)
    produced = solve_ring_step(
        previous, instance, ProducerPrecision.FLOAT64, residual_tolerance=1e-8
    )
    rule = TubeRule(
        (1e-12, 1e-12, 1e-12, 1e-12, 1e-15),
        (1.0, 1.0, 1.0, 1.0, 1e-3),
        4.0,
    )
    initialized = initialize_tube(
        produced.center,
        produced.residual,
        produced.jacobian,
        ProducerPrecision.FLOAT64,
        rule,
    )
    assert initialized.raw_residual_inf == max(
        abs(value) for value in produced.residual
    )
    assert all(radius > 0.0 for radius in initialized.radii)
    assert all(
        interval.lower < center < interval.upper
        for center, interval in zip(produced.center, initialized.tube, strict=True)
    )


def test_common_trace_api_preserves_accept_unknown_and_reference_diagnostics() -> None:
    trace = produce_trace(
        "nmos_ring_3stage",
        "balanced",
        ProducerPrecision.FLOAT64,
        1e-10,
        4,
        None,
        4.0,
    )
    assert len(trace.records) == 4
    assert all(record.reference is not None for record in trace.records)
    assert all(record.tube is not None for record in trace.records)
    assert all(
        record.checker_verdict
        in {CheckerVerdict.ACCEPT, CheckerVerdict.UNKNOWN, CheckerVerdict.UNSUPPORTED}
        for record in trace.records
    )
    assert all(record.reference_in_tube is not None for record in trace.records)


def test_ring_runner_executes_reduced_full_instance_precision_grid() -> None:
    artifact = run_ring_canary(step_counts=(2,))
    assert artifact["attempted_traces"] == 6
    assert artifact["attempted_steps"] == 12
    assert artifact["completed_steps"] == 12
    assert len(artifact["traces"]) == 6
    assert artifact["eligible_reference_excluding_accepts"] == 0
