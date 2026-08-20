"""Stage 8: Baseline defect reproduction.

Before any hypothesis is generated, the pipeline must confirm that a real,
algorithmic defect exists in the strongest existing baseline (AGENTS.md §5.4,
§10.2). This stage:

1. Reads the literature synthesis (stage 7).
2. Asks the LLM to name the strongest baseline, the specific defect, the
   minimal reproduction plan, and a self-contained Python script.
3. Validates the script (AST + security) with a one-shot repair pass.
4. Runs it in the sandbox and collects numeric evidence.
5. Adjudicates whether the defect is CONFIRMED (algorithmic) or NOT CONFIRMED
   (refuted / engineering issue).
6. Writes ``defect_report.md`` + ``defect_report.json`` + ``reproduce/``.

Confirmed defects → DONE (the gate human then signs off).
Refuted / engineering defects → PAUSED with decision ``pivot`` so the
orchestrator can roll back to synthesis (GATE_ROLLBACK 8 → 7).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from researchclaw.adapters import AdapterBundle
from researchclaw.config import RCConfig
from researchclaw.experiment.validator import format_issues_for_llm, validate_code
from researchclaw.llm.client import LLMClient
from researchclaw.pipeline._helpers import (
    StageResult,
    _chat_with_prompt,
    _ensure_sandbox_deps,
    _extract_code_block,
    _get_evolution_overlay,
    _parse_metrics_from_stdout,
    _read_prior_artifact,
    _safe_json_loads,
    _utcnow_iso,
)
from researchclaw.pipeline.stages import Stage, StageStatus
from researchclaw.prompts import PromptManager

logger = logging.getLogger(__name__)

_TEMPLATE_CODE = """\
import random

def main():
    # Minimal synthetic reproduction scaffold (LLM path replaces this body).
    # Prints metric lines as 'name: value' for the defect adjudicator.
    symptom = random.uniform(0.4, 0.6)
    print(f"symptom_metric: {symptom:.4f}")

if __name__ == "__main__":
    main()
"""


def _parse_reproduce_plan(content: str) -> dict[str, Any]:
    """Parse the LLM response into a structured reproduction plan."""
    parsed = _safe_json_loads(content, None)
    if isinstance(parsed, dict):
        return parsed
    # Fallback: markdown-ish output — keep the body and pull any code block.
    return {
        "baseline_name": "",
        "claimed_defect": content[:3000],
        "defect_type": "engineering",
        "symptom_metric": "",
        "reproduction_plan": content[:3000],
        "success_criteria": "",
        "code": _extract_code_block(content) or "",
    }


def _format_plan_md(plan: dict[str, Any]) -> str:
    """Human-readable reproduction plan (written to reproduce/reproduce_plan.md)."""
    return (
        "# Reproduction Plan\n\n"
        f"- **Baseline**: {plan.get('baseline_name', '')}\n"
        f"- **Claimed defect**: {plan.get('claimed_defect', '')}\n"
        f"- **Defect type claimed**: {plan.get('defect_type', '')}\n"
        f"- **Symptom metric**: {plan.get('symptom_metric', '')}\n\n"
        "## Plan\n"
        f"{plan.get('reproduction_plan', '')}\n\n"
        "## Success criteria\n"
        f"{plan.get('success_criteria', '')}\n\n"
        "## Script\n"
        "See `reproduce.py`.\n"
    )


def _repair_code(
    llm: LLMClient, _pm: PromptManager, code: str, issues_text: str
) -> str:
    """One-shot LLM repair of validation issues; returns original on failure."""
    try:
        sp = _pm.sub_prompt(
            "code_repair",
            fname="reproduce.py",
            issues_text=issues_text,
            all_files_ctx=code,
        )
        resp = _chat_with_prompt(llm, sp.system, sp.user, max_tokens=8192)
        fixed = _extract_code_block(resp.content)
        return (fixed or resp.content).strip() or code
    except Exception as exc:  # noqa: BLE001
        logger.warning("baseline_reproduce: code repair failed (%s)", exc)
        return code


def _judge_defect(
    llm: LLMClient | None,
    _pm: PromptManager,
    plan: dict[str, Any],
    run_status: str,
    observed_metrics: dict[str, Any],
    code: str,
) -> dict[str, Any]:
    """Adjudicate whether the defect is confirmed, via LLM or a heuristic.

    Returns a verdict dict with keys: defect_confirmed, defect_type,
    confidence, evidence_summary.
    """
    verdict: dict[str, Any] = {
        "defect_confirmed": False,
        "defect_type": plan.get("defect_type", "engineering"),
        "confidence": 0.0,
        "evidence_summary": "No LLM judge available; template verdict.",
    }
    if llm is not None:
        try:
            sp = _pm.sub_prompt(
                "defect_judge",
                claimed_defect=plan.get("claimed_defect", ""),
                reproduction_plan=plan.get("reproduction_plan", ""),
                success_criteria=plan.get("success_criteria", ""),
                run_status=run_status,
                metrics_json=json.dumps(observed_metrics, indent=2, default=str),
                code=code,
            )
            resp = _chat_with_prompt(
                llm, sp.system, sp.user, json_mode=sp.json_mode, max_tokens=sp.max_tokens
            )
            parsed = _safe_json_loads(resp.content, None)
            if isinstance(parsed, dict):
                for key in verdict:
                    if key in parsed:
                        verdict[key] = parsed[key]
        except Exception as exc:  # noqa: BLE001
            logger.warning("baseline_reproduce: defect judge failed (%s)", exc)
    # Heuristic backstop: without numeric evidence there is no confirmation.
    if not run_status.startswith("completed"):
        verdict["defect_confirmed"] = False
        verdict.setdefault(
            "evidence_summary",
            "Reproduction did not complete with numeric evidence; defect not confirmed.",
        )
    elif llm is None and not observed_metrics:
        verdict["defect_confirmed"] = False
    try:
        verdict["confidence"] = float(verdict.get("confidence") or 0.0)
    except (TypeError, ValueError):
        verdict["confidence"] = 0.0
    return verdict


def _write_defect_report(
    stage_dir: Path,
    plan: dict[str, Any],
    verdict: dict[str, Any],
    run_status: str,
    observed_metrics: dict[str, Any],
) -> None:
    """Write defect_report.md and defect_report.json."""
    confirmed = bool(verdict.get("defect_confirmed"))
    md = (
        "# Baseline Defect Reproduction Report\n\n"
        f"- **Baseline**: {plan.get('baseline_name', '')}\n"
        f"- **Claimed defect**: {plan.get('claimed_defect', '')}\n"
        f"- **Defect type claimed**: {plan.get('defect_type', '')}\n"
        f"- **Symptom metric**: {plan.get('symptom_metric', '')}\n"
        f"- **Verdict**: {'CONFIRMED' if confirmed else 'NOT CONFIRMED'}\n"
        f"- **Adjudicated type**: {verdict.get('defect_type', '')}\n"
        f"- **Confidence**: {verdict.get('confidence', 0.0):.2f}\n"
        f"- **Sandbox status**: {run_status}\n\n"
        "## Evidence summary\n"
        f"{verdict.get('evidence_summary', '')}\n\n"
        "## Observed metrics\n"
        "```json\n"
        f"{json.dumps(observed_metrics, indent=2, default=str)}\n"
        "```\n\n"
        "## Success criteria\n"
        f"{plan.get('success_criteria', '')}\n\n"
        "## Minimal reproduction\n"
        "See `reproduce/reproduce.py`.\n"
    )
    (stage_dir / "defect_report.md").write_text(md, encoding="utf-8")

    report_json = {
        "baseline_name": plan.get("baseline_name", ""),
        "claimed_defect": plan.get("claimed_defect", ""),
        "defect_type": verdict.get("defect_type", plan.get("defect_type", "engineering")),
        "defect_confirmed": confirmed,
        "confidence": verdict.get("confidence", 0.0),
        "evidence_summary": verdict.get("evidence_summary", ""),
        "run_status": run_status,
        "observed_metrics": observed_metrics,
        "success_criteria": plan.get("success_criteria", ""),
        "generated": _utcnow_iso(),
    }
    (stage_dir / "defect_report.json").write_text(
        json.dumps(report_json, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _execute_baseline_reproduce(
    stage_dir: Path,
    run_dir: Path,
    config: RCConfig,
    adapters: AdapterBundle,
    *,
    llm: LLMClient | None = None,
    prompts: PromptManager | None = None,
) -> StageResult:
    synthesis = _read_prior_artifact(run_dir, "synthesis.md") or ""

    # Optional user-specified baseline hint (tools CLI --baseline).
    hint_path = run_dir / "baseline_hint.txt"
    if hint_path.exists():
        try:
            hint = hint_path.read_text(encoding="utf-8").strip()
            if hint:
                synthesis = (
                    f"{synthesis}\n\n"
                    "## User-specified baseline to reproduce\n"
                    f"{hint}"
                )
        except OSError:
            pass

    if llm is not None:
        _pm = prompts or PromptManager()
        _overlay = _get_evolution_overlay(run_dir, "baseline_reproduce")
        sp = _pm.for_stage(
            "baseline_reproduce",
            evolution_overlay=_overlay,
            synthesis=synthesis,
            domain_context="",
        )
        resp = _chat_with_prompt(
            llm, sp.system, sp.user, json_mode=sp.json_mode, max_tokens=sp.max_tokens
        )
        plan = _parse_reproduce_plan(resp.content)
    else:
        _pm = prompts or PromptManager()
        plan = {
            "baseline_name": "template-baseline",
            "claimed_defect": "Template defect (no LLM available) — not adjudicated.",
            "defect_type": "engineering",
            "symptom_metric": "symptom_metric",
            "reproduction_plan": "Template plan generated without an LLM.",
            "success_criteria": "symptom_metric > 0.5",
            "code": _TEMPLATE_CODE,
        }

    code = (plan.get("code") or "").strip()
    if not code:
        logger.error("baseline_reproduce: LLM returned no executable code")
        return StageResult(
            stage=Stage.BASELINE_REPRODUCE,
            status=StageStatus.FAILED,
            artifacts=(),
            error="No reproduction code generated",
            decision="retry",
        )

    # --- Validate (AST + security), one-shot repair on failure ---
    validation = validate_code(code, skip_imports=True)
    if not validation.ok and llm is not None:
        repaired = _repair_code(llm, _pm, code, format_issues_for_llm(validation))
        if repaired != code:
            code = repaired
            validation = validate_code(code, skip_imports=True)
    if not validation.ok:
        logger.error(
            "baseline_reproduce: code validation failed: %s",
            format_issues_for_llm(validation),
        )
        return StageResult(
            stage=Stage.BASELINE_REPRODUCE,
            status=StageStatus.FAILED,
            artifacts=(),
            error="Reproduction code failed validation",
            decision="retry",
        )

    # --- Write reproduce/ project ---
    repro_dir = stage_dir / "reproduce"
    repro_dir.mkdir(parents=True, exist_ok=True)
    (repro_dir / "reproduce.py").write_text(code, encoding="utf-8")
    (repro_dir / "reproduce_plan.md").write_text(
        _format_plan_md(plan), encoding="utf-8"
    )

    # --- Run in the sandbox ---
    run_status = "not-run"
    observed_metrics: dict[str, Any] = {}
    try:
        from researchclaw.experiment.factory import create_sandbox

        _ensure_sandbox_deps(code, config.experiment.sandbox.python_path)
        sandbox = create_sandbox(config.experiment, stage_dir / "reproduce_sandbox")
        result = sandbox.run_project(
            repro_dir,
            entry_point="reproduce.py",
            timeout_sec=config.experiment.time_budget_sec,
        )
        observed_metrics = dict(result.metrics or {})
        if not observed_metrics and result.stdout:
            observed_metrics = dict(_parse_metrics_from_stdout(result.stdout))
        if result.returncode == 0 and not result.timed_out:
            run_status = "completed"
        elif result.timed_out:
            run_status = "timed-out"
        else:
            run_status = f"failed (rc={result.returncode})"
        if result.stderr:
            run_status += f"; stderr tail: {result.stderr[-500:]}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("baseline_reproduce: sandbox run failed (%s)", exc)
        run_status = f"sandbox-error: {exc}"

    # --- Adjudicate ---
    verdict = _judge_defect(llm, _pm, plan, run_status, observed_metrics, code)
    confirmed = bool(verdict.get("defect_confirmed"))
    _write_defect_report(stage_dir, plan, verdict, run_status, observed_metrics)

    artifacts = ("defect_report.md", "reproduce/", "defect_report.json")
    evidence_refs = ("stage-08/defect_report.md", "stage-08/reproduce/")
    if confirmed:
        logger.info(
            "baseline_reproduce: defect CONFIRMED for baseline %r "
            "(type=%s, confidence=%.2f)",
            plan.get("baseline_name", ""),
            verdict.get("defect_type", ""),
            verdict.get("confidence", 0.0),
        )
        return StageResult(
            stage=Stage.BASELINE_REPRODUCE,
            status=StageStatus.DONE,
            artifacts=artifacts,
            evidence_refs=evidence_refs,
        )
    logger.info(
        "baseline_reproduce: defect NOT confirmed (type=%s) — pausing",
        verdict.get("defect_type", ""),
    )
    return StageResult(
        stage=Stage.BASELINE_REPRODUCE,
        status=StageStatus.PAUSED,
        artifacts=artifacts,
        error=(
            "Baseline defect not confirmed (or adjudicated as engineering) — "
            "no valid hypothesis direction"
        ),
        decision="pivot",
        evidence_refs=evidence_refs,
    )
