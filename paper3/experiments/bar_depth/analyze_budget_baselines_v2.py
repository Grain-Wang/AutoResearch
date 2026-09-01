"""Analyze BAR selectors with a replicate-wise maximum baseline envelope."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .analyze_budget_baselines import (
    DETERMINISTIC_METHODS,
    aggregate_sufficient,
    build_image_statistic,
    confidence_interval,
    group_region_rows,
    scan_matrix,
    select_region_indices,
)
from .analyze_oracle_canary import read_region_rows
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic

PRIMARY_METRIC = "signed_primary_error_reduction_ratio"
BOOSTING_EXACT = "boosting_mde_edge_density_selector_adapted_to_bar_exact_k"
BOOSTING_THRESHOLD = (
    "boosting_mde_edge_density_selector_adapted_to_bar_official_threshold"
)
SIMPLE_BASELINES = (
    "random_topk_100_seeds",
    "fixed_spatial_uniform_topk",
    "rgb_gradient_topk",
    "base_gradient_topk",
    "rgb_base_rank_combination_topk",
    BOOSTING_EXACT,
    BOOSTING_THRESHOLD,
)


def replicate_wise_max_envelope(
    oracle_values: np.ndarray, baseline_values: dict[str, np.ndarray]
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return oracle margins, baseline envelope values, and replicate winners."""
    if oracle_values.ndim != 1 or not baseline_values:
        raise ValueError("Envelope inputs must contain one-dimensional replicates")
    names = list(baseline_values)
    arrays = [np.asarray(baseline_values[name], dtype=np.float64) for name in names]
    if any(array.shape != oracle_values.shape for array in arrays):
        raise ValueError("All envelope arrays must share the oracle shape")
    stack = np.stack(arrays)
    winner_indices = np.argmax(stack, axis=0)
    envelope = np.max(stack, axis=0)
    winners = [names[int(index)] for index in winner_indices]
    return oracle_values - envelope, envelope, winners


def _read_boosting_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    **raw,
                    "sample_index": int(raw["sample_index"]),
                    "region_id": int(raw["region_id"]),
                    "boosting_gradient_density_ratio": float(
                        raw["boosting_gradient_density_ratio"]
                    ),
                    "passes_official_density_threshold": raw[
                        "passes_official_density_threshold"
                    ]
                    == "True",
                    "primary_utility_sum": float(raw["primary_utility_sum"]),
                    "absrel_utility_sum": float(raw["absrel_utility_sum"]),
                }
            )
    return rows


def _boosting_selections(
    boosting_rows: list[dict[str, Any]], budgets: list[int]
) -> dict[tuple[int, str], dict[int, np.ndarray]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in boosting_rows:
        grouped[int(row["sample_index"])].append(row)
    output: dict[tuple[int, str], dict[int, np.ndarray]] = {}
    for budget in budgets:
        exact: dict[int, np.ndarray] = {}
        threshold: dict[int, np.ndarray] = {}
        for sample_index, rows in grouped.items():
            ordered = sorted(rows, key=lambda row: int(row["region_id"]))
            if [int(row["region_id"]) for row in ordered] != list(range(12)):
                raise ValueError("Boosting rows do not contain the frozen 12 actions")
            scores = np.asarray(
                [float(row["boosting_gradient_density_ratio"]) for row in ordered]
            )
            score_order = np.argsort(-scores, kind="stable")
            exact[sample_index] = score_order[:budget]
            passing = np.asarray(
                [bool(row["passes_official_density_threshold"]) for row in ordered]
            )
            threshold[sample_index] = np.asarray(
                [index for index in score_order if passing[index]][:budget],
                dtype=np.int64,
            )
        output[(budget, BOOSTING_EXACT)] = exact
        output[(budget, BOOSTING_THRESHOLD)] = threshold
    return output


def analyze_budget_baselines_v2(
    *,
    config_path: Path,
    boosting_csv_path: Path,
    boosting_summary_path: Path,
    output_csv: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Run the scan bootstrap with winner reselection inside every replicate."""
    config = read_json(config_path)
    input_csv = Path(config["input_csv"])
    raw_provenance_path = Path(config["raw_provenance"])
    raw_provenance = read_json(raw_provenance_path)
    boosting_summary = read_json(boosting_summary_path)
    input_digest = file_digest(input_csv)
    if raw_provenance["output_csv_sha256"] != input_digest:
        raise ValueError("Frozen utility CSV does not match provenance")
    if boosting_summary["bindings"]["input_csv_sha256"] != input_digest:
        raise ValueError("Boosting adaptation used a different utility CSV")
    if boosting_summary["bindings"]["output_csv_sha256"] != file_digest(
        boosting_csv_path
    ):
        raise ValueError("Boosting adaptation CSV does not match its summary")

    rows = read_region_rows(input_csv)
    images = group_region_rows(rows, expected_regions=12)
    scan_ids = sorted({str(sample[0]["scan_id"]) for sample in images})
    if len(images) != int(config["expected_sample_count"]):
        raise ValueError("Unexpected image count")
    if len(scan_ids) != int(config["expected_scan_count"]):
        raise ValueError("Unexpected scan count")
    budgets = [int(value) for value in config["budget_counts"]]
    patterns = config["fixed_spatial_uniform_patterns"]
    random_seeds = list(
        range(
            int(config["random"]["seed_start"]),
            int(config["random"]["seed_start"]) + int(config["random"]["seed_count"]),
        )
    )
    boosting_rows = _read_boosting_rows(boosting_csv_path)
    boosting_by_key = _boosting_selections(boosting_rows, budgets)

    matrices: dict[tuple[str, int, int | None], np.ndarray] = {}
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
        for method in (BOOSTING_EXACT, BOOSTING_THRESHOLD):
            selected_by_sample = boosting_by_key[(budget, method)]
            statistics = [
                build_image_statistic(
                    sample, selected_by_sample[int(sample[0]["sample_index"])]
                )
                for sample in images
            ]
            matrices[(method, budget, None)] = scan_matrix(statistics, scan_ids)
        for random_seed in random_seeds:
            statistics = [
                build_image_statistic(
                    sample,
                    select_region_indices(
                        sample,
                        method="random_topk_100_seeds",
                        budget_count=budget,
                        random_seed=random_seed,
                    ),
                )
                for sample in images
            ]
            matrices[("random_topk_100_seeds", budget, random_seed)] = scan_matrix(
                statistics, scan_ids
            )

    def public_matrix(method: str, budget: int) -> np.ndarray:
        if method != "random_topk_100_seeds":
            return matrices[(method, budget, None)]
        return np.mean(
            np.stack([matrices[(method, budget, seed)] for seed in random_seeds]),
            axis=0,
        )

    estimates: dict[int, dict[str, float]] = {}
    for budget in budgets:
        oracle_matrix = matrices[("oracle_at_most_k_positive", budget, None)]
        oracle_sum = oracle_matrix.sum(axis=0)
        estimates[budget] = {
            method: aggregate_sufficient(
                public_matrix(method, budget).sum(axis=0), oracle_sum
            )[PRIMARY_METRIC]
            for method in (*SIMPLE_BASELINES, "oracle_at_most_k_positive")
        }

    bootstrap_config = config["bootstrap"]
    replicate_count = int(bootstrap_config["replicates"])
    confidence_level = float(bootstrap_config["confidence_level"])
    rng = np.random.default_rng(int(bootstrap_config["seed"]))
    bootstrap_values: dict[int, dict[str, list[float]]] = {
        budget: {
            method: [] for method in (*SIMPLE_BASELINES, "oracle_at_most_k_positive")
        }
        for budget in budgets
    }
    for _ in range(replicate_count):
        sampled = rng.integers(0, len(scan_ids), size=len(scan_ids))
        counts = np.bincount(sampled, minlength=len(scan_ids)).astype(np.float64)
        random_seed = random_seeds[int(rng.integers(0, len(random_seeds)))]
        for budget in budgets:
            oracle_matrix = matrices[("oracle_at_most_k_positive", budget, None)]
            oracle_sum = counts @ oracle_matrix
            for method in (*SIMPLE_BASELINES, "oracle_at_most_k_positive"):
                matrix = (
                    matrices[(method, budget, random_seed)]
                    if method == "random_topk_100_seeds"
                    else matrices[(method, budget, None)]
                )
                value = aggregate_sufficient(counts @ matrix, oracle_sum)[
                    PRIMARY_METRIC
                ]
                bootstrap_values[budget][method].append(value)

    intervals: dict[int, dict[str, dict[str, float]]] = {}
    margins: dict[int, dict[str, Any]] = {}
    envelope_values_by_budget: dict[int, np.ndarray] = {}
    for budget in budgets:
        intervals[budget] = {
            method: confidence_interval(values, confidence_level)
            for method, values in bootstrap_values[budget].items()
        }
        oracle_values = np.asarray(
            bootstrap_values[budget]["oracle_at_most_k_positive"], dtype=np.float64
        )
        baseline_values = {
            method: np.asarray(bootstrap_values[budget][method], dtype=np.float64)
            for method in SIMPLE_BASELINES
        }
        margin_values, envelope_values, winners = replicate_wise_max_envelope(
            oracle_values, baseline_values
        )
        envelope_values_by_budget[budget] = envelope_values
        point_winner = max(
            SIMPLE_BASELINES, key=lambda method: estimates[budget][method]
        )
        winner_counts = {method: winners.count(method) for method in SIMPLE_BASELINES}
        margins[budget] = {
            "point_estimate_strongest_method": point_winner,
            "point_estimate_difference": estimates[budget]["oracle_at_most_k_positive"]
            - estimates[budget][point_winner],
            "replicate_wise_max_envelope": True,
            "paired_scan_bootstrap_95ci": confidence_interval(
                margin_values.tolist(), confidence_level
            ),
            "replicate_winner_counts": winner_counts,
        }

    primary_budget = int(config["primary_budget_count"])
    gate_config = config["g0_oracle_margin_gate"]
    primary_margin = margins[primary_budget]
    point_pass = float(primary_margin["point_estimate_difference"]) >= float(
        gate_config["min_primary_reduction_difference"]
    )
    ci_pass = float(primary_margin["paired_scan_bootstrap_95ci"]["lower"]) > 0
    all_pass = point_pass and (
        ci_pass if bool(gate_config["require_paired_ci_lower_above_zero"]) else True
    )

    output_rows: list[dict[str, Any]] = []
    for budget in budgets:
        for method in (*SIMPLE_BASELINES, "oracle_at_most_k_positive"):
            output_rows.append(
                {
                    "budget_count": budget,
                    "method": method,
                    "metric": PRIMARY_METRIC,
                    "estimate": estimates[budget][method],
                    "ci_lower": intervals[budget][method]["lower"],
                    "ci_upper": intervals[budget][method]["upper"],
                }
            )
        envelope = envelope_values_by_budget[budget]
        output_rows.append(
            {
                "budget_count": budget,
                "method": "replicate_wise_max_non_oracle_envelope",
                "metric": PRIMARY_METRIC,
                "estimate": max(estimates[budget][m] for m in SIMPLE_BASELINES),
                "ci_lower": confidence_interval(envelope.tolist(), confidence_level)[
                    "lower"
                ],
                "ci_upper": confidence_interval(envelope.tolist(), confidence_level)[
                    "upper"
                ],
            }
        )
    write_csv_atomic(output_csv, output_rows)

    summary: dict[str, Any] = {
        "schema_version": 2,
        "status": (
            "GO_ORACLE_MARGIN_OVER_REPLICATE_WISE_BASELINE_ENVELOPE"
            if all_pass
            else "STOP_NO_ORACLE_MARGIN_OVER_REPLICATE_WISE_BASELINE_ENVELOPE"
        ),
        "paper_candidate": False,
        "sample_count": len(images),
        "scan_count": len(scan_ids),
        "bootstrap_replicates": replicate_count,
        "replicate_wise_max_envelope": True,
        "baseline_family": list(SIMPLE_BASELINES),
        "estimates": {str(key): value for key, value in estimates.items()},
        "cluster_bootstrap_95ci": {str(key): value for key, value in intervals.items()},
        "oracle_margins": {str(key): value for key, value in margins.items()},
        "g0_oracle_margin_gate": {
            "budget_count": primary_budget,
            "point_margin_pass": point_pass,
            "replicate_envelope_ci_pass": ci_pass,
            "all_pass": all_pass,
            "thresholds": gate_config,
        },
        "bindings": {
            "config_sha256": file_digest(config_path),
            "input_csv_sha256": input_digest,
            "raw_provenance_sha256": file_digest(raw_provenance_path),
            "boosting_csv_sha256": file_digest(boosting_csv_path),
            "boosting_summary_sha256": file_digest(boosting_summary_path),
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
    parser.add_argument("--boosting-csv", type=Path, required=True)
    parser.add_argument("--boosting-summary", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Run the v2 budget-baseline analysis."""
    args = parse_args()
    summary = analyze_budget_baselines_v2(
        config_path=args.config,
        boosting_csv_path=args.boosting_csv,
        boosting_summary_path=args.boosting_summary,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(summary["status"])


if __name__ == "__main__":
    main()
