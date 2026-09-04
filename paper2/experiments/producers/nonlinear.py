"""Residual-stopped Newton solver for the untrusted binary producers."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from experiments.producers.precision import BinaryArithmetic, ProducerPrecision

type PointVector = tuple[float, ...]
type PointMatrix = tuple[tuple[float, ...], ...]
type Evaluator = Callable[[PointVector], tuple[PointVector, PointMatrix]]


@dataclass(frozen=True, slots=True)
class NewtonResult:
    """Untrusted producer result and diagnostics for one nonlinear solve."""

    center: PointVector
    residual: PointVector
    jacobian: PointMatrix
    raw_residual_inf: float
    scaled_residual_inf: float
    tolerance: float
    iterations: int
    converged: bool
    failure_code: str | None


def solve_linear_system(
    matrix: PointMatrix,
    right_hand_side: PointVector,
    precision: ProducerPrecision,
) -> PointVector:
    """Solve a small dense system in the declared untrusted precision."""

    dimension = len(right_hand_side)
    if dimension == 0 or len(matrix) != dimension:
        raise ValueError("linear system must be nonempty and square")
    if any(len(row) != dimension for row in matrix):
        raise ValueError("linear system must be square")
    arithmetic = BinaryArithmetic(precision)
    augmented = [
        [arithmetic.cast(value) for value in row]
        + [arithmetic.cast(right_hand_side[index])]
        for index, row in enumerate(matrix)
    ]
    for pivot_index in range(dimension):
        pivot_row = max(
            range(pivot_index, dimension),
            key=lambda row_index: abs(augmented[row_index][pivot_index]),
        )
        pivot = augmented[pivot_row][pivot_index]
        if pivot == 0.0 or not math.isfinite(pivot):
            raise ArithmeticError("producer Jacobian is singular")
        augmented[pivot_index], augmented[pivot_row] = (
            augmented[pivot_row],
            augmented[pivot_index],
        )
        for row_index in range(pivot_index + 1, dimension):
            factor = arithmetic.divide(
                augmented[row_index][pivot_index],
                augmented[pivot_index][pivot_index],
            )
            for column_index in range(pivot_index, dimension + 1):
                augmented[row_index][column_index] = arithmetic.subtract(
                    augmented[row_index][column_index],
                    arithmetic.multiply(factor, augmented[pivot_index][column_index]),
                )
    solution = [arithmetic.cast(0.0) for _ in range(dimension)]
    for row_index in range(dimension - 1, -1, -1):
        tail = arithmetic.sum(
            tuple(
                arithmetic.multiply(
                    augmented[row_index][column_index], solution[column_index]
                )
                for column_index in range(row_index + 1, dimension)
            )
        )
        solution[row_index] = arithmetic.divide(
            arithmetic.subtract(augmented[row_index][dimension], tail),
            augmented[row_index][row_index],
        )
    if any(not math.isfinite(value) for value in solution):
        raise ArithmeticError("producer linear solve produced a nonfinite value")
    return tuple(solution)


def _residual_norms(
    residual: PointVector,
    jacobian: PointMatrix,
    arithmetic: BinaryArithmetic,
) -> tuple[float, float]:
    raw = max(abs(value) for value in residual)
    scaled_values = []
    for value, row in zip(residual, jacobian, strict=True):
        row_scale = arithmetic.sum(tuple(abs(item) for item in row))
        denominator = max(row_scale, 1e-30)
        scaled_values.append(abs(arithmetic.divide(value, denominator)))
    return raw, max(scaled_values)


def newton_solve(
    evaluator: Evaluator,
    initial_center: PointVector,
    precision: ProducerPrecision,
    residual_tolerance: float,
    *,
    max_iterations: int = 30,
    max_backtracks: int = 12,
) -> NewtonResult:
    """Run residual-stopped, damped Newton without consulting a test reference."""

    if not initial_center:
        raise ValueError("Newton state must be nonempty")
    if residual_tolerance < 0.0 or not math.isfinite(residual_tolerance):
        raise ValueError("residual tolerance must be finite and nonnegative")
    if max_iterations < 0 or max_backtracks < 0:
        raise ValueError("iteration limits must be nonnegative")
    arithmetic = BinaryArithmetic(precision)
    center = tuple(arithmetic.cast(value) for value in initial_center)
    tolerance = arithmetic.cast(residual_tolerance)
    iterations = 0
    failure_code: str | None = None
    while True:
        try:
            residual, jacobian = evaluator(center)
            if len(residual) != len(center) or len(jacobian) != len(center):
                raise ValueError("producer evaluator dimension mismatch")
            raw_residual, scaled_residual = _residual_norms(
                residual, jacobian, arithmetic
            )
        except (ArithmeticError, OverflowError, ValueError):
            failure_code = "EVALUATION_FAILED"
            break
        if scaled_residual <= tolerance or iterations >= max_iterations:
            if scaled_residual > tolerance:
                failure_code = "MAX_ITERATIONS"
            break
        try:
            correction = solve_linear_system(
                jacobian,
                tuple(arithmetic.cast(-value) for value in residual),
                precision,
            )
        except (ArithmeticError, OverflowError, ValueError):
            failure_code = "SINGULAR_JACOBIAN"
            break
        accepted_trial: PointVector | None = None
        alpha = arithmetic.cast(1.0)
        for _ in range(max_backtracks + 1):
            trial = tuple(
                arithmetic.add(value, arithmetic.multiply(alpha, delta))
                for value, delta in zip(center, correction, strict=True)
            )
            try:
                trial_residual, trial_jacobian = evaluator(trial)
                _, trial_scaled = _residual_norms(
                    trial_residual, trial_jacobian, arithmetic
                )
            except (ArithmeticError, OverflowError, ValueError):
                trial_scaled = math.inf
            if trial_scaled < scaled_residual:
                accepted_trial = trial
                break
            alpha = arithmetic.multiply(alpha, 0.5)
        if accepted_trial is None:
            failure_code = "LINE_SEARCH_FAILED"
            break
        center = accepted_trial
        iterations += 1

    try:
        residual, jacobian = evaluator(center)
        raw_residual, scaled_residual = _residual_norms(residual, jacobian, arithmetic)
    except (ArithmeticError, OverflowError, ValueError):
        dimension = len(center)
        residual = tuple(math.nan for _ in center)
        jacobian = tuple(
            tuple(math.nan for _ in range(dimension)) for _ in range(dimension)
        )
        raw_residual = math.inf
        scaled_residual = math.inf
        failure_code = failure_code or "FINAL_EVALUATION_FAILED"
    return NewtonResult(
        center,
        residual,
        jacobian,
        raw_residual,
        scaled_residual,
        tolerance,
        iterations,
        failure_code is None and scaled_residual <= tolerance,
        failure_code,
    )
