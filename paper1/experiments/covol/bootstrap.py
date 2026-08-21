"""Paired scene/drive cluster bootstrap for policy hypervolume."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace

from paper1.experiments.covol.metrics import (
    clean_gain_retention,
    corruption_metrics,
    pareto_hypervolume,
)


@dataclass(frozen=True)
class PolicyImageOutcome:
    """Per-image losses for every frozen coverage threshold."""

    image_id: str
    scene_id: str
    d0_clean_loss: float
    d1_clean_loss: float
    routed_clean_losses: tuple[float, ...]
    routed_variant_losses: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class ClusterBootstrapResult:
    """Point estimate and percentile interval for a paired HV difference."""

    estimate: float
    ci_lower: float
    ci_upper: float
    cluster_count: int
    replicates: int


def _validate_outcomes(outcomes: Sequence[PolicyImageOutcome]) -> tuple[int, int]:
    if not outcomes:
        raise ValueError("outcomes must not be empty")
    threshold_count = len(outcomes[0].routed_clean_losses)
    if threshold_count == 0:
        raise ValueError("each outcome must contain at least one threshold")
    variant_count = len(outcomes[0].routed_variant_losses[0])
    if variant_count == 0:
        raise ValueError("each threshold must contain caption variants")
    seen_images: set[str] = set()
    for outcome in outcomes:
        if not outcome.image_id or not outcome.scene_id:
            raise ValueError("image_id and scene_id must be nonempty")
        if outcome.image_id in seen_images:
            raise ValueError(f"duplicate image_id: {outcome.image_id}")
        if len(outcome.routed_clean_losses) != threshold_count:
            raise ValueError("threshold count mismatch")
        if len(outcome.routed_variant_losses) != threshold_count:
            raise ValueError("clean/corruption threshold count mismatch")
        if any(
            len(variants) != variant_count for variants in outcome.routed_variant_losses
        ):
            raise ValueError("caption variant count mismatch")
        numeric_values = (
            outcome.d0_clean_loss,
            outcome.d1_clean_loss,
            *outcome.routed_clean_losses,
            *(
                value
                for variants in outcome.routed_variant_losses
                for value in variants
            ),
        )
        if any(not math.isfinite(float(value)) for value in numeric_values):
            raise ValueError("outcomes contain a non-finite loss")
        seen_images.add(outcome.image_id)
    return threshold_count, variant_count


def policy_hypervolume(
    outcomes: Sequence[PolicyImageOutcome],
    *,
    reference_cvar: float,
) -> float:
    """Recompute retention, CVaR, Pareto front, and HV from image rows."""

    threshold_count, variant_count = _validate_outcomes(outcomes)
    d0_losses = [outcome.d0_clean_loss for outcome in outcomes]
    d1_losses = [outcome.d1_clean_loss for outcome in outcomes]
    points: list[tuple[float, float]] = []
    for threshold in range(threshold_count):
        retention = clean_gain_retention(
            d0_losses,
            d1_losses,
            [outcome.routed_clean_losses[threshold] for outcome in outcomes],
            clean_gain_ci_lower=math.inf,
        )
        risks = corruption_metrics(
            d0_losses,
            [outcome.routed_variant_losses[threshold] for outcome in outcomes],
            expected_variants=variant_count,
        )
        points.append((retention, risks.cvar))
    return pareto_hypervolume(
        points,
        reference_retention=0.0,
        reference_cvar=reference_cvar,
    )


def cluster_bootstrap_indices(
    cluster_ids: Sequence[str],
    *,
    replicates: int,
    seed: int,
) -> list[tuple[int, ...]]:
    """Sample clusters with replacement while retaining all member images."""

    if replicates <= 0:
        raise ValueError("replicates must be positive")
    if not cluster_ids or any(not cluster_id for cluster_id in cluster_ids):
        raise ValueError("cluster_ids must be nonempty strings")
    members: dict[str, list[int]] = defaultdict(list)
    for index, cluster_id in enumerate(cluster_ids):
        members[cluster_id].append(index)
    clusters = sorted(members)
    if len(clusters) < 2:
        raise ValueError("at least two independent clusters are required")
    rng = random.Random(seed)
    samples: list[tuple[int, ...]] = []
    for _ in range(replicates):
        indices: list[int] = []
        for _ in clusters:
            sampled_cluster = rng.choice(clusters)
            indices.extend(members[sampled_cluster])
        samples.append(tuple(indices))
    return samples


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values or not 0.0 <= probability <= 1.0:
        raise ValueError("invalid percentile input")
    ordered = sorted(float(value) for value in values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def cluster_bootstrap_hypervolume_difference(
    left: Sequence[PolicyImageOutcome],
    right: Sequence[PolicyImageOutcome],
    *,
    reference_cvar: float,
    replicates: int = 10_000,
    seed: int = 20260821,
    confidence: float = 0.95,
) -> ClusterBootstrapResult:
    """Paired cluster bootstrap with full metric recomputation per replicate."""

    _validate_outcomes(left)
    _validate_outcomes(right)
    if len(left) != len(right):
        raise ValueError("paired methods must contain the same images")
    for left_row, right_row in zip(left, right, strict=True):
        if (left_row.image_id, left_row.scene_id) != (
            right_row.image_id,
            right_row.scene_id,
        ):
            raise ValueError("paired methods must have identical image ordering")
        if (
            left_row.d0_clean_loss != right_row.d0_clean_loss
            or left_row.d1_clean_loss != right_row.d1_clean_loss
        ):
            raise ValueError("paired methods must share the same frozen experts")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")

    estimate = policy_hypervolume(
        left,
        reference_cvar=reference_cvar,
    ) - policy_hypervolume(right, reference_cvar=reference_cvar)
    sampled_indices = cluster_bootstrap_indices(
        [row.scene_id for row in left],
        replicates=replicates,
        seed=seed,
    )
    differences: list[float] = []
    for indices in sampled_indices:
        left_sample = [
            replace(
                left[index],
                image_id=f"{left[index].image_id}@bootstrap-{position}",
            )
            for position, index in enumerate(indices)
        ]
        right_sample = [
            replace(
                right[index],
                image_id=f"{right[index].image_id}@bootstrap-{position}",
            )
            for position, index in enumerate(indices)
        ]
        differences.append(
            policy_hypervolume(
                left_sample,
                reference_cvar=reference_cvar,
            )
            - policy_hypervolume(
                right_sample,
                reference_cvar=reference_cvar,
            )
        )
    tail = (1.0 - confidence) / 2.0
    return ClusterBootstrapResult(
        estimate=estimate,
        ci_lower=_percentile(differences, tail),
        ci_upper=_percentile(differences, 1.0 - tail),
        cluster_count=len({row.scene_id for row in left}),
        replicates=replicates,
    )
