"""Generate human-readable run reports from pipeline artifacts."""

# pyright: basic
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def generate_report(run_dir: Path) -> str:
    """Generate a Markdown report from a pipeline run directory.

    Args:
        run_dir: Path to the run artifacts directory (e.g., artifacts/rc-xxx/)

    Returns:
        Markdown string with the report content.

    Raises:
        FileNotFoundError: If run_dir doesn't exist.
        ValueError: If run_dir has no pipeline_summary.json.
    """
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    summary_path = run_dir / "pipeline_summary.json"
    if not summary_path.exists():
        raise ValueError(f"No pipeline_summary.json found in {run_dir}")

    loaded = json.loads(summary_path.read_text(encoding="utf-8"))
    summary = loaded if isinstance(loaded, dict) else {}

    sections = []
    sections.append(_header(summary, run_dir))
    sections.append(_experiment_section(run_dir))
    sections.append(_decision_section(run_dir))
    sections.append(_warnings_section(summary, run_dir))

    return "\n\n".join(section for section in sections if section)


def _header(summary: dict[str, Any], run_dir: Path) -> str:
    run_id = summary.get("run_id", "unknown")
    stages_done = summary.get("stages_done", 0)
    stages_total = summary.get("stages_executed", 0)
    status = summary.get("final_status", "unknown")
    generated = summary.get("generated", "unknown")

    status_icon = "✅" if status == "done" else "❌" if status == "failed" else "⚠️"

    lines = [
        "# ResearchClaw Experiment Report",
        "",
        f"**Run ID**: {run_id}",
        f"**Date**: {generated}",
        f"**Status**: {status_icon} {status} ({stages_done}/{stages_total} stages done)",
        f"**Artifacts**: `{run_dir}`",
    ]
    return "\n".join(lines)


def _experiment_section(run_dir: Path) -> str:
    lines = ["## Experiments"]

    # Best experiment summary (promoted to run root, else newest stage-15)
    summary_path = run_dir / "experiment_summary_best.json"
    if not summary_path.exists():
        for _s15 in sorted(run_dir.glob("stage-15*"), reverse=True):
            _alt = _s15 / "experiment_summary.json"
            if _alt.exists():
                summary_path = _alt
                break
    if summary_path.exists():
        lines.append(f"- Summary: `{summary_path.relative_to(run_dir)}`")
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ms = data.get("metrics_summary", {})
                if isinstance(ms, dict) and ms:
                    lines.append(f"- Metric keys: {', '.join(str(k) for k in ms)}")
                best = data.get("best_run")
                if isinstance(best, dict) and best.get("metrics"):
                    lines.append(f"- Best run: `{best.get('run_id', '?')}`")
                conditions = data.get("condition_summaries")
                if isinstance(conditions, dict) and conditions:
                    lines.append(f"- Conditions: {len(conditions)}")
        except (json.JSONDecodeError, TypeError):
            lines.append("- Summary: present (parse error)")
    else:
        lines.append("- Summary: not available")

    code_path = run_dir / "stage-11" / "experiment_code.py"
    if code_path.exists():
        lines.append(f"- Code: `{code_path.relative_to(run_dir)}`")

    results_path = run_dir / "stage-13" / "experiment_results.json"
    if results_path.exists():
        try:
            loaded = json.loads(results_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
                runs_default: list[Any] = []
                iterations = data.get("iterations", data.get("runs", runs_default))
                if isinstance(iterations, list):
                    lines.append(f"- Runs: {len(iterations)} iterations")
                best = data.get("best_metric") or data.get("best_result")
                if best is not None:
                    lines.append(f"- Best metric: {best}")
        except (json.JSONDecodeError, TypeError):
            lines.append("- Results: present (parse error)")
    else:
        lines.append("- Results: not available")

    # BUG-215: Also search stage-15* versioned dirs when stage-15/ is missing.
    analysis_path = run_dir / "stage-15" / "analysis.md"
    if not analysis_path.exists():
        for _s15 in sorted(run_dir.glob("stage-15*"), reverse=True):
            _alt = _s15 / "analysis.md"
            if _alt.exists():
                analysis_path = _alt
                break
    if analysis_path.exists():
        lines.append(f"- Analysis: `{analysis_path.relative_to(run_dir)}`")

    return "\n".join(lines)


def _decision_section(run_dir: Path) -> str:
    lines = ["## Research Decision"]

    decision_path = run_dir / "stage-16" / "decision.md"
    if not decision_path.exists():
        for _s16 in sorted(run_dir.glob("stage-16*"), reverse=True):
            _alt = _s16 / "decision.md"
            if _alt.exists():
                decision_path = _alt
                break
    if decision_path.exists():
        text = decision_path.read_text(encoding="utf-8").strip()
        first_line = text.splitlines()[0] if text else ""
        lines.append(f"- Decision: `{decision_path.relative_to(run_dir)}`")
        if first_line:
            lines.append(f"- Verdict: {first_line}")
    else:
        lines.append("- Decision: not generated")

    return "\n".join(lines)


def _warnings_section(summary: dict[str, Any], run_dir: Path) -> str:
    warnings: list[str] = []

    stages_failed = summary.get("stages_failed", 0)
    if stages_failed:
        warnings.append(f"- ⚠️ {stages_failed} stage(s) failed during execution")

    content_metrics = summary.get("content_metrics", {})
    if isinstance(content_metrics, dict):
        best_metric = content_metrics.get("best_metric")
        if isinstance(best_metric, dict) and best_metric.get("mean") is None:
            warnings.append("- ⚠️ Best metric missing — experiments may have failed")

        degraded = content_metrics.get("degraded_sources", [])
        if isinstance(degraded, list) and degraded:
            warnings.append(f"- ⚠️ Degraded sources: {', '.join(degraded)}")

    # Surface max-pivot quality warnings from the forced-PROCEED path
    qw_path = run_dir / "quality_warning.txt"
    if qw_path.exists():
        text = qw_path.read_text(encoding="utf-8").strip()
        if text:
            first_line = text.splitlines()[0]
            warnings.append(f"- ⚠️ {first_line}")

    if not warnings:
        return ""

    return "## Warnings\n" + "\n".join(warnings)


def print_report(run_dir: Path) -> None:
    print(generate_report(run_dir))


def write_report(run_dir: Path, output_path: Path) -> None:
    report = generate_report(run_dir)
    _ = output_path.write_text(report, encoding="utf-8")
