"""Frozen oracle-free candidate-tube initialization."""

from __future__ import annotations

import math
from dataclasses import dataclass

from experiments.interval_backend import Interval
from experiments.producers.nonlinear import solve_linear_system
from experiments.producers.precision import ProducerPrecision

type PointVector = tuple[float, ...]
type PointMatrix = tuple[tuple[float, ...], ...]


@dataclass(frozen=True, slots=True)
class TubeRule:
    """Predeclared residual/Jacobian radius rule, independent of any reference."""

    base_radii: PointVector
    semantic_scales: PointVector
    radius_multiplier: float
    rounding_ulps: float = 8.0


@dataclass(frozen=True, slots=True)
class TubeInitialization:
    """Tube and observable terms used to compute each component radius."""

    tube: tuple[Interval, ...]
    radii: PointVector
    correction_proxy: PointVector
    inverse_row_norms: PointVector
    raw_residual_inf: float
    rule: TubeRule


def _inverse_row_norms(
    jacobian: PointMatrix, precision: ProducerPrecision
) -> PointVector:
    dimension = len(jacobian)
    columns = tuple(
        solve_linear_system(
            jacobian,
            tuple(1.0 if row == column else 0.0 for row in range(dimension)),
            precision,
        )
        for column in range(dimension)
    )
    return tuple(
        sum(abs(columns[column][row]) for column in range(dimension))
        for row in range(dimension)
    )


def initialize_tube(
    center: PointVector,
    residual: PointVector,
    jacobian: PointMatrix,
    precision: ProducerPrecision,
    rule: TubeRule,
) -> TubeInitialization:
    """Create a tube from producer residual, local Jacobian scale, and frozen rules."""

    dimension = len(center)
    if (
        dimension == 0
        or len(residual) != dimension
        or len(jacobian) != dimension
        or len(rule.base_radii) != dimension
        or len(rule.semantic_scales) != dimension
        or any(len(row) != dimension for row in jacobian)
    ):
        raise ValueError("tube initializer dimensions do not match")
    if rule.radius_multiplier <= 0.0 or not math.isfinite(rule.radius_multiplier):
        raise ValueError("radius multiplier must be finite and positive")
    if any(radius <= 0.0 for radius in rule.base_radii):
        raise ValueError("base radii must be positive")
    raw_residual_inf = max(abs(value) for value in residual)
    inverse_row_norms = _inverse_row_norms(jacobian, precision)
    correction = solve_linear_system(
        jacobian, tuple(-value for value in residual), precision
    )
    epsilon = precision.unit_roundoff
    radii = tuple(
        rule.radius_multiplier
        * max(
            base,
            abs(delta),
            row_norm * raw_residual_inf,
            rule.rounding_ulps * epsilon * max(abs(value), semantic_scale),
        )
        for value, delta, row_norm, base, semantic_scale in zip(
            center,
            correction,
            inverse_row_norms,
            rule.base_radii,
            rule.semantic_scales,
            strict=True,
        )
    )
    tube = tuple(
        Interval(
            math.nextafter(value - radius, -math.inf),
            math.nextafter(value + radius, math.inf),
        )
        for value, radius in zip(center, radii, strict=True)
    )
    return TubeInitialization(
        tube,
        radii,
        tuple(abs(value) for value in correction),
        inverse_row_norms,
        raw_residual_inf,
        rule,
    )
