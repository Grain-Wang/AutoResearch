"""Evaluate the budget-matched Boosting MDE 2021 selector on BAR actions."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .analyze_budget_baselines import (
    METRIC_KEYS,
    aggregate_sufficient,
    build_image_statistic,
    confidence_interval,
    group_region_rows,
    scan_matrix,
    select_region_indices,
)
from .analyze_oracle_canary import read_region_rows
from .core import make_regions
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic
from .selectors.boosting2021_selector import (
    boosting_score_records,
    score_fixed_regions,
    select_boosting_regions,
)


def analyze_boosting_selector(
    *, config_path: Path, output_csv: Path, output_json: Path
) -> dict[str, Any]:
    """Score the frozen cells, evaluate signed utility, and apply the G0 gate."""
    config = read_json(config_path)
    input_csv = Path(config["input_csv"])
    raw_provenance_path = Path(config["raw_provenance"])
    raw_provenance = read_json(raw_provenance_path)
    if raw_provenance["output_csv_sha256"] != file_digest(input_csv):
        raise ValueError("Frozen utility CSV does not match raw provenance")
    fidelity_path = Path(config["fidelity_audit"])
    fidelity = read_json(fidelity_path)
    if fidelity["status"] != "PASS":
        raise ValueError("Boosting selector fidelity audit did not pass")
    if fidelity["official_revision"] != config["official_revision"]:
        raise ValueError("Boosting selector revision differs from fidelity audit")
    extract_audit_path = Path(config["rgb_extract_audit"])
    extract_audit = read_json(extract_audit_path)
    if extract_audit["status"] != "PASS":
        raise ValueError("DIODE RGB extraction audit did not pass")
    extracted_hashes = {
        str(record["image_relpath"]): str(record["image_sha256"])
        for record in extract_audit["records"]
    }

    rows = read_region_rows(input_csv)
    region_count = int(config["region_rows"]) * int(config["region_columns"])
    images = group_region_rows(rows, region_count)
    if len(images) != int(config["expected_sample_count"]):
        raise ValueError("Unexpected image count")
    scan_ids = sorted({str(sample[0]["scan_id"]) for sample in images})
    if len(scan_ids) != int(config["expected_scan_count"]):
        raise ValueError("Unexpected scan count")

    budget_count = int(config["budget_count"])
    image_root = Path(config["image_root"])
    statistics: dict[str, list[dict[str, Any]]] = {
        "boosting2021_exact_k": [],
        "boosting2021_at_most_k_official_threshold": [],
        "prior_strongest_simple": [],
        "oracle_at_most_k_positive": [],
    }
    score_rows: list[dict[str, Any]] = []
    score_seconds: list[float] = []
    prior_summary = read_json(Path(config["budget_baseline_summary"]))
    prior_method = str(
        prior_summary["oracle_margins"][str(budget_count)][
            "strongest_non_oracle_method"
        ]
    )

    for sample in images:
        relative_path = str(sample[0]["image_relpath"])
        image_path = image_root / relative_path
        if relative_path not in extracted_hashes:
            raise ValueError(f"RGB extraction audit lacks {relative_path}")
        if file_digest(image_path) != extracted_hashes[relative_path]:
            raise ValueError(f"Extracted RGB hash mismatch for {relative_path}")
        with Image.open(image_path) as handle:
            image_rgb = np.asarray(handle.convert("RGB"))
        if image_rgb.shape[:2] != (
            int(config["expected_height"]),
            int(config["expected_width"]),
        ):
            raise ValueError(f"Unexpected RGB dimensions for {relative_path}")
        regions = make_regions(
            image_rgb.shape[0],
            image_rgb.shape[1],
            int(config["region_rows"]),
            int(config["region_columns"]),
            context_scale=1.0,
        )
        started = time.perf_counter()
        scores, global_density = score_fixed_regions(image_rgb, regions)
        score_seconds.append(time.perf_counter() - started)
        exact_selected = select_boosting_regions(
            scores,
            budget_count=budget_count,
            require_official_density_threshold=False,
        )
        threshold_selected = select_boosting_regions(
            scores,
            budget_count=budget_count,
            require_official_density_threshold=True,
        )
        prior_selected = select_region_indices(
            sample, method=prior_method, budget_count=budget_count
        )
        oracle_selected = select_region_indices(
            sample,
            method="oracle_at_most_k_positive",
            budget_count=budget_count,
        )
        selections = {
            "boosting2021_exact_k": exact_selected,
            "boosting2021_at_most_k_official_threshold": threshold_selected,
            "prior_strongest_simple": prior_selected,
            "oracle_at_most_k_positive": oracle_selected,
        }
        for method, selected in selections.items():
            statistics[method].append(build_image_statistic(sample, selected))
        records = boosting_score_records(scores, exact_selected, threshold_selected)
        for record in records:
            region_id = int(record["region_id"])
            score_rows.append(
                {
                    "sample_index": int(sample[0]["sample_index"]),
                    "scan_id": str(sample[0]["scan_id"]),
                    "image_relpath": relative_path,
                    "global_thresholded_gradient_density": global_density,
                    **record,
                    "primary_utility_sum": float(
                        sample[region_id]["primary_utility_sum"]
                    ),
                    "absrel_utility_sum": float(
                        sample[region_id]["absrel_utility_sum"]
                    ),
                }
            )

    write_csv_atomic(output_csv, score_rows)
    matrices = {
        method: scan_matrix(values, scan_ids) for method, values in statistics.items()
    }
    oracle_matrix = matrices["oracle_at_most_k_positive"]
    estimates = {
        method: aggregate_sufficient(matrix.sum(axis=0), oracle_matrix.sum(axis=0))
        for method, matrix in matrices.items()
    }
    bootstrap_config = config["bootstrap"]
    rng = np.random.default_rng(int(bootstrap_config["seed"]))
    bootstrap_values = {
        method: {metric: [] for metric in METRIC_KEYS} for method in matrices
    }
    scan_count = len(scan_ids)
    for _ in range(int(bootstrap_config["replicates"])):
        sampled = rng.integers(0, scan_count, size=scan_count)
        counts = np.bincount(sampled, minlength=scan_count).astype(np.float64)
        oracle_sufficient = counts @ oracle_matrix
        for method, matrix in matrices.items():
            metrics = aggregate_sufficient(counts @ matrix, oracle_sufficient)
            for metric, value in metrics.items():
                bootstrap_values[method][metric].append(value)
    confidence_level = float(bootstrap_config["confidence_level"])
    intervals = {
        method: {
            metric: confidence_interval(values, confidence_level)
            for metric, values in metrics.items()
        }
        for method, metrics in bootstrap_values.items()
    }

    killer_methods = (
        "prior_strongest_simple",
        "boosting2021_exact_k",
        "boosting2021_at_most_k_official_threshold",
    )
    strongest = max(
        killer_methods,
        key=lambda method: estimates[method]["signed_primary_error_reduction_ratio"],
    )
    oracle_values = np.asarray(
        bootstrap_values["oracle_at_most_k_positive"][
            "signed_primary_error_reduction_ratio"
        ]
    )
    strongest_values = np.asarray(
        bootstrap_values[strongest]["signed_primary_error_reduction_ratio"]
    )
    margin_values = (oracle_values - strongest_values).tolist()
    margin = {
        "strongest_method": strongest,
        "prior_strongest_method_name": prior_method,
        "difference": estimates["oracle_at_most_k_positive"][
            "signed_primary_error_reduction_ratio"
        ]
        - estimates[strongest]["signed_primary_error_reduction_ratio"],
        "paired_scan_bootstrap_95ci": confidence_interval(
            margin_values, confidence_level
        ),
    }
    gate_config = config["g0_oracle_margin_gate"]
    point_pass = float(margin["difference"]) >= float(
        gate_config["min_primary_reduction_difference"]
    )
    ci_pass = float(margin["paired_scan_bootstrap_95ci"]["lower"]) > 0
    gate_pass = point_pass and (
        ci_pass if bool(gate_config["require_paired_ci_lower_above_zero"]) else True
    )
    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": (
            "GO_ORACLE_MARGIN_OVER_BOOSTING2021"
            if gate_pass
            else "STOP_NO_ORACLE_MARGIN_OVER_KILLER"
        ),
        "paper_candidate": False,
        "sample_count": len(images),
        "scan_count": len(scan_ids),
        "budget_count": budget_count,
        "estimates": estimates,
        "cluster_bootstrap_95ci": intervals,
        "oracle_margin_over_strongest_killer": margin,
        "g0_oracle_margin_gate": {
            "all_pass": gate_pass,
            "point_margin_pass": point_pass,
            "paired_ci_pass": ci_pass,
            "thresholds": gate_config,
        },
        "selector_cpu_timing_diagnostic": {
            "interpretation": "local_cpu_diagnostic_not_gpu_efficiency_claim",
            "p50_seconds": float(np.median(score_seconds)),
            "p90_seconds": float(np.quantile(score_seconds, 0.9)),
            "total_seconds": float(sum(score_seconds)),
        },
        "fidelity": {
            "official_revision": fidelity["official_revision"],
            "official_example_audit_status": fidelity["status"],
            "adaptation": fidelity["adaptation"],
        },
        "bindings": {
            "config_sha256": file_digest(config_path),
            "input_csv_sha256": file_digest(input_csv),
            "raw_provenance_sha256": file_digest(raw_provenance_path),
            "fidelity_audit_sha256": file_digest(fidelity_path),
            "rgb_extract_audit_sha256": file_digest(extract_audit_path),
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
    """Run the Boosting selector analysis from the command line."""
    args = parse_args()
    summary = analyze_boosting_selector(
        config_path=args.config,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(summary["status"])


if __name__ == "__main__":
    main()
