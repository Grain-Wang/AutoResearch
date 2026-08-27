"""Aggregate BAR-Depth oracle utilities and apply the frozen decision gate."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic

NUMERIC_COLUMNS = {
    "sample_index": int,
    "region_id": int,
    "valid_pixel_count": int,
    "boundary_pixel_count": int,
    "weight_sum": float,
    "base_primary_error_sum": float,
    "refined_primary_error_sum": float,
    "primary_utility_sum": float,
    "base_absrel_error_sum": float,
    "refined_absrel_error_sum": float,
    "absrel_utility_sum": float,
    "rgb_gradient_score": float,
    "base_gradient_score": float,
}

METRIC_KEYS = (
    "positive_headroom_ratio",
    "oracle_capture_at_budget",
    "oracle_primary_reduction_ratio",
    "oracle_absrel_relative_degradation",
    "uniform_primary_reduction_ratio",
    "rgb_gradient_capture_at_budget",
    "base_gradient_capture_at_budget",
    "combined_gradient_capture_at_budget",
)


def read_region_rows(path: Path) -> list[dict[str, Any]]:
    """Read typed region-utility rows."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = dict(raw)
            for column, converter in NUMERIC_COLUMNS.items():
                row[column] = converter(raw[column])
            rows.append(row)
    return rows


def _rank_sum(values: list[float]) -> np.ndarray:
    order = np.argsort(np.asarray(values, dtype=np.float64), kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(len(values), dtype=np.float64)
    return ranks


def build_image_statistics(
    rows: list[dict[str, Any]], budget_count: int, expected_regions: int
) -> list[dict[str, Any]]:
    """Reduce region rows to image-level sufficient statistics."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["sample_index"])].append(row)
    image_statistics: list[dict[str, Any]] = []
    for sample_index in sorted(grouped):
        sample_rows = sorted(grouped[sample_index], key=lambda row: row["region_id"])
        if len(sample_rows) != expected_regions:
            raise ValueError(
                f"Sample {sample_index} has {len(sample_rows)} regions, "
                f"expected {expected_regions}"
            )
        utility = np.asarray(
            [row["primary_utility_sum"] for row in sample_rows], dtype=np.float64
        )
        absrel_utility = np.asarray(
            [row["absrel_utility_sum"] for row in sample_rows], dtype=np.float64
        )
        positive = np.maximum(utility, 0.0)
        oracle_order = np.argsort(-utility, kind="stable")[:budget_count]
        oracle_selected = oracle_order[utility[oracle_order] > 0]

        rgb_scores = [float(row["rgb_gradient_score"]) for row in sample_rows]
        base_scores = [float(row["base_gradient_score"]) for row in sample_rows]
        combined_scores = _rank_sum(rgb_scores) + _rank_sum(base_scores)
        heuristic_orders = {
            "rgb": np.argsort(-np.asarray(rgb_scores), kind="stable")[:budget_count],
            "base": np.argsort(-np.asarray(base_scores), kind="stable")[:budget_count],
            "combined": np.argsort(-combined_scores, kind="stable")[:budget_count],
        }
        image_statistics.append(
            {
                "sample_index": sample_index,
                "scan_id": sample_rows[0]["scan_id"],
                "domain": sample_rows[0]["domain"],
                "base_primary_error_sum": float(
                    sum(row["base_primary_error_sum"] for row in sample_rows)
                ),
                "base_absrel_error_sum": float(
                    sum(row["base_absrel_error_sum"] for row in sample_rows)
                ),
                "positive_utility_sum": float(positive.sum()),
                "oracle_utility_sum": float(positive[oracle_selected].sum()),
                "oracle_absrel_utility_sum": float(
                    absrel_utility[oracle_selected].sum()
                ),
                "uniform_utility_sum": float(utility.sum()),
                "rgb_positive_utility_sum": float(
                    positive[heuristic_orders["rgb"]].sum()
                ),
                "base_positive_utility_sum": float(
                    positive[heuristic_orders["base"]].sum()
                ),
                "combined_positive_utility_sum": float(
                    positive[heuristic_orders["combined"]].sum()
                ),
                "oracle_selected_count": int(oracle_selected.size),
            }
        )
    return image_statistics


def aggregate_statistics(image_statistics: list[dict[str, Any]]) -> dict[str, float]:
    """Compute globally weighted canary metrics from image-level statistics."""
    base_primary = sum(row["base_primary_error_sum"] for row in image_statistics)
    base_absrel = sum(row["base_absrel_error_sum"] for row in image_statistics)
    positive = sum(row["positive_utility_sum"] for row in image_statistics)
    oracle = sum(row["oracle_utility_sum"] for row in image_statistics)
    oracle_absrel = sum(row["oracle_absrel_utility_sum"] for row in image_statistics)
    if base_primary <= 0 or base_absrel <= 0:
        raise ValueError("Canary statistics have no positive base-error denominator")

    def capture(numerator: float) -> float:
        return numerator / positive if positive > 0 else 0.0

    return {
        "positive_headroom_ratio": positive / base_primary,
        "oracle_capture_at_budget": capture(oracle),
        "oracle_primary_reduction_ratio": oracle / base_primary,
        "oracle_absrel_relative_degradation": -oracle_absrel / base_absrel,
        "uniform_primary_reduction_ratio": sum(
            row["uniform_utility_sum"] for row in image_statistics
        )
        / base_primary,
        "rgb_gradient_capture_at_budget": capture(
            sum(row["rgb_positive_utility_sum"] for row in image_statistics)
        ),
        "base_gradient_capture_at_budget": capture(
            sum(row["base_positive_utility_sum"] for row in image_statistics)
        ),
        "combined_gradient_capture_at_budget": capture(
            sum(row["combined_positive_utility_sum"] for row in image_statistics)
        ),
    }


def cluster_bootstrap(
    image_statistics: list[dict[str, Any]], *, replicates: int, seed: int
) -> list[dict[str, float]]:
    """Bootstrap complete scan clusters with replacement."""
    by_scan: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in image_statistics:
        by_scan[str(row["scan_id"])].append(row)
    scan_ids = sorted(by_scan)
    rng = np.random.default_rng(seed)
    bootstrap_rows: list[dict[str, float]] = []
    for replicate in range(replicates):
        sampled = rng.choice(scan_ids, size=len(scan_ids), replace=True)
        sample_statistics: list[dict[str, Any]] = []
        for scan_id in sampled:
            sample_statistics.extend(by_scan[str(scan_id)])
        metrics = aggregate_statistics(sample_statistics)
        bootstrap_rows.append({"replicate": replicate, **metrics})
    return bootstrap_rows


def _interval(
    bootstrap_rows: list[dict[str, float]], metric: str, confidence_level: float
) -> dict[str, float]:
    alpha = 1.0 - confidence_level
    values = np.asarray([row[metric] for row in bootstrap_rows], dtype=np.float64)
    return {
        "lower": float(np.quantile(values, alpha / 2.0)),
        "upper": float(np.quantile(values, 1.0 - alpha / 2.0)),
    }


def apply_gate(
    estimates: dict[str, float],
    intervals: dict[str, dict[str, float]],
    gate_config: dict[str, Any],
) -> dict[str, Any]:
    """Apply the preregistered GO/STOP gate."""
    lower_bound_required = bool(gate_config["require_cluster_ci_lower_bounds"])

    def minimum_pass(metric: str, threshold: float) -> bool:
        point_pass = estimates[metric] >= threshold
        interval_pass = intervals[metric]["lower"] >= threshold
        return point_pass and (interval_pass if lower_bound_required else True)

    checks = {
        "positive_headroom": minimum_pass(
            "positive_headroom_ratio",
            float(gate_config["min_positive_headroom_ratio"]),
        ),
        "oracle_capture": minimum_pass(
            "oracle_capture_at_budget",
            float(gate_config["min_oracle_capture_at_budget"]),
        ),
        "oracle_primary_reduction": minimum_pass(
            "oracle_primary_reduction_ratio",
            float(gate_config["min_oracle_primary_reduction_ratio"]),
        ),
        "global_absrel_safety": estimates["oracle_absrel_relative_degradation"]
        <= float(gate_config["max_oracle_absrel_relative_degradation"]),
    }
    if not checks["positive_headroom"]:
        decision = "STOP_INSUFFICIENT_HEADROOM"
    elif not checks["oracle_capture"]:
        decision = "STOP_DIFFUSE_UTILITY"
    elif not checks["oracle_primary_reduction"]:
        decision = "STOP_INSUFFICIENT_BUDGET_GAIN"
    elif not checks["global_absrel_safety"]:
        decision = "STOP_GLOBAL_SAFETY"
    else:
        decision = "GO_ORACLE_ROUTABILITY_UNVERIFIED"
    return {"decision": decision, "checks": checks, "all_pass": all(checks.values())}


def analyze(
    *,
    input_csv: Path,
    raw_provenance_path: Path,
    config_path: Path,
    output_summary: Path,
    output_bootstrap: Path,
) -> dict[str, Any]:
    """Analyze raw rows, bootstrap scans, and write the final gate result."""
    config = read_json(config_path)
    raw_provenance = read_json(raw_provenance_path)
    if raw_provenance["output_csv_sha256"] != file_digest(input_csv):
        raise ValueError("Raw CSV does not match its provenance")
    if raw_provenance["contract"]["config_sha256"] != file_digest(config_path):
        raise ValueError("Config does not match raw-run provenance")
    rows = read_region_rows(input_csv)
    expected_rows = int(config["dataset"]["expected_sample_count"]) * int(
        config["regions"]["expected_region_count"]
    )
    if len(rows) != expected_rows:
        raise ValueError(f"Expected {expected_rows} region rows, found {len(rows)}")
    image_statistics = build_image_statistics(
        rows,
        int(config["regions"]["expected_budget_count"]),
        int(config["regions"]["expected_region_count"]),
    )
    scans = sorted({str(row["scan_id"]) for row in image_statistics})
    if len(image_statistics) != int(config["dataset"]["expected_sample_count"]):
        raise ValueError("Unexpected image count during analysis")
    if len(scans) != int(config["dataset"]["expected_scan_count"]):
        raise ValueError("Unexpected scan count during analysis")

    estimates = aggregate_statistics(image_statistics)
    bootstrap_rows = cluster_bootstrap(
        image_statistics,
        replicates=int(config["bootstrap"]["replicates"]),
        seed=int(config["bootstrap"]["seed"]),
    )
    intervals = {
        metric: _interval(
            bootstrap_rows,
            metric,
            float(config["bootstrap"]["confidence_level"]),
        )
        for metric in METRIC_KEYS
    }
    gate = apply_gate(estimates, intervals, config["gate"])
    domain_slices = {
        domain: aggregate_statistics(
            [row for row in image_statistics if row["domain"] == domain]
        )
        for domain in sorted({str(row["domain"]) for row in image_statistics})
    }
    write_csv_atomic(output_bootstrap, bootstrap_rows)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": gate["decision"],
        "paper_candidate": False,
        "router_claim": "UNVERIFIED",
        "sample_count": len(image_statistics),
        "scan_count": len(scans),
        "region_row_count": len(rows),
        "budget_count": int(config["regions"]["expected_budget_count"]),
        "estimates": estimates,
        "cluster_bootstrap_95ci": intervals,
        "domain_slices": domain_slices,
        "gate": gate,
        "thresholds": config["gate"],
        "metric_definition": {
            "primary": config["metric"]["primary"],
            "boundary_weight": config["metric"]["boundary_weight"],
            "metric_alignment": config["metric"].get(
                "alignment_variant", "robust_affine"
            ),
            "oracle_selection": (
                "up to three positive primary-utility regions per image"
            ),
            "prediction_depth_range": [
                config["metric"]["min_depth"],
                config["metric"]["max_depth"],
            ],
        },
        "base_metric_depth_range_clipped_pixel_count": raw_provenance[
            "base_metric_clipped_pixel_count_total"
        ],
        "heuristic_interpretation": "descriptive_only_not_a_trained_router",
        "timing_interpretation": raw_provenance["timing_interpretation"],
        "bindings": {
            "config_sha256": file_digest(config_path),
            "raw_csv_sha256": file_digest(input_csv),
            "raw_provenance_sha256": file_digest(raw_provenance_path),
            "bootstrap_csv_sha256": file_digest(output_bootstrap),
            "model_source_revision": raw_provenance["contract"]["source_revision"],
            "model_weights_sha256": raw_provenance["contract"]["weights_sha256"],
            "implementation_canonical_sha256": raw_provenance["contract"][
                "implementation_canonical_sha256"
            ],
            "manifest_sha256": raw_provenance["contract"]["manifest_sha256"],
        },
    }
    write_json_atomic(output_summary, summary)
    return summary


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--raw-provenance", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    parser.add_argument("--output-bootstrap", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    summary = analyze(
        input_csv=args.input_csv,
        raw_provenance_path=args.raw_provenance,
        config_path=args.config,
        output_summary=args.output_summary,
        output_bootstrap=args.output_bootstrap,
    )
    print(summary["status"])


if __name__ == "__main__":
    main()
