"""Executable scalar pieces of the frozen Main-PR training objective."""

from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import fmean


def _finite(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    normalized = tuple(float(value) for value in values)
    if not normalized or any(not math.isfinite(value) for value in normalized):
        raise ValueError(f"{name} must contain finite values")
    return normalized


def image_worst_variant_regret(
    d0_region_losses: Sequence[float],
    routed_variant_region_losses: Sequence[Sequence[float]],
    *,
    region_weights: Sequence[float],
) -> float:
    """Aggregate each complete caption variant before taking worst-of-V."""

    d0 = _finite(d0_region_losses, name="d0_region_losses")
    weights = _finite(region_weights, name="region_weights")
    if len(d0) != len(weights):
        raise ValueError("region_weights and d0_region_losses length mismatch")
    if any(weight < 0.0 for weight in weights) or not math.isclose(
        sum(weights),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("region_weights must be nonnegative and sum to one")
    variant_regrets: list[float] = []
    for variant_index, raw_variant in enumerate(routed_variant_region_losses):
        variant = _finite(raw_variant, name=f"variant[{variant_index}]")
        if len(variant) != len(d0):
            raise ValueError("every complete caption variant must cover all regions")
        variant_regrets.append(
            sum(
                weight * (routed_loss - baseline_loss)
                for weight, routed_loss, baseline_loss in zip(
                    weights,
                    variant,
                    d0,
                    strict=True,
                )
            )
        )
    if not variant_regrets:
        raise ValueError("at least one complete caption variant is required")
    return max(0.0, max(variant_regrets))


def huber_loss(residuals: Sequence[float], *, delta: float) -> float:
    """Return the mean Huber loss with a frozen positive transition delta."""

    values = _finite(residuals, name="residuals")
    if not math.isfinite(delta) or delta <= 0.0:
        raise ValueError("delta must be finite and positive")
    losses = [
        (
            0.5 * value * value
            if abs(value) <= delta
            else delta * (abs(value) - 0.5 * delta)
        )
        for value in values
    ]
    return fmean(losses)


def rockafellar_uryasev_cvar(
    image_risks: Sequence[float],
    *,
    eta: float,
    tail_fraction: float,
) -> float:
    """Evaluate the Rockafellar--Uryasev CVaR objective at fixed eta."""

    risks = _finite(image_risks, name="image_risks")
    if not math.isfinite(eta):
        raise ValueError("eta must be finite")
    if not math.isfinite(tail_fraction) or not 0.0 < tail_fraction <= 1.0:
        raise ValueError("tail_fraction must be finite and in (0, 1]")
    return eta + fmean(max(0.0, risk - eta) for risk in risks) / tail_fraction


def standard_lagrangian(
    partial_residual_loss: float,
    cvar_risk: float,
    constraint_violation: float,
    *,
    beta: float,
    multiplier: float,
) -> float:
    """Return L_PR + beta*CVaR + lambda*(kappa*G1-Gg)."""

    values = (
        partial_residual_loss,
        cvar_risk,
        constraint_violation,
        beta,
        multiplier,
    )
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("Lagrangian inputs must be finite")
    if beta < 0.0 or multiplier < 0.0:
        raise ValueError("beta and multiplier must be nonnegative")
    return (
        float(partial_residual_loss)
        + float(beta) * float(cvar_risk)
        + float(multiplier) * float(constraint_violation)
    )


def projected_dual_ascent(
    multiplier: float,
    constraint_violation: float,
    *,
    learning_rate: float,
    maximum: float,
) -> float:
    """Perform one signed dual-ascent update projected onto [0, maximum]."""

    values = (multiplier, constraint_violation, learning_rate, maximum)
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("dual update inputs must be finite")
    if multiplier < 0.0 or learning_rate <= 0.0 or maximum <= 0.0:
        raise ValueError("dual multiplier/bounds are invalid")
    return min(
        float(maximum),
        max(
            0.0,
            float(multiplier) + float(learning_rate) * float(constraint_violation),
        ),
    )
