from fractions import Fraction
from itertools import product

from experiments.blockstamp_operator import OperatorStatus
from experiments.checkers import (
    CheckerVerdict,
    check_be_step,
    dense_to_sparse,
    sparse_solve_adapter,
    sparse_verified_solve,
)
from experiments.interval_backend import Interval
from experiments.mna import rc_closed_form_next, rc_source_circuit, rc_state


def _fraction_solve(
    matrix: tuple[tuple[float, ...], ...], right_hand_side: tuple[float, ...]
) -> tuple[Fraction, ...]:
    dimension = len(matrix)
    coefficients = [[Fraction.from_float(value) for value in row] for row in matrix]
    values = [Fraction.from_float(value) for value in right_hand_side]
    for column in range(dimension):
        pivot_row = next(
            row for row in range(column, dimension) if coefficients[row][column] != 0
        )
        coefficients[column], coefficients[pivot_row] = (
            coefficients[pivot_row],
            coefficients[column],
        )
        values[column], values[pivot_row] = values[pivot_row], values[column]
        for row in range(column + 1, dimension):
            factor = coefficients[row][column] / coefficients[column][column]
            for target in range(column, dimension):
                coefficients[row][target] -= factor * coefficients[column][target]
            values[row] -= factor * values[column]
    solution = [Fraction(0) for _ in range(dimension)]
    for row in range(dimension - 1, -1, -1):
        residual = values[row] - sum(
            coefficients[row][column] * solution[column]
            for column in range(row + 1, dimension)
        )
        solution[row] = residual / coefficients[row][row]
    return tuple(solution)


def test_sparse_verified_solve_contains_exact_interval_box_action() -> None:
    matrix = (
        (4.0, -1.0, 0.0, 0.0),
        (-1.0, 4.0, -1.0, 0.0),
        (0.0, -1.0, 4.0, -1.0),
        (0.0, 0.0, -1.0, 3.0),
    )
    right_hand_side = (
        Interval(0.9, 1.1),
        Interval(1.9, 2.1),
        Interval(2.9, 3.1),
        Interval(3.9, 4.1),
    )
    result = sparse_verified_solve(dense_to_sparse(matrix), right_hand_side)
    assert result.status is OperatorStatus.OK
    assert result.enclosure is not None
    exact_vertices = [
        _fraction_solve(matrix, tuple(vertex))
        for vertex in product(
            *((value.lower, value.upper) for value in right_hand_side)
        )
    ]
    for coordinate, enclosure in enumerate(result.enclosure):
        lower = min(vertex[coordinate] for vertex in exact_vertices)
        upper = max(vertex[coordinate] for vertex in exact_vertices)
        assert Fraction.from_float(enclosure.lower) <= lower
        assert upper <= Fraction.from_float(enclosure.upper)
    assert result.input_nonzeros == 10
    assert result.verified_pivots == 4


def test_sparse_kernel_fails_closed_on_singular_matrix() -> None:
    result = sparse_verified_solve(
        ({0: 1.0, 1: 2.0}, {0: 2.0, 1: 4.0}),
        (Interval.point(1.0), Interval.point(2.0)),
    )
    assert result.status is OperatorStatus.UNSUPPORTED
    assert result.enclosure is None


def test_sparse_and_dense_b2_accept_the_same_rc_step() -> None:
    circuit = rc_source_circuit()
    previous = rc_state(0.0)
    step_size = 1e-5
    current = rc_state(rc_closed_form_next(previous[0], step_size))
    radii = (1e-9, 1e-12, 1e-12)
    tube = tuple(
        Interval(value - radius, value + radius)
        for value, radius in zip(current, radii, strict=True)
    )
    previous_box = tuple(Interval.point(value) for value in previous)
    dense = check_be_step(circuit, current, tube, previous_box, step_size)
    sparse = check_be_step(
        circuit,
        current,
        tube,
        previous_box,
        step_size,
        linear_solver=sparse_solve_adapter,
    )
    assert dense.verdict is CheckerVerdict.ACCEPT
    assert sparse.verdict is CheckerVerdict.ACCEPT
