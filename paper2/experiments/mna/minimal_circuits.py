"""Frozen programmatic circuits for correctness and mechanism probes."""

from __future__ import annotations

from experiments.devices import DiodeParameters
from experiments.mna.fixed_be import (
    Capacitor,
    Circuit,
    Diode,
    Resistor,
    VoltageSource,
)

RESISTANCE = 1_000.0
CAPACITANCE = 1e-6
SOURCE_VOLTAGE = 0.7


def rc_source_circuit(*, diode: bool = False) -> Circuit:
    """Return the frozen RC or diode-RC voltage-step circuit."""

    diodes = (Diode(1, 0, DiodeParameters()),) if diode else ()
    return Circuit(
        node_count=2,
        resistors=(Resistor(1, 2, RESISTANCE),),
        capacitors=(Capacitor(1, 0, CAPACITANCE),),
        voltage_sources=(VoltageSource(2, 0, SOURCE_VOLTAGE),),
        diodes=diodes,
    )


def rc_state(voltage: float) -> tuple[float, float, float]:
    """Return node voltages and ideal-source branch current for a root voltage."""

    source_current = -(SOURCE_VOLTAGE - voltage) / RESISTANCE
    return voltage, SOURCE_VOLTAGE, source_current
