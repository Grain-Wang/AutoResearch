"""Untrusted binary transient producers and oracle-free tube initialization."""

from experiments.producers.config import load_minimal_probe_config
from experiments.producers.nonlinear import (
    NewtonResult,
    newton_solve,
    solve_linear_system,
)
from experiments.producers.precision import BinaryArithmetic, ProducerPrecision
from experiments.producers.trace import (
    TraceResult,
    TraceStep,
    build_test_reference,
    produce_trace,
)
from experiments.producers.transient import (
    diode_rc_evaluator,
    ring_evaluator,
    solve_diode_rc_step,
    solve_ring_step,
)
from experiments.producers.tube import TubeInitialization, TubeRule, initialize_tube

__all__ = [
    "BinaryArithmetic",
    "NewtonResult",
    "ProducerPrecision",
    "TubeInitialization",
    "TubeRule",
    "diode_rc_evaluator",
    "TraceResult",
    "TraceStep",
    "build_test_reference",
    "initialize_tube",
    "load_minimal_probe_config",
    "newton_solve",
    "produce_trace",
    "ring_evaluator",
    "solve_diode_rc_step",
    "solve_linear_system",
    "solve_ring_step",
]
