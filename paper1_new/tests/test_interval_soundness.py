import json
import math
import random
from decimal import Decimal, localcontext

import pytest

from experiments.interval_backend import (
    Interval,
    IntervalStatus,
    add,
    divide,
    exp,
    log,
    multiply,
    sqrt,
    subtract,
)


def _assert_contains(result, oracle: Decimal) -> None:
    assert result.status is IntervalStatus.OK
    assert result.interval is not None
    assert Decimal.from_float(result.interval.lower) <= oracle
    assert oracle <= Decimal.from_float(result.interval.upper)


@pytest.mark.parametrize(
    ("operation", "oracle"),
    [
        (add, lambda x, y: x + y),
        (subtract, lambda x, y: x - y),
        (multiply, lambda x, y: x * y),
        (divide, lambda x, y: x / y),
    ],
)
def test_binary_point_containment(operation, oracle) -> None:
    generator = random.Random(17)
    for _ in range(10_000):
        left = generator.uniform(-1e100, 1e100)
        right = generator.uniform(-1e100, 1e100)
        if operation is divide and abs(right) < 1e-200:
            right = 1.0
        with localcontext() as context:
            context.prec = 2_500
            exact = oracle(Decimal.from_float(left), Decimal.from_float(right))
        _assert_contains(operation(Interval.point(left), Interval.point(right)), exact)


@pytest.mark.parametrize(
    "value",
    [0.0, math.ulp(0.0), -math.ulp(0.0), 1.0, -1.0, 1e-300, 1e300],
)
def test_boundary_arithmetic(value: float) -> None:
    with localcontext() as context:
        context.prec = 2_500
        exact = Decimal.from_float(value) + Decimal.from_float(math.ulp(0.0))
    _assert_contains(add(Interval.point(value), Interval.point(math.ulp(0.0))), exact)


def test_transcendental_point_containment() -> None:
    generator = random.Random(29)
    with localcontext() as context:
        context.prec = 90
        for _ in range(10_000):
            value = generator.uniform(-50.0, 50.0)
            decimal_value = Decimal.from_float(value)
            _assert_contains(exp(Interval.point(value)), decimal_value.exp())
            positive = abs(value) + 1e-12
            decimal_positive = Decimal.from_float(positive)
            _assert_contains(log(Interval.point(positive)), decimal_positive.ln())
            _assert_contains(sqrt(Interval.point(positive)), decimal_positive.sqrt())


def test_unsupported_domains_are_structured() -> None:
    division = divide(Interval.point(1.0), Interval(-1.0, 1.0))
    assert division.status is IntervalStatus.UNSUPPORTED
    assert log(Interval(-1.0, 1.0)).status is IntervalStatus.UNSUPPORTED
    assert sqrt(Interval(-1.0, 1.0)).status is IntervalStatus.UNSUPPORTED


def test_hex_serialization_round_trip() -> None:
    original = Interval(-math.ulp(0.0), math.nextafter(1.0, math.inf))
    encoded = json.loads(json.dumps(original.to_dict(), sort_keys=True))
    assert Interval.from_dict(encoded) == original
