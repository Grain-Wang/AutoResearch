"""Directed-rounded binary64 intervals backed by MPFR.

The checker uses MPFR for every elementary operation and requests the directed
rounding mode both for the high-precision operation and for the final conversion to
binary64.  A finite returned lower (upper) endpoint is therefore no greater (smaller)
than the corresponding exact-real result, subject to the declared MPFR TCB.

The older :mod:`experiments.interval_backend` remains a transparent Decimal canary.
This module is the arithmetic path used by the executable BlockStamp microkernel.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import math
from collections.abc import Callable
from dataclasses import dataclass

from experiments.interval_backend import Interval, IntervalResult, IntervalStatus

_PRECISION_BITS = 256
_RNDN = 0
_RNDU = 2
_RNDD = 3


class _MpfrStruct(ctypes.Structure):
    _fields_ = [
        ("_mpfr_prec", ctypes.c_long),
        ("_mpfr_sign", ctypes.c_int),
        ("_mpfr_exp", ctypes.c_long),
        ("_mpfr_d", ctypes.POINTER(ctypes.c_ulong)),
    ]


@dataclass(frozen=True, slots=True)
class BackendInfo:
    name: str
    version: str
    precision_bits: int
    library: str


def _load_mpfr() -> tuple[ctypes.CDLL | None, str | None, str | None]:
    library_name = ctypes.util.find_library("mpfr")
    if library_name is None:
        return None, None, "the MPFR shared library was not found"
    try:
        library = ctypes.CDLL(library_name)
    except OSError as error:
        return None, library_name, str(error)

    pointer = ctypes.POINTER(_MpfrStruct)
    library.mpfr_init2.argtypes = [pointer, ctypes.c_long]
    library.mpfr_init2.restype = None
    library.mpfr_clear.argtypes = [pointer]
    library.mpfr_clear.restype = None
    library.mpfr_set_d.argtypes = [pointer, ctypes.c_double, ctypes.c_int]
    library.mpfr_set_d.restype = ctypes.c_int
    library.mpfr_get_d.argtypes = [pointer, ctypes.c_int]
    library.mpfr_get_d.restype = ctypes.c_double
    for function_name in ("add", "sub", "mul", "div"):
        function = getattr(library, f"mpfr_{function_name}")
        function.argtypes = [pointer, pointer, pointer, ctypes.c_int]
        function.restype = ctypes.c_int
    for function_name in ("exp", "expm1", "log", "sqrt"):
        function = getattr(library, f"mpfr_{function_name}")
        function.argtypes = [pointer, pointer, ctypes.c_int]
        function.restype = ctypes.c_int
    library.mpfr_get_version.argtypes = []
    library.mpfr_get_version.restype = ctypes.c_char_p
    return library, library_name, None


_MPFR, _MPFR_LIBRARY, _MPFR_ERROR = _load_mpfr()


def backend_info() -> BackendInfo | None:
    """Return the loaded MPFR identity, or ``None`` when it is unavailable."""

    if _MPFR is None or _MPFR_LIBRARY is None:
        return None
    raw_version = _MPFR.mpfr_get_version()
    version = raw_version.decode("ascii") if raw_version is not None else "unknown"
    return BackendInfo("MPFR", version, _PRECISION_BITS, _MPFR_LIBRARY)


def _unsupported(reason: str) -> IntervalResult:
    return IntervalResult(IntervalStatus.UNSUPPORTED, None, reason)


def _mpfr_error() -> str | None:
    if _MPFR is not None:
        return None
    return _MPFR_ERROR or "MPFR is unavailable"


def _binary_scalar(
    left: float, right: float, function_name: str, rounding: int
) -> float:
    if _MPFR is None:
        raise RuntimeError(_mpfr_error())
    left_value = _MpfrStruct()
    right_value = _MpfrStruct()
    output_value = _MpfrStruct()
    values = (left_value, right_value, output_value)
    initialized = 0
    try:
        for value in values:
            _MPFR.mpfr_init2(ctypes.byref(value), _PRECISION_BITS)
            initialized += 1
        _MPFR.mpfr_set_d(ctypes.byref(left_value), left, _RNDN)
        _MPFR.mpfr_set_d(ctypes.byref(right_value), right, _RNDN)
        operation = getattr(_MPFR, f"mpfr_{function_name}")
        operation(
            ctypes.byref(output_value),
            ctypes.byref(left_value),
            ctypes.byref(right_value),
            rounding,
        )
        return float(_MPFR.mpfr_get_d(ctypes.byref(output_value), rounding))
    finally:
        for value in reversed(values[:initialized]):
            _MPFR.mpfr_clear(ctypes.byref(value))


def _unary_scalar(value: float, function_name: str, rounding: int) -> float:
    if _MPFR is None:
        raise RuntimeError(_mpfr_error())
    input_value = _MpfrStruct()
    output_value = _MpfrStruct()
    values = (input_value, output_value)
    initialized = 0
    try:
        for item in values:
            _MPFR.mpfr_init2(ctypes.byref(item), _PRECISION_BITS)
            initialized += 1
        _MPFR.mpfr_set_d(ctypes.byref(input_value), value, _RNDN)
        operation = getattr(_MPFR, f"mpfr_{function_name}")
        operation(ctypes.byref(output_value), ctypes.byref(input_value), rounding)
        return float(_MPFR.mpfr_get_d(ctypes.byref(output_value), rounding))
    finally:
        for item in reversed(values[:initialized]):
            _MPFR.mpfr_clear(ctypes.byref(item))


def _finite_interval(lower: float, upper: float) -> IntervalResult:
    if math.isnan(lower) or math.isnan(upper):
        return _unsupported("MPFR operation produced NaN")
    if not math.isfinite(lower) or not math.isfinite(upper):
        return _unsupported("exact result is outside the finite binary64 range")
    return IntervalResult(IntervalStatus.OK, Interval(lower, upper))


def _run_binary(
    candidates: tuple[tuple[float, float], ...], function_name: str
) -> IntervalResult:
    error = _mpfr_error()
    if error is not None:
        return _unsupported(error)
    unique_candidates = tuple(dict.fromkeys(candidates))
    try:
        lower = min(
            _binary_scalar(left, right, function_name, _RNDD)
            for left, right in unique_candidates
        )
        upper = max(
            _binary_scalar(left, right, function_name, _RNDU)
            for left, right in unique_candidates
        )
    except (RuntimeError, ValueError) as caught:
        return _unsupported(str(caught))
    return _finite_interval(lower, upper)


def add(left: Interval, right: Interval) -> IntervalResult:
    """Return an outward-rounded enclosure of ``left + right``."""

    return _run_binary(((left.lower, right.lower), (left.upper, right.upper)), "add")


def subtract(left: Interval, right: Interval) -> IntervalResult:
    """Return an outward-rounded enclosure of ``left - right``."""

    return _run_binary(((left.lower, right.upper), (left.upper, right.lower)), "sub")


def multiply(left: Interval, right: Interval) -> IntervalResult:
    """Return an outward-rounded enclosure of ``left * right``."""

    candidates = tuple(
        (left_value, right_value)
        for left_value in (left.lower, left.upper)
        for right_value in (right.lower, right.upper)
    )
    return _run_binary(candidates, "mul")


def divide(left: Interval, right: Interval) -> IntervalResult:
    """Return an enclosure of ``left / right`` or fail closed across zero."""

    if right.lower <= 0.0 <= right.upper:
        return _unsupported("division interval contains zero")
    candidates = tuple(
        (left_value, right_value)
        for left_value in (left.lower, left.upper)
        for right_value in (right.lower, right.upper)
    )
    return _run_binary(candidates, "div")


def _monotone_unary(
    value: Interval,
    function_name: str,
    domain: Callable[[Interval], bool],
    domain_message: str,
) -> IntervalResult:
    if not domain(value):
        return _unsupported(domain_message)
    error = _mpfr_error()
    if error is not None:
        return _unsupported(error)
    try:
        lower = _unary_scalar(value.lower, function_name, _RNDD)
        upper = _unary_scalar(value.upper, function_name, _RNDU)
    except (RuntimeError, ValueError) as caught:
        return _unsupported(str(caught))
    return _finite_interval(lower, upper)


def exp(value: Interval) -> IntervalResult:
    """Return an outward-rounded enclosure of the exponential."""

    return _monotone_unary(value, "exp", lambda _: True, "")


def expm1(value: Interval) -> IntervalResult:
    """Return an outward-rounded enclosure of ``exp(value) - 1``."""

    return _monotone_unary(value, "expm1", lambda _: True, "")


def log(value: Interval) -> IntervalResult:
    """Return an enclosure of the natural logarithm on a positive interval."""

    return _monotone_unary(
        value,
        "log",
        lambda item: item.lower > 0.0,
        "log requires a strictly positive interval",
    )


def sqrt(value: Interval) -> IntervalResult:
    """Return an enclosure of the square root on a nonnegative interval."""

    return _monotone_unary(
        value,
        "sqrt",
        lambda item: item.lower >= 0.0,
        "sqrt requires a nonnegative interval",
    )
