"""Cluster-aware conditional-detectability simulation for CoVoL Step 003.

This module conditions on prespecified score/loss distributions.  It does not
simulate model fitting, hyperparameter search, caption generation, or threshold
estimation and therefore must not be interpreted as end-to-end study power.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import NormalDist, fmean
from typing import Any

try:
    from paper1.experiments.covol.audit_provenance import (
        EXPANDED_SELECTION_STAGE,
        PILOT_SELECTION_STAGE,
        POWER_GRID_CANONICAL_SHA256,
        SPLIT_ORDER,
        canonical_json_sha256,
        file_sha256,
        split_audit_link_payload,
        validate_trusted_training_source,
        verify_split_audit,
    )
    from paper1.experiments.covol.bootstrap import (
        PolicyImageOutcome,
        policy_hypervolume,
    )
    from paper1.experiments.covol.metrics import (
        corruption_metrics,
        fixed_reference_cvar,
    )
except ModuleNotFoundError:  # Direct script execution from the repository root.
    from audit_provenance import (  # type: ignore[no-redef]
        EXPANDED_SELECTION_STAGE,
        PILOT_SELECTION_STAGE,
        POWER_GRID_CANONICAL_SHA256,
        SPLIT_ORDER,
        canonical_json_sha256,
        file_sha256,
        split_audit_link_payload,
        validate_trusted_training_source,
        verify_split_audit,
    )
    from bootstrap import (  # type: ignore[no-redef]
        PolicyImageOutcome,
        policy_hypervolume,
    )
    from metrics import (  # type: ignore[no-redef]
        corruption_metrics,
        fixed_reference_cvar,
    )

SCHEMA_VERSION = "covol-power-analysis-v1"
DEFAULT_SEED = 20260821
PREREGISTERED_GRID_SHA256 = POWER_GRID_CANONICAL_SHA256
REQUIRED_POWER_DATASETS = frozenset({"KITTI", "NYUv2"})
ALLOWED_POWER_DATASET_SETS = frozenset(
    {
        frozenset({"KITTI", "NYUv2"}),
        frozenset({"NYUv2", "Virtual KITTI 2"}),
    }
)
DEFAULT_GRID_PATH = (
    Path(__file__).resolve().parents[2] / "configs" / "covol" / "power_grid_v1.json"
)


@dataclass(frozen=True)
class PowerScenario:
    """One row of the frozen prevalence/ICC/effect grid."""

    scenario_id: str
    error_prevalence: float
    scene_icc: float
    conditional_advantage_standardized_effect: float


@dataclass(frozen=True)
class PowerGrid:
    """Validated preregistered simulation settings."""

    grid_version: str
    primary_scenario_id: str
    primary_scenario_rationale: str
    formal_simulations: int
    minimum_power: float
    alpha: float
    minimum_positive_errors: int
    minimum_independent_scenes: int
    auc_baseline: float
    planning_auc_delta: float
    minimum_auc_delta: float
    score_correlation: float
    hv_reference_margin_multiplier: float
    paired_expert_advantage_absrel_sd: float
    policy_coverage_grid: tuple[float, ...]
    scenarios: tuple[PowerScenario, ...]


@dataclass(frozen=True)
class DatasetDesign:
    """Independent scene/sequence-component sizes from the pilot manifest."""

    dataset: str
    scene_sizes: tuple[int, ...]
    dev_scene_sizes: tuple[int, ...]

    @property
    def image_count(self) -> int:
        """Return the number of images in the simulated design."""

        return sum(self.scene_sizes)

    @property
    def scene_count(self) -> int:
        """Return the number of independent scene/drive clusters."""

        return len(self.scene_sizes)

    @property
    def dev_image_count(self) -> int:
        """Return the independent dev sample used to freeze score thresholds."""

        return sum(self.dev_scene_sizes)

    @property
    def dev_scene_count(self) -> int:
        """Return the number of dev calibration clusters."""

        return len(self.dev_scene_sizes)


def load_power_dataset_decision(
    path: Path,
    *,
    manifest_sha256: str,
) -> tuple[frozenset[str], dict[str, Any]]:
    """Load a hash-linked, pre-result dataset choice from the coverage audit."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("coverage decision artifact must be a JSON object")
    input_payload = payload.get("input")
    decision = payload.get("claim_dataset_decision")
    if (
        payload.get("schema_version") != "covol-annotation-coverage-v1"
        or payload.get("status") != "PASS"
        or not isinstance(input_payload, Mapping)
        or str(input_payload.get("manifest_sha256", "")).lower() != manifest_sha256
        or not isinstance(decision, Mapping)
    ):
        raise ValueError(
            "coverage decision must be a PASS artifact bound to the power manifest"
        )
    selected = frozenset(
        str(value).strip() for value in decision.get("local_claim_datasets", [])
    )
    if selected not in ALLOWED_POWER_DATASET_SETS:
        raise ValueError("coverage decision selected an unregistered dataset set")
    expected_decision = (
        "GO_LOCAL_CLAIMS_NYUV2_KITTI"
        if selected == REQUIRED_POWER_DATASETS
        else "GO_LOCAL_CLAIMS_NYUV2_VKITTI2"
    )
    if decision.get("decision") != expected_decision:
        raise ValueError("coverage decision name and selected datasets disagree")
    dataset_rows = payload.get("datasets")
    if not isinstance(dataset_rows, list):
        raise ValueError("coverage decision lacks dataset gate rows")
    structured_pass = {
        str(row.get("dataset"))
        for row in dataset_rows
        if isinstance(row, Mapping) and row.get("structured_requirement_pass") is True
    }
    if not selected <= structured_pass:
        raise ValueError("selected power dataset did not pass the coverage contract")
    return selected, {
        "source": "frozen_coverage_audit",
        "coverage_decision_sha256": file_sha256(path),
        "coverage_manifest_sha256": manifest_sha256,
        "decision": expected_decision,
        "selected_datasets": sorted(selected),
    }


def _strict_integer(value: object, *, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    try:
        integer = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an integer") from error
    if integer != value:
        raise ValueError(f"{field} must be an integer")
    return integer


def _finite_float(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be numeric") from error
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def load_power_grid(path: Path = DEFAULT_GRID_PATH) -> PowerGrid:
    """Load and validate the exactly 20-row preregistered grid."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("power grid must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("power grid schema_version must equal 1")
    raw_scenarios = payload.get("scenarios")
    if not isinstance(raw_scenarios, list) or len(raw_scenarios) != 20:
        raise ValueError("power grid must contain exactly 20 scenarios")
    scenarios: list[PowerScenario] = []
    for index, raw in enumerate(raw_scenarios):
        if not isinstance(raw, Mapping):
            raise ValueError(f"scenario {index} must be a JSON object")
        scenario_id = str(raw.get("scenario_id", "")).strip()
        prevalence = _finite_float(
            raw.get("error_prevalence"),
            field=f"scenario {index} error_prevalence",
        )
        icc = _finite_float(
            raw.get("scene_icc"),
            field=f"scenario {index} scene_icc",
        )
        conditional_effect = _finite_float(
            raw.get("conditional_advantage_standardized_effect"),
            field=f"scenario {index} conditional_advantage_standardized_effect",
        )
        if not scenario_id:
            raise ValueError(f"scenario {index} has an empty scenario_id")
        if not 0.0 < prevalence < 1.0:
            raise ValueError(f"scenario {index} prevalence must be in (0, 1)")
        if not 0.0 <= icc < 1.0:
            raise ValueError(f"scenario {index} scene_icc must be in [0, 1)")
        if conditional_effect <= 0.0:
            raise ValueError(
                f"scenario {index} conditional advantage effect must be positive"
            )
        scenarios.append(
            PowerScenario(
                scenario_id=scenario_id,
                error_prevalence=prevalence,
                scene_icc=icc,
                conditional_advantage_standardized_effect=conditional_effect,
            )
        )
    scenario_ids = [scenario.scenario_id for scenario in scenarios]
    scenario_tuples = [
        (
            scenario.error_prevalence,
            scenario.scene_icc,
            scenario.conditional_advantage_standardized_effect,
        )
        for scenario in scenarios
    ]
    if len(set(scenario_ids)) != 20:
        raise ValueError("power-grid scenario_id values must be unique")
    if len(set(scenario_tuples)) != 20:
        raise ValueError("power-grid prevalence/ICC/effect rows must be unique")

    primary_scenario_id = str(payload.get("primary_scenario_id", "")).strip()
    if primary_scenario_id not in scenario_ids:
        raise ValueError("primary_scenario_id must identify one grid row")
    primary_scenario_rationale = str(
        payload.get("primary_scenario_rationale", "")
    ).strip()
    if not primary_scenario_rationale:
        raise ValueError("primary_scenario_rationale must be nonempty")
    formal_simulations = _strict_integer(
        payload.get("formal_simulations"),
        field="formal_simulations",
    )
    minimum_positive_errors = _strict_integer(
        payload.get("minimum_positive_errors"),
        field="minimum_positive_errors",
    )
    minimum_independent_scenes = _strict_integer(
        payload.get("minimum_independent_scenes"),
        field="minimum_independent_scenes",
    )
    minimum_power = _finite_float(payload.get("minimum_power"), field="minimum_power")
    alpha = _finite_float(payload.get("alpha"), field="alpha")
    auc_baseline = _finite_float(payload.get("auc_baseline"), field="auc_baseline")
    planning_auc_delta = _finite_float(
        payload.get("planning_auc_delta"),
        field="planning_auc_delta",
    )
    minimum_auc_delta = _finite_float(
        payload.get("minimum_auc_delta"),
        field="minimum_auc_delta",
    )
    score_correlation = _finite_float(
        payload.get("score_correlation"),
        field="score_correlation",
    )
    hv_reference_margin_multiplier = _finite_float(
        payload.get("hv_reference_margin_multiplier"),
        field="hv_reference_margin_multiplier",
    )
    paired_expert_advantage_absrel_sd = _finite_float(
        payload.get("paired_expert_advantage_absrel_sd"),
        field="paired_expert_advantage_absrel_sd",
    )
    raw_coverage_grid = payload.get("policy_coverage_grid")
    if not isinstance(raw_coverage_grid, list) or not raw_coverage_grid:
        raise ValueError("policy_coverage_grid must be a nonempty list")
    policy_coverage_grid = tuple(
        _finite_float(value, field="policy_coverage_grid")
        for value in raw_coverage_grid
    )
    if formal_simulations != 5_000:
        raise ValueError("formal_simulations is preregistered at exactly 5000")
    if minimum_positive_errors <= 0:
        raise ValueError("minimum_positive_errors must be positive")
    if minimum_independent_scenes < 2:
        raise ValueError("minimum_independent_scenes must be at least two")
    if not 0.0 < minimum_power < 1.0:
        raise ValueError("minimum_power must be in (0, 1)")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    if not 0.5 < auc_baseline < 1.0:
        raise ValueError("auc_baseline must be in (0.5, 1)")
    if (
        minimum_auc_delta <= 0.0
        or planning_auc_delta <= minimum_auc_delta
        or auc_baseline + planning_auc_delta >= 1.0
    ):
        raise ValueError(
            "AUC deltas must satisfy 0 < minimum < planning and keep target below 1"
        )
    if not 0.0 <= score_correlation < 1.0:
        raise ValueError("score_correlation must be in [0, 1)")
    if hv_reference_margin_multiplier != 1.05:
        raise ValueError("hv_reference_margin_multiplier is frozen at 1.05")
    if paired_expert_advantage_absrel_sd <= 0.0:
        raise ValueError("paired expert-advantage SD must be positive")
    expected_coverage_grid = tuple(index / 20 for index in range(21))
    if policy_coverage_grid != expected_coverage_grid:
        raise ValueError("policy_coverage_grid must be exactly 0.00, 0.05, ..., 1.00")
    grid_version = str(payload.get("grid_version", "")).strip()
    if not grid_version:
        raise ValueError("grid_version must be nonempty")
    return PowerGrid(
        grid_version=grid_version,
        primary_scenario_id=primary_scenario_id,
        primary_scenario_rationale=primary_scenario_rationale,
        formal_simulations=formal_simulations,
        minimum_power=minimum_power,
        alpha=alpha,
        minimum_positive_errors=minimum_positive_errors,
        minimum_independent_scenes=minimum_independent_scenes,
        auc_baseline=auc_baseline,
        planning_auc_delta=planning_auc_delta,
        minimum_auc_delta=minimum_auc_delta,
        score_correlation=score_correlation,
        hv_reference_margin_multiplier=hv_reference_margin_multiplier,
        paired_expert_advantage_absrel_sd=paired_expert_advantage_absrel_sd,
        policy_coverage_grid=policy_coverage_grid,
        scenarios=tuple(scenarios),
    )


def _valid_sha256(value: object) -> bool:
    text = str(value).strip().lower()
    return len(text) == 64 and all(
        character in "0123456789abcdef" for character in text
    )


def _read_manifest_design_data(
    manifest_path: Path,
    *,
    split: str = "internal_test",
) -> tuple[list[DatasetDesign], int, dict[str, dict[str, int]], str]:
    if split not in SPLIT_ORDER:
        raise ValueError(f"split must be one of {SPLIT_ORDER}")

    cluster_images: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    dev_cluster_images: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    seen_images: set[tuple[str, str]] = set()
    seen_rgb_hashes: set[str] = set()
    internal_group_splits: dict[tuple[str, str, str], str] = {}
    declared_cluster_by_group: dict[tuple[str, str, str], str] = {}
    split_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {name: 0 for name in SPLIT_ORDER}
    )
    record_count = 0
    selection_stages: set[str] = set()
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, Mapping):
                raise ValueError(
                    f"{manifest_path.name}:{line_number} is not a JSON object"
                )
            validate_trusted_training_source(
                raw,
                context=f"{manifest_path.name}:{line_number}",
            )
            dataset = str(raw.get("dataset", "")).strip()
            image_id = str(raw.get("image_id", "")).strip()
            scene_id = str(raw.get("scene_id", "")).strip()
            sequence_id = str(raw.get("sequence_id", "")).strip()
            cluster_id = str(raw.get("cluster_id", "")).strip().lower()
            record_split = str(raw.get("split", "")).strip()
            official_split = str(raw.get("official_split", "")).strip()
            rgb_sha256 = str(raw.get("rgb_sha256", "")).strip().lower()
            selection_hash = str(raw.get("selection_hash", "")).strip().lower()
            selection_stage = str(raw.get("selection_stage", "")).strip()
            if (
                not dataset
                or not image_id
                or not scene_id
                or not sequence_id
                or not _valid_sha256(cluster_id)
            ):
                raise ValueError(
                    f"{manifest_path.name}:{line_number} lacks dataset, image_id, "
                    "scene_id, sequence_id, or a valid cluster_id"
                )
            if official_split != "train":
                raise ValueError("power manifest must use official_split=train")
            if record_split not in SPLIT_ORDER:
                raise ValueError(f"manifest split must be one of {SPLIT_ORDER}")
            if not _valid_sha256(rgb_sha256) or not _valid_sha256(selection_hash):
                raise ValueError(
                    "power manifest requires valid rgb_sha256 and selection_hash"
                )
            if raw.get("manifest_scope") != "training_pilot_step003":
                raise ValueError(
                    "power manifest requires manifest_scope=training_pilot_step003"
                )
            if raw.get("official_test_audit_status") != "DEFERRED_FROZEN":
                raise ValueError(
                    "power manifest requires official_test_audit_status="
                    "DEFERRED_FROZEN"
                )
            if selection_stage not in {
                PILOT_SELECTION_STAGE,
                EXPANDED_SELECTION_STAGE,
            }:
                raise ValueError("power manifest requires a recognized selection_stage")
            selection_stages.add(selection_stage)
            key = (dataset, image_id)
            if key in seen_images:
                raise ValueError(
                    f"{manifest_path.name}:{line_number} duplicates image key {key!r}"
                )
            seen_images.add(key)
            if rgb_sha256 in seen_rgb_hashes:
                raise ValueError("power manifest contains duplicate RGB content")
            seen_rgb_hashes.add(rgb_sha256)
            for group_name, group_value in (
                ("scene_id", scene_id),
                ("sequence_id", sequence_id),
            ):
                group_key = (dataset, group_name, group_value)
                previous_cluster = declared_cluster_by_group.get(group_key)
                if previous_cluster is not None and previous_cluster != cluster_id:
                    raise ValueError(
                        f"{dataset}: {group_name} maps to multiple cluster_id values"
                    )
                declared_cluster_by_group[group_key] = cluster_id
            for group_name, group_value in (
                ("cluster_id", cluster_id),
                ("scene_id", scene_id),
                ("sequence_id", sequence_id),
                ("rgb_sha256", rgb_sha256),
            ):
                group_key = (dataset, group_name, group_value)
                previous_split = internal_group_splits.get(group_key)
                if previous_split is not None and previous_split != record_split:
                    raise ValueError(
                        f"{dataset}: internal {group_name} split leakage detected"
                    )
                internal_group_splits[group_key] = record_split
            split_counts[dataset][record_split] += 1
            record_count += 1
            if record_split == split:
                cluster_images[dataset][cluster_id].add(image_id)
            if record_split == "dev":
                dev_cluster_images[dataset][cluster_id].add(image_id)
    if not cluster_images:
        raise ValueError(f"manifest contains no records for split {split!r}")
    if len(selection_stages) != 1:
        raise ValueError("power manifest must use one selection_stage")
    designs: list[DatasetDesign] = []
    for dataset in sorted(cluster_images):
        sizes = tuple(
            len(cluster_images[dataset][cluster_id])
            for cluster_id in sorted(cluster_images[dataset])
        )
        if len(sizes) < 2:
            raise ValueError(
                f"{dataset}: at least two independent clusters are required for power"
            )
        dev_sizes = tuple(
            len(dev_cluster_images[dataset][cluster_id])
            for cluster_id in sorted(dev_cluster_images[dataset])
        )
        if len(dev_sizes) < 2:
            raise ValueError(
                f"{dataset}: at least two independent dev clusters are required "
                "for threshold calibration"
            )
        designs.append(
            DatasetDesign(
                dataset=dataset,
                scene_sizes=sizes,
                dev_scene_sizes=dev_sizes,
            )
        )
    return designs, record_count, dict(split_counts), next(iter(selection_stages))


def read_dataset_designs(
    manifest_path: Path,
    *,
    split: str = "internal_test",
) -> list[DatasetDesign]:
    """Infer per-dataset independent cluster sizes from an image JSONL manifest."""

    designs, _, _, _ = _read_manifest_design_data(manifest_path, split=split)
    return designs


def _stable_seed(seed: int, *parts: str) -> int:
    payload = "/".join((str(seed), *parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _clustered_labels(
    scene_sizes: Sequence[int],
    *,
    prevalence: float,
    icc: float,
    rng: random.Random,
) -> tuple[list[int], list[int]]:
    labels: list[int] = []
    clusters: list[int] = []
    if icc == 0.0:
        alpha = beta = None
    else:
        concentration = 1.0 / icc - 1.0
        alpha = prevalence * concentration
        beta = (1.0 - prevalence) * concentration
    for scene_index, size in enumerate(scene_sizes):
        if size <= 0:
            raise ValueError("scene sizes must be positive")
        scene_prevalence = (
            prevalence
            if alpha is None or beta is None
            else rng.betavariate(alpha, beta)
        )
        labels.extend(int(rng.random() < scene_prevalence) for _ in range(size))
        clusters.extend([scene_index] * size)
    return labels, clusters


def _simulate_control_scores(
    labels: Sequence[int],
    clusters: Sequence[int],
    *,
    auc_baseline: float,
    planning_auc_delta: float,
    score_correlation: float,
    scene_icc: float,
    rng: random.Random,
) -> dict[str, list[float]]:
    """Simulate B, permuted-C, and paired null/alternative C scores."""

    baseline_separation = math.sqrt(2.0) * NormalDist().inv_cdf(auc_baseline)
    enhanced_separation = math.sqrt(2.0) * NormalDist().inv_cdf(
        auc_baseline + planning_auc_delta
    )
    scene_count = len(set(clusters))
    shared_scene = [rng.gauss(0.0, 1.0) for _ in range(scene_count)]
    b_scene = [rng.gauss(0.0, 1.0) for _ in range(scene_count)]
    permuted_scene = [rng.gauss(0.0, 1.0) for _ in range(scene_count)]
    c_scene = [rng.gauss(0.0, 1.0) for _ in range(scene_count)]
    scene_scale = math.sqrt(scene_icc)
    image_scale = math.sqrt(1.0 - scene_icc)
    shared_scale = math.sqrt(score_correlation)
    specific_scale = math.sqrt(1.0 - score_correlation)

    b_scores: list[float] = []
    permuted_scores: list[float] = []
    c_null_scores: list[float] = []
    c_alternative_scores: list[float] = []
    for label, cluster in zip(labels, clusters, strict=True):
        shared_component = scene_scale * shared_scene[
            cluster
        ] + image_scale * rng.gauss(0.0, 1.0)
        b_component = scene_scale * b_scene[cluster] + image_scale * rng.gauss(0.0, 1.0)
        permuted_component = scene_scale * permuted_scene[
            cluster
        ] + image_scale * rng.gauss(0.0, 1.0)
        c_component = scene_scale * c_scene[cluster] + image_scale * rng.gauss(0.0, 1.0)
        b_noise = shared_scale * shared_component + specific_scale * b_component
        permuted_noise = (
            shared_scale * shared_component + specific_scale * permuted_component
        )
        c_noise = shared_scale * shared_component + specific_scale * c_component
        b_scores.append(baseline_separation * label + b_noise)
        permuted_scores.append(baseline_separation * label + permuted_noise)
        c_null_scores.append(baseline_separation * label + c_noise)
        c_alternative_scores.append(enhanced_separation * label + c_noise)
    return {
        "b": b_scores,
        "permuted": permuted_scores,
        "c_null": c_null_scores,
        "c_alternative": c_alternative_scores,
    }


def _simulate_expert_losses(
    labels: Sequence[int],
    clusters: Sequence[int],
    *,
    prevalence: float,
    scene_icc: float,
    conditional_effect: float,
    paired_expert_advantage_absrel_sd: float,
    rng: random.Random,
) -> tuple[list[float], list[float], list[tuple[float, ...]]]:
    """Simulate one shared set of D0/D1 losses for every policy."""

    scene_count = len(set(clusters))
    scene_scale = math.sqrt(scene_icc)
    image_scale = math.sqrt(1.0 - scene_icc)
    base_scene = [rng.gauss(0.0, 1.0) for _ in range(scene_count)]
    clean_advantage_scene = [rng.gauss(0.0, 1.0) for _ in range(scene_count)]
    variant_advantage_scenes = [
        [rng.gauss(0.0, 1.0) for _ in range(scene_count)] for _ in range(3)
    ]
    d0_clean_losses: list[float] = []
    d1_clean_losses: list[float] = []
    d1_variant_losses: list[tuple[float, ...]] = []
    conditional_absrel_shift = paired_expert_advantage_absrel_sd * conditional_effect
    for label, cluster in zip(labels, clusters, strict=True):
        d0_clean_loss = max(
            0.25,
            1.0
            + 0.02 * scene_scale * base_scene[cluster]
            + 0.01 * image_scale * rng.gauss(0.0, 1.0),
        )
        centered_label = label - prevalence
        clean_noise = paired_expert_advantage_absrel_sd * (
            scene_scale * clean_advantage_scene[cluster]
            + image_scale * rng.gauss(0.0, 1.0)
        )
        clean_gain = 0.20 + conditional_absrel_shift * centered_label + clean_noise
        variants: list[float] = []
        for variant_scene in variant_advantage_scenes:
            variant_noise = paired_expert_advantage_absrel_sd * (
                scene_scale * variant_scene[cluster] + image_scale * rng.gauss(0.0, 1.0)
            )
            d1_regret = 0.05 - conditional_absrel_shift * centered_label + variant_noise
            variants.append(max(0.0, d0_clean_loss + d1_regret))
        d0_clean_losses.append(d0_clean_loss)
        d1_clean_losses.append(max(0.0, d0_clean_loss - clean_gain))
        d1_variant_losses.append(tuple(variants))
    return d0_clean_losses, d1_clean_losses, d1_variant_losses


def _dev_calibrated_score_thresholds(
    dev_scores: Sequence[float],
    coverage_grid: Sequence[float],
) -> tuple[float, ...]:
    """Freeze top-q score cutoffs using only an independent dev sample."""

    if not dev_scores:
        raise ValueError("dev_scores must not be empty")
    if any(not math.isfinite(float(score)) for score in dev_scores):
        raise ValueError("dev_scores must be finite")
    ordered = sorted((float(score) for score in dev_scores), reverse=True)
    thresholds: list[float] = []
    for coverage in coverage_grid:
        if not 0.0 <= coverage <= 1.0:
            raise ValueError("coverage values must be in [0, 1]")
        selected_count = int(math.floor(coverage * len(ordered) + 0.5))
        if selected_count == 0:
            thresholds.append(math.inf)
        elif selected_count == len(ordered):
            thresholds.append(-math.inf)
        else:
            thresholds.append(
                (ordered[selected_count - 1] + ordered[selected_count]) / 2.0
            )
    return tuple(thresholds)


def _apply_frozen_score_thresholds(
    scores: Sequence[float],
    thresholds: Sequence[float],
) -> tuple[tuple[bool, ...], ...]:
    """Apply dev-frozen absolute cutoffs without ranking internal-test scores."""

    if not scores or any(not math.isfinite(float(score)) for score in scores):
        raise ValueError("internal-test scores must be finite and nonempty")
    return tuple(
        tuple(float(score) > threshold for score in scores) for threshold in thresholds
    )


def _policy_outcomes_from_scores(
    scores: Sequence[float],
    dev_scores: Sequence[float],
    clusters: Sequence[int],
    d0_clean_losses: Sequence[float],
    d1_clean_losses: Sequence[float],
    d1_variant_losses: Sequence[Sequence[float]],
    coverage_grid: Sequence[float],
) -> list[PolicyImageOutcome]:
    """Apply a discrete top-q D1 selector to shared per-image expert losses."""

    image_count = len(scores)
    if not (
        image_count
        == len(clusters)
        == len(d0_clean_losses)
        == len(d1_clean_losses)
        == len(d1_variant_losses)
    ):
        raise ValueError("scores, clusters, and expert losses must have equal length")
    if not d1_variant_losses or any(
        len(variants) != 3 for variants in d1_variant_losses
    ):
        raise ValueError("each image must contain exactly three D1 variant losses")
    thresholds = _dev_calibrated_score_thresholds(dev_scores, coverage_grid)
    route_masks = _apply_frozen_score_thresholds(scores, thresholds)
    outcomes: list[PolicyImageOutcome] = []
    for image_index in range(image_count):
        d0_loss = float(d0_clean_losses[image_index])
        d1_loss = float(d1_clean_losses[image_index])
        d1_variants = tuple(float(value) for value in d1_variant_losses[image_index])
        routed_clean_losses = tuple(
            d1_loss if mask[image_index] else d0_loss for mask in route_masks
        )
        routed_variant_losses = tuple(
            d1_variants if mask[image_index] else (d0_loss, d0_loss, d0_loss)
            for mask in route_masks
        )
        outcomes.append(
            PolicyImageOutcome(
                image_id=f"simulation-image-{image_index}",
                cluster_id=f"simulation-cluster-{clusters[image_index]}",
                d0_clean_loss=d0_loss,
                d1_clean_loss=d1_loss,
                routed_clean_losses=routed_clean_losses,
                routed_variant_losses=routed_variant_losses,
            )
        )
    return outcomes


def _simulate_policy_hypervolume_contrasts(
    labels: Sequence[int],
    clusters: Sequence[int],
    scores: Mapping[str, Sequence[float]],
    dev_scores: Mapping[str, Sequence[float]],
    *,
    prevalence: float,
    scene_icc: float,
    conditional_effect: float,
    paired_expert_advantage_absrel_sd: float,
    coverage_grid: Sequence[float],
    reference_cvar: float,
    rng: random.Random,
) -> dict[str, float]:
    """Compute both Claim-F HV contrasts from score-routed shared experts."""

    expert_losses = _simulate_expert_losses(
        labels,
        clusters,
        prevalence=prevalence,
        scene_icc=scene_icc,
        conditional_effect=conditional_effect,
        paired_expert_advantage_absrel_sd=paired_expert_advantage_absrel_sd,
        rng=rng,
    )
    d0_clean_losses, d1_clean_losses, d1_variant_losses = expert_losses
    hypervolumes: dict[str, float] = {}
    for method in ("b", "permuted", "c_null", "c_alternative"):
        outcomes = _policy_outcomes_from_scores(
            scores[method],
            dev_scores[method],
            clusters,
            d0_clean_losses,
            d1_clean_losses,
            d1_variant_losses,
            coverage_grid,
        )
        hypervolumes[method] = policy_hypervolume(
            outcomes,
            reference_cvar=reference_cvar,
        )
    return {
        "null_c_minus_b": hypervolumes["c_null"] - hypervolumes["b"],
        "null_c_minus_permuted": (hypervolumes["c_null"] - hypervolumes["permuted"]),
        "alternative_c_minus_b": (hypervolumes["c_alternative"] - hypervolumes["b"]),
        "alternative_c_minus_permuted": (
            hypervolumes["c_alternative"] - hypervolumes["permuted"]
        ),
    }


def _auc_components(
    labels: Sequence[int],
    scores: Sequence[float],
) -> tuple[float, list[float]]:
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must have equal nonzero length")
    positive_indices = [index for index, label in enumerate(labels) if label == 1]
    negative_indices = [index for index, label in enumerate(labels) if label == 0]
    if not positive_indices or not negative_indices:
        raise ValueError("AUC requires both positive and negative observations")
    positives = sorted(float(scores[index]) for index in positive_indices)
    negatives = sorted(float(scores[index]) for index in negative_indices)
    components = [0.0] * len(labels)
    for index in positive_indices:
        score = float(scores[index])
        below = bisect.bisect_left(negatives, score)
        at_or_below = bisect.bisect_right(negatives, score)
        ties = at_or_below - below
        components[index] = (below + 0.5 * ties) / len(negatives)
    for index in negative_indices:
        score = float(scores[index])
        below = bisect.bisect_left(positives, score)
        at_or_below = bisect.bisect_right(positives, score)
        ties = at_or_below - below
        above = len(positives) - at_or_below
        components[index] = (above + 0.5 * ties) / len(positives)
    auc = fmean(components[index] for index in positive_indices)
    return auc, components


def _auc_value(labels: Sequence[int], scores: Sequence[float]) -> float:
    auc, _ = _auc_components(labels, scores)
    return auc


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


def _simulation_is_estimable(
    labels: Sequence[int],
    clusters: Sequence[int],
    *,
    minimum_positive_errors: int,
) -> bool:
    positive_count = sum(labels)
    if positive_count < minimum_positive_errors or positive_count == len(labels):
        return False
    positive_clusters = {
        cluster for label, cluster in zip(labels, clusters, strict=True) if label
    }
    negative_clusters = {
        cluster for label, cluster in zip(labels, clusters, strict=True) if not label
    }
    return len(positive_clusters) >= 2 and len(negative_clusters) >= 2


def simulate_power_scenario(
    design: DatasetDesign,
    scenario: PowerScenario,
    grid: PowerGrid,
    *,
    simulations: int,
    seed: int,
) -> dict[str, Any]:
    """Estimate power for the joint four-contrast Claim-F event."""

    if simulations <= 0:
        raise ValueError("simulations must be positive")
    rng = random.Random(_stable_seed(seed, design.dataset, scenario.scenario_id))
    estimable_count = 0
    positive_count_sum = 0
    metric_names = (
        "c_minus_b_auc",
        "c_minus_permuted_auc",
        "c_minus_b_hv",
        "c_minus_permuted_hv",
    )
    null_differences = {name: [] for name in metric_names}
    alternative_differences = {name: [] for name in metric_names}
    dev_reference_cvars: list[float] = []

    for _ in range(simulations):
        labels, clusters = _clustered_labels(
            design.scene_sizes,
            prevalence=scenario.error_prevalence,
            icc=scenario.scene_icc,
            rng=rng,
        )
        positive_count_sum += sum(labels)
        if not _simulation_is_estimable(
            labels,
            clusters,
            minimum_positive_errors=grid.minimum_positive_errors,
        ):
            continue
        estimable_count += 1
        scores = _simulate_control_scores(
            labels,
            clusters,
            auc_baseline=grid.auc_baseline,
            planning_auc_delta=grid.planning_auc_delta,
            score_correlation=grid.score_correlation,
            scene_icc=scenario.scene_icc,
            rng=rng,
        )
        dev_labels, dev_clusters = _clustered_labels(
            design.dev_scene_sizes,
            prevalence=scenario.error_prevalence,
            icc=scenario.scene_icc,
            rng=rng,
        )
        dev_scores = _simulate_control_scores(
            dev_labels,
            dev_clusters,
            auc_baseline=grid.auc_baseline,
            planning_auc_delta=grid.planning_auc_delta,
            score_correlation=grid.score_correlation,
            scene_icc=scenario.scene_icc,
            rng=rng,
        )
        dev_expert_losses = _simulate_expert_losses(
            dev_labels,
            dev_clusters,
            prevalence=scenario.error_prevalence,
            scene_icc=scenario.scene_icc,
            conditional_effect=(scenario.conditional_advantage_standardized_effect),
            paired_expert_advantage_absrel_sd=(grid.paired_expert_advantage_absrel_sd),
            rng=rng,
        )
        dev_always_d1_cvar = corruption_metrics(
            dev_expert_losses[0],
            dev_expert_losses[2],
            expected_variants=3,
        ).cvar
        reference_cvar = fixed_reference_cvar(
            dev_always_d1_cvar,
            margin_multiplier=grid.hv_reference_margin_multiplier,
        )
        dev_reference_cvars.append(reference_cvar)
        b_auc = _auc_value(labels, scores["b"])
        permuted_auc = _auc_value(labels, scores["permuted"])
        c_null_auc = _auc_value(labels, scores["c_null"])
        c_alternative_auc = _auc_value(labels, scores["c_alternative"])
        null_differences["c_minus_b_auc"].append(c_null_auc - b_auc)
        null_differences["c_minus_permuted_auc"].append(c_null_auc - permuted_auc)
        alternative_differences["c_minus_b_auc"].append(c_alternative_auc - b_auc)
        alternative_differences["c_minus_permuted_auc"].append(
            c_alternative_auc - permuted_auc
        )
        hv_contrasts = _simulate_policy_hypervolume_contrasts(
            labels,
            clusters,
            scores,
            dev_scores,
            prevalence=scenario.error_prevalence,
            scene_icc=scenario.scene_icc,
            conditional_effect=(scenario.conditional_advantage_standardized_effect),
            paired_expert_advantage_absrel_sd=(grid.paired_expert_advantage_absrel_sd),
            coverage_grid=grid.policy_coverage_grid,
            reference_cvar=reference_cvar,
            rng=rng,
        )
        null_differences["c_minus_b_hv"].append(hv_contrasts["null_c_minus_b"])
        null_differences["c_minus_permuted_hv"].append(
            hv_contrasts["null_c_minus_permuted"]
        )
        alternative_differences["c_minus_b_hv"].append(
            hv_contrasts["alternative_c_minus_b"]
        )
        alternative_differences["c_minus_permuted_hv"].append(
            hv_contrasts["alternative_c_minus_permuted"]
        )

    contrast_results: dict[str, dict[str, Any]] = {}
    if estimable_count:
        null_quantile = 1.0 - grid.alpha / 2.0
        detections: dict[str, list[bool]] = {}
        for name in metric_names:
            critical_value = _percentile(null_differences[name], null_quantile)
            metric_detections = [
                value > critical_value for value in alternative_differences[name]
            ]
            detections[name] = metric_detections
            detection_count = sum(metric_detections)
            power = detection_count / simulations
            contrast_results[name] = {
                "null_critical_value": critical_value,
                "mean_alternative_difference": fmean(alternative_differences[name]),
                "detection_count": detection_count,
                "power": power,
                "power_monte_carlo_se": math.sqrt(power * (1.0 - power) / simulations),
                "power_threshold_pass": power >= grid.minimum_power,
            }
        auc_joint_detections = [
            left and right
            for left, right in zip(
                detections["c_minus_b_auc"],
                detections["c_minus_permuted_auc"],
                strict=True,
            )
        ]
        hv_joint_detections = [
            left and right
            for left, right in zip(
                detections["c_minus_b_hv"],
                detections["c_minus_permuted_hv"],
                strict=True,
            )
        ]
        four_contrast_inferential_detections = [
            auc_detected and hv_detected
            for auc_detected, hv_detected in zip(
                auc_joint_detections,
                hv_joint_detections,
                strict=True,
            )
        ]
        point_effect_detections = [
            value >= grid.minimum_auc_delta
            for value in alternative_differences["c_minus_b_auc"]
        ]
        full_statistical_gate_detections = [
            inferential and point_effect
            for inferential, point_effect in zip(
                four_contrast_inferential_detections,
                point_effect_detections,
                strict=True,
            )
        ]
        four_contrast_inferential_detection_count = sum(
            four_contrast_inferential_detections
        )
        point_effect_detection_count = sum(point_effect_detections)
        full_statistical_gate_detection_count = sum(full_statistical_gate_detections)
        auc_joint_detection_count = sum(auc_joint_detections)
        hv_joint_detection_count = sum(hv_joint_detections)
    else:
        for name in metric_names:
            contrast_results[name] = {
                "null_critical_value": None,
                "mean_alternative_difference": None,
                "detection_count": 0,
                "power": 0.0,
                "power_monte_carlo_se": 0.0,
                "power_threshold_pass": False,
            }
        auc_joint_detection_count = 0
        hv_joint_detection_count = 0
        four_contrast_inferential_detection_count = 0
        point_effect_detection_count = 0
        full_statistical_gate_detection_count = 0
    auc_joint_power = auc_joint_detection_count / simulations
    hv_joint_power = hv_joint_detection_count / simulations
    four_contrast_inferential_power = (
        four_contrast_inferential_detection_count / simulations
    )
    point_effect_power = point_effect_detection_count / simulations
    full_statistical_gate_power = full_statistical_gate_detection_count / simulations
    full_statistical_gate_threshold_pass = (
        full_statistical_gate_power >= grid.minimum_power
    )
    return {
        **asdict(scenario),
        "is_primary": scenario.scenario_id == grid.primary_scenario_id,
        "simulations_requested": simulations,
        "estimable_simulations": estimable_count,
        "inestimable_simulations": simulations - estimable_count,
        "estimable_fraction": estimable_count / simulations,
        "mean_simulated_positive_errors": positive_count_sum / simulations,
        "mean_estimable_dev_reference_cvar": (
            fmean(dev_reference_cvars) if estimable_count else None
        ),
        "contrasts": contrast_results,
        "auc_joint_detection_count": auc_joint_detection_count,
        "hv_joint_detection_count": hv_joint_detection_count,
        "four_contrast_inferential_detection_count": (
            four_contrast_inferential_detection_count
        ),
        "point_effect_detection_count": point_effect_detection_count,
        "full_statistical_gate_detection_count": (
            full_statistical_gate_detection_count
        ),
        "auc_joint_power": auc_joint_power,
        "hv_joint_power": hv_joint_power,
        "four_contrast_inferential_power": four_contrast_inferential_power,
        "point_effect_power": point_effect_power,
        "full_statistical_gate_power": full_statistical_gate_power,
        "full_statistical_gate_power_monte_carlo_se": math.sqrt(
            full_statistical_gate_power
            * (1.0 - full_statistical_gate_power)
            / simulations
        ),
        "auc_joint_power_threshold_pass": auc_joint_power >= grid.minimum_power,
        "hv_joint_power_threshold_pass": hv_joint_power >= grid.minimum_power,
        "four_contrast_inferential_power_threshold_pass": (
            four_contrast_inferential_power >= grid.minimum_power
        ),
        "full_statistical_gate_power_threshold_pass": (
            full_statistical_gate_threshold_pass
        ),
        "scenario_power_threshold_pass": full_statistical_gate_threshold_pass,
        "inferential_joint_event_definition": (
            "C-B AUROC, C-permuted AUROC, C-B policy HV, and "
            "C-permuted policy HV all exceed their paired-null critical values"
        ),
        "full_decision_definition": (
            "the four inferential contrasts all pass and observed C-B AUROC "
            f"difference is at least {grid.minimum_auc_delta}"
        ),
    }


def run_power_analysis(
    manifest_path: Path,
    *,
    output_csv: Path,
    output_json: Path,
    split_audit_path: Path | None = None,
    grid_path: Path = DEFAULT_GRID_PATH,
    split: str = "internal_test",
    simulations: int = 5_000,
    seed: int = DEFAULT_SEED,
    coverage_decision_path: Path | None = None,
) -> dict[str, Any]:
    """Run all 20 scenarios per dataset and write CSV/JSON audit artifacts."""

    if simulations <= 0:
        raise ValueError("simulations must be positive")
    grid = load_power_grid(grid_path)
    all_designs, record_count, split_counts, manifest_selection_stage = (
        _read_manifest_design_data(
            manifest_path,
            split=split,
        )
    )
    manifest_hash = file_sha256(manifest_path)
    if coverage_decision_path is None:
        required_power_datasets = REQUIRED_POWER_DATASETS
        dataset_decision = {
            "source": "preregistered_primary_default",
            "decision": "GO_LOCAL_CLAIMS_NYUV2_KITTI",
            "selected_datasets": sorted(REQUIRED_POWER_DATASETS),
        }
    else:
        required_power_datasets, dataset_decision = load_power_dataset_decision(
            coverage_decision_path,
            manifest_sha256=manifest_hash,
        )
    grid_file_hash = file_sha256(grid_path)
    grid_hash = canonical_json_sha256(grid_path)
    manifest_dataset_names = set(split_counts)
    designs = [
        design for design in all_designs if design.dataset in required_power_datasets
    ]
    if not designs:
        raise ValueError("manifest contains no preregistered power datasets")
    analysis_dataset_names = {design.dataset for design in designs}
    required_datasets_present = required_power_datasets <= manifest_dataset_names
    supplemental_datasets = sorted(manifest_dataset_names - required_power_datasets)
    split_link = None
    if split_audit_path is not None:
        split_link = verify_split_audit(
            split_audit_path,
            manifest_sha256=manifest_hash,
            manifest_record_count=record_count,
            manifest_split_counts=split_counts,
            required_datasets=required_power_datasets,
            manifest_path=manifest_path,
        )
        if split_link.selection_stage != manifest_selection_stage:
            raise ValueError("manifest row selection_stage does not match split audit")
    minimum_test_scenes_met = all(
        design.scene_count >= grid.minimum_independent_scenes for design in designs
    )
    minimum_dev_scenes_met = all(
        design.dev_scene_count >= grid.minimum_independent_scenes for design in designs
    )
    formal_run = (
        simulations == grid.formal_simulations
        and grid_hash == PREREGISTERED_GRID_SHA256
        and split == "internal_test"
        and seed == DEFAULT_SEED
        and analysis_dataset_names == required_power_datasets
        and required_datasets_present
        and split_link is not None
        and minimum_test_scenes_met
        and minimum_dev_scenes_met
    )
    dataset_payloads: list[dict[str, Any]] = []
    for design in designs:
        scenario_results = [
            simulate_power_scenario(
                design,
                scenario,
                grid,
                simulations=simulations,
                seed=seed,
            )
            for scenario in grid.scenarios
        ]
        primary = next(result for result in scenario_results if result["is_primary"])
        primary_power_pass = bool(primary["scenario_power_threshold_pass"])
        if not formal_run:
            decision = "DIAGNOSTIC_ONLY_NOT_A_GATE"
        elif primary_power_pass:
            decision = "PASS_STEP003_CONDITIONAL_DETECTABILITY_ONLY"
        else:
            decision = "EXPAND_INDEPENDENT_SCENES_OR_DOWNGRADE_CLAIM"
        dataset_payloads.append(
            {
                "dataset": design.dataset,
                "image_count": design.image_count,
                "scene_count": design.scene_count,
                "dev_image_count": design.dev_image_count,
                "dev_scene_count": design.dev_scene_count,
                "minimum_images_per_scene": min(design.scene_sizes),
                "maximum_images_per_scene": max(design.scene_sizes),
                "mean_images_per_scene": design.image_count / design.scene_count,
                "primary_power_threshold_pass": primary_power_pass,
                "formal_gate_pass": formal_run and primary_power_pass,
                "decision": decision,
                "scenarios": scenario_results,
            }
        )
    if not formal_run:
        status = "DIAGNOSTIC_ONLY"
    elif all(dataset["formal_gate_pass"] for dataset in dataset_payloads):
        status = "PASS"
    else:
        status = "FAIL"
    audit = {
        "schema_version": SCHEMA_VERSION,
        "estimand_scope": "CONDITIONAL_INFERENTIAL_DETECTABILITY_NOT_END_TO_END_POWER",
        "status": status,
        "run_mode": "FORMAL" if formal_run else "DIAGNOSTIC",
        "input": {
            "manifest_sha256": manifest_hash,
            "split": split,
            "record_count": record_count,
            "datasets": sorted(manifest_dataset_names),
            "power_analysis_datasets": sorted(analysis_dataset_names),
            "supplemental_structured_datasets_not_powered": supplemental_datasets,
            "selection_stage": manifest_selection_stage,
        },
        "split_audit": (
            split_audit_link_payload(split_link) if split_link is not None else None
        ),
        "dataset_decision": dataset_decision,
        "authorization_scope": (
            split_link.authorization_scope if split_link is not None else None
        ),
        "implementation_sha256": file_sha256(Path(__file__)),
        "grid": {
            "grid_version": grid.grid_version,
            "grid_sha256": grid_hash,
            "grid_file_sha256": grid_file_hash,
            "preregistered_grid_sha256": PREREGISTERED_GRID_SHA256,
            "matches_preregistered_grid": (grid_hash == PREREGISTERED_GRID_SHA256),
            "scenario_count": len(grid.scenarios),
            "primary_scenario_id": grid.primary_scenario_id,
            "primary_scenario_rationale": grid.primary_scenario_rationale,
            "formal_simulations": grid.formal_simulations,
            "minimum_power": grid.minimum_power,
            "alpha": grid.alpha,
            "minimum_positive_errors": grid.minimum_positive_errors,
            "minimum_independent_scenes": grid.minimum_independent_scenes,
            "auc_baseline": grid.auc_baseline,
            "planning_auc_delta": grid.planning_auc_delta,
            "minimum_auc_delta": grid.minimum_auc_delta,
            "score_correlation": grid.score_correlation,
            "hv_reference_margin_multiplier": (grid.hv_reference_margin_multiplier),
            "hv_reference_definition": (
                "within each replicate, 1.05 times independent-dev "
                "CVaR(always-D1), shared by every policy"
            ),
            "paired_expert_advantage_absrel_sd": (
                grid.paired_expert_advantage_absrel_sd
            ),
            "policy_coverage_grid": list(grid.policy_coverage_grid),
            "conditional_effect_definition": (
                "method-independent label-conditional D1-vs-D0 AbsRel advantage "
                "separation, standardized by paired_expert_advantage_absrel_sd"
            ),
            "selector_definition": (
                "each method freezes absolute score cutoffs at dev top-q quantiles "
                "for q=0.00,0.05,...,1.00, then applies those cutoffs unchanged "
                "to internal-test; selected images use D1 and all others use D0, "
                "with no interpolation and shared expert losses across methods"
            ),
            "inference": (
                "scene-cluster generative Monte Carlo with paired null calibration "
                "at each 97.5th percentile and joint four-contrast detection; "
                "formal real-data inference still uses the preregistered paired "
                "scene bootstrap"
            ),
        },
        "simulation": {
            "simulations": simulations,
            "seed": seed,
            "formal_run": formal_run,
            "formal_conditions": {
                "exact_simulations_met": simulations == grid.formal_simulations,
                "preregistered_grid_matched": (grid_hash == PREREGISTERED_GRID_SHA256),
                "split_is_internal_test": split == "internal_test",
                "seed_is_preregistered": seed == DEFAULT_SEED,
                "required_power_datasets_present": required_datasets_present,
                "analysis_datasets_exact": (
                    analysis_dataset_names == required_power_datasets
                ),
                "split_audit_linked": split_link is not None,
                "minimum_internal_test_scenes_met": minimum_test_scenes_met,
                "minimum_dev_scenes_met": minimum_dev_scenes_met,
            },
            "inestimable_replicates_count_as_power_failures": True,
            "powered_statistical_gate_has_four_contrasts_plus_auc_point_gate": True,
            "unpowered_claim_f_conditions": (
                "held-out captioner/family direction and regression/Spearman "
                "consistency remain Step-006 empirical gates"
            ),
        },
        "datasets": dataset_payloads,
    }
    write_power_outputs(audit, output_csv=output_csv, output_json=output_json)
    return audit


def _power_csv_rows(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    grid = audit["grid"]
    simulation = audit["simulation"]
    for dataset in audit["datasets"]:
        for scenario in dataset["scenarios"]:
            row = {
                "schema_version": audit["schema_version"],
                "run_mode": audit["run_mode"],
                "dataset": dataset["dataset"],
                "scenario_id": scenario["scenario_id"],
                "is_primary": scenario["is_primary"],
                "error_prevalence": scenario["error_prevalence"],
                "scene_icc": scenario["scene_icc"],
                "conditional_advantage_standardized_effect": scenario[
                    "conditional_advantage_standardized_effect"
                ],
                "auc_baseline": grid["auc_baseline"],
                "planning_auc_delta": grid["planning_auc_delta"],
                "minimum_auc_delta": grid["minimum_auc_delta"],
                "score_correlation": grid["score_correlation"],
                "minimum_positive_errors": grid["minimum_positive_errors"],
                "minimum_power": grid["minimum_power"],
                "image_count": dataset["image_count"],
                "scene_count": dataset["scene_count"],
                "dev_image_count": dataset["dev_image_count"],
                "dev_scene_count": dataset["dev_scene_count"],
                "mean_images_per_scene": dataset["mean_images_per_scene"],
                "simulations_requested": scenario["simulations_requested"],
                "estimable_simulations": scenario["estimable_simulations"],
                "inestimable_simulations": scenario["inestimable_simulations"],
                "estimable_fraction": scenario["estimable_fraction"],
                "mean_simulated_positive_errors": scenario[
                    "mean_simulated_positive_errors"
                ],
                "mean_estimable_dev_reference_cvar": scenario[
                    "mean_estimable_dev_reference_cvar"
                ],
                "auc_joint_power": scenario["auc_joint_power"],
                "hv_joint_power": scenario["hv_joint_power"],
                "four_contrast_inferential_power": scenario[
                    "four_contrast_inferential_power"
                ],
                "point_effect_power": scenario["point_effect_power"],
                "full_statistical_gate_power": scenario["full_statistical_gate_power"],
                "full_statistical_gate_power_monte_carlo_se": scenario[
                    "full_statistical_gate_power_monte_carlo_se"
                ],
                "auc_joint_power_threshold_pass": scenario[
                    "auc_joint_power_threshold_pass"
                ],
                "hv_joint_power_threshold_pass": scenario[
                    "hv_joint_power_threshold_pass"
                ],
                "four_contrast_inferential_power_threshold_pass": scenario[
                    "four_contrast_inferential_power_threshold_pass"
                ],
                "full_statistical_gate_power_threshold_pass": scenario[
                    "full_statistical_gate_power_threshold_pass"
                ],
                "scenario_power_threshold_pass": scenario[
                    "scenario_power_threshold_pass"
                ],
                "dataset_formal_gate_pass": dataset["formal_gate_pass"],
                "dataset_decision": dataset["decision"],
                "authorization_scope": audit["authorization_scope"],
                "seed": simulation["seed"],
                "manifest_sha256": audit["input"]["manifest_sha256"],
                "grid_version": grid["grid_version"],
                "grid_sha256": grid["grid_sha256"],
                "grid_file_sha256": grid["grid_file_sha256"],
                "implementation_sha256": audit["implementation_sha256"],
            }
            for contrast_name, contrast in scenario["contrasts"].items():
                row[f"{contrast_name}_null_critical_value"] = contrast[
                    "null_critical_value"
                ]
                row[f"{contrast_name}_mean_alternative_difference"] = contrast[
                    "mean_alternative_difference"
                ]
                row[f"{contrast_name}_power"] = contrast["power"]
                row[f"{contrast_name}_power_monte_carlo_se"] = contrast[
                    "power_monte_carlo_se"
                ]
                row[f"{contrast_name}_power_threshold_pass"] = contrast[
                    "power_threshold_pass"
                ]
            rows.append(row)
    return rows


def write_power_outputs(
    audit: Mapping[str, Any],
    *,
    output_csv: Path,
    output_json: Path,
) -> None:
    """Write deterministic power results to CSV and JSON."""

    rows = _power_csv_rows(audit)
    if not rows:
        raise ValueError("power audit must contain at least one scenario")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    output_json.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split-audit", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--grid-config", type=Path, default=DEFAULT_GRID_PATH)
    parser.add_argument("--split", default="internal_test")
    parser.add_argument("--simulations", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--coverage-decision",
        type=Path,
        help=(
            "PASS annotation-coverage JSON that freezes KITTI or Virtual KITTI 2 "
            "before power analysis"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    audit = run_power_analysis(
        args.manifest,
        output_csv=args.output_csv,
        output_json=args.output_json,
        split_audit_path=args.split_audit,
        grid_path=args.grid_config,
        split=args.split,
        simulations=args.simulations,
        seed=args.seed,
        coverage_decision_path=args.coverage_decision,
    )
    if audit["run_mode"] == "FORMAL" and audit["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
