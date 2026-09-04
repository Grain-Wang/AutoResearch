"""Aggregate the frozen Round 5 M2 evidence and its checkpoint-only replay."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from experiments.provenance import (
    canonical_sha256,
    git_state,
    runtime_provenance,
    sha256_file,
)

_PAPER_ROOT = Path(__file__).resolve().parents[1]
_RESULT_ROOT = _PAPER_ROOT / "results/blockstamp"
_DEFAULT_RESULTS = _RESULT_ROOT / "minimal_probe.csv"
_DEFAULT_MANIFEST = _RESULT_ROOT / "minimal_probe.manifest.json"
_DEFAULT_GATE = _RESULT_ROOT / "next_round_gate.json"
_DEFAULT_REPLAY_RESULTS = _RESULT_ROOT / "integrity_replay/minimal_probe.csv"
_DEFAULT_REPLAY_MANIFEST = _RESULT_ROOT / "integrity_replay/minimal_probe.manifest.json"
_DEFAULT_OUTPUT = _RESULT_ROOT / "minimal_probe.summary.json"
_DEFAULT_REPLAY_REPORT = _RESULT_ROOT / "clean_replay_report.json"

_METHODS = (
    "dense_slab_generic",
    "device_local_pointwise_b2",
    "temporal_only",
    "temporal_device_blockstamp",
    "strict_mpfr_rerun",
)
_PRIMARY_METHODS = _METHODS[:-1]
_MATCH_KEY = (
    "circuit_id",
    "instance_id",
    "steps",
    "slab_length",
    "replicate",
)
_PRIMARY_SHARED_HASHES = (
    "input_sha256",
    "producer_trace_sha256",
    "candidate_sha256",
    "tube_sha256",
    "backend_sha256",
    "semantics_sha256",
    "scaling_sha256",
    "ordering_sha256",
    "factor_sha256",
    "hardware_id",
)
_STRICT_REQUIRED_EQUAL = (
    "input_sha256",
    "backend_sha256",
    "semantics_sha256",
    "scaling_sha256",
    "ordering_sha256",
    "hardware_id",
    "threads",
)
_HASH_COLUMNS = (
    "input_sha256",
    "producer_trace_sha256",
    "candidate_sha256",
    "tube_sha256",
    "backend_sha256",
    "semantics_sha256",
    "scaling_sha256",
    "ordering_sha256",
    "factor_sha256",
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return payload


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(row: dict[str, str], column: str) -> float:
    return float(row[column])


def _integer(row: dict[str, str], column: str) -> int:
    return int(row[column])


def _key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[column] for column in _MATCH_KEY)


def _distribution(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _summary(values: Iterable[float]) -> dict[str, float | int]:
    items = list(values)
    if not items:
        raise ValueError("cannot summarize an empty sequence")
    if len(items) == 1:
        lower_quartile = upper_quartile = items[0]
    else:
        lower_quartile, _, upper_quartile = statistics.quantiles(
            items, n=4, method="inclusive"
        )
    return {
        "count": len(items),
        "min": min(items),
        "q1": lower_quartile,
        "median": statistics.median(items),
        "q3": upper_quartile,
        "max": max(items),
        "mean": statistics.fmean(items),
        "sum": math.fsum(items),
    }


def _ratio_summary(values: Iterable[float]) -> dict[str, float | int]:
    result = _summary(values)
    items = list(values)
    result["geometric_mean"] = math.exp(
        math.fsum(math.log(value) for value in items) / len(items)
    )
    return result


def _rows_by_method(
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    grouped = {method: [] for method in _METHODS}
    for row in rows:
        method = row["method"]
        if method not in grouped:
            raise ValueError(f"unexpected method: {method}")
        grouped[method].append(row)
    return grouped


def _baseline_map(
    rows: list[dict[str, str]], method: str
) -> dict[tuple[str, ...], dict[str, str]]:
    selected = {_key(row): row for row in rows if row["method"] == method}
    expected = sum(row["method"] == method for row in rows)
    if len(selected) != expected:
        raise ValueError(f"duplicate {method} match keys")
    return selected


def _method_summary(
    rows: list[dict[str, str]],
    dense: dict[tuple[str, ...], dict[str, str]],
) -> dict[str, object]:
    if not rows:
        raise ValueError("missing method rows")
    check_ratios = [
        _number(dense[_key(row)], "check_seconds") / _number(row, "check_seconds")
        for row in rows
    ]
    end_to_end_ratios = [
        _number(dense[_key(row)], "end_to_end_seconds")
        / _number(row, "end_to_end_seconds")
        for row in rows
    ]
    total_steps = sum(_integer(row, "steps") for row in rows)
    certified_steps = math.fsum(
        _number(row, "certification_rate") * _integer(row, "steps") for row in rows
    )
    return {
        "configuration_count": len(rows),
        "producer_complete_configurations": len(rows),
        "configuration_verdict_counts": _distribution(
            row["checker_verdict"] for row in rows
        ),
        "configuration_accept_rate": (
            sum(row["checker_verdict"] == "ACCEPT" for row in rows) / len(rows)
        ),
        "certification_rate": {
            **_summary(_number(row, "certification_rate") for row in rows),
            "step_weighted": certified_steps / total_steps,
            "certified_step_slots": certified_steps,
            "total_step_slots": total_steps,
        },
        "continuous_certified_prefix_steps": _summary(
            float(_integer(row, "certified_prefix_steps")) for row in rows
        ),
        "inclusion_margin": _summary(
            _number(row, "inclusion_margin_min") for row in rows
        ),
        "tube_max_relative_width": _summary(
            _number(row, "tube_max_relative_width") for row in rows
        ),
        "tube_growth_rate": _summary(_number(row, "tube_growth_rate") for row in rows),
        "failure_code_distribution": _distribution(
            row["failure_code"] or "NONE" for row in rows
        ),
        "checker_runtime_seconds": _summary(
            _number(row, "check_seconds") for row in rows
        ),
        "certificate_generation_seconds": _summary(
            _number(row, "certificate_generation_seconds") for row in rows
        ),
        "fallback_seconds": _summary(_number(row, "fallback_seconds") for row in rows),
        "end_to_end_seconds": _summary(
            _number(row, "end_to_end_seconds") for row in rows
        ),
        "checker_runtime_speedup_vs_dense": _ratio_summary(check_ratios),
        "end_to_end_speedup_vs_dense": _ratio_summary(end_to_end_ratios),
        "peak_rss_bytes": _summary(_number(row, "peak_rss_bytes") for row in rows),
        "certificate_bytes": _summary(
            _number(row, "certificate_bytes") for row in rows
        ),
        "raw_trajectory_bytes": _summary(
            _number(row, "raw_trajectory_bytes") for row in rows
        ),
    }


def _grouped_method_statistics(
    rows: list[dict[str, str]], column: str
) -> dict[str, object]:
    values = sorted({row[column] for row in rows}, key=float)
    result: dict[str, object] = {}
    for value in values:
        selected = [row for row in rows if row[column] == value]
        dense = _baseline_map(selected, "dense_slab_generic")
        result[value] = {
            method: _method_summary(method_rows, dense)
            for method, method_rows in _rows_by_method(selected).items()
        }
    return result


def _matched_hash_audit(rows: list[dict[str, str]]) -> dict[str, object]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(_key(row), []).append(row)
    primary_mismatches: list[dict[str, object]] = []
    strict_mismatches: list[dict[str, object]] = []
    for key, group in sorted(groups.items()):
        methods = Counter(row["method"] for row in group)
        primary = [row for row in group if row["method"] in _PRIMARY_METHODS]
        bad_primary_columns = [
            column
            for column in _PRIMARY_SHARED_HASHES
            if len({row[column] for row in primary}) != 1
        ]
        if (
            methods != Counter(_METHODS)
            or len(primary) != len(_PRIMARY_METHODS)
            or bad_primary_columns
        ):
            primary_mismatches.append(
                {
                    "match_key": dict(zip(_MATCH_KEY, key, strict=True)),
                    "method_counts": dict(sorted(methods.items())),
                    "mismatched_columns": bad_primary_columns,
                }
            )
        bad_strict_columns = [
            column
            for column in _STRICT_REQUIRED_EQUAL
            if len({row[column] for row in group}) != 1
        ]
        if bad_strict_columns:
            strict_mismatches.append(
                {
                    "match_key": dict(zip(_MATCH_KEY, key, strict=True)),
                    "mismatched_columns": bad_strict_columns,
                }
            )
    hash_sets = {
        column: {
            "unique_count": len(values),
            "set_sha256": canonical_sha256(values),
        }
        for column in _HASH_COLUMNS
        for values in [sorted({row[column] for row in rows})]
    }
    return {
        "status": (
            "PASS" if not primary_mismatches and not strict_mismatches else "FAIL"
        ),
        "matched_group_count": len(groups),
        "expected_matched_group_count": 450,
        "five_methods_per_group": all(
            Counter(row["method"] for row in group) == Counter(_METHODS)
            for group in groups.values()
        ),
        "primary_shared_columns": list(_PRIMARY_SHARED_HASHES),
        "primary_mismatches": primary_mismatches,
        "strict_required_equal_columns": list(_STRICT_REQUIRED_EQUAL),
        "strict_mismatches": strict_mismatches,
        "strict_allowed_different_columns": [
            "producer_trace_sha256",
            "candidate_sha256",
            "tube_sha256",
            "factor_sha256",
        ],
        "hash_sets": hash_sets,
    }


def _paired_runtime_difference(
    rows: list[dict[str, str]], candidate_method: str, baseline_method: str
) -> dict[str, object]:
    candidates = _baseline_map(rows, candidate_method)
    baselines = _baseline_map(rows, baseline_method)
    keys = sorted(candidates)
    if keys != sorted(baselines):
        raise ValueError("runtime comparison keys differ")
    ratios = [
        _number(candidates[key], "check_seconds")
        / _number(baselines[key], "check_seconds")
        for key in keys
    ]
    differences = [
        _number(candidates[key], "check_seconds")
        - _number(baselines[key], "check_seconds")
        for key in keys
    ]
    candidate_total = math.fsum(
        _number(candidates[key], "check_seconds") for key in keys
    )
    baseline_total = math.fsum(_number(baselines[key], "check_seconds") for key in keys)
    return {
        "candidate": candidate_method,
        "baseline": baseline_method,
        "paired_runtime_ratio_candidate_over_baseline": _ratio_summary(ratios),
        "paired_absolute_seconds_candidate_minus_baseline": _summary(differences),
        "ratio_of_total_checker_seconds": candidate_total / baseline_total,
        "relative_total_runtime_change": candidate_total / baseline_total - 1.0,
        "interpretation": (
            "ratios above one and positive changes mean the candidate is slower"
        ),
    }


def _clean_replay_report(
    *,
    results: Path,
    manifest: dict[str, Any],
    replay_results: Path,
    replay_manifest: dict[str, Any],
) -> dict[str, object]:
    main_csv_sha256 = sha256_file(results)
    replay_csv_sha256 = sha256_file(replay_results)
    checkpoint_hash_equal = manifest.get(
        "checkpoint_set_sha256"
    ) == replay_manifest.get("checkpoint_set_sha256")
    replay_reused_all = replay_manifest.get("checkpoint_counts") == {
        "measured_executed": 0,
        "measured_reused": 2250,
        "warmups_executed": 0,
        "warmups_reused": 450,
    }
    integrity_pass = all(
        (
            main_csv_sha256 == replay_csv_sha256,
            checkpoint_hash_equal,
            replay_reused_all,
            replay_manifest.get("integrity", {}).get("all_pass") is True,
            replay_manifest.get("row_count") == 2250,
        )
    )
    clean_pass = all(
        (
            manifest.get("dirty_worktree") is False,
            replay_manifest.get("dirty_worktree") is False,
            manifest.get("git_commit") == replay_manifest.get("git_commit"),
        )
    )
    return {
        "schema_version": 1,
        **runtime_provenance(),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        "status": "PASS" if integrity_pass and clean_pass else "INCOMPLETE",
        "integrity_replay": {
            "status": "PASS" if integrity_pass else "FAIL",
            "mode": (
                "checkpoint-only aggregate replay; no producer/checker child "
                "process was launched"
            ),
            "main_csv_sha256": main_csv_sha256,
            "replay_csv_sha256": replay_csv_sha256,
            "csv_byte_identical": main_csv_sha256 == replay_csv_sha256,
            "main_checkpoint_set_sha256": manifest.get("checkpoint_set_sha256"),
            "replay_checkpoint_set_sha256": replay_manifest.get(
                "checkpoint_set_sha256"
            ),
            "checkpoint_set_identical": checkpoint_hash_equal,
            "replay_checkpoint_counts": replay_manifest.get("checkpoint_counts"),
            "all_2700_checkpoints_reused": replay_reused_all,
            "replay_integrity": replay_manifest.get("integrity"),
        },
        "clean_independent_replay": {
            "status": "PASS" if clean_pass else "NOT-PERFORMED",
            "main_dirty_worktree": manifest.get("dirty_worktree"),
            "replay_dirty_worktree": replay_manifest.get("dirty_worktree"),
            "main_git_commit": manifest.get("git_commit"),
            "replay_git_commit": replay_manifest.get("git_commit"),
            "required_but_missing": [
                "frozen source committed before execution",
                (
                    "execution from an independent clean checkout into an external "
                    "clean output directory"
                ),
                (
                    "dirty_worktree=false on all M0/M1/M2 manifests from one source "
                    "commit"
                ),
                (
                    "a second independent process replay of the experiment rather "
                    "than checkpoint reaggregation"
                ),
                "a preregistered timing-replay tolerance and its comparison",
                "one core table reproduced through a second producer path",
            ],
            "reason": (
                "the completed run and checkpoint-only replay both bind to a dirty "
                "worktree; checkpoint reaggregation cannot satisfy the frozen "
                "clean-replay protocol"
            ),
        },
    }


def build_summary(
    *,
    rows: list[dict[str, str]],
    manifest: dict[str, Any],
    gate: dict[str, Any],
    results_path: Path,
    manifest_path: Path,
    replay_results_path: Path,
    replay_manifest_path: Path,
    replay_report: dict[str, object],
) -> dict[str, object]:
    """Build the complete frozen Round 5 M2 aggregate."""

    if len(rows) != 2250:
        raise ValueError(f"expected 2250 M2 rows, found {len(rows)}")
    grouped = _rows_by_method(rows)
    if any(len(method_rows) != 450 for method_rows in grouped.values()):
        raise ValueError("expected exactly 450 rows per method")
    dense = _baseline_map(rows, "dense_slab_generic")
    matched = _matched_hash_audit(rows)
    integrity = manifest.get("integrity", {})
    if matched["status"] != "PASS" or integrity.get("all_pass") is not True:
        raise ValueError("M2 matched-integrity audit failed")
    return {
        "schema_version": 1,
        "round": "round5-frozen-m2-v1",
        "status": "COMPLETE",
        "scope": "frozen matched nonlinear M2; no Round 6 work is included",
        **runtime_provenance(),
        **git_state(_PAPER_ROOT.parent, "paper2"),
        "completion": {
            "expected_measured_configurations": 2250,
            "completed_measured_configurations": len(rows),
            "expected_warmups": 450,
            "completed_warmups": manifest.get("warmup_processes"),
            "missing_configurations": integrity.get("missing_rows"),
            "duplicate_configurations": integrity.get("duplicate_rows"),
            "extra_configurations": integrity.get("extra_rows"),
            "unsupported_configurations": manifest.get("unsupported_cases"),
            "producer_completion": manifest.get("producer_completion"),
            "configuration_verdict_counts": manifest.get("verdict_counts"),
            "failure_code_distribution": manifest.get("failure_code_distribution"),
            "confirmed_false_accepts": manifest.get("confirmed_false_accepts"),
        },
        "frozen_protocol": {
            "workloads": manifest.get("observed_instances"),
            "producer_precision": "float64",
            "producer_tolerance": 1.0e-10,
            "radius_multiplier": 4.0,
            "steps_grid": manifest.get("steps_grid"),
            "slab_lengths": manifest.get("slab_lengths"),
            "replicate_ids": [0, 1, 2, 3, 4],
            "method_order": list(_METHODS),
            "workers": manifest.get("workers"),
            "warmups_excluded": manifest.get("warmups_excluded"),
        },
        "per_method": {
            method: _method_summary(method_rows, dense)
            for method, method_rows in grouped.items()
        },
        "by_steps": _grouped_method_statistics(rows, "steps"),
        "by_slab": _grouped_method_statistics(rows, "slab_length"),
        "by_replicate": _grouped_method_statistics(rows, "replicate"),
        "direct_runtime_comparisons": {
            "temporal_device_blockstamp_vs_device_local_pointwise_b2": (
                _paired_runtime_difference(
                    rows,
                    "temporal_device_blockstamp",
                    "device_local_pointwise_b2",
                )
            ),
            "temporal_device_blockstamp_vs_temporal_only": (
                _paired_runtime_difference(
                    rows,
                    "temporal_device_blockstamp",
                    "temporal_only",
                )
            ),
        },
        "fallback_and_recovery": manifest.get("fallback_and_recovery"),
        "matched_hash_consistency": matched,
        "contract_hashes": {
            "config_sha256": manifest.get("config_sha256"),
            "backend_sha256": manifest.get("backend_sha256"),
            "semantics_sha256": manifest.get("semantics_sha256"),
            "input_set_sha256": manifest.get("input_sha256"),
            "checkpoint_set_sha256": manifest.get("checkpoint_set_sha256"),
        },
        "m2_frozen_decision": {
            "runner_status": manifest.get("status"),
            "claim_w": manifest.get("claims", {}).get("W"),
            "claim_e": manifest.get("claims", {}).get("E"),
            "claim_d": manifest.get("claims", {}).get("D"),
            "interpretation": (
                "W passes the frozen prefix/rate mechanism criterion; E and D stop. "
                "This is not an algorithm-novelty or Paper Candidate pass."
            ),
        },
        "round5_gate": {
            "status": gate.get("status"),
            "m2": gate.get("m2"),
            "blockers": gate.get("blockers"),
            "pre_paper_candidate": gate.get("pre_paper_candidate"),
            "paper_candidate": gate.get("paper_candidate"),
        },
        "claim_assessment": {
            "established_or_supported": [
                (
                    "The restricted implementation remained fail-closed: zero "
                    "confirmed false accepts."
                ),
                (
                    "All 450 primary matched groups bind the same producer trace, "
                    "candidate, tube, backend, semantics, scaling, ordering, factor, "
                    "and hardware hashes."
                ),
                (
                    "Claim W passes only its frozen within-matrix mechanism rule at "
                    "slabs 2 and 4."
                ),
            ],
            "plausible_but_not_established": [
                (
                    "A narrower circuit-structured independently checkable "
                    "certification system may remain a Research Opportunity, but a "
                    "useful end-to-end system benefit is not established."
                ),
            ],
            "unsupported": [
                (
                    "full-trajectory certification on the frozen M2 matrix (zero "
                    "configuration-level ACCEPT results)"
                ),
                (
                    "stable checker-time, peak-RSS, or certificate-size advantage "
                    "versus both dense slab and matched B2 (Claim E STOP)"
                ),
                "useful fallback recovery (1800 triggers, zero recovered ACCEPT rows)",
                "clean independent reproducibility evidence",
            ],
            "abandoned": [
                "a novel BlockStamp numerical algorithm headline",
                (
                    "device-locality as a contribution of the current globally "
                    "assembled implementation (Claim D STOP)"
                ),
                (
                    "novelty claims for Krawczyk/interval Newton, block substitution, "
                    "temporal block structure, verified sparse/factorized solves, or "
                    "proof-carrying architecture"
                ),
            ],
        },
        "artifact_scope_limits": {
            "certificate_size": manifest.get("certificate_size_scope"),
            "strict_comparator": manifest.get("strict_comparator_scope"),
            "rss": manifest.get("rss_measurement_scope"),
        },
        "replay": replay_report,
        "artifacts": {
            "minimal_probe_csv": {
                "path": results_path.relative_to(_PAPER_ROOT).as_posix(),
                "sha256": sha256_file(results_path),
            },
            "minimal_probe_manifest": {
                "path": manifest_path.relative_to(_PAPER_ROOT).as_posix(),
                "sha256": sha256_file(manifest_path),
            },
            "integrity_replay_csv": {
                "path": replay_results_path.relative_to(_PAPER_ROOT).as_posix(),
                "sha256": sha256_file(replay_results_path),
            },
            "integrity_replay_manifest": {
                "path": replay_manifest_path.relative_to(_PAPER_ROOT).as_posix(),
                "sha256": sha256_file(replay_manifest_path),
            },
            "next_round_gate": {
                "path": _DEFAULT_GATE.relative_to(_PAPER_ROOT).as_posix(),
                "sha256": sha256_file(_DEFAULT_GATE),
            },
        },
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=_DEFAULT_RESULTS)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--gate", type=Path, default=_DEFAULT_GATE)
    parser.add_argument("--replay-results", type=Path, default=_DEFAULT_REPLAY_RESULTS)
    parser.add_argument(
        "--replay-manifest", type=Path, default=_DEFAULT_REPLAY_MANIFEST
    )
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--replay-report", type=Path, default=_DEFAULT_REPLAY_REPORT)
    arguments = parser.parse_args()

    manifest = _read_json(arguments.manifest)
    replay_manifest = _read_json(arguments.replay_manifest)
    replay_report = _clean_replay_report(
        results=arguments.results,
        manifest=manifest,
        replay_results=arguments.replay_results,
        replay_manifest=replay_manifest,
    )
    _write_json(arguments.replay_report, replay_report)
    summary = build_summary(
        rows=_read_rows(arguments.results),
        manifest=manifest,
        gate=_read_json(arguments.gate),
        results_path=arguments.results,
        manifest_path=arguments.manifest,
        replay_results_path=arguments.replay_results,
        replay_manifest_path=arguments.replay_manifest,
        replay_report=replay_report,
    )
    _write_json(arguments.output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
