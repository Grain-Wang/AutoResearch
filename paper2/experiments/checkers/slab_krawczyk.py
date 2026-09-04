"""Component-matched Krawczyk checks for fixed-BE time slabs.

For a candidate sequence, this module reconstructs the block-lower-bidiagonal
midpoint Jacobian and evaluates the same Krawczyk right-hand side through either a
generic dense solve or the BlockStamp temporal recurrence.  The streamed remainder
path avoids materializing ``M-[JF(X)]`` but currently consumes a globally assembled
MNA Jacobian; it is an implementation ablation, not device-stamp novelty.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from experiments.blockstamp_operator import (
    OperatorStatus,
    PointMatrix,
    dense_verified_apply,
    recursive_verified_apply,
)
from experiments.checkers.pointwise_krawczyk import (
    CheckerVerdict,
    IntervalMatrix,
    IntervalVector,
    interval_matrix_vector_product,
    interval_midpoint,
)
from experiments.interval_backend import Interval, IntervalResult, IntervalStatus
from experiments.mna import Circuit, MnaStatus, interval_be_residual_jacobian
from experiments.rigorous_backend import add, multiply, subtract


class SlabMethod(StrEnum):
    DENSE_SLAB_GENERIC = "dense_slab_generic"
    TEMPORAL_ONLY = "temporal_only"
    TEMPORAL_DEVICE_BLOCKSTAMP = "temporal_device_blockstamp"


@dataclass(frozen=True, slots=True)
class SlabProblem:
    """Frozen midpoint blocks and interval Krawczyk right-hand sides."""

    diagonal_blocks: tuple[PointMatrix, ...]
    subdiagonal_blocks: tuple[PointMatrix, ...]
    remainder_blocks: tuple[IntervalVector, ...]
    centers: tuple[tuple[float, ...], ...]
    tubes: tuple[IntervalVector, ...]
    interval_jacobian_entries: int
    streamed_remainder: bool


@dataclass(frozen=True, slots=True)
class SlabBuildResult:
    status: OperatorStatus
    problem: SlabProblem | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SlabCheckResult:
    verdict: CheckerVerdict
    image_blocks: tuple[IntervalVector, ...] | None
    inclusion_margin: float | None
    verified_pivots: int
    reason: str | None = None


class _UnsupportedArithmetic(RuntimeError):
    pass


def _require(result: IntervalResult) -> Interval:
    if result.status is not IntervalStatus.OK or result.interval is None:
        raise _UnsupportedArithmetic(result.reason or "unsupported interval operation")
    return result.interval


def _add_point_entry(
    matrix: list[list[float]], row_node: int, column_node: int, value: float
) -> None:
    if row_node != 0 and column_node != 0:
        matrix[row_node - 1][column_node - 1] += value


def be_history_jacobian(circuit: Circuit) -> PointMatrix:
    """Return the exact point derivative of restricted BE residuals by history."""

    dimension = circuit.state_dimension
    matrix = [[0.0 for _ in range(dimension)] for _ in range(dimension)]
    for capacitor in circuit.capacitors:
        value = -capacitor.capacitance
        _add_point_entry(matrix, capacitor.positive, capacitor.positive, value)
        _add_point_entry(matrix, capacitor.positive, capacitor.negative, -value)
        _add_point_entry(matrix, capacitor.negative, capacitor.positive, -value)
        _add_point_entry(matrix, capacitor.negative, capacitor.negative, value)
    return tuple(tuple(row) for row in matrix)


def _centered_tube(center: tuple[float, ...], tube: IntervalVector) -> IntervalVector:
    if len(center) != len(tube):
        raise ValueError("center/tube dimension mismatch")
    if any(
        not enclosure.lower < value < enclosure.upper
        for value, enclosure in zip(center, tube, strict=True)
    ):
        raise ValueError("every center must lie in the strict tube interior")
    return tuple(
        _require(subtract(enclosure, Interval.point(value)))
        for value, enclosure in zip(center, tube, strict=True)
    )


def _materialized_remainder(
    midpoint: PointMatrix,
    jacobian: IntervalMatrix,
    centered_tube: IntervalVector,
) -> IntervalVector:
    matrix = tuple(
        tuple(
            _require(subtract(Interval.point(midpoint[row][column]), coefficient))
            for column, coefficient in enumerate(jacobian_row)
        )
        for row, jacobian_row in enumerate(jacobian)
    )
    return interval_matrix_vector_product(matrix, centered_tube)


def _streamed_remainder(
    midpoint: PointMatrix,
    jacobian: IntervalMatrix,
    centered_tube: IntervalVector,
) -> IntervalVector:
    output: list[Interval] = []
    for row, jacobian_row in enumerate(jacobian):
        total = Interval.point(0.0)
        for column, coefficient in enumerate(jacobian_row):
            difference = _require(
                subtract(Interval.point(midpoint[row][column]), coefficient)
            )
            product = _require(multiply(difference, centered_tube[column]))
            total = _require(add(total, product))
        output.append(total)
    return tuple(output)


def build_slab_problem(
    circuit: Circuit,
    centers: tuple[tuple[float, ...], ...],
    tubes: tuple[IntervalVector, ...],
    incoming_state: IntervalVector,
    step_size: float,
    *,
    streamed_remainder: bool,
) -> SlabBuildResult:
    """Reconstruct one slab Krawczyk problem from circuit semantics."""

    if not centers or len(centers) != len(tubes):
        return SlabBuildResult(
            OperatorStatus.UNSUPPORTED,
            None,
            "a slab needs equally many nonempty centers and tubes",
        )
    dimension = circuit.state_dimension
    if len(incoming_state) != dimension or any(
        len(center) != dimension for center in centers
    ):
        return SlabBuildResult(
            OperatorStatus.UNSUPPORTED, None, "slab state dimension mismatch"
        )
    diagonal_blocks: list[PointMatrix] = []
    remainder_blocks: list[IntervalVector] = []
    try:
        for index, (center, tube) in enumerate(zip(centers, tubes, strict=True)):
            point_box = tuple(Interval.point(value) for value in center)
            previous_center = (
                incoming_state
                if index == 0
                else tuple(Interval.point(value) for value in centers[index - 1])
            )
            center_evaluation = interval_be_residual_jacobian(
                circuit, point_box, previous_center, step_size
            )
            tube_evaluation = interval_be_residual_jacobian(
                circuit,
                tube,
                incoming_state if index == 0 else tubes[index - 1],
                step_size,
            )
            if (
                center_evaluation.status is not MnaStatus.OK
                or center_evaluation.residual is None
                or tube_evaluation.status is not MnaStatus.OK
                or tube_evaluation.jacobian is None
            ):
                reason = center_evaluation.reason or tube_evaluation.reason
                return SlabBuildResult(
                    OperatorStatus.UNSUPPORTED,
                    None,
                    f"MNA slab reconstruction failed at block {index}: {reason}",
                )
            midpoint = tuple(
                tuple(interval_midpoint(value) for value in row)
                for row in tube_evaluation.jacobian
            )
            delta = _centered_tube(center, tube)
            nonlinear = (
                _streamed_remainder(midpoint, tube_evaluation.jacobian, delta)
                if streamed_remainder
                else _materialized_remainder(midpoint, tube_evaluation.jacobian, delta)
            )
            remainder = tuple(
                _require(subtract(nonlinear_value, residual))
                for nonlinear_value, residual in zip(
                    nonlinear, center_evaluation.residual, strict=True
                )
            )
            diagonal_blocks.append(midpoint)
            remainder_blocks.append(remainder)
    except (ValueError, _UnsupportedArithmetic) as error:
        return SlabBuildResult(OperatorStatus.UNSUPPORTED, None, str(error))

    history = be_history_jacobian(circuit)
    problem = SlabProblem(
        tuple(diagonal_blocks),
        tuple(history for _ in range(len(centers) - 1)),
        tuple(remainder_blocks),
        centers,
        tubes,
        len(centers) * dimension * dimension,
        streamed_remainder,
    )
    return SlabBuildResult(OperatorStatus.OK, problem)


def check_slab(problem: SlabProblem, method: SlabMethod) -> SlabCheckResult:
    """Evaluate strict slab inclusion through a selected matched organization."""

    if method is SlabMethod.DENSE_SLAB_GENERIC:
        solved = dense_verified_apply(
            problem.diagonal_blocks,
            problem.subdiagonal_blocks,
            problem.remainder_blocks,
        )
        flattened = solved.enclosure
        verified_pivots = solved.verified_pivots
        reason = solved.reason
    else:
        solved_recursive = recursive_verified_apply(
            problem.diagonal_blocks,
            problem.subdiagonal_blocks,
            problem.remainder_blocks,
        )
        flattened = solved_recursive.flattened()
        verified_pivots = solved_recursive.verified_pivots
        reason = solved_recursive.reason
        solved = solved_recursive
    if solved.status is not OperatorStatus.OK or flattened is None:
        return SlabCheckResult(
            CheckerVerdict.UNSUPPORTED,
            None,
            None,
            verified_pivots,
            reason,
        )

    dimension = len(problem.centers[0])
    corrections = tuple(
        tuple(flattened[index * dimension : (index + 1) * dimension])
        for index in range(len(problem.centers))
    )
    try:
        images = tuple(
            tuple(
                _require(add(Interval.point(value), correction))
                for value, correction in zip(center, block, strict=True)
            )
            for center, block in zip(problem.centers, corrections, strict=True)
        )
    except _UnsupportedArithmetic as error:
        return SlabCheckResult(
            CheckerVerdict.UNSUPPORTED,
            None,
            None,
            verified_pivots,
            str(error),
        )
    margins = tuple(
        min(image.lower - tube.lower, tube.upper - image.upper)
        for image_block, tube_block in zip(images, problem.tubes, strict=True)
        for image, tube in zip(image_block, tube_block, strict=True)
    )
    margin = min(margins)
    accepted = all(value > 0.0 for value in margins)
    return SlabCheckResult(
        CheckerVerdict.ACCEPT if accepted else CheckerVerdict.UNKNOWN,
        images,
        margin,
        verified_pivots,
        None if accepted else "strict slab inclusion was not established",
    )
