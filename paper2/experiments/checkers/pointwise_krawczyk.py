"""Dense B2 pointwise Krawczyk canary.

The checker fixes ``C`` to the exact-real inverse action of the midpoint point
Jacobian ``M``.  It never accepts unless interval elimination proves ``M``
nonsingular and the resulting Krawczyk image is strictly inside the declared tube.
This auditable dense elimination path is not the verified-sparse B2-strong baseline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from experiments.blockstamp_operator import OperatorStatus, verified_solve
from experiments.interval_backend import Interval, IntervalResult, IntervalStatus
from experiments.rigorous_backend import add, multiply, subtract

type IntervalVector = tuple[Interval, ...]
type IntervalMatrix = tuple[tuple[Interval, ...], ...]


class CheckerVerdict(StrEnum):
    ACCEPT = "ACCEPT"
    UNKNOWN = "UNKNOWN"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class CheckerResult:
    verdict: CheckerVerdict
    image: IntervalVector | None
    inclusion_margin: float | None
    reason: str | None = None


class _UnsupportedArithmetic(RuntimeError):
    pass


def _require(result: IntervalResult) -> Interval:
    if result.status is not IntervalStatus.OK or result.interval is None:
        raise _UnsupportedArithmetic(result.reason or "unsupported interval operation")
    return result.interval


def _midpoint(value: Interval) -> float:
    midpoint = value.lower * 0.5 + value.upper * 0.5
    if not math.isfinite(midpoint):
        raise ValueError("Jacobian midpoint is not finite")
    return min(value.upper, max(value.lower, midpoint))


def _interval_matrix_vector_product(
    matrix: IntervalMatrix, vector: IntervalVector
) -> IntervalVector:
    if any(len(row) != len(vector) for row in matrix):
        raise ValueError("matrix/vector dimension mismatch")
    output: list[Interval] = []
    for row in matrix:
        total = Interval.point(0.0)
        for coefficient, value in zip(row, vector, strict=True):
            total = _require(add(total, _require(multiply(coefficient, value))))
        output.append(total)
    return tuple(output)


def pointwise_krawczyk(
    center: tuple[float, ...],
    tube: IntervalVector,
    residual_at_center: IntervalVector,
    jacobian_enclosure: IntervalMatrix,
) -> CheckerResult:
    """Check strict Krawczyk inclusion for one discrete time point.

    ``residual_at_center`` may itself be an interval, for example because the incoming
    state is an interface box.  The returned ``UNKNOWN`` means only that this proof
    attempt failed; it is not a proof that the tube contains no root.
    """

    dimension = len(center)
    if dimension == 0:
        return CheckerResult(
            CheckerVerdict.UNSUPPORTED, None, None, "state must be nonempty"
        )
    if len(tube) != dimension or len(residual_at_center) != dimension:
        return CheckerResult(
            CheckerVerdict.UNSUPPORTED, None, None, "vector dimension mismatch"
        )
    if len(jacobian_enclosure) != dimension or any(
        len(row) != dimension for row in jacobian_enclosure
    ):
        return CheckerResult(
            CheckerVerdict.UNSUPPORTED, None, None, "Jacobian dimension mismatch"
        )
    if any(
        not interval.lower < value < interval.upper
        for value, interval in zip(center, tube, strict=True)
    ):
        return CheckerResult(
            CheckerVerdict.UNSUPPORTED,
            None,
            None,
            "center must lie in the strict interior of the declared tube",
        )

    try:
        midpoint_matrix = tuple(
            tuple(_midpoint(value) for value in row) for row in jacobian_enclosure
        )
        centered_tube = tuple(
            _require(subtract(interval, Interval.point(value)))
            for value, interval in zip(center, tube, strict=True)
        )
        remainder_matrix: IntervalMatrix = tuple(
            tuple(
                _require(subtract(Interval.point(midpoint_matrix[row][column]), value))
                for column, value in enumerate(jacobian_row)
            )
            for row, jacobian_row in enumerate(jacobian_enclosure)
        )
        nonlinear_remainder = _interval_matrix_vector_product(
            remainder_matrix, centered_tube
        )
        right_hand_side = tuple(
            _require(subtract(nonlinear_remainder[index], residual_at_center[index]))
            for index in range(dimension)
        )
    except (ValueError, _UnsupportedArithmetic) as error:
        return CheckerResult(CheckerVerdict.UNSUPPORTED, None, None, str(error))

    solved = verified_solve(midpoint_matrix, right_hand_side)
    if solved.status is not OperatorStatus.OK or solved.enclosure is None:
        return CheckerResult(
            CheckerVerdict.UNSUPPORTED,
            None,
            None,
            f"midpoint operator is not verified nonsingular: {solved.reason}",
        )
    try:
        image = tuple(
            _require(add(Interval.point(value), correction))
            for value, correction in zip(center, solved.enclosure, strict=True)
        )
    except _UnsupportedArithmetic as error:
        return CheckerResult(CheckerVerdict.UNSUPPORTED, None, None, str(error))

    margins = tuple(
        min(candidate.lower - enclosure.lower, enclosure.upper - candidate.upper)
        for candidate, enclosure in zip(image, tube, strict=True)
    )
    margin = min(margins)
    if all(
        enclosure.lower < candidate.lower and candidate.upper < enclosure.upper
        for candidate, enclosure in zip(image, tube, strict=True)
    ):
        return CheckerResult(CheckerVerdict.ACCEPT, image, margin)
    return CheckerResult(
        CheckerVerdict.UNKNOWN,
        image,
        margin,
        "strict Krawczyk inclusion was not established",
    )
