import random
from fractions import Fraction

import pytest

from experiments.blockstamp_operator import (
    OperatorStatus,
    assemble_dense_matrix,
    dense_verified_apply,
    recursive_verified_apply,
)
from experiments.interval_backend import Interval


def _fraction_solve(
    matrix: tuple[tuple[float, ...], ...], right_hand_side: tuple[float, ...]
) -> tuple[Fraction, ...]:
    coefficients = [[Fraction.from_float(value) for value in row] for row in matrix]
    values = [Fraction.from_float(value) for value in right_hand_side]
    dimension = len(coefficients)
    for column in range(dimension):
        pivot_row = next(
            row for row in range(column, dimension) if coefficients[row][column] != 0
        )
        if pivot_row != column:
            coefficients[column], coefficients[pivot_row] = (
                coefficients[pivot_row],
                coefficients[column],
            )
            values[column], values[pivot_row] = values[pivot_row], values[column]
        pivot = coefficients[column][column]
        for row in range(column + 1, dimension):
            if coefficients[row][column] == 0:
                continue
            factor = coefficients[row][column] / pivot
            for target in range(column + 1, dimension):
                coefficients[row][target] -= factor * coefficients[column][target]
            values[row] -= factor * values[column]
            coefficients[row][column] = Fraction(0)
    solution = [Fraction(0) for _ in range(dimension)]
    for row in range(dimension - 1, -1, -1):
        residual = values[row] - sum(
            coefficients[row][column] * solution[column]
            for column in range(row + 1, dimension)
        )
        solution[row] = residual / coefficients[row][row]
    return tuple(solution)


def _case(generator: random.Random, dimension: int, slab_length: int) -> tuple:
    diagonal_blocks = []
    subdiagonal_blocks = []
    remainder_blocks = []
    for block_index in range(slab_length):
        rows = []
        for row in range(dimension):
            values = [generator.randint(-2, 2) / 4 for _ in range(dimension)]
            values[row] = sum(abs(value) for value in values) + 1.0
            rows.append(tuple(values))
        diagonal_blocks.append(tuple(rows))
        remainder_blocks.append(
            tuple(
                Interval.point(generator.randint(-16, 16) / 8) for _ in range(dimension)
            )
        )
        if block_index > 0:
            subdiagonal_blocks.append(
                tuple(
                    tuple(generator.randint(-2, 2) / 8 for _ in range(dimension))
                    for _ in range(dimension)
                )
            )
    return (
        tuple(diagonal_blocks),
        tuple(subdiagonal_blocks),
        tuple(remainder_blocks),
    )


@pytest.mark.parametrize("dimension", [1, 2, 4])
@pytest.mark.parametrize("slab_length", [2, 4])
def test_recursive_and_dense_enclosures_contain_exact_fraction_action(
    dimension: int, slab_length: int
) -> None:
    generator = random.Random(1_000 + 10 * dimension + slab_length)
    for _ in range(10):
        diagonal, subdiagonal, remainder = _case(generator, dimension, slab_length)
        dense_matrix = assemble_dense_matrix(diagonal, subdiagonal)
        exact = _fraction_solve(
            dense_matrix,
            tuple(value.lower for block in remainder for value in block),
        )
        recursive = recursive_verified_apply(diagonal, subdiagonal, remainder)
        dense = dense_verified_apply(diagonal, subdiagonal, remainder)
        assert recursive.status is OperatorStatus.OK
        assert dense.status is OperatorStatus.OK
        assert recursive.flattened() is not None
        assert dense.enclosure is not None
        for recursive_value, dense_value, exact_value in zip(
            recursive.flattened(), dense.enclosure, exact, strict=True
        ):
            exact_lower_bound = Fraction.from_float(recursive_value.lower)
            exact_upper_bound = Fraction.from_float(recursive_value.upper)
            assert exact_lower_bound <= exact_value <= exact_upper_bound
            assert Fraction.from_float(dense_value.lower) <= exact_value
            assert exact_value <= Fraction.from_float(dense_value.upper)


def test_interval_remainder_is_propagated_as_a_box() -> None:
    diagonal = (((2.0,),), ((3.0,),))
    subdiagonal = (((1.0,),),)
    remainder = ((Interval(1.0, 2.0),), (Interval(4.0, 5.0),))
    result = recursive_verified_apply(diagonal, subdiagonal, remainder)
    assert result.status is OperatorStatus.OK
    assert result.blocks is not None
    assert result.blocks[0][0].lower <= 0.5
    assert result.blocks[0][0].upper >= 1.0
    assert result.blocks[1][0].lower <= 1.0
    assert result.blocks[1][0].upper >= 1.5


def test_singular_or_malformed_block_system_fails_closed() -> None:
    singular = recursive_verified_apply((((0.0,),),), (), ((Interval.point(1.0),),))
    assert singular.status is OperatorStatus.UNSUPPORTED
    malformed = dense_verified_apply(
        (((1.0,),),), (), ((Interval.point(1.0), Interval.point(2.0)),)
    )
    assert malformed.status is OperatorStatus.UNSUPPORTED
