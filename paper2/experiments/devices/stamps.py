"""Restricted smooth diode and Level-1 NMOS interval stamps.

Boxes crossing a Level-1 region boundary are deliberately unsupported.  This avoids
using a center-point floating branch as a purported interval Jacobian.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from experiments.interval_backend import (
    Interval,
    IntervalResult,
    IntervalStatus,
    add,
    divide,
    exp,
    multiply,
    subtract,
)


@dataclass(frozen=True, slots=True)
class DiodeParameters:
    saturation_current: float = 1e-14
    thermal_voltage: float = 0.02585


@dataclass(frozen=True, slots=True)
class DiodeStamp:
    current: Interval
    conductance: Interval


@dataclass(frozen=True, slots=True)
class MosParameters:
    beta: float = 1e-3
    threshold: float = 0.5
    channel_length_modulation: float = 0.02


class MosRegion(StrEnum):
    CUTOFF = "cutoff"
    TRIODE = "triode"
    SATURATION = "saturation"


@dataclass(frozen=True, slots=True)
class MosStamp:
    drain_current: Interval
    transconductance: Interval
    output_conductance: Interval
    region: MosRegion


def _require(result: IntervalResult) -> Interval:
    if result.status is not IntervalStatus.OK or result.interval is None:
        raise ArithmeticError(result.reason or "unsupported interval operation")
    return result.interval


def _widen_one_ulp(value: Interval) -> Interval:
    """Absorb the final rounding of an independently evaluated point stamp."""
    return Interval(
        math.nextafter(value.lower, -math.inf),
        math.nextafter(value.upper, math.inf),
    )


def diode_point(voltage: float, parameters: DiodeParameters) -> tuple[float, float]:
    exponent = voltage / parameters.thermal_voltage
    current = parameters.saturation_current * math.expm1(exponent)
    conductance = (
        parameters.saturation_current / parameters.thermal_voltage * math.exp(exponent)
    )
    return current, conductance


def diode_interval(voltage: Interval, parameters: DiodeParameters) -> DiodeStamp | None:
    if parameters.saturation_current <= 0.0 or parameters.thermal_voltage <= 0.0:
        return None
    exponent = _require(divide(voltage, Interval.point(parameters.thermal_voltage)))
    exponential = exp(exponent)
    if exponential.status is not IntervalStatus.OK or exponential.interval is None:
        return None
    shifted = _require(subtract(exponential.interval, Interval.point(1.0)))
    current = _require(multiply(Interval.point(parameters.saturation_current), shifted))
    scale = parameters.saturation_current / parameters.thermal_voltage
    conductance = _require(multiply(Interval.point(scale), exponential.interval))
    return DiodeStamp(_widen_one_ulp(current), _widen_one_ulp(conductance))


def _mos_region(vgs: Interval, vds: Interval, threshold: float) -> MosRegion | None:
    if vds.lower < 0.0:
        return None
    if vgs.upper <= threshold:
        return MosRegion.CUTOFF
    if vgs.lower > threshold and vds.upper < vgs.lower - threshold:
        return MosRegion.TRIODE
    if vgs.lower > threshold and vds.lower >= vgs.upper - threshold:
        return MosRegion.SATURATION
    return None


def mos_point(
    vgs: float, vds: float, parameters: MosParameters
) -> tuple[float, float, float, MosRegion]:
    if vds < 0.0:
        raise ValueError("the restricted NMOS semantics require nonnegative Vds")
    overdrive = vgs - parameters.threshold
    modulation = 1.0 + parameters.channel_length_modulation * vds
    if overdrive <= 0.0:
        return 0.0, 0.0, 0.0, MosRegion.CUTOFF
    if vds < overdrive:
        base = parameters.beta * (overdrive * vds - 0.5 * vds * vds)
        current = base * modulation
        transconductance = parameters.beta * vds * modulation
        output_conductance = parameters.beta * (
            (overdrive - vds) * modulation
            + (overdrive * vds - 0.5 * vds * vds) * parameters.channel_length_modulation
        )
        return current, transconductance, output_conductance, MosRegion.TRIODE
    base = 0.5 * parameters.beta * overdrive * overdrive
    current = base * modulation
    transconductance = parameters.beta * overdrive * modulation
    output_conductance = base * parameters.channel_length_modulation
    return current, transconductance, output_conductance, MosRegion.SATURATION


def mos_interval(
    vgs: Interval, vds: Interval, parameters: MosParameters
) -> MosStamp | None:
    if parameters.beta <= 0.0 or parameters.channel_length_modulation < 0.0:
        return None
    region = _mos_region(vgs, vds, parameters.threshold)
    if region is None:
        return None
    zero = Interval.point(0.0)
    if region is MosRegion.CUTOFF:
        return MosStamp(zero, zero, zero, region)

    overdrive = _require(subtract(vgs, Interval.point(parameters.threshold)))
    modulation = _require(
        add(
            Interval.point(1.0),
            _require(
                multiply(Interval.point(parameters.channel_length_modulation), vds)
            ),
        )
    )
    beta = Interval.point(parameters.beta)
    if region is MosRegion.SATURATION:
        square = _require(multiply(overdrive, overdrive))
        base = _require(multiply(Interval.point(0.5 * parameters.beta), square))
        current = _require(multiply(base, modulation))
        transconductance = _require(
            multiply(_require(multiply(beta, overdrive)), modulation)
        )
        output_conductance = _require(
            multiply(base, Interval.point(parameters.channel_length_modulation))
        )
        return MosStamp(current, transconductance, output_conductance, region)

    vds_square = _require(multiply(vds, vds))
    channel = _require(
        subtract(
            _require(multiply(overdrive, vds)),
            _require(multiply(Interval.point(0.5), vds_square)),
        )
    )
    base = _require(multiply(beta, channel))
    current = _require(multiply(base, modulation))
    transconductance = _require(multiply(_require(multiply(beta, vds)), modulation))
    slope = _require(subtract(overdrive, vds))
    first = _require(multiply(slope, modulation))
    second = _require(
        multiply(channel, Interval.point(parameters.channel_length_modulation))
    )
    output_conductance = _require(multiply(beta, _require(add(first, second))))
    return MosStamp(current, transconductance, output_conductance, region)
