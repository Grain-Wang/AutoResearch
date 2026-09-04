"""Auditable verified sparse solve for the B2-strong baseline.

The kernel stores a point matrix as sparse rows and performs outward-rounded
interval Gaussian elimination with partial pivoting.  It deliberately retains all
interval fill-in: sparsity changes storage and traversal only, never the arithmetic
contract.  An ``OK`` result therefore certifies every elimination pivot away from
zero and encloses the exact-real solve of the declared binary64 matrix for every
right-hand side in the supplied interval box.

This is a correctness-oriented sparse baseline, not a claim of a state-of-the-art
high-performance sparse factorization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from experiments.blockstamp_operator import (
    OperatorStatus,
    PointMatrix,
    VerifiedSolveResult,
)
from experiments.interval_backend import Interval, IntervalResult, IntervalStatus
from experiments.rigorous_backend import divide, multiply, subtract

type IntervalVector = tuple[Interval, ...]
type SparsePointRow = dict[int, float]
type SparsePointMatrix = tuple[SparsePointRow, ...]


@dataclass(frozen=True, slots=True)
class VerifiedSparseSolveResult:
    """Verified solution and sparse-factor diagnostics."""

    status: OperatorStatus
    enclosure: IntervalVector | None
    verified_pivots: int
    input_nonzeros: int
    factor_nonzeros: int
    fill_in_nonzeros: int
    reason: str | None = None

    def as_dense_result(self) -> VerifiedSolveResult:
        """Return the common solve contract used by Krawczyk evaluation."""

        return VerifiedSolveResult(
            self.status,
            self.enclosure,
            self.verified_pivots,
            self.reason,
        )


class _UnsupportedArithmetic(RuntimeError):
    pass


def _require(result: IntervalResult) -> Interval:
    if result.status is not IntervalStatus.OK or result.interval is None:
        raise _UnsupportedArithmetic(result.reason or "unsupported interval operation")
    return result.interval


def _pivot_strength(value: Interval | None) -> float:
    if value is None or value.lower <= 0.0 <= value.upper:
        return 0.0
    return min(abs(value.lower), abs(value.upper))


def dense_to_sparse(matrix: PointMatrix) -> SparsePointMatrix:
    """Convert a finite square point matrix to canonical sparse rows."""

    dimension = len(matrix)
    if dimension == 0 or any(len(row) != dimension for row in matrix):
        raise ValueError("matrix must be nonempty and square")
    if any(not math.isfinite(value) for row in matrix for value in row):
        raise ValueError("matrix entries must be finite")
    return tuple(
        {column: value for column, value in enumerate(row) if value != 0.0}
        for row in matrix
    )


def sparse_verified_solve(
    matrix: SparsePointMatrix, right_hand_side: IntervalVector
) -> VerifiedSparseSolveResult:
    """Enclose a sparse binary64 point-matrix solve with verified pivots."""

    dimension = len(matrix)
    input_nonzeros = sum(len(row) for row in matrix)
    if dimension == 0:
        return VerifiedSparseSolveResult(
            OperatorStatus.UNSUPPORTED,
            None,
            0,
            input_nonzeros,
            input_nonzeros,
            0,
            "matrix must be nonempty",
        )
    if len(right_hand_side) != dimension:
        return VerifiedSparseSolveResult(
            OperatorStatus.UNSUPPORTED,
            None,
            0,
            input_nonzeros,
            input_nonzeros,
            0,
            "right-hand side dimension does not match the matrix",
        )
    if any(
        column < 0 or column >= dimension or not math.isfinite(value) or value == 0.0
        for row in matrix
        for column, value in row.items()
    ):
        return VerifiedSparseSolveResult(
            OperatorStatus.UNSUPPORTED,
            None,
            0,
            input_nonzeros,
            input_nonzeros,
            0,
            "sparse rows contain an invalid column or coefficient",
        )

    coefficients = [
        {column: Interval.point(value) for column, value in row.items()}
        for row in matrix
    ]
    values = list(right_hand_side)
    verified_pivots = 0
    elimination_multipliers = 0
    fill_in_nonzeros = 0
    try:
        for column in range(dimension):
            pivot_row = max(
                range(column, dimension),
                key=lambda row: _pivot_strength(coefficients[row].get(column)),
            )
            pivot = coefficients[pivot_row].get(column)
            if _pivot_strength(pivot) == 0.0:
                factor_nonzeros = sum(len(row) for row in coefficients)
                factor_nonzeros += elimination_multipliers
                return VerifiedSparseSolveResult(
                    OperatorStatus.UNSUPPORTED,
                    None,
                    verified_pivots,
                    input_nonzeros,
                    factor_nonzeros,
                    fill_in_nonzeros,
                    f"pivot interval contains zero at column {column}",
                )
            if pivot_row != column:
                coefficients[column], coefficients[pivot_row] = (
                    coefficients[pivot_row],
                    coefficients[column],
                )
                values[column], values[pivot_row] = values[pivot_row], values[column]
            pivot = coefficients[column][column]
            verified_pivots += 1
            pivot_targets = tuple(
                (target_column, coefficient)
                for target_column, coefficient in coefficients[column].items()
                if target_column > column
            )
            for row in range(column + 1, dimension):
                leading = coefficients[row].get(column)
                if leading is None:
                    continue
                factor = _require(divide(leading, pivot))
                elimination_multipliers += 1
                coefficients[row].pop(column)
                for target_column, pivot_coefficient in pivot_targets:
                    product = _require(multiply(factor, pivot_coefficient))
                    if target_column not in coefficients[row]:
                        fill_in_nonzeros += 1
                    current = coefficients[row].get(target_column, Interval.point(0.0))
                    coefficients[row][target_column] = _require(
                        subtract(current, product)
                    )
                values[row] = _require(
                    subtract(values[row], _require(multiply(factor, values[column])))
                )

        solution = [Interval.point(0.0) for _ in range(dimension)]
        for row in range(dimension - 1, -1, -1):
            residual = values[row]
            for column, coefficient in coefficients[row].items():
                if column > row:
                    residual = _require(
                        subtract(
                            residual,
                            _require(multiply(coefficient, solution[column])),
                        )
                    )
            pivot = coefficients[row].get(row)
            if _pivot_strength(pivot) == 0.0:
                factor_nonzeros = sum(len(item) for item in coefficients)
                factor_nonzeros += elimination_multipliers
                return VerifiedSparseSolveResult(
                    OperatorStatus.UNSUPPORTED,
                    None,
                    verified_pivots,
                    input_nonzeros,
                    factor_nonzeros,
                    fill_in_nonzeros,
                    f"back-substitution pivot contains zero at row {row}",
                )
            solution[row] = _require(divide(residual, pivot))
    except _UnsupportedArithmetic as error:
        factor_nonzeros = sum(len(row) for row in coefficients)
        factor_nonzeros += elimination_multipliers
        return VerifiedSparseSolveResult(
            OperatorStatus.UNSUPPORTED,
            None,
            verified_pivots,
            input_nonzeros,
            factor_nonzeros,
            fill_in_nonzeros,
            str(error),
        )

    factor_nonzeros = sum(len(row) for row in coefficients)
    factor_nonzeros += elimination_multipliers
    return VerifiedSparseSolveResult(
        OperatorStatus.OK,
        tuple(solution),
        verified_pivots,
        input_nonzeros,
        factor_nonzeros,
        fill_in_nonzeros,
    )


def sparse_solve_adapter(
    matrix: PointMatrix, right_hand_side: IntervalVector
) -> VerifiedSolveResult:
    """Use the sparse kernel through the common Krawczyk solver contract."""

    try:
        sparse = dense_to_sparse(matrix)
    except ValueError as error:
        return VerifiedSolveResult(OperatorStatus.UNSUPPORTED, None, 0, str(error))
    return sparse_verified_solve(sparse, right_hand_side).as_dense_result()
