"""Independent binary producers for diode-RC and smooth-NMOS ring steps."""

from __future__ import annotations

from collections.abc import Callable

from experiments.devices import DiodeParameters, SmoothNmosParameters
from experiments.mna.minimal_circuits import (
    CAPACITANCE,
    RESISTANCE,
    RING_SUPPLY_VOLTAGE,
    SOURCE_VOLTAGE,
    RingInstance,
)
from experiments.producers.nonlinear import NewtonResult, newton_solve
from experiments.producers.precision import BinaryArithmetic, ProducerPrecision

type PointVector = tuple[float, ...]
type PointMatrix = tuple[tuple[float, ...], ...]
type Evaluator = Callable[[PointVector], tuple[PointVector, PointMatrix]]

_DEFAULT_DIODE_PARAMETERS = DiodeParameters()
_DEFAULT_SMOOTH_NMOS_PARAMETERS = SmoothNmosParameters()


def diode_rc_evaluator(
    previous_state: PointVector,
    step_size: float,
    precision: ProducerPrecision,
    *,
    resistance: float = RESISTANCE,
    capacitance: float = CAPACITANCE,
    source_voltage: float = SOURCE_VOLTAGE,
    parameters: DiodeParameters = _DEFAULT_DIODE_PARAMETERS,
) -> Evaluator:
    """Build the producer-side diode-RC residual independently of checker MNA."""

    if len(previous_state) != 3:
        raise ValueError("diode-RC producer state must have dimension three")
    arithmetic = BinaryArithmetic(precision)
    previous = tuple(arithmetic.cast(value) for value in previous_state)
    step = arithmetic.cast(step_size)
    resistance_value = arithmetic.cast(resistance)
    capacitance_value = arithmetic.cast(capacitance)
    source_value = arithmetic.cast(source_voltage)
    saturation_current = arithmetic.cast(parameters.saturation_current)
    thermal_voltage = arithmetic.cast(parameters.thermal_voltage)

    def evaluate(state: PointVector) -> tuple[PointVector, PointMatrix]:
        voltage, supply, branch_current = (arithmetic.cast(value) for value in state)
        resistor_current = arithmetic.divide(
            arithmetic.subtract(voltage, supply), resistance_value
        )
        exponent = arithmetic.divide(voltage, thermal_voltage)
        diode_current = arithmetic.multiply(
            saturation_current, arithmetic.expm1(exponent)
        )
        diode_conductance = arithmetic.multiply(
            arithmetic.divide(saturation_current, thermal_voltage),
            arithmetic.exp(exponent),
        )
        dynamic = arithmetic.multiply(
            capacitance_value, arithmetic.subtract(voltage, previous[0])
        )
        first_residual = arithmetic.add(
            dynamic,
            arithmetic.multiply(step, arithmetic.add(resistor_current, diode_current)),
        )
        second_residual = arithmetic.multiply(
            step,
            arithmetic.add(
                arithmetic.divide(
                    arithmetic.subtract(supply, voltage), resistance_value
                ),
                branch_current,
            ),
        )
        third_residual = arithmetic.multiply(
            step, arithmetic.subtract(supply, source_value)
        )
        resistor_conductance = arithmetic.divide(step, resistance_value)
        first_diagonal = arithmetic.add(
            capacitance_value,
            arithmetic.add(
                resistor_conductance,
                arithmetic.multiply(step, diode_conductance),
            ),
        )
        jacobian = (
            (first_diagonal, -resistor_conductance, arithmetic.cast(0.0)),
            (-resistor_conductance, resistor_conductance, step),
            (arithmetic.cast(0.0), step, arithmetic.cast(0.0)),
        )
        return (first_residual, second_residual, third_residual), jacobian

    return evaluate


def solve_diode_rc_step(
    previous_state: PointVector,
    step_size: float,
    precision: ProducerPrecision,
    residual_tolerance: float,
    *,
    max_iterations: int = 30,
    resistance: float = RESISTANCE,
    capacitance: float = CAPACITANCE,
    source_voltage: float = SOURCE_VOLTAGE,
) -> NewtonResult:
    """Produce one diode-RC candidate without importing a test reference."""

    evaluator = diode_rc_evaluator(
        previous_state,
        step_size,
        precision,
        resistance=resistance,
        capacitance=capacitance,
        source_voltage=source_voltage,
    )
    return newton_solve(
        evaluator,
        previous_state,
        precision,
        residual_tolerance,
        max_iterations=max_iterations,
    )


def ring_evaluator(
    previous_state: PointVector,
    instance: RingInstance,
    precision: ProducerPrecision,
    *,
    parameters: SmoothNmosParameters = _DEFAULT_SMOOTH_NMOS_PARAMETERS,
) -> Evaluator:
    """Build a producer-side ring residual independent of checker MNA assembly."""

    if len(previous_state) != 5:
        raise ValueError("ring producer state must have dimension five")
    arithmetic = BinaryArithmetic(precision)
    previous = tuple(arithmetic.cast(value) for value in previous_state)
    resistance = arithmetic.cast(instance.load_resistance)
    capacitance = arithmetic.cast(instance.load_capacitance)
    step = arithmetic.cast(instance.step_size)
    supply_target = arithmetic.cast(RING_SUPPLY_VOLTAGE)
    scale = arithmetic.cast(parameters.conductance_scale)
    threshold = arithmetic.cast(parameters.threshold)
    slope_voltage = arithmetic.cast(parameters.slope_voltage)
    floor_conductance = arithmetic.cast(parameters.floor_conductance)
    gate_indices = (2, 0, 1)

    def evaluate(state: PointVector) -> tuple[PointVector, PointMatrix]:
        values = tuple(arithmetic.cast(value) for value in state)
        voltages = values[:3]
        supply = values[3]
        branch_current = values[4]
        residual = [arithmetic.cast(0.0) for _ in range(5)]
        jacobian = [[arithmetic.cast(0.0) for _ in range(5)] for _ in range(5)]
        for index, gate_index in enumerate(gate_indices):
            exponent = arithmetic.divide(
                arithmetic.subtract(voltages[gate_index], threshold),
                slope_voltage,
            )
            controlled = arithmetic.multiply(scale, arithmetic.exp(exponent))
            conductance = arithmetic.add(floor_conductance, controlled)
            transconductance = arithmetic.divide(controlled, slope_voltage)
            load_current = arithmetic.divide(
                arithmetic.subtract(voltages[index], supply), resistance
            )
            drain_current = arithmetic.multiply(conductance, voltages[index])
            dynamic = arithmetic.multiply(
                capacitance,
                arithmetic.subtract(voltages[index], previous[index]),
            )
            residual[index] = arithmetic.add(
                dynamic,
                arithmetic.multiply(step, arithmetic.add(load_current, drain_current)),
            )
            load_conductance_step = arithmetic.divide(step, resistance)
            jacobian[index][index] = arithmetic.add(
                capacitance,
                arithmetic.add(
                    load_conductance_step,
                    arithmetic.multiply(step, conductance),
                ),
            )
            jacobian[index][gate_index] = arithmetic.multiply(
                step,
                arithmetic.multiply(transconductance, voltages[index]),
            )
            jacobian[index][3] = -load_conductance_step
        supply_terms = tuple(
            arithmetic.divide(arithmetic.subtract(supply, voltage), resistance)
            for voltage in voltages
        )
        residual[3] = arithmetic.multiply(
            step, arithmetic.add(arithmetic.sum(supply_terms), branch_current)
        )
        load_conductance_step = arithmetic.divide(step, resistance)
        for index in range(3):
            jacobian[3][index] = -load_conductance_step
        jacobian[3][3] = arithmetic.multiply(3.0, load_conductance_step)
        jacobian[3][4] = step
        residual[4] = arithmetic.multiply(
            step, arithmetic.subtract(supply, supply_target)
        )
        jacobian[4][3] = step
        return tuple(residual), tuple(tuple(row) for row in jacobian)

    return evaluate


def solve_ring_step(
    previous_state: PointVector,
    instance: RingInstance,
    precision: ProducerPrecision,
    residual_tolerance: float,
    *,
    max_iterations: int = 30,
) -> NewtonResult:
    """Produce one smooth-NMOS ring candidate without a reference dependency."""

    evaluator = ring_evaluator(previous_state, instance, precision)
    return newton_solve(
        evaluator,
        previous_state,
        precision,
        residual_tolerance,
        max_iterations=max_iterations,
    )
