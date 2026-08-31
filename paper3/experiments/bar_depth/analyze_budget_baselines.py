"""Evaluate signed, budget-matched BAR-Depth selectors on frozen utilities."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .analyze_oracle_canary import read_region_rows
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic

SUFFICIENT_KEYS = (
    "base_primary",
    "base_absrel",
    "positive_primary",
    "selected_primary",
    "selected_absrel",
    "selected_positive_primary",
    "selected_count",
    "harmful_count",
    "image_count",
)

METRIC_KEYS = (
    "signed_primary_error_reduction_ratio",
    "signed_absrel_error_reduction_ratio",
    "harmful_selection_rate",
    "oracle_regret_ratio",
    "actual_selection_count",
    "positive_utility_capture",
)

DETERMINISTIC_METHODS = (
    "fixed_spatial_uniform_topk",
    "rgb_gradient_topk",
    "base_gradient_topk",
    "rgb_base_rank_combination_topk",
    "oracle_at_most_k_positive",
)


def _rank_sum(values: list[float]) -> np.ndarray:
    order = np.argsort(np.asarray(values, dtype=np.float64), kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(len(values), dtype=np.float64)
    return ranks


def group_region_rows(
    rows: list[dict[str, Any]], expected_regions: int
) -> list[list[dict[str, Any]]]:
    """Group typed utility rows into complete, region-ordered images."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["sample_index"])].append(row)
    images: list[list[dict[str, Any]]] = []
    for sample_index in sorted(grouped):
        sample_rows = sorted(grouped[sample_index], key=lambda row: row["region_id"])
        if len(sample_rows) != expected_regions:
            raise ValueError(
                f"Sample {sample_index} has {len(sample_rows)} regions, "
                f"expected {expected_regions}"
            )
        region_ids = [int(row["region_id"]) for row in sample_rows]
        if region_ids != list(range(expected_regions)):
            raise ValueError(f"Sample {sample_index} has invalid region identifiers")
        if len({str(row["scan_id"]) for row in sample_rows}) != 1:
            raise ValueError(f"Sample {sample_index} spans multiple scans")
        images.append(sample_rows)
    return images


def select_region_indices(
    sample_rows: list[dict[str, Any]],
    *,
    method: str,
    budget_count: int,
    spatial_pattern: list[int] | None = None,
    random_seed: int | None = None,
) -> np.ndarray:
    """Return selected region indices for one frozen selector."""
    region_count = len(sample_rows)
    if not 0 < budget_count <= region_count:
        raise ValueError("Budget must fit the region count")
    utilities = np.asarray(
        [float(row["primary_utility_sum"]) for row in sample_rows],
        dtype=np.float64,
    )
    if method == "oracle_at_most_k_positive":
        order = np.argsort(-utilities, kind="stable")[:budget_count]
        return order[utilities[order] > 0]
    if method == "fixed_spatial_uniform_topk":
        if spatial_pattern is None or len(spatial_pattern) != budget_count:
            raise ValueError("Spatial pattern must contain exactly K regions")
        selected = np.asarray(spatial_pattern, dtype=np.int64)
        if (
            len(set(selected.tolist())) != budget_count
            or np.any(selected < 0)
            or np.any(selected >= region_count)
        ):
            raise ValueError("Spatial pattern has invalid region identifiers")
        return selected
    if method == "random_topk_100_seeds":
        if random_seed is None:
            raise ValueError("Random selector requires a seed")
        sample_index = int(sample_rows[0]["sample_index"])
        rng = np.random.default_rng(
            np.random.SeedSequence([int(random_seed), sample_index])
        )
        return np.sort(
            rng.choice(region_count, size=budget_count, replace=False).astype(np.int64)
        )
    if method == "rgb_gradient_topk":
        scores = np.asarray(
            [float(row["rgb_gradient_score"]) for row in sample_rows],
            dtype=np.float64,
        )
    elif method == "base_gradient_topk":
        scores = np.asarray(
            [float(row["base_gradient_score"]) for row in sample_rows],
            dtype=np.float64,
        )
    elif method == "rgb_base_rank_combination_topk":
        scores = _rank_sum(
            [float(row["rgb_gradient_score"]) for row in sample_rows]
        ) + _rank_sum([float(row["base_gradient_score"]) for row in sample_rows])
    elif method == "all_12_regions":
        return np.arange(region_count, dtype=np.int64)
    else:
        raise ValueError(f"Unknown selector: {method}")
    return np.argsort(-scores, kind="stable")[:budget_count]


def build_image_statistic(
    sample_rows: list[dict[str, Any]], selected: np.ndarray
) -> dict[str, Any]:
    """Build sufficient statistics for one image and one selector."""
    utility = np.asarray(
        [float(row["primary_utility_sum"]) for row in sample_rows],
        dtype=np.float64,
    )
    absrel_utility = np.asarray(
        [float(row["absrel_utility_sum"]) for row in sample_rows],
        dtype=np.float64,
    )
    selected_utility = utility[selected]
    return {
        "sample_index": int(sample_rows[0]["sample_index"]),
        "scan_id": str(sample_rows[0]["scan_id"]),
        "base_primary": float(
            sum(float(row["base_primary_error_sum"]) for row in sample_rows)
        ),
        "base_absrel": float(
            sum(float(row["base_absrel_error_sum"]) for row in sample_rows)
        ),
        "positive_primary": float(np.maximum(utility, 0.0).sum()),
        "selected_primary": float(selected_utility.sum()),
        "selected_absrel": float(absrel_utility[selected].sum()),
        "selected_positive_primary": float(np.maximum(selected_utility, 0.0).sum()),
        "selected_count": float(selected.size),
        "harmful_count": float(np.count_nonzero(selected_utility < 0)),
        "image_count": 1.0,
    }


def scan_matrix(
    image_statistics: list[dict[str, Any]], scan_ids: list[str]
) -> np.ndarray:
    by_scan: dict[str, np.ndarray] = {
        scan_id: np.zeros(len(SUFFICIENT_KEYS), dtype=np.float64)
        for scan_id in scan_ids
    }
    for row in image_statistics:
        scan_id = str(row["scan_id"])
        if scan_id not in by_scan:
            raise ValueError(f"Unexpected scan {scan_id}")
        by_scan[scan_id] += np.asarray(
            [float(row[key]) for key in SUFFICIENT_KEYS], dtype=np.float64
        )
    return np.stack([by_scan[scan_id] for scan_id in scan_ids])


def aggregate_sufficient(
    sufficient: np.ndarray, oracle_sufficient: np.ndarray
) -> dict[str, float]:
    """Convert summed sufficient statistics into signed selector metrics."""
    values = dict(zip(SUFFICIENT_KEYS, sufficient, strict=True))
    oracle = dict(zip(SUFFICIENT_KEYS, oracle_sufficient, strict=True))
    if values["base_primary"] <= 0 or values["base_absrel"] <= 0:
        raise ValueError("Baseline error denominators must be positive")
    if oracle["selected_primary"] <= 0:
        raise ValueError("Oracle signed utility denominator must be positive")
    return {
        "signed_primary_error_reduction_ratio": float(
            values["selected_primary"] / values["base_primary"]
        ),
        "signed_absrel_error_reduction_ratio": float(
            values["selected_absrel"] / values["base_absrel"]
        ),
        "harmful_selection_rate": float(
            values["harmful_count"] / max(values["selected_count"], 1.0)
        ),
        "oracle_regret_ratio": float(
            (oracle["selected_primary"] - values["selected_primary"])
            / oracle["selected_primary"]
        ),
        "actual_selection_count": float(
            values["selected_count"] / values["image_count"]
        ),
        "positive_utility_capture": float(
            values["selected_positive_primary"] / max(values["positive_primary"], 1e-12)
        ),
    }


def confidence_interval(
    values: list[float], confidence_level: float
) -> dict[str, float]:
    alpha = 1.0 - confidence_level
    array = np.asarray(values, dtype=np.float64)
    return {
        "lower": float(np.quantile(array, alpha / 2.0)),
        "upper": float(np.quantile(array, 1.0 - alpha / 2.0)),
    }


def analyze_budget_baselines(
    *,
    config_path: Path,
    output_csv: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Run signed selector analysis and the preregistered oracle-margin gate."""
    config = read_json(config_path)
    input_csv = Path(config["input_csv"])
    raw_provenance_path = Path(config["raw_provenance"])
    raw_provenance = read_json(raw_provenance_path)
    if raw_provenance["output_csv_sha256"] != file_digest(input_csv):
        raise ValueError("Frozen utility CSV does not match raw provenance")
    rows = read_region_rows(input_csv)
    region_count = int(config["region_rows"]) * int(config["region_columns"])
    images = group_region_rows(rows, region_count)
    if len(images) != int(config["expected_sample_count"]):
        raise ValueError("Unexpected image count")
    scan_ids = sorted({str(sample[0]["scan_id"]) for sample in images})
    if len(scan_ids) != int(config["expected_scan_count"]):
        raise ValueError("Unexpected scan count")

    matrices: dict[tuple[str, int, int | None], np.ndarray] = {}
    budgets = [int(value) for value in config["budget_counts"]]
    random_seeds = list(
        range(
            int(config["random"]["seed_start"]),
            int(config["random"]["seed_start"]) + int(config["random"]["seed_count"]),
        )
    )
    patterns = config["fixed_spatial_uniform_patterns"]

    for budget in budgets:
        for method in DETERMINISTIC_METHODS:
            statistics = [
                build_image_statistic(
                    sample,
                    select_region_indices(
                        sample,
                        method=method,
                        budget_count=budget,
                        spatial_pattern=(
                            [int(value) for value in patterns[str(budget)]]
                            if method == "fixed_spatial_uniform_topk"
                            else None
                        ),
                    ),
                )
                for sample in images
            ]
            matrices[(method, budget, None)] = scan_matrix(statistics, scan_ids)
        for seed in random_seeds:
            statistics = [
                build_image_statistic(
                    sample,
                    select_region_indices(
                        sample,
                        method="random_topk_100_seeds",
                        budget_count=budget,
                        random_seed=seed,
                    ),
                )
                for sample in images
            ]
            matrices[("random_topk_100_seeds", budget, seed)] = scan_matrix(
                statistics, scan_ids
            )

    all_statistics = [
        build_image_statistic(
            sample,
            select_region_indices(
                sample,
                method="all_12_regions",
                budget_count=region_count,
            ),
        )
        for sample in images
    ]
    matrices[("all_12_regions", region_count, None)] = scan_matrix(
        all_statistics, scan_ids
    )
    oracle_all_statistics = [
        build_image_statistic(
            sample,
            select_region_indices(
                sample,
                method="oracle_at_most_k_positive",
                budget_count=region_count,
            ),
        )
        for sample in images
    ]
    matrices[("oracle_at_most_k_positive", region_count, None)] = scan_matrix(
        oracle_all_statistics, scan_ids
    )

    public_keys = [
        (method, budget)
        for budget in budgets
        for method in (
            "random_topk_100_seeds",
            *DETERMINISTIC_METHODS,
        )
    ] + [
        ("all_12_regions", region_count),
        ("oracle_at_most_k_positive", region_count),
    ]

    def public_matrix(method: str, budget: int) -> np.ndarray:
        if method != "random_topk_100_seeds":
            return matrices[(method, budget, None)]
        return np.mean(
            np.stack([matrices[(method, budget, seed)] for seed in random_seeds]),
            axis=0,
        )

    estimates: dict[tuple[str, int], dict[str, float]] = {}
    for method, budget in public_keys:
        oracle_matrix = matrices[("oracle_at_most_k_positive", budget, None)]
        estimates[(method, budget)] = aggregate_sufficient(
            public_matrix(method, budget).sum(axis=0), oracle_matrix.sum(axis=0)
        )

    random_seed_estimates: list[dict[str, Any]] = []
    for budget in budgets:
        oracle_sum = matrices[("oracle_at_most_k_positive", budget, None)].sum(axis=0)
        for seed in random_seeds:
            metrics = aggregate_sufficient(
                matrices[("random_topk_100_seeds", budget, seed)].sum(axis=0),
                oracle_sum,
            )
            random_seed_estimates.append(
                {"budget_count": budget, "seed": seed, **metrics}
            )

    bootstrap_config = config["bootstrap"]
    replicate_count = int(bootstrap_config["replicates"])
    rng = np.random.default_rng(int(bootstrap_config["seed"]))
    bootstrap_values: dict[tuple[str, int], dict[str, list[float]]] = {
        key: {metric: [] for metric in METRIC_KEYS} for key in public_keys
    }
    scan_count = len(scan_ids)
    for _ in range(replicate_count):
        sampled_indices = rng.integers(0, scan_count, size=scan_count)
        counts = np.bincount(sampled_indices, minlength=scan_count).astype(np.float64)
        random_seed = random_seeds[int(rng.integers(0, len(random_seeds)))]
        for method, budget in public_keys:
            matrix = (
                matrices[(method, budget, random_seed)]
                if method == "random_topk_100_seeds"
                else matrices[(method, budget, None)]
            )
            oracle_matrix = matrices[("oracle_at_most_k_positive", budget, None)]
            metrics = aggregate_sufficient(counts @ matrix, counts @ oracle_matrix)
            for metric, value in metrics.items():
                bootstrap_values[(method, budget)][metric].append(value)

    confidence_level = float(bootstrap_config["confidence_level"])
    intervals = {
        key: {
            metric: confidence_interval(values, confidence_level)
            for metric, values in metric_values.items()
        }
        for key, metric_values in bootstrap_values.items()
    }

    non_oracle_methods = (
        "random_topk_100_seeds",
        "fixed_spatial_uniform_topk",
        "rgb_gradient_topk",
        "base_gradient_topk",
        "rgb_base_rank_combination_topk",
    )
    oracle_margins: dict[str, Any] = {}
    for budget in budgets:
        strongest = max(
            non_oracle_methods,
            key=lambda method: estimates[(method, budget)][
                "signed_primary_error_reduction_ratio"
            ],
        )
        oracle_key = ("oracle_at_most_k_positive", budget)
        strongest_key = (strongest, budget)
        differences = (
            np.asarray(
                bootstrap_values[oracle_key]["signed_primary_error_reduction_ratio"]
            )
            - np.asarray(
                bootstrap_values[strongest_key]["signed_primary_error_reduction_ratio"]
            )
        ).tolist()
        oracle_margins[str(budget)] = {
            "strongest_non_oracle_method": strongest,
            "difference": estimates[oracle_key]["signed_primary_error_reduction_ratio"]
            - estimates[strongest_key]["signed_primary_error_reduction_ratio"],
            "paired_scan_bootstrap_95ci": confidence_interval(
                differences, confidence_level
            ),
        }

    primary_budget = int(config["primary_budget_count"])
    primary_margin = oracle_margins[str(primary_budget)]
    gate_config = config["g0_oracle_margin_gate"]
    margin_point_pass = float(primary_margin["difference"]) >= float(
        gate_config["min_primary_reduction_difference"]
    )
    margin_ci_pass = float(primary_margin["paired_scan_bootstrap_95ci"]["lower"]) > 0
    gate_pass = margin_point_pass and (
        margin_ci_pass
        if bool(gate_config["require_paired_ci_lower_above_zero"])
        else True
    )

    csv_rows: list[dict[str, Any]] = []
    for method, budget in public_keys:
        for metric in METRIC_KEYS:
            csv_rows.append(
                {
                    "method": method,
                    "budget_count": budget,
                    "metric": metric,
                    "estimate": estimates[(method, budget)][metric],
                    "ci_lower": intervals[(method, budget)][metric]["lower"],
                    "ci_upper": intervals[(method, budget)][metric]["upper"],
                }
            )
    write_csv_atomic(output_csv, csv_rows)

    def serialize_keyed(
        values: dict[tuple[str, int], dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return {
            f"{method}__k{budget}": value for (method, budget), value in values.items()
        }

    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": (
            "GO_ORACLE_MARGIN_OVER_SIMPLE_SELECTORS"
            if gate_pass
            else "STOP_NO_ORACLE_MARGIN_OVER_KILLER"
        ),
        "paper_candidate": False,
        "sample_count": len(images),
        "scan_count": len(scan_ids),
        "random_seed_count": len(random_seeds),
        "bootstrap_replicates": replicate_count,
        "estimates": serialize_keyed(estimates),
        "cluster_bootstrap_95ci": serialize_keyed(intervals),
        "random_seed_estimates": random_seed_estimates,
        "oracle_margins": oracle_margins,
        "g0_oracle_margin_gate": {
            "all_pass": gate_pass,
            "point_margin_pass": margin_point_pass,
            "paired_ci_pass": margin_ci_pass,
            "thresholds": gate_config,
        },
        "metric_contract": {
            "primary": "signed_primary_error_reduction_ratio",
            "positive_capture": "diagnostic_only",
            "harmful_selection": "selected_primary_utility_below_zero",
            "random_uncertainty": "nested_random_seed_within_scan_bootstrap",
        },
        "historical_correction": {
            "uniform_primary_reduction_ratio": "all_12_regions_not_budget_matched"
        },
        "bindings": {
            "config_sha256": file_digest(config_path),
            "input_csv_sha256": file_digest(input_csv),
            "raw_provenance_sha256": file_digest(raw_provenance_path),
            "implementation_sha256": file_digest(Path(__file__)),
            "output_csv_sha256": file_digest(output_csv),
        },
    }
    write_json_atomic(output_json, summary)
    return summary


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Run the budget-baseline analysis from the command line."""
    args = parse_args()
    summary = analyze_budget_baselines(
        config_path=args.config,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(summary["status"])


if __name__ == "__main__":
    main()
