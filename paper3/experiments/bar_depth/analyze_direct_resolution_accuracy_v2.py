"""Analyze the closed-range W07-v2 accuracy sweep before latency completes."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .analyze_budget_baselines import (
    build_image_statistic,
    confidence_interval,
    group_region_rows,
    select_region_indices,
)
from .analyze_budget_baselines_v2 import replicate_wise_max_envelope
from .analyze_oracle_canary import read_region_rows
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic


def direct_accuracy_envelope(
    oracle_values: np.ndarray, direct_values: dict[int, np.ndarray]
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Reselect the strongest whole-image size in every bootstrap replicate."""
    named_values = {
        f"whole_image_{size}": values for size, values in sorted(direct_values.items())
    }
    margins, envelope, winners = replicate_wise_max_envelope(
        oracle_values, named_values
    )
    winner_sizes = [int(name.rsplit("_", 1)[1]) for name in winners]
    return margins, envelope, winner_sizes


def _read_direct_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            if str(raw["status"]) != "OK":
                continue
            rows.append(
                {
                    "sample_index": int(raw["sample_index"]),
                    "scan_id": str(raw["scan_id"]),
                    "input_size": int(raw["input_size"]),
                    "base_primary_error_sum": float(raw["base_primary_error_sum"]),
                    "primary_utility_sum": float(raw["primary_utility_sum"]),
                }
            )
    return rows


def _scan_primary_matrix(
    rows: list[dict[str, Any]], scan_ids: list[str], utility_key: str
) -> np.ndarray:
    by_scan = {scan_id: np.zeros(2, dtype=np.float64) for scan_id in scan_ids}
    for row in rows:
        scan_id = str(row["scan_id"])
        if scan_id not in by_scan:
            raise ValueError(f"Unexpected scan {scan_id}")
        by_scan[scan_id] += np.asarray(
            [float(row["base_primary"]), float(row[utility_key])],
            dtype=np.float64,
        )
    return np.stack([by_scan[scan_id] for scan_id in scan_ids])


def analyze_direct_resolution_accuracy_v2(
    *,
    config_path: Path,
    regional_csv: Path,
    regional_provenance_path: Path,
    direct_csv: Path,
    direct_provenance_path: Path,
    output_csv: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Compare the regional references with every completed direct size."""
    config = read_json(config_path)
    regional_provenance = read_json(regional_provenance_path)
    direct_provenance = read_json(direct_provenance_path)
    config_digest = file_digest(config_path)
    if regional_provenance["output_csv_sha256"] != file_digest(regional_csv):
        raise ValueError("Regional CSV does not match provenance")
    if direct_provenance["output_csv_sha256"] != file_digest(direct_csv):
        raise ValueError("Direct CSV does not match provenance")
    if direct_provenance["contract"]["config_sha256"] != config_digest:
        raise ValueError("Direct accuracy used a different W07-v2 config")
    if direct_provenance["status"] != "COMPLETE_DIRECT_RESOLUTION_V2_MATRIX":
        raise ValueError("Direct-resolution v2 matrix is incomplete")

    all_input_sizes = [int(value) for value in config["whole_image_input_sizes"]]
    if int(direct_provenance["candidate_count"]) != len(all_input_sizes):
        raise ValueError("Direct provenance has an unexpected candidate count")
    oom_sizes = {int(value) for value in direct_provenance.get("oom_sizes", [])}
    input_sizes = [size for size in all_input_sizes if size not in oom_sizes]
    if not input_sizes:
        raise ValueError("All direct-resolution candidates are OOM")

    regional_rows = [
        row
        for row in read_region_rows(regional_csv)
        if str(row["variant"]) == str(config["regional_pipeline"]["merge_variant"])
    ]
    regional_images = group_region_rows(regional_rows, expected_regions=12)
    expected_samples = int(config["accuracy"]["expected_sample_count"])
    if len(regional_images) != expected_samples:
        raise ValueError("Regional reference has an unexpected image count")
    budget = int(config["regional_pipeline"]["budget_count"])
    regional_statistics = {
        method: [
            build_image_statistic(
                sample,
                select_region_indices(
                    sample,
                    method=(
                        str(config["regional_pipeline"]["selector"])
                        if method == "fixed"
                        else "oracle_at_most_k_positive"
                    ),
                    budget_count=budget,
                ),
            )
            for sample in regional_images
        ]
        for method in ("fixed", "oracle")
    }
    scan_ids = sorted({str(row["scan_id"]) for row in regional_statistics["oracle"]})
    if len(scan_ids) != int(config["accuracy"]["expected_scan_count"]):
        raise ValueError("Regional reference has an unexpected scan count")

    direct_by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_direct_rows(direct_csv):
        if int(row["input_size"]) not in oom_sizes:
            direct_by_size[int(row["input_size"])].append(row)
    oracle_by_sample = {
        int(row["sample_index"]): row for row in regional_statistics["oracle"]
    }
    direct_statistics: dict[int, list[dict[str, Any]]] = {}
    for size in input_sizes:
        rows = sorted(direct_by_size[size], key=lambda row: row["sample_index"])
        if len(rows) != expected_samples:
            raise ValueError(f"Direct candidate {size} has incomplete accuracy rows")
        if len({int(row["sample_index"]) for row in rows}) != expected_samples:
            raise ValueError(f"Direct candidate {size} has duplicate samples")
        statistics: list[dict[str, Any]] = []
        for row in rows:
            sample_index = int(row["sample_index"])
            reference = oracle_by_sample.get(sample_index)
            if reference is None:
                raise ValueError("Direct candidate contains an unexpected sample")
            if str(row["scan_id"]) != str(reference["scan_id"]):
                raise ValueError("Regional and direct scan identifiers disagree")
            base_primary = float(reference["base_primary"])
            if not np.isclose(
                base_primary,
                float(row["base_primary_error_sum"]),
                rtol=1e-9,
                atol=1e-6,
            ):
                raise ValueError("Regional and direct base errors disagree")
            statistics.append(
                {
                    "sample_index": sample_index,
                    "scan_id": str(row["scan_id"]),
                    "base_primary": base_primary,
                    "utility": float(row["primary_utility_sum"]),
                }
            )
        direct_statistics[size] = statistics

    accuracy_matrices = {
        "fixed": _scan_primary_matrix(
            regional_statistics["fixed"], scan_ids, "selected_primary"
        ),
        "oracle": _scan_primary_matrix(
            regional_statistics["oracle"], scan_ids, "selected_primary"
        ),
        **{
            f"whole_image_{size}": _scan_primary_matrix(
                direct_statistics[size], scan_ids, "utility"
            )
            for size in input_sizes
        },
    }

    def ratio(matrix: np.ndarray, counts: np.ndarray) -> float:
        totals = counts @ matrix
        return float(totals[1] / totals[0])

    full_counts = np.ones(len(scan_ids), dtype=np.float64)
    point_estimates = {
        method: ratio(matrix, full_counts)
        for method, matrix in accuracy_matrices.items()
    }
    point_best_size = max(
        input_sizes,
        key=lambda size: (point_estimates[f"whole_image_{size}"], -size),
    )

    bootstrap = config["bootstrap"]
    replicate_count = int(bootstrap["replicates"])
    confidence_level = float(bootstrap["confidence_level"])
    rng = np.random.default_rng(int(bootstrap["seed"]))
    bootstrap_values = {
        method: np.empty(replicate_count, dtype=np.float64)
        for method in accuracy_matrices
    }
    for replicate_index in range(replicate_count):
        sampled = rng.integers(0, len(scan_ids), size=len(scan_ids))
        counts = np.bincount(sampled, minlength=len(scan_ids)).astype(np.float64)
        for method, matrix in accuracy_matrices.items():
            bootstrap_values[method][replicate_index] = ratio(matrix, counts)

    margin_values, envelope_values, winner_sizes = direct_accuracy_envelope(
        bootstrap_values["oracle"],
        {size: bootstrap_values[f"whole_image_{size}"] for size in input_sizes},
    )
    winner_counts = Counter(winner_sizes)
    intervals = {
        method: confidence_interval(values.tolist(), confidence_level)
        for method, values in bootstrap_values.items()
    }
    margin_interval = confidence_interval(margin_values.tolist(), confidence_level)
    envelope_interval = confidence_interval(envelope_values.tolist(), confidence_level)
    point_margin = (
        point_estimates["oracle"] - point_estimates[f"whole_image_{point_best_size}"]
    )
    accuracy_checks_pass = point_margin > 0 and margin_interval["lower"] > 0
    decision = (
        "PROVISIONAL_ACCURACY_ONLY_GO_ORACLE_MARGIN_OVER_ALL_DIRECT_SIZES"
        if accuracy_checks_pass
        else "PROVISIONAL_ACCURACY_ONLY_STOP_DIRECT_RESOLUTION_ENVELOPE"
    )

    output_rows: list[dict[str, Any]] = []
    for method in ("fixed", "oracle"):
        output_rows.append(
            {
                "method": method,
                "input_size": None,
                "candidate_status": "REGIONAL_REFERENCE",
                "primary_reduction_ratio": point_estimates[method],
                "ci_lower": intervals[method]["lower"],
                "ci_upper": intervals[method]["upper"],
                "replicate_best_direct_probability": 0.0,
            }
        )
    for size in all_input_sizes:
        method = f"whole_image_{size}"
        if size in oom_sizes:
            output_rows.append(
                {
                    "method": method,
                    "input_size": size,
                    "candidate_status": "OOM",
                    "primary_reduction_ratio": None,
                    "ci_lower": None,
                    "ci_upper": None,
                    "replicate_best_direct_probability": 0.0,
                }
            )
            continue
        output_rows.append(
            {
                "method": method,
                "input_size": size,
                "candidate_status": "OK",
                "primary_reduction_ratio": point_estimates[method],
                "ci_lower": intervals[method]["lower"],
                "ci_upper": intervals[method]["upper"],
                "replicate_best_direct_probability": (
                    winner_counts[size] / replicate_count
                ),
            }
        )
    write_csv_atomic(output_csv, output_rows)

    result: dict[str, Any] = {
        "schema_version": 2,
        "status": decision,
        "formal_latency_gate_completed": False,
        "paper_candidate": False,
        "accuracy_only": True,
        "conservative_for_any_future_latency_feasible_subset": True,
        "candidate_selection": (
            "replicate_wise_max_over_all_non_oom_whole_image_sizes"
        ),
        "candidate_count": len(all_input_sizes),
        "non_oom_candidate_count": len(input_sizes),
        "oom_whole_image_input_sizes": sorted(oom_sizes),
        "bootstrap_replicates": replicate_count,
        "point_estimates": point_estimates,
        "cluster_bootstrap_95ci": intervals,
        "point_best_whole_image_input_size": point_best_size,
        "bootstrap_best_whole_image_winner_counts": {
            str(size): winner_counts[size] for size in input_sizes
        },
        "accuracy_only_gate": {
            "decision": decision,
            "point_oracle_minus_best_direct": point_margin,
            "paired_envelope_bootstrap_95ci": margin_interval,
            "direct_envelope_bootstrap_95ci": envelope_interval,
            "all_statistical_checks_pass": accuracy_checks_pass,
            "does_not_complete_formal_latency_gate": True,
        },
        "bindings": {
            "config_sha256": config_digest,
            "regional_csv_sha256": file_digest(regional_csv),
            "regional_provenance_sha256": file_digest(regional_provenance_path),
            "direct_csv_sha256": file_digest(direct_csv),
            "direct_provenance_sha256": file_digest(direct_provenance_path),
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
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Run the W07-v2 accuracy-only stage analysis."""
    args = parse_args()
    result = analyze_direct_resolution_accuracy_v2(
        config_path=args.config,
        regional_csv=args.regional_csv,
        regional_provenance_path=args.regional_provenance,
        direct_csv=args.direct_csv,
        direct_provenance_path=args.direct_provenance,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(result["status"])


if __name__ == "__main__":
    main()
