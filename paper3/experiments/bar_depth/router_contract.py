"""Validate the preregistered BAR-Depth router-probe contract."""

from __future__ import annotations

import argparse
import string
from pathlib import Path
from typing import Any

from .io_utils import read_json

REQUIRED_SECTIONS = {
    "dataset",
    "split",
    "actions",
    "label",
    "features",
    "probe_models",
    "baselines",
    "metrics",
    "bootstrap",
    "gate",
    "stop_rules",
}

REQUIRED_FORBIDDEN_FEATURES = {
    "ground_truth_depth",
    "ground_truth_valid_mask",
    "patch_prediction",
    "patch_affine_parameters",
    "primary_utility",
    "absrel_utility",
    "image_relpath",
    "dataset_id",
    "scene_id",
    "scan_id",
}

REQUIRED_BASELINES = {
    "random_topk_100_seeds",
    "fixed_spatial_uniform_topk",
    "rgb_gradient_topk",
    "base_gradient_topk",
    "rgb_base_rank_combination_topk",
    "boosting_mde_2021_budget_matched",
    "point_utility_ridge",
    "point_utility_mlp",
    "oracle_at_most_k_positive",
    "all_12_regions",
}

REQUIRED_METRICS = {
    "signed_primary_error_reduction_ratio",
    "signed_absrel_error_reduction_ratio",
    "harmful_selection_rate",
    "oracle_regret_ratio",
    "actual_selection_count",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in string.hexdigits for character in value)
    )


def validate_router_config(config: dict[str, Any]) -> None:
    """Raise ``ValueError`` when a router-probe contract is incomplete or unsafe."""
    _require(config.get("schema_version") == 1, "Unsupported schema version")
    missing = REQUIRED_SECTIONS - set(config)
    _require(not missing, f"Missing router config sections: {sorted(missing)}")

    dataset = config["dataset"]
    _require(
        dataset["train_partition"] != dataset["evaluation_partition"],
        "Router train and evaluation partitions must differ",
    )
    _require(
        bool(dataset["evaluation_is_one_time_frozen"]),
        "Evaluation must be a one-time frozen partition",
    )
    _require(
        _is_sha256(dataset["evaluation_manifest_sha256"]),
        "Evaluation manifest must have a SHA256 binding",
    )

    split = config["split"]
    _require(split["group_key"] == "scan_id", "Router split must group by scan")
    _require(int(split["folds"]) >= 2, "Router cross-fitting needs at least two folds")
    _require(
        bool(split["require_train_evaluation_group_disjoint"]),
        "Router train/evaluation groups must be disjoint",
    )

    actions = config["actions"]
    region_count = int(actions["region_count"])
    budgets = [int(value) for value in actions["budget_counts"]]
    _require(budgets == sorted(set(budgets)), "Budget counts must be sorted and unique")
    _require(
        budgets and all(0 < value <= region_count for value in budgets),
        "Every budget must fit the candidate action space",
    )
    _require(
        int(actions["primary_budget_count"]) in budgets,
        "Primary budget must be preregistered in budget counts",
    )
    tracks = set(actions["selection_tracks"])
    _require(
        tracks == {"exact_k_ranking", "at_most_k_train_calibrated_abstention"},
        "Both exact-K and fair at-most-K tracks are required",
    )
    _require(
        actions["primary_selection_track"] in tracks,
        "Primary selection track is not declared",
    )

    label = config["label"]
    _require(
        label["numerator"] == "primary_utility_sum"
        and label["denominator"] == "weight_sum",
        "Router target must be normalized signed primary utility",
    )
    _require(
        bool(label["generated_from_patch_prediction_on_training_partition_only"]),
        "Patch-derived labels are allowed only on training data",
    )

    features = config["features"]
    allowlist = set(features["allowlist"])
    forbidden = set(features["forbidden"])
    _require(allowlist, "Feature allowlist cannot be empty")
    _require(not allowlist & forbidden, "Allowed and forbidden features overlap")
    _require(
        REQUIRED_FORBIDDEN_FEATURES <= forbidden,
        "Inference feature firewall is incomplete",
    )
    _require(
        bool(features["inference_firewall_required"]),
        "Inference feature firewall must be enabled",
    )

    probe_models = config["probe_models"]
    _require(
        {"ridge", "mlp"} <= set(probe_models),
        "Both Ridge and MLP diagnostics are required",
    )
    seeds = [int(value) for value in probe_models["seeds"]]
    _require(len(seeds) >= 5 and len(seeds) == len(set(seeds)), "Need five seeds")
    _require(
        probe_models["interpretation"] == "routability_diagnostic_not_paper_algorithm",
        "Probe cannot be declared as the paper algorithm",
    )

    baselines = config["baselines"]
    _require(
        REQUIRED_BASELINES <= set(baselines["required"]),
        "Required novelty killers are missing",
    )
    _require(int(baselines["random_seeds"]) >= 100, "Random baseline needs 100 seeds")
    _require(
        bool(baselines["abstention_thresholds_fit_on_train_only"]),
        "Abstention thresholds must be fitted on train only",
    )

    metrics = config["metrics"]
    _require(
        metrics["primary"] == "signed_primary_error_reduction_ratio",
        "Signed end-to-end reduction must be primary",
    )
    _require(
        REQUIRED_METRICS <= set(metrics["required"]),
        "Required signed and harm metrics are missing",
    )
    _require(
        metrics["positive_utility_capture"] == "diagnostic_only",
        "Positive capture cannot be a primary metric",
    )

    bootstrap = config["bootstrap"]
    _require(bootstrap["cluster_key"] == "scan_id", "Bootstrap must use scans")
    _require(int(bootstrap["replicates"]) >= 10000, "Need 10,000 bootstrap draws")
    _require(
        bootstrap["comparison"].startswith("paired_"),
        "Method comparisons must be paired",
    )

    gate = config["gate"]
    _require(
        int(gate["budget_count"]) == int(actions["primary_budget_count"]),
        "Gate and primary budget disagree",
    )
    _require(
        float(gate["min_method_minus_baseline_primary_reduction_percentage_points"])
        >= 1.0,
        "Method must clear the one-percentage-point gate",
    )
    _require(
        bool(gate["require_paired_difference_ci_lower_above_zero"]),
        "Gate must require a positive paired CI lower bound",
    )
    _require(
        float(gate["min_oracle_signed_gain_recovery"]) >= 0.8,
        "Router must recover at least 80% of oracle signed gain",
    )
    _require(
        gate["absrel_safety_statistic"] == "paired_ci_upper",
        "AbsRel safety must use the paired CI upper bound",
    )
    _require(
        float(gate["max_selector_p50_end_to_end_fraction"]) <= 0.05,
        "Selector overhead gate cannot exceed 5%",
    )


def load_router_config(path: Path) -> dict[str, Any]:
    """Load and validate a router-probe contract from JSON."""
    config = read_json(path)
    validate_router_config(config)
    return config


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Validate a router-probe contract and print its experiment identifier."""
    config = load_router_config(parse_args().config)
    print(config["experiment_id"])


if __name__ == "__main__":
    main()
