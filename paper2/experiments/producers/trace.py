"""Common transient producer trace API with post-hoc checker/reference diagnostics."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from experiments.checkers import CheckerVerdict, check_be_step
from experiments.interval_backend import Interval
from experiments.mna import (
    DIODE_RC_INSTANCES,
    RING_INSTANCES,
    DiodeRcInstance,
    RingInstance,
    diode_rc_circuit,
    diode_rc_decimal_next,
    diode_rc_state,
    nmos_ring_3stage,
    ring_decimal_initial_state,
    ring_decimal_next,
    ring_initial_state,
)
from experiments.producers.precision import ProducerPrecision
from experiments.producers.transient import solve_diode_rc_step, solve_ring_step
from experiments.producers.tube import TubeRule, initialize_tube

type DecimalState = tuple[Decimal, ...]


@dataclass(frozen=True, slots=True)
class TraceStep:
    """One unfiltered candidate, tube, checker, and post-hoc reference record."""

    step_index: int
    center: tuple[float, ...]
    tube: tuple[Interval, ...] | None
    radii: tuple[float, ...] | None
    producer_converged: bool
    producer_iterations: int
    producer_raw_residual_inf: float
    producer_scaled_residual_inf: float
    producer_failure_code: str | None
    reference: tuple[float, ...] | None
    reference_error_inf: float | None
    reference_in_tube: bool | None
    checker_verdict: CheckerVerdict
    checker_inclusion_margin: float | None
    checker_reason: str | None
    generation_seconds: float
    tube_seconds: float
    check_seconds: float
    reference_seconds: float
    incoming_reference_in_tube: bool = True


@dataclass(frozen=True, slots=True)
class TraceResult:
    """Complete unfiltered result of a requested transient producer trace."""

    circuit_id: str
    instance_name: str
    precision: ProducerPrecision
    tolerance: float
    steps_requested: int
    step_size: float
    radius_multiplier: float
    tube_rule: TubeRule
    test_reference_method: str
    records: tuple[TraceStep, ...]
    failure_code: str | None


def _ring_instance(name: str, step_size: float | None) -> RingInstance:
    try:
        instance = next(item for item in RING_INSTANCES if item.name == name)
    except StopIteration as error:
        raise ValueError(f"unknown ring instance: {name}") from error
    return instance if step_size is None else replace(instance, step_size=step_size)


def _diode_instance(name: str, step_size: float | None) -> DiodeRcInstance:
    try:
        instance = next(item for item in DIODE_RC_INSTANCES if item.name == name)
    except StopIteration as error:
        raise ValueError(f"unknown diode-RC instance: {name}") from error
    return instance if step_size is None else replace(instance, step_size=step_size)


def build_test_reference(
    circuit_id: str,
    instance: str,
    steps: int,
    step_size: float | None = None,
) -> tuple[DecimalState, ...]:
    """Build an independent Decimal-160 trajectory for post-hoc evaluation."""

    if steps <= 0:
        raise ValueError("reference steps must be positive")
    states: list[DecimalState] = []
    if circuit_id == "diode_rc":
        diode_instance = _diode_instance(instance, step_size)
        with localcontext() as context:
            context.prec = 160
            previous_voltage = Decimal.from_float(diode_instance.initial_voltage)
            supply = Decimal.from_float(diode_instance.source_voltage)
            resistance = Decimal.from_float(diode_instance.resistance)
            for _ in range(steps):
                voltage = diode_rc_decimal_next(
                    previous_voltage,
                    diode_instance.step_size,
                    resistance=diode_instance.resistance,
                    capacitance=diode_instance.capacitance,
                    source_voltage=diode_instance.source_voltage,
                )
                branch_current = (voltage - supply) / resistance
                states.append((voltage, supply, +branch_current))
                previous_voltage = voltage
        return tuple(states)
    if circuit_id == "nmos_ring_3stage":
        ring_instance = _ring_instance(instance, step_size)
        previous = ring_decimal_initial_state(ring_instance)
        for _ in range(steps):
            previous = ring_decimal_next(previous, ring_instance)
            states.append(previous)
        return tuple(states)
    raise ValueError(f"unsupported circuit id: {circuit_id}")


def _reference_inside(reference: DecimalState, tube: tuple[Interval, ...]) -> bool:
    return all(
        Decimal.from_float(interval.lower)
        <= value
        <= Decimal.from_float(interval.upper)
        for value, interval in zip(reference, tube, strict=True)
    )


def _unsupported_step(
    step_index: int,
    center: tuple[float, ...],
    *,
    producer_converged: bool,
    producer_iterations: int,
    raw_residual: float,
    scaled_residual: float,
    producer_failure_code: str | None,
    incoming_reference_in_tube: bool,
    generation_seconds: float,
    reason: str,
) -> TraceStep:
    return TraceStep(
        step_index,
        center,
        None,
        None,
        producer_converged,
        producer_iterations,
        raw_residual,
        scaled_residual,
        producer_failure_code,
        None,
        None,
        None,
        CheckerVerdict.UNSUPPORTED,
        None,
        reason,
        generation_seconds,
        0.0,
        0.0,
        0.0,
        incoming_reference_in_tube=incoming_reference_in_tube,
    )


def produce_trace(
    circuit_id: str,
    instance: str,
    precision: ProducerPrecision | str,
    tolerance: float,
    steps: int,
    step_size: float | None,
    radius_multiplier: float,
    *,
    test_reference: tuple[DecimalState, ...] | None = None,
) -> TraceResult:
    """Produce candidates/tubes, then attach independent post-hoc diagnostics.

    The producer and :func:`initialize_tube` receive no reference object.  Reference
    states are indexed only after the candidate tube is frozen, so this orchestration
    API cannot use the test reference to choose a center or radius.
    """

    declared_precision = ProducerPrecision(precision)
    if steps <= 0:
        raise ValueError("trace steps must be positive")
    if tolerance < 0.0 or not math.isfinite(tolerance):
        raise ValueError("producer tolerance must be finite and nonnegative")
    if radius_multiplier <= 0.0 or not math.isfinite(radius_multiplier):
        raise ValueError("radius multiplier must be finite and positive")
    if circuit_id == "diode_rc":
        diode_instance = _diode_instance(instance, step_size)
        actual_step_size = diode_instance.step_size
        circuit = diode_rc_circuit(diode_instance)
        previous_center = diode_rc_state(diode_instance.initial_voltage, diode_instance)
        rule = TubeRule(
            (1e-12, 1e-12, 1e-15),
            (1.0, 1.0, 1e-3),
            radius_multiplier,
        )

        def solve_step(previous: tuple[float, ...]):
            return solve_diode_rc_step(
                previous,
                actual_step_size,
                declared_precision,
                tolerance,
                resistance=diode_instance.resistance,
                capacitance=diode_instance.capacitance,
                source_voltage=diode_instance.source_voltage,
            )

        reference_method = "Decimal-160 high-precision test reference (non-rigorous)"
    elif circuit_id == "nmos_ring_3stage":
        ring_instance = _ring_instance(instance, step_size)
        actual_step_size = ring_instance.step_size
        circuit = nmos_ring_3stage(ring_instance)
        previous_center = ring_initial_state(ring_instance)
        rule = TubeRule(
            (1e-12, 1e-12, 1e-12, 1e-12, 1e-15),
            (1.0, 1.0, 1.0, 1.0, 1e-3),
            radius_multiplier,
        )

        def solve_step(previous: tuple[float, ...]):
            return solve_ring_step(
                previous, ring_instance, declared_precision, tolerance
            )

        reference_method = "Decimal-160 high-precision test reference (non-rigorous)"
    else:
        raise ValueError(f"unsupported circuit id: {circuit_id}")
    if actual_step_size <= 0.0 or not math.isfinite(actual_step_size):
        raise ValueError("step size must be finite and positive")
    references = test_reference or build_test_reference(
        circuit_id, instance, steps, actual_step_size
    )
    if len(references) != steps:
        raise ValueError("test reference length does not match requested steps")

    previous_tube = tuple(Interval.point(value) for value in previous_center)
    incoming_reference_in_tube = True
    records: list[TraceStep] = []
    trace_failure: str | None = None
    for step_index in range(steps):
        started = time.perf_counter()
        produced = solve_step(previous_center)
        generation_seconds = time.perf_counter() - started
        if any(
            not math.isfinite(value)
            for value in (
                *produced.center,
                *produced.residual,
                produced.raw_residual_inf,
                produced.scaled_residual_inf,
            )
        ):
            records.append(
                _unsupported_step(
                    step_index,
                    produced.center,
                    producer_converged=produced.converged,
                    producer_iterations=produced.iterations,
                    raw_residual=produced.raw_residual_inf,
                    scaled_residual=produced.scaled_residual_inf,
                    producer_failure_code=produced.failure_code,
                    incoming_reference_in_tube=incoming_reference_in_tube,
                    generation_seconds=generation_seconds,
                    reason="producer returned nonfinite diagnostics",
                )
            )
            trace_failure = produced.failure_code or "NONFINITE_PRODUCER_RESULT"
            break
        started = time.perf_counter()
        try:
            initialized = initialize_tube(
                produced.center,
                produced.residual,
                produced.jacobian,
                declared_precision,
                rule,
            )
        except (ArithmeticError, OverflowError, ValueError) as error:
            records.append(
                _unsupported_step(
                    step_index,
                    produced.center,
                    producer_converged=produced.converged,
                    producer_iterations=produced.iterations,
                    raw_residual=produced.raw_residual_inf,
                    scaled_residual=produced.scaled_residual_inf,
                    producer_failure_code=produced.failure_code,
                    incoming_reference_in_tube=incoming_reference_in_tube,
                    generation_seconds=generation_seconds,
                    reason=f"tube initialization failed: {error}",
                )
            )
            trace_failure = "TUBE_INITIALIZATION_FAILED"
            break
        tube_seconds = time.perf_counter() - started
        started = time.perf_counter()
        checked = check_be_step(
            circuit,
            produced.center,
            initialized.tube,
            previous_tube,
            actual_step_size,
        )
        check_seconds = time.perf_counter() - started

        # The reference is accessed only after the candidate and tube are frozen.
        started = time.perf_counter()
        reference_decimal = references[step_index]
        reference = tuple(float(value) for value in reference_decimal)
        reference_error = max(
            abs(value - candidate)
            for value, candidate in zip(reference, produced.center, strict=True)
        )
        reference_in_tube = _reference_inside(reference_decimal, initialized.tube)
        reference_seconds = time.perf_counter() - started
        records.append(
            TraceStep(
                step_index,
                produced.center,
                initialized.tube,
                initialized.radii,
                produced.converged,
                produced.iterations,
                produced.raw_residual_inf,
                produced.scaled_residual_inf,
                produced.failure_code,
                reference,
                reference_error,
                reference_in_tube,
                checked.verdict,
                checked.inclusion_margin,
                checked.reason,
                generation_seconds,
                tube_seconds,
                check_seconds,
                reference_seconds,
                incoming_reference_in_tube=incoming_reference_in_tube,
            )
        )
        previous_center = produced.center
        previous_tube = initialized.tube
        incoming_reference_in_tube = reference_in_tube
    return TraceResult(
        circuit_id,
        instance,
        declared_precision,
        tolerance,
        steps,
        actual_step_size,
        radius_multiplier,
        rule,
        reference_method,
        tuple(records),
        trace_failure,
    )
