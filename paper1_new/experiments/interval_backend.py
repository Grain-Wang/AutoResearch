"""Small auditable binary64 interval backend for the Stage-0 canary.

This module favors a transparent containment chain over speed.  Scalar operations use
exact Decimal images of binary64 inputs, then direct the final conversion outward.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum


class IntervalStatus(StrEnum):
    OK = "OK"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class IntervalResult:
    status: IntervalStatus
    interval: Interval | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Interval:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise ValueError("interval endpoints must be finite")
        if self.lower > self.upper:
            raise ValueError("interval endpoints are reversed")

    @classmethod
    def point(cls, value: float) -> Interval:
        return cls(value, value)

    def contains(self, value: float) -> bool:
        return self.lower <= value <= self.upper

    def subset_of(self, other: Interval) -> bool:
        return other.lower <= self.lower and self.upper <= other.upper

    def to_dict(self) -> dict[str, str]:
        return {"lower": self.lower.hex(), "upper": self.upper.hex()}

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> Interval:
        if set(payload) != {"lower", "upper"}:
            raise ValueError("interval payload has unknown or missing fields")
        return cls(float.fromhex(payload["lower"]), float.fromhex(payload["upper"]))


def _decimal(value: float) -> Decimal:
    return Decimal.from_float(value)


def _round_decimal(value: Decimal, direction: float) -> float:
    candidate = float(value)
    if not math.isfinite(candidate):
        raise OverflowError("finite interval endpoint overflowed binary64")
    represented = _decimal(candidate)
    if direction < 0.0 and represented > value:
        return math.nextafter(candidate, -math.inf)
    if direction > 0.0 and represented < value:
        return math.nextafter(candidate, math.inf)
    return candidate


def _binary_values(
    left: Interval, right: Interval, operator: Callable[[Decimal, Decimal], Decimal]
) -> IntervalResult:
    try:
        # Binary64 endpoints can require over 1,000 decimal digits near subnormal
        # values.  This precision makes +, -, and * exact for every finite endpoint
        # pair and leaves a very large guard for division before binary64 rounding.
        with localcontext() as context:
            context.prec = 2_500
            values = [
                operator(_decimal(x), _decimal(y))
                for x in (left.lower, left.upper)
                for y in (right.lower, right.upper)
            ]
        return IntervalResult(
            IntervalStatus.OK,
            Interval(
                _round_decimal(min(values), -math.inf),
                _round_decimal(max(values), math.inf),
            ),
        )
    except (InvalidOperation, OverflowError, ZeroDivisionError) as error:
        return IntervalResult(IntervalStatus.UNSUPPORTED, None, str(error))


def add(left: Interval, right: Interval) -> IntervalResult:
    return _binary_values(left, right, lambda x, y: x + y)


def subtract(left: Interval, right: Interval) -> IntervalResult:
    return _binary_values(left, right, lambda x, y: x - y)


def multiply(left: Interval, right: Interval) -> IntervalResult:
    return _binary_values(left, right, lambda x, y: x * y)


def divide(left: Interval, right: Interval) -> IntervalResult:
    if right.lower <= 0.0 <= right.upper:
        return IntervalResult(
            IntervalStatus.UNSUPPORTED, None, "division interval contains zero"
        )
    return _binary_values(left, right, lambda x, y: x / y)


def _monotone_unary(
    value: Interval,
    operator: Callable[[Decimal], Decimal],
    *,
    domain: Callable[[Interval], bool],
    domain_message: str,
) -> IntervalResult:
    if not domain(value):
        return IntervalResult(IntervalStatus.UNSUPPORTED, None, domain_message)
    try:
        with localcontext() as context:
            context.prec = 100
            lower = operator(_decimal(value.lower))
            upper = operator(_decimal(value.upper))
        return IntervalResult(
            IntervalStatus.OK,
            Interval(
                _round_decimal(lower, -math.inf),
                _round_decimal(upper, math.inf),
            ),
        )
    except (InvalidOperation, OverflowError) as error:
        return IntervalResult(IntervalStatus.UNSUPPORTED, None, str(error))


def exp(value: Interval) -> IntervalResult:
    return _monotone_unary(
        value,
        lambda x: x.exp(),
        domain=lambda _: True,
        domain_message="",
    )


def log(value: Interval) -> IntervalResult:
    return _monotone_unary(
        value,
        lambda x: x.ln(),
        domain=lambda x: x.lower > 0.0,
        domain_message="log requires a strictly positive interval",
    )


def sqrt(value: Interval) -> IntervalResult:
    return _monotone_unary(
        value,
        lambda x: x.sqrt(),
        domain=lambda x: x.lower >= 0.0,
        domain_message="sqrt requires a nonnegative interval",
    )
