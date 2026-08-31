"""Analyze W07 direct-resolution accuracy and exclusive latency results."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .analyze_budget_baselines import (
    build_image_statistic,
    confidence_interval,
    group_region_rows,
    select_region_indices,
)
from .analyze_oracle_canary import read_region_rows
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic

DIRECT_NUMERIC_COLUMNS = {
    "sample_index": int,
    "input_size": int,
    "base_primary_error_sum": float,
    "primary_error_sum": float,
    "primary_utility_sum": float,
    "base_absrel_error_sum": float,
    "absrel_error_sum": float,
    "absrel_utility_sum": float,
}


def _latency_evidence_mode(
    status: str, allow_shared_diagnostic: bool
) -> tuple[str, bool]:
    if status == "COMPLETE_EXCLUSIVE_MATCHED_LATENCY":
        return "exclusive", True
    if (
        status == "COMPLETE_SHARED_DIAGNOSTIC_MATCHED_LATENCY"
        and allow_shared_diagnostic
    ):
        return "shared_diagnostic", False
    raise ValueError("Latency artifact is not an accepted complete run")


def _read_direct_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = dict(raw)
            for column, converter in DIRECT_NUMERIC_COLUMNS.items():
                row[column] = converter(raw[column])
            rows.append(row)
    return rows


def apply_pareto_gate(
    *,
    oracle_estimate: float,
    direct_estimate: float,
    paired_differences: list[float],
    confidence_level: float,
    require_point_above_zero: bool,
    require_ci_lower_above_zero: bool,
) -> dict[str, Any]:
    """Apply the preregistered regional-oracle versus direct-resolution gate."""
    interval = confidence_interval(paired_differences, confidence_level)
    difference = oracle_estimate - direct_estimate
    point_pass = difference > 0
    ci_pass = interval["lower"] > 0
    all_pass = (point_pass or not require_point_above_zero) and (
        ci_pass or not require_ci_lower_above_zero
    )
    return {
        "decision": (
            "GO_REGIONAL_ORACLE_PARETO"
            if all_pass
            else "STOP_DIRECT_RESOLUTION_DOMINATES"
        ),
        "all_pass": all_pass,
        "point_pass": point_pass,
        "paired_ci_pass": ci_pass,
        "difference": difference,
        "paired_scan_bootstrap_95ci": interval,
    }


def analyze_matched_latency(
    *,
    config_path: Path,
    regional_csv: Path,
    regional_provenance_path: Path,
    direct_csv: Path,
    direct_provenance_path: Path,
    latency_path: Path,
    output_csv: Path,
    output_json: Path,
    allow_shared_diagnostic: bool,
) -> dict[str, Any]:
    """Select the strongest feasible direct killer and apply the W07 gate."""
    config = read_json(config_path)
    regional_provenance = read_json(regional_provenance_path)
    direct_provenance = read_json(direct_provenance_path)
    latency = read_json(latency_path)
    if regional_provenance["output_csv_sha256"] != file_digest(regional_csv):
        raise ValueError("Regional CSV does not match provenance")
    if regional_provenance["contract"]["config_sha256"] != str(
        config["merge_config_sha256"]
    ):
        raise ValueError("Regional run used a different merge config")
    if direct_provenance["output_csv_sha256"] != file_digest(direct_csv):
        raise ValueError("Direct-resolution CSV does not match provenance")
    config_digest = file_digest(config_path)
    if direct_provenance["contract"]["config_sha256"] != config_digest:
        raise ValueError("Direct-resolution run used a different W07 config")
    if latency["bindings"]["config_sha256"] != config_digest:
        raise ValueError("Latency run used a different W07 config")
    latency_mode, formal_gate_completed = _latency_evidence_mode(
        str(latency["status"]), allow_shared_diagnostic
    )

    regional_rows = [
        row
        for row in read_region_rows(regional_csv)
        if str(row["variant"]) == str(config["regional_pipeline"]["merge_variant"])
    ]
    regional_images = group_region_rows(regional_rows, expected_regions=12)
    budget_count = int(config["regional_pipeline"]["budget_count"])
    regional_statistics: dict[str, list[dict[str, Any]]] = {}
    for method in ("fixed", "oracle"):
        regional_statistics[method] = [
            build_image_statistic(
                sample,
                select_region_indices(
                    sample,
                    method=(
                        str(config["regional_pipeline"]["selector"])
                        if method == "fixed"
                        else "oracle_at_most_k_positive"
                    ),
                    budget_count=budget_count,
                ),
            )
            for sample in regional_images
        ]

    direct_rows = _read_direct_rows(direct_csv)
    direct_by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in direct_rows:
        direct_by_size[int(row["input_size"])].append(row)
    input_sizes = [int(value) for value in config["whole_image_input_sizes"]]
    expected_samples = int(config["accuracy"]["expected_sample_count"])
    if any(len(direct_by_size[size]) != expected_samples for size in input_sizes):
        raise ValueError("Direct-resolution candidates have incomplete sample rows")

    oracle_by_sample = {
        int(row["sample_index"]): row for row in regional_statistics["oracle"]
    }
    direct_statistics: dict[int, list[dict[str, Any]]] = {}
    for input_size in input_sizes:
        statistics: list[dict[str, Any]] = []
        for row in sorted(
            direct_by_size[input_size], key=lambda item: item["sample_index"]
        ):
            sample_index = int(row["sample_index"])
            regional_base = float(oracle_by_sample[sample_index]["base_primary"])
            direct_base = float(row["base_primary_error_sum"])
            if not np.isclose(regional_base, direct_base, rtol=1e-9, atol=1e-6):
                raise ValueError(f"Base errors disagree for sample {sample_index}")
            statistics.append(
                {
                    "sample_index": sample_index,
                    "scan_id": str(row["scan_id"]),
                    "base_primary": direct_base,
                    "utility": float(row["primary_utility_sum"]),
                }
            )
        direct_statistics[input_size] = statistics

    summaries = latency["summaries"]
    regional_latency = summaries["regional_k3"]
    feasible_sizes = [
        input_size
        for input_size in input_sizes
        if summaries[f"whole_image_{input_size}"]["p50_milliseconds"]
        <= regional_latency["p50_milliseconds"]
        and summaries[f"whole_image_{input_size}"]["p95_milliseconds"]
        <= regional_latency["p95_milliseconds"]
    ]
    if not feasible_sizes:
        if bool(config["gate"]["stop_if_no_whole_image_candidate_is_feasible"]):
            raise ValueError("No whole-image candidate is latency-feasible")
        raise ValueError(
            "Base whole-image candidate unexpectedly exceeds regional latency"
        )

    def estimate(statistics: list[dict[str, Any]], utility_key: str) -> float:
        return float(
            sum(float(row[utility_key]) for row in statistics)
            / sum(float(row["base_primary"]) for row in statistics)
        )

    direct_estimates = {
        input_size: estimate(direct_statistics[input_size], "utility")
        for input_size in input_sizes
    }
    best_direct_size = max(feasible_sizes, key=lambda value: direct_estimates[value])
    regional_estimates = {
        method: estimate(statistics, "selected_primary")
        for method, statistics in regional_statistics.items()
    }

    scan_ids = sorted({str(row["scan_id"]) for row in regional_statistics["oracle"]})

    def scan_sums(statistics: list[dict[str, Any]], utility_key: str) -> np.ndarray:
        by_scan = {scan_id: np.zeros(2, dtype=np.float64) for scan_id in scan_ids}
        for row in statistics:
            by_scan[str(row["scan_id"])] += np.asarray(
                [float(row["base_primary"]), float(row[utility_key])]
            )
        return np.stack([by_scan[scan_id] for scan_id in scan_ids])

    matrices = {
        "fixed": scan_sums(regional_statistics["fixed"], "selected_primary"),
        "oracle": scan_sums(regional_statistics["oracle"], "selected_primary"),
        **{
            f"whole_image_{input_size}": scan_sums(
                direct_statistics[input_size], "utility"
            )
            for input_size in input_sizes
        },
    }
    rng = np.random.default_rng(int(config["bootstrap"]["seed"]))
    bootstrap_values = {method: [] for method in matrices}
    paired_differences: list[float] = []
    scan_count = len(scan_ids)
    direct_key = f"whole_image_{best_direct_size}"
    for _ in range(int(config["bootstrap"]["replicates"])):
        sampled = rng.integers(0, scan_count, size=scan_count)
        counts = np.bincount(sampled, minlength=scan_count).astype(np.float64)
        current: dict[str, float] = {}
        for method, matrix in matrices.items():
            totals = counts @ matrix
            current[method] = float(totals[1] / totals[0])
            bootstrap_values[method].append(current[method])
        paired_differences.append(current["oracle"] - current[direct_key])
    confidence_level = float(config["bootstrap"]["confidence_level"])
    intervals = {
        method: confidence_interval(values, confidence_level)
        for method, values in bootstrap_values.items()
    }
    gate_config = config["gate"]
    gate = apply_pareto_gate(
        oracle_estimate=regional_estimates["oracle"],
        direct_estimate=direct_estimates[best_direct_size],
        paired_differences=paired_differences,
        confidence_level=confidence_level,
        require_point_above_zero=bool(
            gate_config["require_point_difference_above_zero"]
        ),
        require_ci_lower_above_zero=bool(
            gate_config["require_paired_ci_lower_above_zero"]
        ),
    )
    gate["best_feasible_whole_image_input_size"] = best_direct_size
    gate["feasible_whole_image_input_sizes"] = feasible_sizes

    estimates = {
        "fixed": regional_estimates["fixed"],
        "oracle": regional_estimates["oracle"],
        **{
            f"whole_image_{input_size}": direct_estimates[input_size]
            for input_size in input_sizes
        },
    }
    output_rows: list[dict[str, Any]] = []
    for method, method_estimate in estimates.items():
        latency_key = "regional_k3" if method in {"fixed", "oracle"} else method
        input_size = (
            None if method in {"fixed", "oracle"} else int(method.rsplit("_", 1)[1])
        )
        output_rows.append(
            {
                "method": method,
                "input_size": input_size,
                "primary_reduction_ratio": method_estimate,
                "ci_lower": intervals[method]["lower"],
                "ci_upper": intervals[method]["upper"],
                "p50_milliseconds": summaries[latency_key]["p50_milliseconds"],
                "p95_milliseconds": summaries[latency_key]["p95_milliseconds"],
                "latency_feasible": (
                    True
                    if method in {"fixed", "oracle"}
                    else input_size in feasible_sizes
                ),
            }
        )
    write_csv_atomic(output_csv, output_rows)
    result = {
        "schema_version": 1,
        "status": (
            gate["decision"]
            if formal_gate_completed
            else f"PROVISIONAL_SHARED_DIAGNOSTIC_{gate['decision']}"
        ),
        "latency_evidence_mode": latency_mode,
        "formal_gate_completed": formal_gate_completed,
        "paper_candidate": False,
        "estimates": estimates,
        "cluster_bootstrap_95ci": intervals,
        "latency_summaries": summaries,
        "pareto_gate": gate,
        "bindings": {
            "config_sha256": config_digest,
            "regional_csv_sha256": file_digest(regional_csv),
            "regional_provenance_sha256": file_digest(regional_provenance_path),
            "direct_csv_sha256": file_digest(direct_csv),
            "direct_provenance_sha256": file_digest(direct_provenance_path),
            "latency_sha256": file_digest(latency_path),
            "implementation_sha256": file_digest(Path(__file__)),
            "output_csv_sha256": file_digest(output_csv),
        },
    }
    write_json_atomic(output_json, result)
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--regional-csv", type=Path, required=True)
    parser.add_argument("--regional-provenance", type=Path, required=True)
    parser.add_argument("--direct-csv", type=Path, required=True)
    parser.add_argument("--direct-provenance", type=Path, required=True)
    parser.add_argument("--latency", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--allow-shared-diagnostic", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Analyze the frozen W07 accuracy-latency gate."""
    args = parse_args()
    result = analyze_matched_latency(
        config_path=args.config,
        regional_csv=args.regional_csv,
        regional_provenance_path=args.regional_provenance,
        direct_csv=args.direct_csv,
        direct_provenance_path=args.direct_provenance,
        latency_path=args.latency,
        output_csv=args.output_csv,
        output_json=args.output_json,
        allow_shared_diagnostic=args.allow_shared_diagnostic,
    )
    print(result["status"])


if __name__ == "__main__":
    main()
