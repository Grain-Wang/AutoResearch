import math
import random
from decimal import Decimal, localcontext

import pytest

from experiments.interval_backend import Interval, IntervalStatus
from experiments.rigorous_backend import (
    add,
    backend_info,
    divide,
    exp,
    expm1,
    log,
    multiply,
    sqrt,
    subtract,
)

_MAX_BINARY64 = Decimal.from_float(float.fromhex("0x1.fffffffffffffp+1023"))


def _assert_decimal_containment(result, exact: Decimal) -> None:
    assert result.status is IntervalStatus.OK
    assert result.interval is not None
    assert Decimal.from_float(result.interval.lower) <= exact
    assert exact <= Decimal.from_float(result.interval.upper)


def test_backend_identity_is_available_and_versioned() -> None:
    info = backend_info()
    assert info is not None
    assert info.name == "MPFR"
    assert info.version
    assert info.precision_bits >= 128
    assert "mpfr" in info.library


@pytest.mark.parametrize(
    ("operation", "oracle"),
    [
        (add, lambda left, right: left + right),
        (subtract, lambda left, right: left - right),
        (multiply, lambda left, right: left * right),
        (divide, lambda left, right: left / right),
    ],
)
def test_directed_binary_point_operations_contain_decimal_oracle(
    operation, oracle
) -> None:
    generator = random.Random(103)
    for _ in range(2_000):
        left = math.ldexp(generator.uniform(-1.0, 1.0), generator.randint(-900, 900))
        right = math.ldexp(generator.uniform(-1.0, 1.0), generator.randint(-900, 900))
        if operation is divide and right == 0.0:
            right = math.ulp(0.0)
        with localcontext() as context:
            context.prec = 2_500
            exact = oracle(Decimal.from_float(left), Decimal.from_float(right))
        result = operation(Interval.point(left), Interval.point(right))
        if exact.copy_abs() > _MAX_BINARY64:
            assert result.status is IntervalStatus.UNSUPPORTED
        else:
            _assert_decimal_containment(result, exact)


def test_interval_multiplication_contains_all_endpoint_products() -> None:
    result = multiply(Interval(-3.0, 2.0), Interval(-5.0, 7.0))
    assert result.status is IntervalStatus.OK
    assert result.interval is not None
    for left in (-3.0, 2.0):
        for right in (-5.0, 7.0):
            assert result.interval.contains(left * right)


def test_directed_special_functions_contain_high_precision_decimal_oracle() -> None:
    generator = random.Random(107)
    with localcontext() as context:
        context.prec = 180
        for _ in range(1_000):
            value = generator.uniform(-50.0, 50.0)
            decimal_value = Decimal.from_float(value)
            _assert_decimal_containment(exp(Interval.point(value)), decimal_value.exp())
            _assert_decimal_containment(
                expm1(Interval.point(value)), decimal_value.exp() - Decimal(1)
            )
            positive = math.ldexp(
                generator.uniform(0.5, 1.0), generator.randint(-900, 900)
            )
            decimal_positive = Decimal.from_float(positive)
            _assert_decimal_containment(
                log(Interval.point(positive)), decimal_positive.ln()
            )
            _assert_decimal_containment(
                sqrt(Interval.point(positive)), decimal_positive.sqrt()
            )


def test_subnormal_near_zero_and_overflow_paths_fail_closed_or_enclose() -> None:
    minimum = math.ulp(0.0)
    with localcontext() as context:
        context.prec = 2_500
        exact_sum = Decimal.from_float(minimum) * 2
    _assert_decimal_containment(
        add(Interval.point(minimum), Interval.point(minimum)),
        exact_sum,
    )
    division = divide(Interval.point(1.0), Interval(minimum, 2 * minimum))
    assert division.status is IntervalStatus.UNSUPPORTED
    overflow = exp(Interval.point(710.0))
    assert overflow.status is IntervalStatus.UNSUPPORTED
    assert divide(Interval.point(1.0), Interval(-minimum, minimum)).status is (
        IntervalStatus.UNSUPPORTED
    )
    assert log(Interval(-1.0, 1.0)).status is IntervalStatus.UNSUPPORTED
    assert sqrt(Interval(-1.0, 1.0)).status is IntervalStatus.UNSUPPORTED
