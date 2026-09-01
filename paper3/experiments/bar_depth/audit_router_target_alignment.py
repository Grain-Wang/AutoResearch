"""Audit whether the router training target preserves the evaluation ordering."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .analyze_budget_baselines import group_region_rows
from .analyze_oracle_canary import read_region_rows
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic

DEFAULT_BUDGETS = (1, 3, 6)
METRIC_KEYS = (
    "mean_top_k_set_jaccard",
    "mean_kendall_tau_b",
    "image_set_disagreement_rate",
    "raw_target_signed_reduction_ratio",
    "normalized_target_signed_reduction_ratio",
    "normalized_target_raw_oracle_recovery",
)


def kendall_tau_b(first: np.ndarray, second: np.ndarray) -> float:
    """Return Kendall's tau-b for two one-dimensional score arrays."""
    if first.ndim != 1 or second.ndim != 1 or first.shape != second.shape:
        raise ValueError("Kendall inputs must be same-length one-dimensional arrays")
    concordant = 0
    discordant = 0
    first_only_ties = 0
    second_only_ties = 0
    for left in range(first.size):
        for right in range(left + 1, first.size):
            first_sign = int(np.sign(first[left] - first[right]))
            second_sign = int(np.sign(second[left] - second[right]))
            if first_sign == 0 and second_sign == 0:
                continue
            if first_sign == 0:
                first_only_ties += 1
            elif second_sign == 0:
                second_only_ties += 1
            elif first_sign == second_sign:
                concordant += 1
            else:
                discordant += 1
    first_denominator = concordant + discordant + first_only_ties
    second_denominator = concordant + discordant + second_only_ties
    denominator = float(np.sqrt(first_denominator * second_denominator))
    if denominator == 0.0:
        return 1.0 if np.array_equal(first, second) else 0.0
    return float((concordant - discordant) / denominator)


def build_image_alignment_rows(
    images: list[list[dict[str, Any]]], budgets: tuple[int, ...]
) -> list[dict[str, Any]]:
    """Build per-image target-alignment diagnostics for every requested budget."""
    output: list[dict[str, Any]] = []
    for sample_rows in images:
        raw_utility = np.asarray(
            [float(row["primary_utility_sum"]) for row in sample_rows],
            dtype=np.float64,
        )
        weight_sum = np.asarray(
            [float(row["weight_sum"]) for row in sample_rows], dtype=np.float64
        )
        if np.any(weight_sum < 0):
            raise ValueError("Primary weights cannot be negative")
        zero_weight = weight_sum == 0
        if np.any(raw_utility[zero_weight] != 0):
            raise ValueError("Zero-weight regions cannot have nonzero raw utility")
        normalized_utility = np.divide(
            raw_utility,
            weight_sum,
            out=np.zeros_like(raw_utility),
            where=~zero_weight,
        )
        raw_order = np.argsort(-raw_utility, kind="stable")
        normalized_order = np.argsort(-normalized_utility, kind="stable")
        tau = kendall_tau_b(raw_utility, normalized_utility)
        base_primary = float(
            sum(float(row["base_primary_error_sum"]) for row in sample_rows)
        )
        if base_primary <= 0:
            raise ValueError("Every image must have positive base primary error")
        for budget in budgets:
            if not 0 < budget <= len(sample_rows):
                raise ValueError("Every budget must fit the region count")
            raw_selected = raw_order[:budget]
            normalized_selected = normalized_order[:budget]
            raw_set = set(int(value) for value in raw_selected)
            normalized_set = set(int(value) for value in normalized_selected)
            intersection = len(raw_set & normalized_set)
            union = len(raw_set | normalized_set)
            output.append(
                {
                    "sample_index": int(sample_rows[0]["sample_index"]),
                    "domain": str(sample_rows[0]["domain"]),
                    "scene_id": str(sample_rows[0]["scene_id"]),
                    "scan_id": str(sample_rows[0]["scan_id"]),
                    "budget_count": budget,
                    "raw_topk_region_ids": ";".join(
                        str(int(value)) for value in raw_selected
                    ),
                    "normalized_topk_region_ids": ";".join(
                        str(int(value)) for value in normalized_selected
                    ),
                    "top_k_set_jaccard": float(intersection / union),
                    "kendall_tau_b": tau,
                    "selected_set_disagreement": float(raw_set != normalized_set),
                    "zero_weight_region_count": int(np.count_nonzero(zero_weight)),
                    "base_primary_error_sum": base_primary,
                    "raw_selected_utility_sum": float(raw_utility[raw_selected].sum()),
                    "normalized_selected_raw_utility_sum": float(
                        raw_utility[normalized_selected].sum()
                    ),
                }
            )
    return output


def aggregate_alignment(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate image rows using the raw paper objective as the denominator."""
    if not rows:
        raise ValueError("Cannot aggregate an empty alignment sample")
    base_primary = sum(float(row["base_primary_error_sum"]) for row in rows)
    raw_selected = sum(float(row["raw_selected_utility_sum"]) for row in rows)
    normalized_selected = sum(
        float(row["normalized_selected_raw_utility_sum"]) for row in rows
    )
    if base_primary <= 0 or raw_selected <= 0:
        raise ValueError("Alignment denominators must be positive")
    return {
        "mean_top_k_set_jaccard": float(
            np.mean([float(row["top_k_set_jaccard"]) for row in rows])
        ),
        "mean_kendall_tau_b": float(
            np.mean([float(row["kendall_tau_b"]) for row in rows])
        ),
        "image_set_disagreement_rate": float(
            np.mean([float(row["selected_set_disagreement"]) for row in rows])
        ),
        "raw_target_signed_reduction_ratio": float(raw_selected / base_primary),
        "normalized_target_signed_reduction_ratio": float(
            normalized_selected / base_primary
        ),
        "normalized_target_raw_oracle_recovery": float(
            normalized_selected / raw_selected
        ),
    }


def confidence_interval(
    values: list[float], confidence_level: float
) -> dict[str, float]:
    """Return a two-sided percentile interval."""
    alpha = 1.0 - confidence_level
    array = np.asarray(values, dtype=np.float64)
    return {
        "lower": float(np.quantile(array, alpha / 2.0)),
        "upper": float(np.quantile(array, 1.0 - alpha / 2.0)),
    }


def bootstrap_by_scan(
    rows: list[dict[str, Any]],
    *,
    replicates: int,
    seed: int,
    confidence_level: float,
) -> dict[str, dict[str, float]]:
    """Bootstrap complete scans and return intervals for alignment metrics."""
    by_scan: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scan[str(row["scan_id"])].append(row)
    scan_ids = sorted(by_scan)
    if len(scan_ids) < 2:
        raise ValueError("Scan bootstrap requires at least two scans")
    values = {metric: [] for metric in METRIC_KEYS}
    rng = np.random.default_rng(seed)
    for _ in range(replicates):
        sampled = rng.choice(scan_ids, size=len(scan_ids), replace=True)
        sampled_rows = [row for scan_id in sampled for row in by_scan[str(scan_id)]]
        metrics = aggregate_alignment(sampled_rows)
        for metric in METRIC_KEYS:
            values[metric].append(metrics[metric])
    return {
        metric: confidence_interval(metric_values, confidence_level)
        for metric, metric_values in values.items()
    }


def audit_router_target_alignment(
    *,
    input_csv: Path,
    provenance_path: Path,
    output_csv: Path,
    output_json: Path,
    budgets: tuple[int, ...] = DEFAULT_BUDGETS,
    replicates: int = 10000,
    seed: int = 271828,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Run the target-alignment gate and write byte-bound audit artifacts."""
    provenance = read_json(provenance_path)
    input_digest = file_digest(input_csv)
    if provenance["output_csv_sha256"] != input_digest:
        raise ValueError("Frozen utility CSV does not match raw provenance")
    typed_rows = read_region_rows(input_csv)
    images = group_region_rows(typed_rows, expected_regions=12)
    image_rows = build_image_alignment_rows(images, budgets)
    write_csv_atomic(output_csv, image_rows)

    estimates: dict[str, dict[str, float]] = {}
    intervals: dict[str, dict[str, dict[str, float]]] = {}
    for budget in budgets:
        budget_rows = [row for row in image_rows if int(row["budget_count"]) == budget]
        estimates[str(budget)] = aggregate_alignment(budget_rows)
        intervals[str(budget)] = bootstrap_by_scan(
            budget_rows,
            replicates=replicates,
            seed=seed + budget,
            confidence_level=confidence_level,
        )

    primary = estimates["3"]
    thresholds = {
        "min_mean_top_k_set_jaccard": 0.90,
        "min_normalized_target_raw_oracle_recovery": 0.95,
    }
    zero_weight_region_count = sum(float(row["weight_sum"]) == 0 for row in typed_rows)
    checks = {
        "normalized_target_defined_for_all_regions": zero_weight_region_count == 0,
        "mean_top_k_set_jaccard": primary["mean_top_k_set_jaccard"]
        >= thresholds["min_mean_top_k_set_jaccard"],
        "normalized_target_raw_oracle_recovery": primary[
            "normalized_target_raw_oracle_recovery"
        ]
        >= thresholds["min_normalized_target_raw_oracle_recovery"],
    }
    keep_normalized = all(checks.values())
    decision = (
        "PASS_KEEP_WEIGHT_NORMALIZED_TARGET"
        if keep_normalized
        else "REDEFINE_RANK_PRESERVING_TARGET"
    )
    recommended_label = {
        "numerator": "primary_utility_sum",
        "denominator": (
            "weight_sum" if keep_normalized else "image_base_primary_error_sum"
        ),
        "rank_preserving_within_image": not keep_normalized,
    }
    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": decision,
        "paper_candidate": False,
        "sample_count": len(images),
        "scan_count": len({str(image[0]["scan_id"]) for image in images}),
        "region_count": 12,
        "zero_weight_region_count": zero_weight_region_count,
        "zero_weight_image_count": len(
            {
                int(row["sample_index"])
                for row in typed_rows
                if float(row["weight_sum"]) == 0
            }
        ),
        "budget_counts": list(budgets),
        "bootstrap": {
            "cluster_key": "scan_id",
            "replicates": replicates,
            "seed_by_budget": {str(budget): seed + budget for budget in budgets},
            "confidence_level": confidence_level,
        },
        "estimands": {
            "ranking_tracks": [
                "primary_utility_sum",
                "primary_utility_sum_per_weight_sum",
            ],
            "selection": "stable_exact_top_k_for_alignment_audit",
            "evaluation": "raw_primary_utility_sum",
            "recovery_denominator": "raw_utility_exact_top_k_sum",
            "zero_weight_audit_convention": (
                "set_undefined_zero_over_zero_normalized_score_to_zero_for_audit_only"
            ),
        },
        "estimates": estimates,
        "scan_bootstrap_95ci": intervals,
        "primary_budget_gate": {
            "budget_count": 3,
            "checks": checks,
            "thresholds": thresholds,
            "all_pass": keep_normalized,
        },
        "recommended_v2_label": recommended_label,
        "bindings": {
            "input_csv_sha256": input_digest,
            "provenance_sha256": file_digest(provenance_path),
            "implementation_sha256": file_digest(Path(__file__)),
            "output_csv_sha256": file_digest(output_csv),
        },
    }
    write_json_atomic(output_json, summary)
    return summary


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=271828)
    return parser.parse_args()


def main() -> None:
    """Run the target-alignment audit from the command line."""
    args = parse_args()
    summary = audit_router_target_alignment(
        input_csv=args.input_csv,
        provenance_path=args.provenance,
        output_csv=args.output_csv,
        output_json=args.output_json,
        replicates=args.bootstrap_replicates,
        seed=args.bootstrap_seed,
    )
    print(summary["status"])


if __name__ == "__main__":
    main()
