"""Independent analytic/high-precision oracles for the minimal BE circuits."""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction

from experiments.devices import DiodeParameters

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
    """Return a high-precision bisection bracket for one diode-RC BE root."""

    if decimal_digits < 80:
        raise ValueError("the oracle requires at least 80 decimal digits")
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
            raise ArithmeticError("fixed oracle bracket does not straddle the root")
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
    """Return the midpoint of the independent high-precision root bracket."""

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
