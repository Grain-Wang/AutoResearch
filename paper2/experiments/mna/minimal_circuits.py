"""Frozen programmatic circuits for correctness and mechanism probes."""

from __future__ import annotations

from dataclasses import dataclass

from experiments.devices import DiodeParameters, SmoothNmosParameters
from experiments.mna.fixed_be import (
    Capacitor,
    Circuit,
    Diode,
    Resistor,
    SmoothNmos,
    VoltageSource,
)

RESISTANCE = 1_000.0
CAPACITANCE = 1e-6
SOURCE_VOLTAGE = 0.7
RING_SUPPLY_VOLTAGE = 1.2


@dataclass(frozen=True, slots=True)
class RingInstance:
    """Frozen load, integration, and initial-state parameters for one ring."""

    name: str
    load_resistance: float
    load_capacitance: float
    step_size: float
    initial_voltages: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class DiodeRcInstance:
    """Frozen nonlinear RC load, source, time step, and initial voltage."""

    name: str
    resistance: float
    capacitance: float
    source_voltage: float
    initial_voltage: float
    step_size: float


RING_INSTANCES = (
    RingInstance("balanced", 10_000.0, 20e-12, 2e-9, (0.05, 0.60, 1.15)),
    RingInstance("light_load", 8_000.0, 15e-12, 1.5e-9, (0.10, 0.20, 1.10)),
    RingInstance("slow_load", 15_000.0, 25e-12, 2.5e-9, (0.02, 0.90, 0.40)),
)

DIODE_RC_INSTANCES = (
    DiodeRcInstance("nominal", 1_000.0, 1e-6, 0.70, 0.00, 1e-5),
    DiodeRcInstance("fast_load", 680.0, 0.8e-6, 0.65, 0.05, 8e-6),
    DiodeRcInstance("slow_hot_start", 2_200.0, 1.5e-6, 0.75, 0.20, 1.2e-5),
)


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


def diode_rc_circuit(instance: DiodeRcInstance) -> Circuit:
    """Return a diode-RC circuit from one frozen nonlinear workload profile."""

    return Circuit(
        node_count=2,
        resistors=(Resistor(1, 2, instance.resistance),),
        capacitors=(Capacitor(1, 0, instance.capacitance),),
        voltage_sources=(VoltageSource(2, 0, instance.source_voltage),),
        diodes=(Diode(1, 0, DiodeParameters()),),
    )


def diode_rc_state(
    voltage: float, instance: DiodeRcInstance
) -> tuple[float, float, float]:
    """Complete a diode-RC voltage with its source node and branch current."""

    source_current = -(instance.source_voltage - voltage) / instance.resistance
    return voltage, instance.source_voltage, source_current


def nmos_ring_3stage(instance: RingInstance) -> Circuit:
    """Return the executable three-stage smooth-NMOS ring benchmark."""

    supply_node = 4
    parameters = SmoothNmosParameters()
    return Circuit(
        node_count=4,
        resistors=tuple(
            Resistor(node, supply_node, instance.load_resistance) for node in (1, 2, 3)
        ),
        capacitors=tuple(
            Capacitor(node, 0, instance.load_capacitance) for node in (1, 2, 3)
        ),
        voltage_sources=(VoltageSource(supply_node, 0, RING_SUPPLY_VOLTAGE),),
        smooth_nmos=(
            SmoothNmos(1, 3, 0, parameters),
            SmoothNmos(2, 1, 0, parameters),
            SmoothNmos(3, 2, 0, parameters),
        ),
    )


def ring_state(
    voltages: tuple[float, float, float], load_resistance: float
) -> tuple[float, float, float, float, float]:
    """Complete a ring voltage triple with supply voltage and branch current."""

    source_current = -sum(
        (RING_SUPPLY_VOLTAGE - voltage) / load_resistance for voltage in voltages
    )
    return *voltages, RING_SUPPLY_VOLTAGE, source_current


def ring_initial_state(instance: RingInstance) -> tuple[float, ...]:
    """Return the complete frozen initial MNA state for one ring instance."""

    return ring_state(instance.initial_voltages, instance.load_resistance)


def transient_workload(
    circuit_id: str, instance_name: str
) -> tuple[Circuit, tuple[float, ...], float]:
    """Resolve one registered transient workload and its initial state."""

    if circuit_id == "diode_rc":
        try:
            instance = next(
                item for item in DIODE_RC_INSTANCES if item.name == instance_name
            )
        except StopIteration as error:
            raise ValueError(f"unknown diode-RC instance: {instance_name}") from error
        return (
            diode_rc_circuit(instance),
            diode_rc_state(instance.initial_voltage, instance),
            instance.step_size,
        )
    if circuit_id == "nmos_ring_3stage":
        try:
            ring_instance = next(
                item for item in RING_INSTANCES if item.name == instance_name
            )
        except StopIteration as error:
            raise ValueError(f"unknown ring instance: {instance_name}") from error
        return (
            nmos_ring_3stage(ring_instance),
            ring_initial_state(ring_instance),
            ring_instance.step_size,
        )
    raise ValueError(f"unknown workload: {circuit_id}/{instance_name}")
