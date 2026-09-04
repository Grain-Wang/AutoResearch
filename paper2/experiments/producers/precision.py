"""Explicit IEEE-754 arithmetic used only by untrusted candidate producers."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from enum import StrEnum

_BINARY32 = struct.Struct("!f")


class ProducerPrecision(StrEnum):
    """Arithmetic precision of an untrusted transient producer."""

    FLOAT32 = "float32"
    FLOAT64 = "float64"

    @property
    def unit_roundoff(self) -> float:
        """Return the nominal unit roundoff of the declared binary format."""

        return 2.0**-24 if self is ProducerPrecision.FLOAT32 else 2.0**-53


@dataclass(frozen=True, slots=True)
class BinaryArithmetic:
    """Round each producer operation to binary32 or binary64."""

    precision: ProducerPrecision

    def cast(self, value: float) -> float:
        """Round one value to the declared producer format."""

        if self.precision is ProducerPrecision.FLOAT32:
            return _BINARY32.unpack(_BINARY32.pack(value))[0]
        return float(value)

    def add(self, left: float, right: float) -> float:
        """Return a rounded producer addition."""

        return self.cast(left + right)

    def subtract(self, left: float, right: float) -> float:
        """Return a rounded producer subtraction."""

        return self.cast(left - right)

    def multiply(self, left: float, right: float) -> float:
        """Return a rounded producer multiplication."""

        return self.cast(left * right)

    def divide(self, left: float, right: float) -> float:
        """Return a rounded producer division."""

        return self.cast(left / right)

    def exp(self, value: float) -> float:
        """Return a rounded producer exponential."""

        return self.cast(math.exp(value))

    def expm1(self, value: float) -> float:
        """Return a rounded producer ``exp(value) - 1``."""

        return self.cast(math.expm1(value))

    def sum(self, values: tuple[float, ...]) -> float:
        """Accumulate a tuple with a rounding after every addition."""

        total = self.cast(0.0)
        for value in values:
            total = self.add(total, value)
        return total
