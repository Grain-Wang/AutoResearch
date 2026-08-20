"""HITL summarizer: generate concise decision summaries for humans.

When the pipeline pauses, the human needs a quick understanding of:
1. What the AI produced
2. Why it paused
3. What decisions need to be made
4. Key risk factors

This module generates those summaries automatically.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Stage-specific summary templates
_STAGE_SUMMARIES: dict[int, str] = {
    1: "Research direction and scope defined. Review the SMART goal and confirm the research topic aligns with your interests.",
    2: "Problem decomposed into sub-questions. Review the problem tree and ensure all important aspects are covered.",
    3: "Search strategy defined. Review the planned search queries and data sources. Add any missing keywords or sources.",
    4: "Literature collected. Review the number and quality of candidate papers.",
    5: "Literature screened. Review the shortlisted papers — are key papers included? Any important ones filtered out?",
    6: "Knowledge cards extracted. Review the summaries of key papers.",
    7: "Research gaps and synthesis complete. Review the identified gaps — do they match your understanding of the field?",
    8: "Baseline defect reproduction gate. Review whether a real, algorithmic defect in the strongest baseline was confirmed. If the defect was refuted or is only an engineering issue, the run pauses and should restart from synthesis.",
    9: "Hypotheses generated. This is a CRITICAL decision point — review each hypothesis for novelty, feasibility, and significance.",
    10: "Experiment plan designed. Review baselines, benchmarks, metrics, and ablations. Ensure all standard comparisons are included.",
    11: "Experiment code generated. Review the code structure and quality.",
    12: "Resource schedule created. Confirm GPU/time allocation.",
    13: "Experiments running/completed. Check if results look reasonable and training is progressing normally.",
    14: "Iterative refinement done. Review the improvement trajectory.",
    15: "Results analyzed. Verify the statistical analysis and conclusions are sound.",
    16: "Research decision point. Choose: PROCEED to conclusion, PIVOT to new hypothesis, or REFINE experiments.",
}


def generate_pause_summary(
    stage_num: int,
    stage_name: str,
    run_dir: Path,
    *,
    result_status: str = "done",
    error: str = "",
) -> str:
    """Generate a human-readable summary when the pipeline pauses.

    Args:
        stage_num: Stage number (1-16).
        stage_name: Stage name.
        run_dir: Pipeline run directory.
        result_status: Stage result status.
        error: Error message if any.

    Returns:
        Formatted summary string.
    """
    lines = []

    # Status header
    if error:
        lines.append(f"Stage {stage_num} ({stage_name}) — ERROR: {error}")
    else:
        lines.append(f"Stage {stage_num} ({stage_name}) — {result_status}")

    # Stage-specific guidance
    guidance = _STAGE_SUMMARIES.get(stage_num, "")
    if guidance:
        lines.append(f"\n{guidance}")

    # Output file summary
    stage_dir = run_dir / f"stage-{stage_num:02d}"
    if stage_dir.exists():
        outputs = [
            f for f in sorted(stage_dir.iterdir())
            if not f.name.startswith(".") and f.name != "stage_health.json"
        ]
        if outputs:
            lines.append("\nOutputs:")
            for f in outputs[:10]:
                if f.is_file():
                    size = f.stat().st_size
                    preview = _file_preview(f)
                    lines.append(f"  {f.name} ({size} bytes)")
                    if preview:
                        lines.append(f"    → {preview}")
                elif f.is_dir():
                    count = sum(1 for _ in f.iterdir())
                    lines.append(f"  {f.name}/ ({count} items)")

    # Quality score if available
    prm_path = stage_dir / "prm_score.json" if stage_dir.exists() else None
    if prm_path and prm_path.exists():
        try:
            prm = json.loads(prm_path.read_text(encoding="utf-8"))
            score = prm.get("prm_score", "N/A")
            lines.append(f"\nQuality score: {score}")
        except (json.JSONDecodeError, OSError):
            pass

    # --- Dynamic content analysis ---
    lines.extend(_dynamic_stage_analysis(stage_num, run_dir))

    return "\n".join(lines)


def _dynamic_stage_analysis(stage_num: int, run_dir: Path) -> list[str]:
    """Generate dynamic analysis based on actual stage output content."""
    lines: list[str] = []
    stage_dir = run_dir / f"stage-{stage_num:02d}"
    if not stage_dir.exists():
        return lines

    try:
        # Stage 5: Literature screening stats
        if stage_num == 5:
            shortlist = stage_dir / "shortlist.jsonl"
            if shortlist.exists():
                count = sum(1 for line in shortlist.read_text(encoding="utf-8").strip().split("\n") if line.strip())
                lines.append(f"\nShortlisted papers: {count}")
                if count < 5:
                    lines.append("⚠ Low paper count — consider broadening search")

        # Stage 8: Baseline defect reproduction
        if stage_num == 8:
            report = stage_dir / "defect_report.json"
            if report.exists():
                data = json.loads(report.read_text(encoding="utf-8"))
                confirmed = data.get("defect_confirmed", False)
                defect_type = data.get("defect_type", "?")
                baseline = data.get("baseline_name", "")
                lines.append(
                    f"\nDefect confirmed: {confirmed} (type={defect_type}, baseline={baseline})"
                )
                if data.get("confidence") is not None:
                    lines.append(f"Confidence: {data.get('confidence')}")

        # Stage 9: Hypothesis analysis
        elif stage_num == 9:
            hyp_file = stage_dir / "hypotheses.md"
            if hyp_file.exists():
                text = hyp_file.read_text(encoding="utf-8")
                hyp_count = text.lower().count("hypothesis")
                lines.append(f"\nHypotheses mentioned: {hyp_count}")
            novelty = stage_dir / "novelty_report.json"
            if novelty.exists():
                data = json.loads(novelty.read_text(encoding="utf-8"))
                score = data.get("novelty_score", "N/A")
                assessment = data.get("assessment", "N/A")
                lines.append(f"Novelty score: {score} ({assessment})")

        # Stage 10: Experiment plan analysis
        elif stage_num == 10:
            import yaml as _yaml_sum
            for plan_file in (stage_dir / "exp_plan.yaml",):
                if plan_file.exists():
                    plan = _yaml_sum.safe_load(plan_file.read_text(encoding="utf-8"))
                    if isinstance(plan, dict):
                        baselines = plan.get("baselines", [])
                        conditions = plan.get("conditions", [])
                        lines.append(f"\nBaselines: {len(baselines)}")
                        lines.append(f"Conditions: {len(conditions)}")
                        if len(baselines) < 2:
                            lines.append("⚠ Few baselines — consider adding standard comparisons")

        # Stage 15: Result analysis
        elif stage_num == 15:
            summary = stage_dir / "experiment_summary.json"
            if summary.exists():
                data = json.loads(summary.read_text(encoding="utf-8"))
                metrics = data.get("metrics_summary", {})
                if metrics:
                    lines.append("\nKey metrics:")
                    for name, vals in list(metrics.items())[:5]:
                        if isinstance(vals, dict):
                            lines.append(f"  {name}: mean={vals.get('mean', '?')}")

    except Exception:
        pass

    return lines


def _file_preview(path: Path, max_len: int = 80) -> str:
    """Get a one-line preview of a file's content."""
    try:
        text = path.read_text(encoding="utf-8")
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith(("{", "[", "---", "#!")):
                return stripped[:max_len]
    except (OSError, UnicodeDecodeError):
        pass
    return ""
