"""Restricted charge-oriented Backward Euler MNA assembly.

The state layout is deterministic: non-ground node voltages in node-number order,
followed by independent voltage-source branch currents in declaration order.  The
residual is ``q(x_k) - q(x_{k-1}) + h i(x_k)``.  Algebraic voltage-source equations
are multiplied by ``h`` so the complete residual follows the same convention.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from experiments.devices import (
    DiodeParameters,
    SmoothNmosParameters,
    diode_interval,
    diode_point,
    smooth_nmos_interval,
    smooth_nmos_point,
)
from experiments.interval_backend import Interval, IntervalResult, IntervalStatus
from experiments.rigorous_backend import add, divide, multiply, subtract

type PointVector = tuple[float, ...]
type PointMatrix = tuple[tuple[float, ...], ...]
type IntervalVector = tuple[Interval, ...]
type IntervalMatrix = tuple[tuple[Interval, ...], ...]


@dataclass(frozen=True, slots=True)
class Resistor:
    positive: int
    negative: int
    resistance: float


@dataclass(frozen=True, slots=True)
class Capacitor:
    positive: int
    negative: int
    capacitance: float


@dataclass(frozen=True, slots=True)
class CurrentSource:
    positive: int
    negative: int
    current: float


@dataclass(frozen=True, slots=True)
class VoltageSource:
    positive: int
    negative: int
    voltage: float


@dataclass(frozen=True, slots=True)
class Diode:
    positive: int
    negative: int
    parameters: DiodeParameters = DiodeParameters()


@dataclass(frozen=True, slots=True)
class SmoothNmos:
    """Three-terminal globally smooth NMOS benchmark element."""

    drain: int
    gate: int
    source: int
    parameters: SmoothNmosParameters = SmoothNmosParameters()


@dataclass(frozen=True, slots=True)
class Circuit:
    node_count: int
    resistors: tuple[Resistor, ...] = ()
    capacitors: tuple[Capacitor, ...] = ()
    current_sources: tuple[CurrentSource, ...] = ()
    voltage_sources: tuple[VoltageSource, ...] = ()
    diodes: tuple[Diode, ...] = ()
    smooth_nmos: tuple[SmoothNmos, ...] = ()

    @property
    def state_dimension(self) -> int:
        """Return node-voltage plus voltage-source-current state size."""

        return self.node_count + len(self.voltage_sources)


class MnaStatus(StrEnum):
    OK = "OK"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class PointMnaEvaluation:
    status: MnaStatus
    residual: PointVector | None
    jacobian: PointMatrix | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class IntervalMnaEvaluation:
    status: MnaStatus
    residual: IntervalVector | None
    jacobian: IntervalMatrix | None
    reason: str | None = None


class _UnsupportedArithmetic(RuntimeError):
    pass


def _require(result: IntervalResult) -> Interval:
    if result.status is not IntervalStatus.OK or result.interval is None:
        raise _UnsupportedArithmetic(result.reason or "unsupported interval operation")
    return result.interval


def _validate_circuit(circuit: Circuit) -> str | None:
    if circuit.node_count <= 0:
        return "a supported circuit needs at least one non-ground node"
    elements = (
        *circuit.resistors,
        *circuit.capacitors,
        *circuit.current_sources,
        *circuit.voltage_sources,
        *circuit.diodes,
    )
    for element in elements:
        if not (0 <= element.positive <= circuit.node_count):
            return "positive node index is outside the normalized layout"
        if not (0 <= element.negative <= circuit.node_count):
            return "negative node index is outside the normalized layout"
        if element.positive == element.negative:
            return "a two-terminal element cannot connect a node to itself"
    for transistor in circuit.smooth_nmos:
        if not (0 <= transistor.drain <= circuit.node_count):
            return "smooth-NMOS drain index is outside the normalized layout"
        if not (0 <= transistor.gate <= circuit.node_count):
            return "smooth-NMOS gate index is outside the normalized layout"
        if not (0 <= transistor.source <= circuit.node_count):
            return "smooth-NMOS source index is outside the normalized layout"
        if transistor.drain == transistor.source:
            return "smooth-NMOS drain and source nodes must differ"
    for resistor in circuit.resistors:
        if not math.isfinite(resistor.resistance) or resistor.resistance <= 0.0:
            return "resistance must be finite and positive"
    for capacitor in circuit.capacitors:
        if not math.isfinite(capacitor.capacitance) or capacitor.capacitance <= 0.0:
            return "capacitance must be finite and positive"
    for source in circuit.current_sources:
        if not math.isfinite(source.current):
            return "current-source value must be finite"
    for source in circuit.voltage_sources:
        if not math.isfinite(source.voltage):
            return "voltage-source value must be finite"
    for diode in circuit.diodes:
        if (
            not math.isfinite(diode.parameters.saturation_current)
            or not math.isfinite(diode.parameters.thermal_voltage)
            or diode.parameters.saturation_current <= 0.0
            or diode.parameters.thermal_voltage <= 0.0
        ):
            return "diode parameters must be finite and positive"
    for transistor in circuit.smooth_nmos:
        parameters = transistor.parameters
        if (
            not math.isfinite(parameters.conductance_scale)
            or not math.isfinite(parameters.threshold)
            or not math.isfinite(parameters.slope_voltage)
            or not math.isfinite(parameters.floor_conductance)
            or parameters.conductance_scale <= 0.0
            or parameters.slope_voltage <= 0.0
            or parameters.floor_conductance < 0.0
        ):
            return "smooth-NMOS parameters are outside the supported finite domain"
    return None


def _node_index(node: int) -> int | None:
    return None if node == 0 else node - 1


def _point_voltage(state: PointVector, node: int) -> float:
    index = _node_index(node)
    return 0.0 if index is None else state[index]


def _interval_voltage(state: IntervalVector, node: int) -> Interval:
    index = _node_index(node)
    return Interval.point(0.0) if index is None else state[index]


def _add_point_value(values: list[float], node: int, value: float) -> None:
    index = _node_index(node)
    if index is not None:
        values[index] += value


def _add_point_jacobian(
    matrix: list[list[float]], row_node: int, column_node: int, value: float
) -> None:
    row = _node_index(row_node)
    column = _node_index(column_node)
    if row is not None and column is not None:
        matrix[row][column] += value


def _stamp_point_branch(
    residual: list[float],
    jacobian: list[list[float]],
    positive: int,
    negative: int,
    current: float,
    conductance: float,
) -> None:
    _add_point_value(residual, positive, current)
    _add_point_value(residual, negative, -current)
    _add_point_jacobian(jacobian, positive, positive, conductance)
    _add_point_jacobian(jacobian, positive, negative, -conductance)
    _add_point_jacobian(jacobian, negative, positive, -conductance)
    _add_point_jacobian(jacobian, negative, negative, conductance)


def _stamp_point_controlled_branch(
    residual: list[float],
    jacobian: list[list[float]],
    drain: int,
    gate: int,
    source: int,
    current: float,
    transconductance: float,
    output_conductance: float,
) -> None:
    """Stamp ``Id(Vg-Vs, Vd-Vs)`` into point KCL rows."""

    _add_point_value(residual, drain, current)
    _add_point_value(residual, source, -current)
    source_derivative = -(transconductance + output_conductance)
    for column, derivative in (
        (drain, output_conductance),
        (gate, transconductance),
        (source, source_derivative),
    ):
        _add_point_jacobian(jacobian, drain, column, derivative)
        _add_point_jacobian(jacobian, source, column, -derivative)


def point_be_residual_jacobian(
    circuit: Circuit,
    current_state: PointVector,
    previous_state: PointVector,
    step_size: float,
) -> PointMnaEvaluation:
    """Assemble point BE residual and current-state Jacobian."""

    reason = _validate_circuit(circuit)
    if reason is not None:
        return PointMnaEvaluation(MnaStatus.UNSUPPORTED, None, None, reason)
    dimension = circuit.state_dimension
    if len(current_state) != dimension or len(previous_state) != dimension:
        return PointMnaEvaluation(
            MnaStatus.UNSUPPORTED, None, None, "state dimension mismatch"
        )
    if not math.isfinite(step_size) or step_size <= 0.0:
        return PointMnaEvaluation(
            MnaStatus.UNSUPPORTED, None, None, "step size must be finite and positive"
        )
    if any(not math.isfinite(value) for value in (*current_state, *previous_state)):
        return PointMnaEvaluation(
            MnaStatus.UNSUPPORTED, None, None, "state values must be finite"
        )

    residual = [0.0 for _ in range(dimension)]
    jacobian = [[0.0 for _ in range(dimension)] for _ in range(dimension)]
    try:
        for resistor in circuit.resistors:
            voltage = _point_voltage(current_state, resistor.positive) - _point_voltage(
                current_state, resistor.negative
            )
            conductance = step_size / resistor.resistance
            _stamp_point_branch(
                residual,
                jacobian,
                resistor.positive,
                resistor.negative,
                conductance * voltage,
                conductance,
            )
        for capacitor in circuit.capacitors:
            voltage = _point_voltage(
                current_state, capacitor.positive
            ) - _point_voltage(
                current_state,
                capacitor.negative,
            )
            previous_voltage = _point_voltage(
                previous_state, capacitor.positive
            ) - _point_voltage(previous_state, capacitor.negative)
            _stamp_point_branch(
                residual,
                jacobian,
                capacitor.positive,
                capacitor.negative,
                capacitor.capacitance * (voltage - previous_voltage),
                capacitor.capacitance,
            )
        for source in circuit.current_sources:
            _add_point_value(residual, source.positive, step_size * source.current)
            _add_point_value(residual, source.negative, -step_size * source.current)
        for diode in circuit.diodes:
            voltage = _point_voltage(current_state, diode.positive) - _point_voltage(
                current_state, diode.negative
            )
            current, conductance = diode_point(voltage, diode.parameters)
            _stamp_point_branch(
                residual,
                jacobian,
                diode.positive,
                diode.negative,
                step_size * current,
                step_size * conductance,
            )
        for transistor in circuit.smooth_nmos:
            vgs = _point_voltage(current_state, transistor.gate) - _point_voltage(
                current_state, transistor.source
            )
            vds = _point_voltage(current_state, transistor.drain) - _point_voltage(
                current_state, transistor.source
            )
            current, transconductance, output_conductance = smooth_nmos_point(
                vgs, vds, transistor.parameters
            )
            _stamp_point_controlled_branch(
                residual,
                jacobian,
                transistor.drain,
                transistor.gate,
                transistor.source,
                step_size * current,
                step_size * transconductance,
                step_size * output_conductance,
            )
        for source_index, source in enumerate(circuit.voltage_sources):
            branch_index = circuit.node_count + source_index
            branch_current = current_state[branch_index]
            _add_point_value(residual, source.positive, step_size * branch_current)
            _add_point_value(residual, source.negative, -step_size * branch_current)
            positive_index = _node_index(source.positive)
            negative_index = _node_index(source.negative)
            if positive_index is not None:
                jacobian[positive_index][branch_index] += step_size
                jacobian[branch_index][positive_index] += step_size
            if negative_index is not None:
                jacobian[negative_index][branch_index] -= step_size
                jacobian[branch_index][negative_index] -= step_size
            residual[branch_index] = step_size * (
                _point_voltage(current_state, source.positive)
                - _point_voltage(current_state, source.negative)
                - source.voltage
            )
    except (OverflowError, ValueError) as error:
        return PointMnaEvaluation(MnaStatus.UNSUPPORTED, None, None, str(error))
    if any(not math.isfinite(value) for value in residual) or any(
        not math.isfinite(value) for row in jacobian for value in row
    ):
        return PointMnaEvaluation(
            MnaStatus.UNSUPPORTED,
            None,
            None,
            "point assembly overflowed the finite binary64 domain",
        )
    return PointMnaEvaluation(
        MnaStatus.OK,
        tuple(residual),
        tuple(tuple(row) for row in jacobian),
    )


def _add_interval_value(values: list[Interval], node: int, value: Interval) -> None:
    index = _node_index(node)
    if index is not None:
        values[index] = _require(add(values[index], value))


def _add_interval_jacobian(
    matrix: list[list[Interval]], row_node: int, column_node: int, value: Interval
) -> None:
    row = _node_index(row_node)
    column = _node_index(column_node)
    if row is not None and column is not None:
        matrix[row][column] = _require(add(matrix[row][column], value))


def _negative(value: Interval) -> Interval:
    return _require(multiply(Interval.point(-1.0), value))


def _stamp_interval_branch(
    residual: list[Interval],
    jacobian: list[list[Interval]],
    positive: int,
    negative: int,
    current: Interval,
    conductance: Interval,
) -> None:
    _add_interval_value(residual, positive, current)
    _add_interval_value(residual, negative, _negative(current))
    _add_interval_jacobian(jacobian, positive, positive, conductance)
    _add_interval_jacobian(jacobian, positive, negative, _negative(conductance))
    _add_interval_jacobian(jacobian, negative, positive, _negative(conductance))
    _add_interval_jacobian(jacobian, negative, negative, conductance)


def _stamp_interval_controlled_branch(
    residual: list[Interval],
    jacobian: list[list[Interval]],
    drain: int,
    gate: int,
    source: int,
    current: Interval,
    transconductance: Interval,
    output_conductance: Interval,
) -> None:
    """Stamp an interval enclosure of a three-terminal controlled branch."""

    _add_interval_value(residual, drain, current)
    _add_interval_value(residual, source, _negative(current))
    source_derivative = _negative(_require(add(transconductance, output_conductance)))
    for column, derivative in (
        (drain, output_conductance),
        (gate, transconductance),
        (source, source_derivative),
    ):
        _add_interval_jacobian(jacobian, drain, column, derivative)
        _add_interval_jacobian(jacobian, source, column, _negative(derivative))


def interval_be_residual_jacobian(
    circuit: Circuit,
    current_state: IntervalVector,
    previous_state: IntervalVector,
    step_size: float,
) -> IntervalMnaEvaluation:
    """Assemble an outward-rounded BE residual and current-state Jacobian."""

    reason = _validate_circuit(circuit)
    if reason is not None:
        return IntervalMnaEvaluation(MnaStatus.UNSUPPORTED, None, None, reason)
    dimension = circuit.state_dimension
    if len(current_state) != dimension or len(previous_state) != dimension:
        return IntervalMnaEvaluation(
            MnaStatus.UNSUPPORTED, None, None, "state dimension mismatch"
        )
    if not math.isfinite(step_size) or step_size <= 0.0:
        return IntervalMnaEvaluation(
            MnaStatus.UNSUPPORTED, None, None, "step size must be finite and positive"
        )

    residual = [Interval.point(0.0) for _ in range(dimension)]
    jacobian = [
        [Interval.point(0.0) for _ in range(dimension)] for _ in range(dimension)
    ]
    step = Interval.point(step_size)
    try:
        for resistor in circuit.resistors:
            voltage = _require(
                subtract(
                    _interval_voltage(current_state, resistor.positive),
                    _interval_voltage(current_state, resistor.negative),
                )
            )
            conductance = _require(divide(step, Interval.point(resistor.resistance)))
            _stamp_interval_branch(
                residual,
                jacobian,
                resistor.positive,
                resistor.negative,
                _require(multiply(conductance, voltage)),
                conductance,
            )
        for capacitor in circuit.capacitors:
            voltage = _require(
                subtract(
                    _interval_voltage(current_state, capacitor.positive),
                    _interval_voltage(current_state, capacitor.negative),
                )
            )
            previous_voltage = _require(
                subtract(
                    _interval_voltage(previous_state, capacitor.positive),
                    _interval_voltage(previous_state, capacitor.negative),
                )
            )
            difference = _require(subtract(voltage, previous_voltage))
            capacitance = Interval.point(capacitor.capacitance)
            _stamp_interval_branch(
                residual,
                jacobian,
                capacitor.positive,
                capacitor.negative,
                _require(multiply(capacitance, difference)),
                capacitance,
            )
        for source in circuit.current_sources:
            source_current = _require(multiply(step, Interval.point(source.current)))
            _add_interval_value(residual, source.positive, source_current)
            _add_interval_value(residual, source.negative, _negative(source_current))
        for diode in circuit.diodes:
            voltage = _require(
                subtract(
                    _interval_voltage(current_state, diode.positive),
                    _interval_voltage(current_state, diode.negative),
                )
            )
            stamp = diode_interval(voltage, diode.parameters)
            if stamp is None:
                raise _UnsupportedArithmetic("diode interval stamp is unsupported")
            _stamp_interval_branch(
                residual,
                jacobian,
                diode.positive,
                diode.negative,
                _require(multiply(step, stamp.current)),
                _require(multiply(step, stamp.conductance)),
            )
        for transistor in circuit.smooth_nmos:
            vgs = _require(
                subtract(
                    _interval_voltage(current_state, transistor.gate),
                    _interval_voltage(current_state, transistor.source),
                )
            )
            vds = _require(
                subtract(
                    _interval_voltage(current_state, transistor.drain),
                    _interval_voltage(current_state, transistor.source),
                )
            )
            stamp = smooth_nmos_interval(vgs, vds, transistor.parameters)
            if stamp is None:
                raise _UnsupportedArithmetic(
                    "smooth-NMOS interval stamp is unsupported"
                )
            _stamp_interval_controlled_branch(
                residual,
                jacobian,
                transistor.drain,
                transistor.gate,
                transistor.source,
                _require(multiply(step, stamp.drain_current)),
                _require(multiply(step, stamp.transconductance)),
                _require(multiply(step, stamp.output_conductance)),
            )
        for source_index, source in enumerate(circuit.voltage_sources):
            branch_index = circuit.node_count + source_index
            branch_current = _require(multiply(step, current_state[branch_index]))
            _add_interval_value(residual, source.positive, branch_current)
            _add_interval_value(residual, source.negative, _negative(branch_current))
            positive_index = _node_index(source.positive)
            negative_index = _node_index(source.negative)
            if positive_index is not None:
                jacobian[positive_index][branch_index] = _require(
                    add(jacobian[positive_index][branch_index], step)
                )
                jacobian[branch_index][positive_index] = _require(
                    add(jacobian[branch_index][positive_index], step)
                )
            if negative_index is not None:
                negative_step = _negative(step)
                jacobian[negative_index][branch_index] = _require(
                    add(jacobian[negative_index][branch_index], negative_step)
                )
                jacobian[branch_index][negative_index] = _require(
                    add(jacobian[branch_index][negative_index], negative_step)
                )
            voltage_error = _require(
                subtract(
                    _require(
                        subtract(
                            _interval_voltage(current_state, source.positive),
                            _interval_voltage(current_state, source.negative),
                        )
                    ),
                    Interval.point(source.voltage),
                )
            )
            residual[branch_index] = _require(multiply(step, voltage_error))
    except _UnsupportedArithmetic as error:
        return IntervalMnaEvaluation(MnaStatus.UNSUPPORTED, None, None, str(error))
    return IntervalMnaEvaluation(
        MnaStatus.OK,
        tuple(residual),
        tuple(tuple(row) for row in jacobian),
    )
