"""Validate the objective-aligned BAR-Depth router-probe v2 contract."""

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
    "objective",
    "risk",
    "calibration",
    "features",
    "probe_models",
    "baselines",
    "metrics",
    "bootstrap",
    "gate",
    "prerequisite_gates",
    "stop_rules",
}

REQUIRED_FORBIDDEN_FEATURES = {
    "ground_truth_depth",
    "ground_truth_valid_mask",
    "patch_prediction",
    "patch_affine_parameters",
    "primary_utility",
    "absrel_utility",
    "weight_sum",
    "image_base_primary_error_sum",
    "image_relpath",
    "dataset_id",
    "scene_id",
    "scan_id",
}

REQUIRED_METRICS = {
    "signed_primary_error_reduction_ratio",
    "signed_absrel_error_reduction_ratio",
    "per_image_harm_event_rate",
    "per_image_harm_event_upper_confidence_bound",
    "negative_utility_mass_ratio",
    "per_image_harm_cvar_90",
    "harmful_selection_rate",
    "oracle_regret_ratio",
    "actual_selection_count",
}

REQUIRED_BASELINES = {
    "random_topk_100_seeds",
    "fixed_spatial_uniform_topk",
    "rgb_gradient_topk",
    "base_gradient_topk",
    "rgb_base_rank_combination_topk",
    "boosting_mde_edge_density_selector_adapted_to_bar",
    "point_utility_ridge",
    "point_utility_mlp",
    "oracle_at_most_k_positive",
    "all_12_regions",
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


def validate_router_config_v2(config: dict[str, Any]) -> None:
    """Raise ``ValueError`` when the v2 objective/risk contract is incomplete."""
    _require(config.get("schema_version") == 2, "Unsupported v2 schema version")
    missing = REQUIRED_SECTIONS - set(config)
    _require(not missing, f"Missing v2 sections: {sorted(missing)}")
    _require(
        config["claim_scope"]
        == "selective_regional_refinement_not_budget_adaptive_allocation",
        "Claim scope must disclose homogeneous costs",
    )

    dataset = config["dataset"]
    _require(
        dataset["train_partition"] != dataset["evaluation_partition"],
        "Router train and evaluation partitions must differ",
    )
    _require(
        bool(dataset["evaluation_is_one_time_frozen"]),
        "Evaluation must be one-time frozen",
    )
    _require(
        _is_sha256(dataset["evaluation_manifest_sha256"]),
        "Evaluation manifest needs a SHA256 binding",
    )

    split = config["split"]
    _require(split["group_key"] == "scan_id", "Cross-fitting must group by scan")
    _require(int(split["folds"]) == 5, "The probe requires five folds")
    _require(
        split["threshold_calibration_scope"] == "train_out_of_fold_predictions_only",
        "Risk thresholds require train-only out-of-fold predictions",
    )
    for key in (
        "require_train_evaluation_scan_disjoint",
        "require_train_evaluation_scene_disjoint",
        "require_perceptual_duplicate_audit",
    ):
        _require(bool(split[key]), f"Split audit is disabled: {key}")

    actions = config["actions"]
    region_count = int(actions["region_count"])
    budgets = [int(value) for value in actions["budget_counts"]]
    _require(budgets == [1, 3, 6], "Budgets must remain frozen at 1, 3, and 6")
    _require(all(value <= region_count for value in budgets), "Budget exceeds actions")
    _require(
        bool(actions["single_fitted_score_model_for_all_budgets"]),
        "Budget operating points cannot retrain the score model",
    )
    _require(
        not bool(actions["heterogeneous_costs_supported"]),
        "The current unit-cost probe cannot claim heterogeneous allocation",
    )

    objective = config["objective"]
    _require(objective["utility_symbol"] == "u_i", "Utility symbol must be u_i")
    _require(
        objective["raw_utility_column"] == "primary_utility_sum",
        "Raw utility column is not evaluation-aligned",
    )
    target = objective["training_target"]
    _require(
        target["numerator"] == "primary_utility_sum"
        and target["denominator"] == "image_base_primary_error_sum",
        "Training target must use the rank-preserving image denominator",
    )
    _require(
        target["denominator_scope"] == "constant_within_image"
        and bool(target["rank_preserving_within_image"]),
        "Training target must certify within-image rank preservation",
    )
    _require(
        bool(target["generated_from_patch_prediction_on_training_partition_only"]),
        "Patch labels must remain train-only",
    )

    risk = config["risk"]
    _require(
        risk["primary_event"] == "image_selected_raw_utility_sum_below_zero",
        "Primary risk event must measure net per-image harm",
    )
    _require(
        float(risk["max_event_probability"]) == 0.1,
        "Harm-event risk level must be 0.10",
    )
    _require(float(risk["confidence_level"]) == 0.95, "Risk confidence must be 95%")
    _require(
        risk["upper_bound"] == "clopper_pearson_one_sided_upper",
        "Risk calibration requires an exact one-sided upper bound",
    )
    _require(
        risk["violation_decision"] == "threshold_infeasible",
        "Risk violations must make a threshold infeasible",
    )

    calibration = config["calibration"]
    grid = calibration["threshold_grid"]
    _require(grid["kind"] == "train_score_quantiles", "Thresholds must be quantiles")
    _require(
        float(grid["start"]) == 0.0
        and float(grid["stop"]) == 1.0
        and int(grid["count"]) == 101,
        "Threshold grid must contain 101 quantiles from zero through one",
    )
    _require(
        calibration["candidate_rule"] == "score_greater_than_or_equal_to_threshold",
        "Threshold equality rule is not frozen",
    )
    _require(
        calibration["budget_rule"]
        == "stable_descending_score_then_region_id_take_at_most_k",
        "Score ties need a deterministic region-id rule",
    )
    _require(
        calibration["tie_break"]
        == ["higher_threshold_quantile", "lower_mean_action_count"],
        "Threshold selection tie-break is incomplete",
    )
    _require(
        calibration["fallback_when_no_threshold_is_feasible"] == "abstain_all",
        "Risk calibration requires an abstain-all fallback",
    )
    _require(
        bool(calibration["apply_identical_rule_to_all_score_based_baselines"]),
        "All score baselines require identical risk calibration",
    )

    features = config["features"]
    allowlist = set(features["allowlist"])
    forbidden = set(features["forbidden"])
    _require(allowlist and not allowlist & forbidden, "Feature firewall overlaps")
    _require(
        REQUIRED_FORBIDDEN_FEATURES <= forbidden,
        "Inference feature firewall is incomplete",
    )
    for key in (
        "serialized_schema_sha256_required",
        "inference_firewall_required",
        "evaluation_patch_backend_must_not_be_instantiated",
    ):
        _require(bool(features[key]), f"Feature provenance control is disabled: {key}")

    models = config["probe_models"]
    _require({"ridge", "mlp"} <= set(models), "Ridge and MLP probes are required")
    seeds = [int(value) for value in models["seeds"]]
    _require(len(seeds) == 5 and len(set(seeds)) == 5, "Exactly five seeds required")
    _require(
        models["interpretation"] == "routability_diagnostic_not_paper_algorithm",
        "Point probes cannot be declared as the paper algorithm",
    )

    baselines = config["baselines"]
    _require(
        REQUIRED_BASELINES <= set(baselines["required"]),
        "Required novelty killers are missing",
    )
    _require(int(baselines["random_seeds"]) >= 100, "Random baseline needs 100 seeds")

    metrics = config["metrics"]
    _require(
        metrics["primary"] == "signed_primary_error_reduction_ratio",
        "Raw signed reduction must remain primary",
    )
    _require(REQUIRED_METRICS <= set(metrics["required"]), "Risk metrics are missing")
    _require(
        metrics["positive_utility_capture"] == "diagnostic_only",
        "Positive capture cannot be a primary metric",
    )

    bootstrap = config["bootstrap"]
    _require(bootstrap["cluster_key"] == "scan_id", "Bootstrap must use scans")
    _require(int(bootstrap["replicates"]) >= 10000, "Need 10,000 bootstrap draws")
    _require(
        bootstrap["comparison"] == "paired_replicate_wise_max_baseline_envelope",
        "Baseline-family uncertainty must use a replicate-wise max envelope",
    )

    gate = config["gate"]
    _require(
        float(gate["max_harm_event_upper_confidence_bound"])
        == float(risk["max_event_probability"]),
        "Gate and calibrated harm risk disagree",
    )
    _require(
        gate["absrel_safety_statistic"] == "paired_ci_upper",
        "AbsRel safety requires a paired CI upper bound",
    )
    _require(
        bool(gate["require_all_seeds_reported"]),
        "The gate cannot omit failed seeds",
    )

    prerequisites = set(config["prerequisite_gates"])
    _require(
        prerequisites
        == {
            "PASS_OBJECTIVE_CONTRACT_V2",
            "CONTINUE_GENERIC_NOVELTY",
            "GO_REGIONAL_ORACLE_PARETO_FORMAL_V2",
        },
        "W08 prerequisite gates are incomplete",
    )


def load_router_config_v2(path: Path) -> dict[str, Any]:
    """Load and validate the v2 router contract."""
    config = read_json(path)
    validate_router_config_v2(config)
    return config


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Validate the v2 contract and print its experiment identifier."""
    config = load_router_config_v2(parse_args().config)
    print(config["experiment_id"])


if __name__ == "__main__":
    main()
