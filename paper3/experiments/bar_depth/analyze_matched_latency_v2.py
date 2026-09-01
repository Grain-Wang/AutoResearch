"""Analyze matched latency with timing resampling and a feasible max envelope."""

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
from .analyze_matched_latency import _latency_evidence_mode, _read_direct_rows
from .analyze_oracle_canary import read_region_rows
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic


def select_best_feasible_candidate(
    *,
    direct_accuracy: dict[int, float],
    direct_latency: dict[int, tuple[float, float]],
    regional_latency: tuple[float, float],
) -> tuple[int, list[int]]:
    """Select the most accurate candidate satisfying both latency percentiles."""
    feasible = [
        size
        for size in sorted(direct_accuracy)
        if direct_latency[size][0] <= regional_latency[0]
        and direct_latency[size][1] <= regional_latency[1]
    ]
    if not feasible:
        raise ValueError("No direct-resolution candidate is latency-feasible")
    best = max(feasible, key=lambda size: (direct_accuracy[size], -size))
    return best, feasible


def _timing_matrix(
    raw_measurements: list[dict[str, Any]], methods: list[str]
) -> tuple[list[tuple[str, int, int]], dict[str, np.ndarray]]:
    by_method: dict[str, dict[tuple[str, int, int], float]] = {
        method: {} for method in methods
    }
    for row in raw_measurements:
        method = str(row["method"])
        if method not in by_method:
            continue
        if str(row.get("status", "OK")) != "OK":
            continue
        unit = (
            str(row.get("session_id", "session-1")),
            int(row["sample_index"]),
            int(row.get("repeat_index", 0)),
        )
        if unit in by_method[method]:
            raise ValueError(f"Duplicate timing unit for {method}: {unit}")
        by_method[method][unit] = float(row["milliseconds"])
    common_units = sorted(set.intersection(*(set(rows) for rows in by_method.values())))
    if len(common_units) < 10:
        raise ValueError("Matched-latency bootstrap needs at least ten paired units")
    matrices = {
        method: np.asarray([by_method[method][unit] for unit in common_units])
        for method in methods
    }
    return common_units, matrices


def candidate_range_is_closed(
    *,
    input_sizes: list[int],
    direct_latency: dict[int, tuple[float, float]],
    regional_latency: tuple[float, float],
    oom_sizes: set[int],
    required_consecutive: int,
) -> bool:
    """Apply the frozen direct-range closure rule."""
    consecutive = 0
    for size in input_sizes:
        if size in oom_sizes:
            consecutive = 0
            continue
        latency = direct_latency[size]
        if latency[0] > regional_latency[0] and latency[1] > regional_latency[1]:
            consecutive += 1
            if consecutive >= required_consecutive:
                return True
        else:
            consecutive = 0
    if oom_sizes:
        first_oom = min(oom_sizes)
        later_sizes = {size for size in input_sizes if size >= first_oom}
        if later_sizes and later_sizes == oom_sizes:
            return True
    return False


def session_relative_difference(first: float, second: float) -> float:
    """Return a symmetric relative difference for two session estimates."""
    denominator = 0.5 * (abs(first) + abs(second))
    if denominator == 0:
        return 0.0 if first == second else float("inf")
    return abs(first - second) / denominator


def _read_direct_rows_with_status(
    path: Path, schema_version: int
) -> list[dict[str, Any]]:
    if schema_version == 1:
        return _read_direct_rows(path)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            if str(raw["status"]) != "OK":
                continue
            rows.append(
                {
                    **raw,
                    "sample_index": int(raw["sample_index"]),
                    "input_size": int(raw["input_size"]),
                    "base_primary_error_sum": float(raw["base_primary_error_sum"]),
                    "primary_utility_sum": float(raw["primary_utility_sum"]),
                }
            )
    return rows


def _load_latency_evidence(
    *,
    latency_paths: list[Path],
    latency_config_path: Path | None,
    direct_config_digest: str,
    allow_shared_diagnostic: bool,
) -> tuple[list[dict[str, Any]], str, bool, dict[str, Any], set[int]]:
    artifacts = [read_json(path) for path in latency_paths]
    if len(artifacts) == 1 and latency_config_path is None:
        artifact = artifacts[0]
        if artifact["bindings"]["config_sha256"] != direct_config_digest:
            raise ValueError("Latency used a different W07 config")
        mode, formal = _latency_evidence_mode(
            str(artifact["status"]), allow_shared_diagnostic
        )
        return (
            list(artifact["raw_measurements"]),
            mode,
            formal,
            {"session_reproducibility_pass": False, "session_count": 1},
            set(),
        )

    if latency_config_path is None or len(artifacts) != 2:
        raise ValueError("Formal W07-v2 requires two artifacts and a latency config")
    latency_config = read_json(latency_config_path)
    latency_config_digest = file_digest(latency_config_path)
    if latency_config["direct_resolution_config_sha256"] != direct_config_digest:
        raise ValueError("Latency contract targets a different direct sweep")
    expected_sessions = list(latency_config["independent_sessions"])
    by_session = {str(artifact["session_id"]): artifact for artifact in artifacts}
    if sorted(by_session) != sorted(expected_sessions):
        raise ValueError("Formal W07-v2 session identifiers are incomplete")
    for artifact in artifacts:
        if artifact["status"] != "COMPLETE_EXCLUSIVE_MATCHED_LATENCY_V2_SESSION":
            raise ValueError("Formal W07-v2 contains an incomplete session")
        if artifact["bindings"]["config_sha256"] != latency_config_digest:
            raise ValueError("Latency session used a different v2 contract")
        if (
            artifact["bindings"]["direct_resolution_config_sha256"]
            != direct_config_digest
        ):
            raise ValueError("Latency session used a different direct contract")

    first = by_session[expected_sessions[0]]
    second = by_session[expected_sessions[1]]
    first_oom = set(first["oom_methods"])
    second_oom = set(second["oom_methods"])
    if first_oom != second_oom:
        raise ValueError("Independent sessions disagree on OOM candidates")
    all_methods = sorted(set(first["summaries"]) | set(second["summaries"]))
    p50_limit = float(
        latency_config["session_reproducibility"]["maximum_relative_p50_difference"]
    )
    p95_limit = float(
        latency_config["session_reproducibility"]["maximum_relative_p95_difference"]
    )
    differences: dict[str, dict[str, float]] = {}
    for method in all_methods:
        if method in first_oom:
            continue
        first_summary = first["summaries"][method]["milliseconds"]
        second_summary = second["summaries"][method]["milliseconds"]
        differences[method] = {
            "p50_relative_difference": session_relative_difference(
                float(first_summary["p50_milliseconds"]),
                float(second_summary["p50_milliseconds"]),
            ),
            "p95_relative_difference": session_relative_difference(
                float(first_summary["p95_milliseconds"]),
                float(second_summary["p95_milliseconds"]),
            ),
        }
    reproducible = all(
        row["p50_relative_difference"] <= p50_limit
        and row["p95_relative_difference"] <= p95_limit
        for row in differences.values()
    )
    raw_measurements = [
        row for artifact in artifacts for row in artifact["raw_measurements"]
    ]
    oom_sizes = {
        int(method.rsplit("_", 1)[1])
        for method in first_oom
        if method.startswith("whole_image_")
    }
    return (
        raw_measurements,
        "exclusive_v2_two_sessions",
        reproducible,
        {
            "session_count": 2,
            "session_reproducibility_pass": reproducible,
            "maximum_relative_p50_difference": p50_limit,
            "maximum_relative_p95_difference": p95_limit,
            "per_method_relative_differences": differences,
        },
        oom_sizes,
    )


def analyze_matched_latency_v2(
    *,
    config_path: Path,
    regional_csv: Path,
    regional_provenance_path: Path,
    direct_csv: Path,
    direct_provenance_path: Path,
    latency_paths: list[Path],
    latency_config_path: Path | None,
    output_csv: Path,
    output_json: Path,
    allow_shared_diagnostic: bool,
) -> dict[str, Any]:
    """Bootstrap accuracy and timing while reselecting the feasible direct killer."""
    config = read_json(config_path)
    regional_provenance = read_json(regional_provenance_path)
    direct_provenance = read_json(direct_provenance_path)
    config_digest = file_digest(config_path)
    if regional_provenance["output_csv_sha256"] != file_digest(regional_csv):
        raise ValueError("Regional CSV does not match provenance")
    if direct_provenance["output_csv_sha256"] != file_digest(direct_csv):
        raise ValueError("Direct CSV does not match provenance")
    if direct_provenance["contract"]["config_sha256"] != config_digest:
        raise ValueError("Direct accuracy used a different W07 config")
    (
        raw_latency_rows,
        latency_mode,
        formal_gate_completed,
        session_checks,
        latency_oom_sizes,
    ) = _load_latency_evidence(
        latency_paths=latency_paths,
        latency_config_path=latency_config_path,
        direct_config_digest=config_digest,
        allow_shared_diagnostic=allow_shared_diagnostic,
    )

    regional_rows = [
        row
        for row in read_region_rows(regional_csv)
        if str(row["variant"]) == str(config["regional_pipeline"]["merge_variant"])
    ]
    regional_images = group_region_rows(regional_rows, expected_regions=12)
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

    all_input_sizes = [int(value) for value in config["whole_image_input_sizes"]]
    accuracy_oom_sizes = {
        int(value) for value in direct_provenance.get("oom_sizes", [])
    }
    if accuracy_oom_sizes != latency_oom_sizes and latency_config_path is not None:
        raise ValueError("Accuracy and latency runs disagree on OOM candidates")
    oom_sizes = accuracy_oom_sizes | latency_oom_sizes
    input_sizes = [size for size in all_input_sizes if size not in oom_sizes]
    if not input_sizes:
        raise ValueError("All direct-resolution candidates are OOM")
    direct_by_size: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_direct_rows_with_status(
        direct_csv, int(direct_provenance["schema_version"])
    ):
        direct_by_size[int(row["input_size"])].append(row)
    expected_samples = int(config["accuracy"]["expected_sample_count"])
    if any(len(direct_by_size[size]) != expected_samples for size in input_sizes):
        raise ValueError("Direct candidates have incomplete accuracy rows")
    oracle_by_sample = {
        int(row["sample_index"]): row for row in regional_statistics["oracle"]
    }
    direct_statistics: dict[int, list[dict[str, Any]]] = {}
    for size in input_sizes:
        statistics: list[dict[str, Any]] = []
        for row in sorted(direct_by_size[size], key=lambda item: item["sample_index"]):
            sample_index = int(row["sample_index"])
            base_primary = float(oracle_by_sample[sample_index]["base_primary"])
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

    scan_ids = sorted({str(row["scan_id"]) for row in regional_statistics["oracle"]})

    def scan_sums(statistics: list[dict[str, Any]], key: str) -> np.ndarray:
        by_scan = {scan_id: np.zeros(2, dtype=np.float64) for scan_id in scan_ids}
        for row in statistics:
            by_scan[str(row["scan_id"])] += np.asarray(
                [float(row["base_primary"]), float(row[key])]
            )
        return np.stack([by_scan[scan_id] for scan_id in scan_ids])

    accuracy_matrices = {
        "fixed": scan_sums(regional_statistics["fixed"], "selected_primary"),
        "oracle": scan_sums(regional_statistics["oracle"], "selected_primary"),
        **{
            f"whole_image_{size}": scan_sums(direct_statistics[size], "utility")
            for size in input_sizes
        },
    }

    methods = ["regional_k3", *[f"whole_image_{size}" for size in input_sizes]]
    timing_units, timing_matrices = _timing_matrix(raw_latency_rows, methods)
    point_latency = {
        method: (
            float(np.percentile(timing_matrices[method], 50)),
            float(np.percentile(timing_matrices[method], 95)),
        )
        for method in methods
    }
    required_consecutive = int(
        config.get("candidate_range_closure", {}).get(
            "required_consecutive_infeasible_sizes", 2
        )
    )
    range_closed = candidate_range_is_closed(
        input_sizes=all_input_sizes,
        direct_latency={
            size: point_latency[f"whole_image_{size}"] for size in input_sizes
        },
        regional_latency=point_latency["regional_k3"],
        oom_sizes=oom_sizes,
        required_consecutive=required_consecutive,
    )
    if latency_config_path is not None:
        formal_gate_completed = formal_gate_completed and range_closed

    def ratio(matrix: np.ndarray, counts: np.ndarray) -> float:
        totals = counts @ matrix
        return float(totals[1] / totals[0])

    full_counts = np.ones(len(scan_ids), dtype=np.float64)
    point_accuracy = {
        method: ratio(matrix, full_counts)
        for method, matrix in accuracy_matrices.items()
    }
    point_best, point_feasible = select_best_feasible_candidate(
        direct_accuracy={
            size: point_accuracy[f"whole_image_{size}"] for size in input_sizes
        },
        direct_latency={
            size: point_latency[f"whole_image_{size}"] for size in input_sizes
        },
        regional_latency=point_latency["regional_k3"],
    )

    bootstrap = config["bootstrap"]
    replicates = int(bootstrap["replicates"])
    confidence_level = float(bootstrap["confidence_level"])
    rng = np.random.default_rng(int(bootstrap["seed"]))
    margin_values: list[float] = []
    oracle_values: list[float] = []
    fixed_values: list[float] = []
    direct_values: dict[int, list[float]] = {size: [] for size in input_sizes}
    feasible_counts = Counter({size: 0 for size in input_sizes})
    winner_counts = Counter({size: 0 for size in input_sizes})
    for _ in range(replicates):
        sampled_scans = rng.integers(0, len(scan_ids), size=len(scan_ids))
        scan_counts = np.bincount(sampled_scans, minlength=len(scan_ids)).astype(
            np.float64
        )
        sampled_timing = rng.integers(0, len(timing_units), size=len(timing_units))
        regional_latency = (
            float(np.percentile(timing_matrices["regional_k3"][sampled_timing], 50)),
            float(np.percentile(timing_matrices["regional_k3"][sampled_timing], 95)),
        )
        direct_accuracy = {
            size: ratio(accuracy_matrices[f"whole_image_{size}"], scan_counts)
            for size in input_sizes
        }
        direct_latency = {
            size: (
                float(
                    np.percentile(
                        timing_matrices[f"whole_image_{size}"][sampled_timing], 50
                    )
                ),
                float(
                    np.percentile(
                        timing_matrices[f"whole_image_{size}"][sampled_timing], 95
                    )
                ),
            )
            for size in input_sizes
        }
        best, feasible = select_best_feasible_candidate(
            direct_accuracy=direct_accuracy,
            direct_latency=direct_latency,
            regional_latency=regional_latency,
        )
        for size in feasible:
            feasible_counts[size] += 1
        winner_counts[best] += 1
        oracle = ratio(accuracy_matrices["oracle"], scan_counts)
        fixed = ratio(accuracy_matrices["fixed"], scan_counts)
        oracle_values.append(oracle)
        fixed_values.append(fixed)
        for size, value in direct_accuracy.items():
            direct_values[size].append(value)
        margin_values.append(oracle - direct_accuracy[best])

    margin_interval = confidence_interval(margin_values, confidence_level)
    point_margin = (
        point_accuracy["oracle"] - point_accuracy[f"whole_image_{point_best}"]
    )
    all_pass = point_margin > 0 and margin_interval["lower"] > 0
    formal_decision = (
        "GO_REGIONAL_ORACLE_PARETO_FORMAL_V2"
        if all_pass
        else "STOP_DIRECT_RESOLUTION_DOMINATES_FORMAL_V2"
    )
    decision = (
        formal_decision
        if formal_gate_completed
        else f"PROVISIONAL_NOT_FORMAL_{formal_decision}"
    )

    intervals = {
        "fixed": confidence_interval(fixed_values, confidence_level),
        "oracle": confidence_interval(oracle_values, confidence_level),
        **{
            f"whole_image_{size}": confidence_interval(values, confidence_level)
            for size, values in direct_values.items()
        },
    }
    output_rows = []
    for method, estimate in point_accuracy.items():
        latency_method = "regional_k3" if method in {"fixed", "oracle"} else method
        size = None if method in {"fixed", "oracle"} else int(method.rsplit("_", 1)[1])
        output_rows.append(
            {
                "method": method,
                "input_size": size,
                "primary_reduction_ratio": estimate,
                "ci_lower": intervals[method]["lower"],
                "ci_upper": intervals[method]["upper"],
                "p50_milliseconds": point_latency[latency_method][0],
                "p95_milliseconds": point_latency[latency_method][1],
                "point_latency_feasible": (
                    True if size is None else size in point_feasible
                ),
                "bootstrap_feasibility_probability": (
                    1.0 if size is None else feasible_counts[size] / replicates
                ),
                "bootstrap_best_feasible_probability": (
                    0.0 if size is None else winner_counts[size] / replicates
                ),
            }
        )
    write_csv_atomic(output_csv, output_rows)

    result: dict[str, Any] = {
        "schema_version": 2,
        "status": decision,
        "formal_gate_completed": formal_gate_completed,
        "latency_evidence_mode": latency_mode,
        "session_checks": session_checks,
        "candidate_range_closed": range_closed,
        "oom_whole_image_input_sizes": sorted(oom_sizes),
        "paper_candidate": False,
        "replicate_wise_max_envelope": True,
        "timing_rows_resampled": True,
        "paired_timing_unit_count": len(timing_units),
        "bootstrap_replicates": replicates,
        "point_estimates": point_accuracy,
        "cluster_bootstrap_95ci": intervals,
        "point_latency_milliseconds": {
            method: {"p50": values[0], "p95": values[1]}
            for method, values in point_latency.items()
        },
        "point_feasible_whole_image_input_sizes": point_feasible,
        "point_best_feasible_whole_image_input_size": point_best,
        "bootstrap_feasibility_probability": {
            str(size): feasible_counts[size] / replicates for size in input_sizes
        },
        "bootstrap_best_feasible_winner_counts": {
            str(size): winner_counts[size] for size in input_sizes
        },
        "pareto_gate": {
            "decision": decision,
            "formal_decision_if_evidence_were_exclusive": formal_decision,
            "point_difference": point_margin,
            "paired_joint_bootstrap_95ci": margin_interval,
            "all_statistical_checks_pass": all_pass,
        },
        "bindings": {
            "config_sha256": config_digest,
            "regional_csv_sha256": file_digest(regional_csv),
            "regional_provenance_sha256": file_digest(regional_provenance_path),
            "direct_csv_sha256": file_digest(direct_csv),
            "direct_provenance_sha256": file_digest(direct_provenance_path),
            "latency_sha256": {path.name: file_digest(path) for path in latency_paths},
            "latency_config_sha256": (
                None
                if latency_config_path is None
                else file_digest(latency_config_path)
            ),
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
    parser.add_argument("--latency", type=Path, nargs="+", required=True)
    parser.add_argument("--latency-config", type=Path)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--allow-shared-diagnostic", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Run the joint accuracy/timing bootstrap."""
    args = parse_args()
    result = analyze_matched_latency_v2(
        config_path=args.config,
        regional_csv=args.regional_csv,
        regional_provenance_path=args.regional_provenance,
        direct_csv=args.direct_csv,
        direct_provenance_path=args.direct_provenance,
        latency_paths=args.latency,
        latency_config_path=args.latency_config,
        output_csv=args.output_csv,
        output_json=args.output_json,
        allow_shared_diagnostic=args.allow_shared_diagnostic,
    )
    print(result["status"])


if __name__ == "__main__":
    main()
