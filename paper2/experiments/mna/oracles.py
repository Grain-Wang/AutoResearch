"""Independent exact and Decimal-160 test references for minimal BE circuits.

The Decimal paths are high-precision *test references*, not rigorous root brackets:
their residual signs and Newton termination are not backed by directed error bounds.
They are deliberately absent from candidate production and tube initialization.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction

from experiments.devices import DiodeParameters
from experiments.mna.minimal_circuits import RING_SUPPLY_VOLTAGE, RingInstance

_DEFAULT_DIODE_PARAMETERS = DiodeParameters()


def rc_closed_form_next(
    previous_voltage: float,
    step_size: float,
    *,
    resistance: float = 1_000.0,
    capacitance: float = 1e-6,
    source_voltage: float = 0.7,
) -> float:
    """Return the exact-form BE update evaluated in binary64."""

    return float(
        rc_exact_next(
            previous_voltage,
            step_size,
            resistance=resistance,
            capacitance=capacitance,
            source_voltage=source_voltage,
        )
    )


def rc_exact_next(
    previous_voltage: float,
    step_size: float,
    *,
    resistance: float = 1_000.0,
    capacitance: float = 1e-6,
    source_voltage: float = 0.7,
) -> Fraction:
    """Return the exact-real RC BE root for the declared binary64 inputs."""

    previous = Fraction.from_float(previous_voltage)
    step = Fraction.from_float(step_size)
    resistance_exact = Fraction.from_float(resistance)
    capacitance_exact = Fraction.from_float(capacitance)
    source = Fraction.from_float(source_voltage)
    conductance_step = step / resistance_exact
    return (capacitance_exact * previous + conductance_step * source) / (
        capacitance_exact + conductance_step
    )


def diode_rc_decimal_bracket(
    previous_voltage: float,
    step_size: float,
    *,
    resistance: float = 1_000.0,
    capacitance: float = 1e-6,
    source_voltage: float = 0.7,
    parameters: DiodeParameters = _DEFAULT_DIODE_PARAMETERS,
    decimal_digits: int = 160,
    bisection_iterations: int = 600,
) -> tuple[Decimal, Decimal]:
    """Return Decimal-160 bisection endpoints around a diode-RC test root.

    The endpoint pair is a high-precision diagnostic, not a sign-certified interval.
    The historical function name is retained for artifact compatibility.
    """

    if decimal_digits < 80:
        raise ValueError("the test reference requires at least 80 decimal digits")
    if bisection_iterations <= 0:
        raise ValueError("bisection_iterations must be positive")
    with localcontext() as context:
        context.prec = decimal_digits
        lower = Decimal("-2")
        upper = Decimal("2")
        decimal_capacitance = Decimal.from_float(capacitance)
        decimal_resistance = Decimal.from_float(resistance)
        decimal_source = Decimal.from_float(source_voltage)
        decimal_step = Decimal.from_float(step_size)
        decimal_previous = Decimal.from_float(previous_voltage)
        saturation_current = Decimal.from_float(parameters.saturation_current)
        thermal_voltage = Decimal.from_float(parameters.thermal_voltage)

        def residual(voltage: Decimal) -> Decimal:
            return decimal_capacitance * (voltage - decimal_previous) + decimal_step * (
                (voltage - decimal_source) / decimal_resistance
                + saturation_current * ((voltage / thermal_voltage).exp() - Decimal(1))
            )

        if residual(lower) >= 0 or residual(upper) <= 0:
            raise ArithmeticError(
                "fixed Decimal test interval does not straddle the root"
            )
        for _ in range(bisection_iterations):
            midpoint = (lower + upper) / 2
            if residual(midpoint) > 0:
                upper = midpoint
            else:
                lower = midpoint
        return lower, upper


def diode_rc_decimal_root(
    previous_voltage: float,
    step_size: float,
    *,
    resistance: float = 1_000.0,
    capacitance: float = 1e-6,
    source_voltage: float = 0.7,
    parameters: DiodeParameters = _DEFAULT_DIODE_PARAMETERS,
    decimal_digits: int = 160,
    bisection_iterations: int = 600,
) -> float:
    """Return the binary64 midpoint of the Decimal-160 test reference endpoints."""

    lower, upper = diode_rc_decimal_bracket(
        previous_voltage,
        step_size,
        resistance=resistance,
        capacitance=capacitance,
        source_voltage=source_voltage,
        parameters=parameters,
        decimal_digits=decimal_digits,
        bisection_iterations=bisection_iterations,
    )
    with localcontext() as context:
        context.prec = decimal_digits
        return float((lower + upper) / 2)


def diode_rc_decimal_next(
    previous_voltage: Decimal | float,
    step_size: float,
    *,
    resistance: float = 1_000.0,
    capacitance: float = 1e-6,
    source_voltage: float = 0.7,
    parameters: DiodeParameters = _DEFAULT_DIODE_PARAMETERS,
    decimal_digits: int = 160,
    bisection_iterations: int = 600,
) -> Decimal:
    """Advance one diode-RC step in the Decimal-160 test-reference trajectory."""

    if decimal_digits < 80:
        raise ValueError("the test reference requires at least 80 decimal digits")
    if bisection_iterations <= 0:
        raise ValueError("bisection_iterations must be positive")
    with localcontext() as context:
        context.prec = decimal_digits
        lower = Decimal("-2")
        upper = Decimal("2")
        previous = (
            previous_voltage
            if isinstance(previous_voltage, Decimal)
            else Decimal.from_float(previous_voltage)
        )
        decimal_capacitance = Decimal.from_float(capacitance)
        decimal_resistance = Decimal.from_float(resistance)
        decimal_source = Decimal.from_float(source_voltage)
        decimal_step = Decimal.from_float(step_size)
        saturation_current = Decimal.from_float(parameters.saturation_current)
        thermal_voltage = Decimal.from_float(parameters.thermal_voltage)

        def residual(voltage: Decimal) -> Decimal:
            return decimal_capacitance * (voltage - previous) + decimal_step * (
                (voltage - decimal_source) / decimal_resistance
                + saturation_current * ((voltage / thermal_voltage).exp() - Decimal(1))
            )

        if residual(lower) >= 0 or residual(upper) <= 0:
            raise ArithmeticError("fixed Decimal test interval does not straddle root")
        for _ in range(bisection_iterations):
            midpoint = (lower + upper) / 2
            if residual(midpoint) > 0:
                upper = midpoint
            else:
                lower = midpoint
        return +(lower + upper) / 2


def ring_decimal_initial_state(instance: RingInstance) -> tuple[Decimal, ...]:
    """Return the exact-Decimal encoding of a ring's declared binary initial state."""

    with localcontext() as context:
        context.prec = 160
        supply = Decimal.from_float(RING_SUPPLY_VOLTAGE)
        resistance = Decimal.from_float(instance.load_resistance)
        voltages = tuple(
            Decimal.from_float(value) for value in instance.initial_voltages
        )
        current = -sum((supply - value) / resistance for value in voltages)
        return *voltages, supply, +current


def _decimal_solve(
    matrix: tuple[tuple[Decimal, ...], ...],
    right_hand_side: tuple[Decimal, ...],
) -> tuple[Decimal, ...]:
    dimension = len(right_hand_side)
    augmented = [
        list(row) + [right_hand_side[index]] for index, row in enumerate(matrix)
    ]
    for pivot_index in range(dimension):
        pivot_row = max(
            range(pivot_index, dimension),
            key=lambda row_index: abs(augmented[row_index][pivot_index]),
        )
        if augmented[pivot_row][pivot_index] == 0:
            raise ArithmeticError("Decimal ring reference Jacobian is singular")
        augmented[pivot_index], augmented[pivot_row] = (
            augmented[pivot_row],
            augmented[pivot_index],
        )
        for row_index in range(pivot_index + 1, dimension):
            factor = (
                augmented[row_index][pivot_index] / augmented[pivot_index][pivot_index]
            )
            for column_index in range(pivot_index, dimension + 1):
                augmented[row_index][column_index] -= (
                    factor * augmented[pivot_index][column_index]
                )
    solution = [Decimal(0) for _ in range(dimension)]
    for row_index in range(dimension - 1, -1, -1):
        tail = sum(
            augmented[row_index][column_index] * solution[column_index]
            for column_index in range(row_index + 1, dimension)
        )
        solution[row_index] = (augmented[row_index][dimension] - tail) / augmented[
            row_index
        ][row_index]
    return tuple(solution)


def ring_decimal_next(
    previous_state: tuple[Decimal, ...],
    instance: RingInstance,
    *,
    decimal_digits: int = 160,
    max_iterations: int = 80,
) -> tuple[Decimal, ...]:
    """Advance the independent Decimal-160 smooth-NMOS ring test reference."""

    if len(previous_state) != 5:
        raise ValueError("ring test-reference state must have dimension five")
    if decimal_digits < 80:
        raise ValueError("the test reference requires at least 80 decimal digits")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")
    with localcontext() as context:
        context.prec = decimal_digits
        resistance = Decimal.from_float(instance.load_resistance)
        capacitance = Decimal.from_float(instance.load_capacitance)
        step = Decimal.from_float(instance.step_size)
        supply = Decimal.from_float(RING_SUPPLY_VOLTAGE)
        conductance_scale = Decimal.from_float(5e-5)
        threshold = Decimal.from_float(0.45)
        slope_voltage = Decimal.from_float(0.12)
        floor_conductance = Decimal.from_float(1e-8)
        gate_indices = (2, 0, 1)
        center = tuple(+value for value in previous_state[:3])

        def evaluate(
            voltages: tuple[Decimal, ...],
        ) -> tuple[tuple[Decimal, ...], tuple[tuple[Decimal, ...], ...]]:
            residual: list[Decimal] = []
            jacobian = [[Decimal(0) for _ in range(3)] for _ in range(3)]
            for index, gate_index in enumerate(gate_indices):
                controlled = (
                    conductance_scale
                    * ((voltages[gate_index] - threshold) / slope_voltage).exp()
                )
                conductance = floor_conductance + controlled
                residual.append(
                    capacitance * (voltages[index] - previous_state[index])
                    + step
                    * (
                        (voltages[index] - supply) / resistance
                        + conductance * voltages[index]
                    )
                )
                jacobian[index][index] += capacitance + step * (
                    Decimal(1) / resistance + conductance
                )
                jacobian[index][gate_index] += (
                    step * controlled / slope_voltage * voltages[index]
                )
            return tuple(residual), tuple(tuple(row) for row in jacobian)

        residual, jacobian = evaluate(center)
        for _ in range(max_iterations):
            norm = max(abs(value) for value in residual)
            if norm <= Decimal(10) ** Decimal(-120):
                break
            correction = _decimal_solve(jacobian, tuple(-value for value in residual))
            alpha = Decimal(1)
            for _ in range(30):
                trial = tuple(
                    value + alpha * delta
                    for value, delta in zip(center, correction, strict=True)
                )
                trial_residual, trial_jacobian = evaluate(trial)
                if max(abs(value) for value in trial_residual) < norm:
                    center = trial
                    residual = trial_residual
                    jacobian = trial_jacobian
                    break
                alpha /= 2
            else:
                raise ArithmeticError("Decimal ring reference line search failed")
        else:
            raise ArithmeticError("Decimal ring reference did not converge")
        if max(abs(value) for value in residual) > Decimal(10) ** Decimal(-100):
            raise ArithmeticError("Decimal ring reference residual is too large")
        branch_current = -sum((supply - value) / resistance for value in center)
        return *tuple(+value for value in center), supply, +branch_current
