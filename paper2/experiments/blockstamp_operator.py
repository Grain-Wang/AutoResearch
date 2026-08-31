"""Verified block-lower-bidiagonal operator microkernel.

For a checker-side point matrix ``M`` with diagonal blocks ``D_k`` and first
subdiagonal blocks ``L_k``, this module evaluates ``M^{-1} R`` without forming an
inverse:

``U_0 = VSolve(D_0, R_0)``
``U_k = VSolve(D_k, R_k - L_k U_{k-1})``.

``VSolve`` performs outward-rounded interval Gaussian elimination.  Acceptance of a
solve requires every verified pivot interval to exclude zero; this both fails closed
on an inconclusive factorization and proves nonsingularity of the exact point matrix
represented by the binary64 entries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from experiments.interval_backend import Interval, IntervalResult, IntervalStatus
from experiments.rigorous_backend import add, divide, multiply, subtract

type PointMatrix = tuple[tuple[float, ...], ...]
type IntervalVector = tuple[Interval, ...]


class OperatorStatus(StrEnum):
    OK = "OK"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class VerifiedSolveResult:
    status: OperatorStatus
    enclosure: IntervalVector | None
    verified_pivots: int
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class OperatorApplyResult:
    status: OperatorStatus
    blocks: tuple[IntervalVector, ...] | None
    verified_pivots: int
    reason: str | None = None

    def flattened(self) -> IntervalVector | None:
        """Return block enclosures in time-major order."""

        if self.blocks is None:
            return None
        return tuple(value for block in self.blocks for value in block)


class _UnsupportedArithmetic(RuntimeError):
    pass


def _require(result: IntervalResult) -> Interval:
    if result.status is not IntervalStatus.OK or result.interval is None:
        raise _UnsupportedArithmetic(result.reason or "unsupported interval operation")
    return result.interval


def _validate_square(matrix: PointMatrix) -> int:
    dimension = len(matrix)
    if dimension == 0:
        raise ValueError("matrix must be nonempty")
    if any(len(row) != dimension for row in matrix):
        raise ValueError("matrix must be square")
    if any(not math.isfinite(value) for row in matrix for value in row):
        raise ValueError("matrix entries must be finite")
    return dimension


def _pivot_strength(value: Interval) -> float:
    if value.lower <= 0.0 <= value.upper:
        return 0.0
    return min(abs(value.lower), abs(value.upper))


def verified_solve(
    matrix: PointMatrix, right_hand_side: IntervalVector
) -> VerifiedSolveResult:
    """Enclose the exact solve of a binary64 point matrix and interval RHS.

    A result with status ``OK`` is also a machine-checked nonsingularity witness for
    ``matrix``: interval elimination enclosed each exact elimination pivot and proved
    that every one excludes zero.
    """

    try:
        dimension = _validate_square(matrix)
    except ValueError as error:
        return VerifiedSolveResult(OperatorStatus.UNSUPPORTED, None, 0, str(error))
    if len(right_hand_side) != dimension:
        return VerifiedSolveResult(
            OperatorStatus.UNSUPPORTED,
            None,
            0,
            "right-hand side dimension does not match the matrix",
        )

    coefficients = [[Interval.point(value) for value in row] for row in matrix]
    values = list(right_hand_side)
    verified_pivots = 0
    try:
        for column in range(dimension):
            pivot_row = max(
                range(column, dimension),
                key=lambda row: _pivot_strength(coefficients[row][column]),
            )
            pivot = coefficients[pivot_row][column]
            if _pivot_strength(pivot) == 0.0:
                return VerifiedSolveResult(
                    OperatorStatus.UNSUPPORTED,
                    None,
                    verified_pivots,
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
            for row in range(column + 1, dimension):
                factor = _require(divide(coefficients[row][column], pivot))
                for target_column in range(column + 1, dimension):
                    product = _require(
                        multiply(factor, coefficients[column][target_column])
                    )
                    coefficients[row][target_column] = _require(
                        subtract(coefficients[row][target_column], product)
                    )
                values[row] = _require(
                    subtract(values[row], _require(multiply(factor, values[column])))
                )
                coefficients[row][column] = Interval.point(0.0)

        solution = [Interval.point(0.0) for _ in range(dimension)]
        for row in range(dimension - 1, -1, -1):
            residual = values[row]
            for column in range(row + 1, dimension):
                residual = _require(
                    subtract(
                        residual,
                        _require(multiply(coefficients[row][column], solution[column])),
                    )
                )
            pivot = coefficients[row][row]
            if _pivot_strength(pivot) == 0.0:
                return VerifiedSolveResult(
                    OperatorStatus.UNSUPPORTED,
                    None,
                    verified_pivots,
                    f"back-substitution pivot contains zero at row {row}",
                )
            solution[row] = _require(divide(residual, pivot))
    except _UnsupportedArithmetic as error:
        return VerifiedSolveResult(
            OperatorStatus.UNSUPPORTED,
            None,
            verified_pivots,
            str(error),
        )
    return VerifiedSolveResult(OperatorStatus.OK, tuple(solution), verified_pivots)


def point_matrix_interval_vector_product(
    matrix: PointMatrix, vector: IntervalVector
) -> IntervalVector:
    """Multiply a point matrix by an interval vector with outward rounding."""

    if not matrix:
        raise ValueError("matrix must be nonempty")
    if any(len(row) != len(vector) for row in matrix):
        raise ValueError("matrix/vector dimensions do not match")
    output: list[Interval] = []
    for row in matrix:
        total = Interval.point(0.0)
        for coefficient, value in zip(row, vector, strict=True):
            total = _require(
                add(
                    total,
                    _require(multiply(Interval.point(coefficient), value)),
                )
            )
        output.append(total)
    return tuple(output)


def _subtract_vectors(left: IntervalVector, right: IntervalVector) -> IntervalVector:
    if len(left) != len(right):
        raise ValueError("vector dimensions do not match")
    return tuple(
        _require(subtract(left_value, right_value))
        for left_value, right_value in zip(left, right, strict=True)
    )


def recursive_verified_apply(
    diagonal_blocks: tuple[PointMatrix, ...],
    subdiagonal_blocks: tuple[PointMatrix, ...],
    remainder_blocks: tuple[IntervalVector, ...],
) -> OperatorApplyResult:
    """Apply the BlockStamp verified recurrence to ``M^{-1} R``."""

    slab_length = len(diagonal_blocks)
    if slab_length == 0:
        return OperatorApplyResult(
            OperatorStatus.UNSUPPORTED, None, 0, "slab must contain at least one block"
        )
    if len(subdiagonal_blocks) != slab_length - 1:
        return OperatorApplyResult(
            OperatorStatus.UNSUPPORTED,
            None,
            0,
            "a slab with k blocks requires k-1 subdiagonal blocks",
        )
    if len(remainder_blocks) != slab_length:
        return OperatorApplyResult(
            OperatorStatus.UNSUPPORTED,
            None,
            0,
            "remainder block count does not match the slab",
        )

    try:
        dimension = _validate_square(diagonal_blocks[0])
        for diagonal in diagonal_blocks:
            if _validate_square(diagonal) != dimension:
                raise ValueError("all diagonal blocks must have one dimension")
        for subdiagonal in subdiagonal_blocks:
            if len(subdiagonal) != dimension or any(
                len(row) != dimension for row in subdiagonal
            ):
                raise ValueError("subdiagonal block dimension mismatch")
            if any(not math.isfinite(value) for row in subdiagonal for value in row):
                raise ValueError("subdiagonal entries must be finite")
        if any(len(block) != dimension for block in remainder_blocks):
            raise ValueError("remainder block dimension mismatch")
    except ValueError as error:
        return OperatorApplyResult(OperatorStatus.UNSUPPORTED, None, 0, str(error))

    output: list[IntervalVector] = []
    verified_pivots = 0
    for block_index in range(slab_length):
        right_hand_side = remainder_blocks[block_index]
        if block_index > 0:
            try:
                coupling = point_matrix_interval_vector_product(
                    subdiagonal_blocks[block_index - 1], output[-1]
                )
                right_hand_side = _subtract_vectors(right_hand_side, coupling)
            except (ValueError, _UnsupportedArithmetic) as error:
                return OperatorApplyResult(
                    OperatorStatus.UNSUPPORTED,
                    None,
                    verified_pivots,
                    f"block {block_index} coupling failed: {error}",
                )
        solved = verified_solve(diagonal_blocks[block_index], right_hand_side)
        verified_pivots += solved.verified_pivots
        if solved.status is not OperatorStatus.OK or solved.enclosure is None:
            return OperatorApplyResult(
                OperatorStatus.UNSUPPORTED,
                None,
                verified_pivots,
                f"block {block_index} solve failed: {solved.reason}",
            )
        output.append(solved.enclosure)
    return OperatorApplyResult(OperatorStatus.OK, tuple(output), verified_pivots)


def assemble_dense_matrix(
    diagonal_blocks: tuple[PointMatrix, ...],
    subdiagonal_blocks: tuple[PointMatrix, ...],
) -> PointMatrix:
    """Materialize the dense block-lower-bidiagonal point matrix."""

    if not diagonal_blocks:
        raise ValueError("slab must contain at least one block")
    dimension = _validate_square(diagonal_blocks[0])
    if len(subdiagonal_blocks) != len(diagonal_blocks) - 1:
        raise ValueError("subdiagonal block count mismatch")
    size = dimension * len(diagonal_blocks)
    dense = [[0.0 for _ in range(size)] for _ in range(size)]
    for block_index, diagonal in enumerate(diagonal_blocks):
        if _validate_square(diagonal) != dimension:
            raise ValueError("diagonal block dimension mismatch")
        offset = block_index * dimension
        for row in range(dimension):
            for column in range(dimension):
                dense[offset + row][offset + column] = diagonal[row][column]
        if block_index == 0:
            continue
        subdiagonal = subdiagonal_blocks[block_index - 1]
        if len(subdiagonal) != dimension or any(
            len(row) != dimension for row in subdiagonal
        ):
            raise ValueError("subdiagonal block dimension mismatch")
        previous_offset = offset - dimension
        for row in range(dimension):
            for column in range(dimension):
                dense[offset + row][previous_offset + column] = subdiagonal[row][column]
    return tuple(tuple(row) for row in dense)


def dense_verified_apply(
    diagonal_blocks: tuple[PointMatrix, ...],
    subdiagonal_blocks: tuple[PointMatrix, ...],
    remainder_blocks: tuple[IntervalVector, ...],
) -> VerifiedSolveResult:
    """Component-matched dense-slab baseline for ``M^{-1} R``."""

    if not diagonal_blocks:
        return VerifiedSolveResult(
            OperatorStatus.UNSUPPORTED, None, 0, "slab must contain at least one block"
        )
    if len(remainder_blocks) != len(diagonal_blocks):
        return VerifiedSolveResult(
            OperatorStatus.UNSUPPORTED,
            None,
            0,
            "remainder block count does not match the slab",
        )
    try:
        dimension = _validate_square(diagonal_blocks[0])
        if any(len(block) != dimension for block in remainder_blocks):
            raise ValueError("remainder block dimension mismatch")
        dense = assemble_dense_matrix(diagonal_blocks, subdiagonal_blocks)
    except ValueError as error:
        return VerifiedSolveResult(OperatorStatus.UNSUPPORTED, None, 0, str(error))
    flattened = tuple(value for block in remainder_blocks for value in block)
    return verified_solve(dense, flattened)
