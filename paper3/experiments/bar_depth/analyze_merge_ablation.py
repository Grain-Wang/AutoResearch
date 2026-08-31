"""Analyze frozen BAR-Depth merge and no-extra-forward controls."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np

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
from .io_utils import file_digest, read_json, write_csv_atomic, write_json_atomic
from .run_merge_ablation import NO_FORWARD_VARIANTS, PATCH_VARIANTS


def apply_patch_necessity_gate(
    *,
    highpass_estimate: float,
    cheap_estimate: float,
    paired_differences: list[float],
    confidence_level: float,
    require_ci_lower_above_zero: bool,
) -> dict[str, Any]:
    """Apply the frozen patch-inference necessity gate."""
    interval = confidence_interval(paired_differences, confidence_level)
    point_difference = highpass_estimate - cheap_estimate
    point_pass = point_difference > 0
    ci_pass = interval["lower"] > 0
    all_pass = point_pass and (ci_pass if require_ci_lower_above_zero else True)
    return {
        "decision": (
            "GO_PATCH_INFORMATION_NECESSARY"
            if all_pass
            else "STOP_PATCH_INFERENCE_NOT_NECESSARY"
        ),
        "all_pass": all_pass,
        "point_pass": point_pass,
        "paired_ci_pass": ci_pass,
        "difference": point_difference,
        "paired_scan_bootstrap_95ci": interval,
    }


def analyze_merge_ablation(
    *,
    config_path: Path,
    input_csv: Path,
    provenance_path: Path,
    output_csv: Path,
    output_json: Path,
) -> dict[str, Any]:
    """Compare merge variants with paired scan bootstrap and apply the gate."""
    config = read_json(config_path)
    provenance = read_json(provenance_path)
    if provenance["output_csv_sha256"] != file_digest(input_csv):
        raise ValueError("Merge-ablation CSV does not match provenance")
    if provenance["contract"]["config_sha256"] != file_digest(config_path):
        raise ValueError("Merge-ablation config does not match provenance")
    rows = read_region_rows(input_csv)
    variants = [str(value) for value in config["variants"]]
    expected_rows = (
        int(provenance["sample_count"]) * 12 * int(provenance["variant_count"])
    )
    if len(rows) != expected_rows:
        raise ValueError("Unexpected merge-ablation row count")
    budget_count = int(config["selection"]["budget_count"])
    fixed_selector = str(config["selection"]["fixed_selector"])

    statistics: dict[tuple[str, str], list[dict[str, Any]]] = {}
    scan_ids: list[str] | None = None
    for variant in variants:
        variant_rows = [row for row in rows if row["variant"] == variant]
        images = group_region_rows(variant_rows, expected_regions=12)
        current_scan_ids = sorted({str(sample[0]["scan_id"]) for sample in images})
        if scan_ids is None:
            scan_ids = current_scan_ids
        elif current_scan_ids != scan_ids:
            raise ValueError("Merge variants do not share scan clusters")
        for selector in (
            fixed_selector,
            "oracle_at_most_k_positive",
            "all_12_regions",
            "oracle_all_positive",
        ):
            selector_statistics: list[dict[str, Any]] = []
            for sample in images:
                if selector == "all_12_regions":
                    selected = select_region_indices(
                        sample,
                        method="all_12_regions",
                        budget_count=len(sample),
                    )
                elif selector in {
                    "oracle_at_most_k_positive",
                    "oracle_all_positive",
                }:
                    selected = select_region_indices(
                        sample,
                        method="oracle_at_most_k_positive",
                        budget_count=(
                            len(sample)
                            if selector == "oracle_all_positive"
                            else budget_count
                        ),
                    )
                else:
                    selected = select_region_indices(
                        sample,
                        method=selector,
                        budget_count=budget_count,
                    )
                selector_statistics.append(build_image_statistic(sample, selected))
            statistics[(variant, selector)] = selector_statistics
    if scan_ids is None:
        raise ValueError("Merge-ablation input has no scans")

    matrices = {
        key: scan_matrix(values, scan_ids) for key, values in statistics.items()
    }
    public_keys = [
        (variant, selector)
        for variant in variants
        for selector in (
            fixed_selector,
            "oracle_at_most_k_positive",
            "all_12_regions",
        )
    ]
    estimates: dict[tuple[str, str], dict[str, float]] = {}
    for variant, selector in public_keys:
        oracle_selector = (
            "oracle_all_positive"
            if selector == "all_12_regions"
            else "oracle_at_most_k_positive"
        )
        estimates[(variant, selector)] = aggregate_sufficient(
            matrices[(variant, selector)].sum(axis=0),
            matrices[(variant, oracle_selector)].sum(axis=0),
        )

    bootstrap_config = config["bootstrap"]
    rng = np.random.default_rng(int(bootstrap_config["seed"]))
    scan_count = len(scan_ids)
    bootstrap_values = {
        key: {metric: [] for metric in METRIC_KEYS} for key in public_keys
    }
    for _ in range(int(bootstrap_config["replicates"])):
        sampled = rng.integers(0, scan_count, size=scan_count)
        counts = np.bincount(sampled, minlength=scan_count).astype(np.float64)
        for variant, selector in public_keys:
            oracle_selector = (
                "oracle_all_positive"
                if selector == "all_12_regions"
                else "oracle_at_most_k_positive"
            )
            metrics = aggregate_sufficient(
                counts @ matrices[(variant, selector)],
                counts @ matrices[(variant, oracle_selector)],
            )
            for metric, value in metrics.items():
                bootstrap_values[(variant, selector)][metric].append(value)
    confidence_level = float(bootstrap_config["confidence_level"])
    intervals = {
        key: {
            metric: confidence_interval(values, confidence_level)
            for metric, values in metrics.items()
        }
        for key, metrics in bootstrap_values.items()
    }

    primary_metric = "signed_primary_error_reduction_ratio"
    cheap_variants = sorted(set(variants) & NO_FORWARD_VARIANTS)
    best_cheap = max(
        cheap_variants,
        key=lambda variant: estimates[(variant, fixed_selector)][primary_metric],
    )
    highpass_key = ("highpass_residual", fixed_selector)
    cheap_key = (best_cheap, fixed_selector)
    paired_differences = (
        np.asarray(bootstrap_values[highpass_key][primary_metric])
        - np.asarray(bootstrap_values[cheap_key][primary_metric])
    ).tolist()
    gate_config = config["patch_necessity_gate"]
    gate = apply_patch_necessity_gate(
        highpass_estimate=estimates[highpass_key][primary_metric],
        cheap_estimate=estimates[cheap_key][primary_metric],
        paired_differences=paired_differences,
        confidence_level=confidence_level,
        require_ci_lower_above_zero=bool(
            gate_config["require_paired_ci_lower_above_zero"]
        ),
    )
    gate["best_no_extra_forward_variant"] = best_cheap
    gate["fixed_selector"] = fixed_selector

    csv_rows: list[dict[str, Any]] = []
    for variant, selector in public_keys:
        for metric in METRIC_KEYS:
            csv_rows.append(
                {
                    "variant": variant,
                    "selector": selector,
                    "metric": metric,
                    "estimate": estimates[(variant, selector)][metric],
                    "ci_lower": intervals[(variant, selector)][metric]["lower"],
                    "ci_upper": intervals[(variant, selector)][metric]["upper"],
                }
            )
    write_csv_atomic(output_csv, csv_rows)

    def serialize(
        values: dict[tuple[str, str], dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return {
            f"{variant}__{selector}": value
            for (variant, selector), value in values.items()
        }

    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": gate["decision"],
        "paper_candidate": False,
        "sample_count": int(provenance["sample_count"]),
        "scan_count": len(scan_ids),
        "variants": variants,
        "patch_variants": sorted(PATCH_VARIANTS),
        "no_extra_forward_variants": cheap_variants,
        "estimates": serialize(estimates),
        "cluster_bootstrap_95ci": serialize(intervals),
        "patch_necessity_gate": gate,
        "bindings": {
            "config_sha256": file_digest(config_path),
            "input_csv_sha256": file_digest(input_csv),
            "raw_provenance_sha256": file_digest(provenance_path),
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
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--raw-provenance", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Analyze the merge ablation from the command line."""
    args = parse_args()
    summary = analyze_merge_ablation(
        config_path=args.config,
        input_csv=args.input_csv,
        provenance_path=args.raw_provenance,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(summary["status"])


if __name__ == "__main__":
    main()
