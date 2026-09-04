"""Bind the B2 pointwise checker to independent BE MNA reconstruction."""

from __future__ import annotations

from experiments.blockstamp_operator import verified_solve
from experiments.checkers.pointwise_krawczyk import (
    CheckerResult,
    CheckerVerdict,
    LinearSolver,
    pointwise_krawczyk,
)
from experiments.interval_backend import Interval
from experiments.mna import Circuit, MnaStatus, interval_be_residual_jacobian


def check_be_step(
    circuit: Circuit,
    center: tuple[float, ...],
    tube: tuple[Interval, ...],
    previous_state: tuple[Interval, ...],
    step_size: float,
    *,
    linear_solver: LinearSolver = verified_solve,
) -> CheckerResult:
    """Rebuild a BE step and run the component-matched pointwise checker."""

    point_box = tuple(Interval.point(value) for value in center)
    center_evaluation = interval_be_residual_jacobian(
        circuit, point_box, previous_state, step_size
    )
    if (
        center_evaluation.status is not MnaStatus.OK
        or center_evaluation.residual is None
    ):
        return CheckerResult(
            CheckerVerdict.UNSUPPORTED,
            None,
            None,
            f"center MNA reconstruction failed: {center_evaluation.reason}",
        )
    tube_evaluation = interval_be_residual_jacobian(
        circuit, tube, previous_state, step_size
    )
    if tube_evaluation.status is not MnaStatus.OK or tube_evaluation.jacobian is None:
        return CheckerResult(
            CheckerVerdict.UNSUPPORTED,
            None,
            None,
            f"tube MNA reconstruction failed: {tube_evaluation.reason}",
        )
    return pointwise_krawczyk(
        center,
        tube,
        center_evaluation.residual,
        tube_evaluation.jacobian,
        linear_solver=linear_solver,
    )
