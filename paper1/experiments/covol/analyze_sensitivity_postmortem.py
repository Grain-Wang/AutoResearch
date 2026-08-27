"""Exploratory postmortem for the stopped CoVoL sensitivity diagnostic."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

CONTROL_FAMILY = "semantic_preserving"
INTERVENTION_FAMILIES = (
    "target_deletion",
    "local_entity_conflict",
    "depth_relation_conflict",
)
ANALYSIS_STATUS = "EXPLORATORY_POSTMORTEM"
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260861


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("sensitivity CSV must not be empty")
    return rows


def _cluster_means(rows: Sequence[Mapping[str, Any]], value_key: str) -> np.ndarray:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        cluster_id = str(row.get("cluster_id", "")).strip()
        value = float(row[value_key])
        if not cluster_id or not math.isfinite(value):
            raise ValueError("postmortem row lacks a finite value or cluster ID")
        grouped[cluster_id].append(value)
    if len(grouped) < 2:
        raise ValueError("postmortem requires at least two independent clusters")
    return np.asarray(
        [np.mean(grouped[cluster]) for cluster in sorted(grouped)],
        dtype=np.float64,
    )


def _cluster_summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_key: str,
    seed: int,
    replicates: int,
) -> dict[str, float | int]:
    values = _cluster_means(rows, value_key)
    rng = np.random.default_rng(seed)
    samples = rng.integers(
        0, len(values), size=(replicates, len(values)), endpoint=False
    )
    bootstrap = np.mean(values[samples], axis=1)
    signs = rng.choice(np.asarray((-1.0, 1.0)), size=(replicates, len(values)))
    null_estimates = np.mean(signs * values, axis=1)
    point = float(np.mean(values))
    sample_sd = float(np.std(values, ddof=1))
    leave_one_out = np.asarray(
        [np.mean(np.delete(values, index)) for index in range(len(values))]
    )
    return {
        "point": point,
        "ci_lower": float(np.quantile(bootstrap, 0.025)),
        "ci_upper": float(np.quantile(bootstrap, 0.975)),
        "cluster_count": len(values),
        "bootstrap_replicates": replicates,
        "p_value_two_sided": float(
            (1 + np.count_nonzero(np.abs(null_estimates) >= abs(point)))
            / (replicates + 1)
        ),
        "standardized_cluster_effect": point / sample_sd if sample_sd else 0.0,
        "maximum_leave_one_cluster_out_influence": float(
            np.max(np.abs(leave_one_out - point))
        ),
    }


def _holm_adjust(rows: list[dict[str, Any]]) -> None:
    ordered = sorted(
        enumerate(rows), key=lambda item: float(item[1]["p_value_two_sided"])
    )
    adjusted_by_index: dict[int, float] = {}
    running = 0.0
    count = len(rows)
    for rank, (index, row) in enumerate(ordered):
        adjusted = min(1.0, (count - rank) * float(row["p_value_two_sided"]))
        running = max(running, adjusted)
        adjusted_by_index[index] = running
    for index, row in enumerate(rows):
        row["holm_adjusted_p_value"] = adjusted_by_index[index]
        row["multiplicity_family"] = f"{row['analysis_level']}_comparisons"


def _matched_difference_rows(
    rows: Sequence[Mapping[str, str]], family: str
) -> list[dict[str, Any]]:
    controls = {
        (row["image_id"], int(row["variant_id"])): row
        for row in rows
        if row["error_type"] == CONTROL_FAMILY
    }
    interventions = [row for row in rows if row["error_type"] == family]
    differences: list[dict[str, Any]] = []
    for row in interventions:
        key = (row["image_id"], int(row["variant_id"]))
        if key not in controls:
            raise ValueError(f"missing matched semantic-preserving control for {key}")
        control = controls[key]
        if row["cluster_id"] != control["cluster_id"]:
            raise ValueError("matched conflict/control rows cross clusters")
        differences.append(
            {
                "image_id": row["image_id"],
                "cluster_id": row["cluster_id"],
                "variant_id": int(row["variant_id"]),
                "difference": float(row["region_abs_rel_degradation"])
                - float(control["region_abs_rel_degradation"]),
            }
        )
    if not differences:
        raise ValueError(f"no rows found for {family}")
    return differences


def _quantile_summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("practical effect values must be nonempty and finite")
    return {
        "median": float(np.median(array)),
        "q25": float(np.quantile(array, 0.25)),
        "q75": float(np.quantile(array, 0.75)),
        "p95": float(np.quantile(array, 0.95)),
    }


def analyze_sensitivity_postmortem(
    rows: Sequence[Mapping[str, str]],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute exploratory direct contrasts and practical-effect slices."""

    if replicates < 1:
        raise ValueError("replicates must be positive")
    observed_families = {row.get("error_type") for row in rows}
    required_families = {CONTROL_FAMILY, *INTERVENTION_FAMILIES}
    if observed_families != required_families:
        raise ValueError("sensitivity rows do not contain the frozen four families")

    difference_rows: list[dict[str, Any]] = []
    for family_index, family in enumerate(INTERVENTION_FAMILIES):
        matched = _matched_difference_rows(rows, family)
        family_summary = _cluster_summary(
            matched,
            value_key="difference",
            seed=seed + family_index,
            replicates=replicates,
        )
        difference_rows.append(
            {
                "analysis_level": "family",
                "family": family,
                "variant_id": "ALL",
                "row_count": len(matched),
                **family_summary,
            }
        )
        for variant_id in (0, 1, 2):
            variant_rows = [
                row for row in matched if int(row["variant_id"]) == variant_id
            ]
            difference_rows.append(
                {
                    "analysis_level": "template_variant",
                    "family": family,
                    "variant_id": variant_id,
                    "row_count": len(variant_rows),
                    **_cluster_summary(
                        variant_rows,
                        value_key="difference",
                        seed=seed + 10 + family_index * 3 + variant_id,
                        replicates=replicates,
                    ),
                }
            )
    for level in ("family", "template_variant"):
        _holm_adjust([row for row in difference_rows if row["analysis_level"] == level])

    practical_metrics = {
        "target_pixel_mass": lambda row: float(row["region_valid_pixel_count"])
        / float(row["full_valid_pixel_count"]),
        "clean_region_abs_rel": lambda row: float(row["region_clean_abs_rel"]),
        "absolute_region_abs_rel_degradation": lambda row: float(
            row["region_abs_rel_degradation"]
        ),
        "relative_region_abs_rel_degradation": lambda row: float(
            row["region_abs_rel_degradation"]
        )
        / float(row["region_clean_abs_rel"]),
        "full_image_abs_rel_degradation": lambda row: float(
            row["full_abs_rel_degradation"]
        ),
    }
    practical_rows: list[dict[str, Any]] = []
    for family_index, family in enumerate((CONTROL_FAMILY, *INTERVENTION_FAMILIES)):
        family_source = [row for row in rows if row["error_type"] == family]
        for metric_index, (metric, calculate) in enumerate(practical_metrics.items()):
            calculated = [
                {**row, "practical_value": calculate(row)} for row in family_source
            ]
            practical_rows.append(
                {
                    "family": family,
                    "metric": metric,
                    "row_count": len(calculated),
                    **_quantile_summary(
                        [float(row["practical_value"]) for row in calculated]
                    ),
                    **{
                        key: value
                        for key, value in _cluster_summary(
                            calculated,
                            value_key="practical_value",
                            seed=seed + 100 + family_index * 10 + metric_index,
                            replicates=replicates,
                        ).items()
                        if key
                        not in {
                            "p_value_two_sided",
                            "standardized_cluster_effect",
                        }
                    },
                }
            )

    common = {
        "analysis_status": ANALYSIS_STATUS,
        "cannot_reverse_preregistered_stop": True,
        "control_family": CONTROL_FAMILY,
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }
    differences = {
        "schema_version": "covol-conflict-minus-control-postmortem-v1",
        **common,
        "estimand": (
            "cluster-balanced matched difference in region AbsRel degradation: "
            "intervention family minus semantic-preserving template"
        ),
        "rows": difference_rows,
    }
    practical = {
        "schema_version": "covol-practical-effects-postmortem-v1",
        **common,
        "rows": practical_rows,
    }
    return differences, practical


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("CSV output requires at least one row")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = tuple(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--difference-json", type=Path, required=True)
    parser.add_argument("--difference-csv", type=Path, required=True)
    parser.add_argument("--practical-json", type=Path, required=True)
    parser.add_argument("--practical-csv", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=BOOTSTRAP_REPLICATES)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    differences, practical = analyze_sensitivity_postmortem(
        _read_csv(args.input), replicates=args.replicates, seed=args.seed
    )
    _write_json(args.difference_json, differences)
    _write_rows(args.difference_csv, differences["rows"])
    _write_json(args.practical_json, practical)
    _write_rows(args.practical_csv, practical["rows"])


if __name__ == "__main__":
    main()
