from __future__ import annotations

import json
import logging
import math
import os
import shutil
import tempfile
import threading
import time as _time
from pathlib import Path

from researchclaw.adapters import AdapterBundle
from researchclaw.config import RCConfig
from researchclaw.evolution import EvolutionStore, extract_lessons
from researchclaw.knowledge.base import write_stage_to_kb
from researchclaw.pipeline.executor import StageResult, execute_stage
from researchclaw.pipeline.stages import (
    DECISION_ROLLBACK,
    MAX_DECISION_PIVOTS,
    NONCRITICAL_STAGES,
    STAGE_SEQUENCE,
    Stage,
    StageStatus,
)

def _utcnow_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _should_start(stage: Stage, from_stage: Stage, started: bool) -> bool:
    if started:
        return True
    return stage == from_stage

def _build_pipeline_summary(
    *,
    run_id: str,
    results: list[StageResult],
    from_stage: Stage,
    run_dir: Path | None = None,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "run_id": run_id,
        "stages_executed": len(results),
        "stages_done": sum(1 for item in results if item.status == StageStatus.DONE),
        "stages_paused": sum(
            1 for item in results if item.status == StageStatus.PAUSED
        ),
        "stages_blocked": sum(
            1 for item in results if item.status == StageStatus.BLOCKED_APPROVAL
        ),
        "stages_failed": sum(
            1 for item in results if item.status == StageStatus.FAILED
        ),
        "degraded": any(r.decision == "degraded" for r in results),
        "from_stage": int(from_stage),
        "final_stage": int(results[-1].stage) if results else int(from_stage),
        "final_status": results[-1].status.value if results else "no_stages",
        "generated": _utcnow_iso(),
        "content_metrics": _collect_content_metrics(run_dir),
    }
    return summary

def _write_pipeline_summary(run_dir: Path, summary: dict[str, object]) -> None:
    (run_dir / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

def _write_checkpoint(
    run_dir: Path, stage: Stage, run_id: str,
    adapters: "AdapterBundle | None" = None,
) -> None:
    """Write checkpoint atomically via temp file + rename to prevent corruption."""
    checkpoint: dict[str, object] = {
        "last_completed_stage": int(stage),
        "last_completed_name": stage.name,
        "run_id": run_id,
        "timestamp": _utcnow_iso(),
    }

    # Embed HITL session data if available
    if adapters is not None:
        hitl_session = getattr(adapters, "hitl", None)
        if hitl_session is not None:
            try:
                checkpoint["hitl"] = hitl_session.hitl_checkpoint_data()
            except Exception:
                pass
    target = run_dir / "checkpoint.json"
    fd, tmp_path = tempfile.mkstemp(dir=run_dir, suffix=".tmp", prefix="checkpoint_")
    os.close(fd)
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(checkpoint, indent=2))
        Path(tmp_path).replace(target)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise

def _write_heartbeat(run_dir: Path, stage: Stage, run_id: str) -> None:
    """Write heartbeat file for sentinel watchdog monitoring."""
    import os

    heartbeat = {
        "pid": os.getpid(),
        "last_stage": int(stage),
        "last_stage_name": stage.name,
        "run_id": run_id,
        "timestamp": _utcnow_iso(),
    }
    (run_dir / "heartbeat.json").write_text(
        json.dumps(heartbeat, indent=2), encoding="utf-8"
    )

def read_checkpoint(run_dir: Path) -> Stage | None:
    """Read checkpoint and return the NEXT stage to execute, or None if no checkpoint."""
    cp_path = run_dir / "checkpoint.json"
    if not cp_path.exists():
        return None
    try:
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        last_num = data.get("last_completed_stage")
        if last_num is None:
            return None
        for i, stage in enumerate(STAGE_SEQUENCE):
            if int(stage) == last_num:
                if i + 1 < len(STAGE_SEQUENCE):
                    return STAGE_SEQUENCE[i + 1]
                return None
        return None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None

def resume_from_checkpoint(
    run_dir: Path, default_stage: Stage = Stage.TOPIC_INIT
) -> Stage:
    """Resolve the stage to resume from using checkpoint metadata."""
    next_stage = read_checkpoint(run_dir)
    return next_stage if next_stage is not None else default_stage

def _collect_content_metrics(run_dir: Path | None) -> dict[str, object]:
    """Collect experiment result metrics from stage outputs."""
    metrics: dict[str, object] = {
        "best_metric": None,
        "decision": None,
        "degraded_sources": [],
    }
    if run_dir is None:
        return metrics

    # Best experiment summary (promoted to run root by _promote_best_stage15)
    summary_path = run_dir / "experiment_summary_best.json"
    if not summary_path.exists():
        for _s15 in sorted(run_dir.glob("stage-15*"), reverse=True):
            _alt = _s15 / "experiment_summary.json"
            if _alt.exists():
                summary_path = _alt
                break
    if summary_path.exists():
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ms = data.get("metrics_summary", {})
                if isinstance(ms, dict):
                    for key, val in ms.items():
                        if isinstance(val, dict) and "mean" in val:
                            metrics["best_metric"] = {
                                "name": key,
                                "mean": val["mean"],
                            }
                            break
                        if isinstance(val, (int, float)):
                            metrics["best_metric"] = {"name": key, "mean": val}
                            break
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    # Research decision (stage-16)
    decision_path = run_dir / "stage-16" / "decision.md"
    if not decision_path.exists():
        for _s16 in sorted(run_dir.glob("stage-16*"), reverse=True):
            _alt = _s16 / "decision.md"
            if _alt.exists():
                decision_path = _alt
                break
    if decision_path.exists():
        try:
            first_line = decision_path.read_text(encoding="utf-8").strip().splitlines()
            metrics["decision"] = first_line[0] if first_line else "recorded"
        except (OSError, UnicodeDecodeError):
            metrics["decision"] = "recorded"

    return metrics

logger = logging.getLogger(__name__)

def _run_experiment_diagnosis(run_dir: Path, config: RCConfig, run_id: str) -> None:
    """Run experiment diagnosis after Stage 15 and save reports.

    Produces:
    - ``run_dir/experiment_diagnosis.json`` — structured diagnosis + quality assessment
    - ``run_dir/repair_prompt.txt`` — repair instructions (if quality is insufficient)
    """
    try:
        from researchclaw.pipeline.experiment_diagnosis import (
            diagnose_experiment,
            assess_experiment_quality,
        )

        # Find the most recent stage-15 experiment_summary.json
        summary_path = None
        for candidate in sorted(run_dir.glob("stage-15*/experiment_summary.json")):
            summary_path = candidate
        if not summary_path or not summary_path.exists():
            return

        summary = json.loads(summary_path.read_text(encoding="utf-8"))

        # Collect stdout/stderr from experiment runs
        # Look in stage-13 (EXPERIMENT_RUN) and stage-14 (ITERATIVE_REFINE), not stage-15
        stdout, stderr = "", ""
        runs_dir = None
        for _candidate_runs in sorted(run_dir.glob("stage-1[23]*/runs"), reverse=True):
            if _candidate_runs.is_dir():
                runs_dir = _candidate_runs
                break
        if runs_dir is None:
            runs_dir = summary_path.parent / "runs"
        if runs_dir.is_dir():
            for run_file in sorted(runs_dir.glob("*.json"))[:5]:
                try:
                    run_data = json.loads(run_file.read_text(encoding="utf-8"))
                    if isinstance(run_data, dict):
                        stdout += run_data.get("stdout", "") + "\n"
                        stderr += run_data.get("stderr", "") + "\n"
                except (json.JSONDecodeError, OSError):
                    continue

        # Load experiment plan from stage-10
        plan = None
        for candidate in sorted(run_dir.glob("stage-10*/exp_plan.yaml")):
            try:
                import yaml as _yaml_diag
                plan = _yaml_diag.safe_load(candidate.read_text(encoding="utf-8"))
            except Exception:
                pass
        if plan is None:
            for candidate in sorted(run_dir.glob("stage-10*/experiment_design.json")):
                try:
                    plan = json.loads(candidate.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass

        # Load refinement log if available
        ref_log = None
        for candidate in sorted(run_dir.glob("stage-14*/refinement_log.json")):
            try:
                ref_log = json.loads(candidate.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        # Run diagnosis
        diag = diagnose_experiment(
            experiment_summary=summary,
            experiment_plan=plan,
            refinement_log=ref_log,
            stdout=stdout.strip(),
            stderr=stderr.strip(),
        )

        # Run quality assessment
        qa = assess_experiment_quality(summary, ref_log)

        # Save diagnosis report
        diag_report = {
            "diagnosis": diag.to_dict(),
            "quality_assessment": {
                "mode": qa.mode.value,
                "sufficient": qa.sufficient,
                "repair_possible": qa.repair_possible,
                "deficiency_types": [d.type.value for d in qa.deficiencies],
            },
            "repair_needed": not qa.sufficient,
            "generated": _utcnow_iso(),
        }
        (run_dir / "experiment_diagnosis.json").write_text(
            json.dumps(diag_report, indent=2), encoding="utf-8"
        )

        if not qa.sufficient:
            # Generate repair prompt for the REFINE loop
            from researchclaw.pipeline.experiment_repair import build_repair_prompt

            code: dict[str, str] = {}
            # Try refined code first, then stage-11 experiment dir, then raw stage-11
            for _glob_pat in (
                "stage-14*/experiment_final/*.py",
                "stage-11*/experiment/*.py",
                "stage-11*/*.py",
            ):
                for candidate in sorted(run_dir.glob(_glob_pat)):
                    try:
                        code[candidate.name] = candidate.read_text(encoding="utf-8")
                    except (OSError, UnicodeDecodeError):
                        pass
                if code:
                    break

            repair_prompt = build_repair_prompt(
                diag, code, time_budget_sec=config.experiment.time_budget_sec
            )
            (run_dir / "repair_prompt.txt").write_text(
                repair_prompt, encoding="utf-8"
            )
            logger.info(
                "[%s] Experiment diagnosis: mode=%s, deficiencies=%d — repair prompt saved",
                run_id, qa.mode.value, len(diag.deficiencies),
            )
            print(
                f"[{run_id}] Experiment diagnosis: {qa.mode.value} "
                f"({len(diag.deficiencies)} issues found, repair needed)"
            )
        else:
            logger.info(
                "[%s] Experiment diagnosis: mode=%s, sufficient=True — quality OK",
                run_id, qa.mode.value,
            )
            print(f"[{run_id}] Experiment diagnosis: {qa.mode.value} — quality OK")

    except Exception as exc:
        logger.warning("Experiment diagnosis failed: %s", exc)

def _run_experiment_repair(run_dir: Path, config: RCConfig, run_id: str) -> None:
    """Execute the experiment repair loop when diagnosis finds quality issues.

    Calls the repair loop from ``experiment_repair.py`` which:
    1. Loads experiment code and diagnosis
    2. Gets fixes from LLM or OpenCode
    3. Re-runs experiment in sandbox
    4. Re-assesses quality
    5. Repeats up to max_cycles
    """
    try:
        from researchclaw.pipeline.experiment_repair import run_repair_loop

        repair_result = run_repair_loop(
            run_dir=run_dir,
            config=config,
            run_id=run_id,
        )

        # Save repair result
        (run_dir / "experiment_repair_result.json").write_text(
            json.dumps(repair_result.to_dict(), indent=2), encoding="utf-8"
        )

        # BUG-186: Promote best experiment summary to stage-15/ so
        # downstream stages (analysis, decision) see it.
        # BUG-198: Only promote if the repair summary is RICHER than
        # the existing stage-15 summary.  The repair loop can produce
        # empty summaries (metrics: {}, 0 conditions) which would
        # overwrite enriched data from the analysis stage.
        if repair_result.best_experiment_summary:
            from researchclaw.pipeline.experiment_repair import (
                _summary_quality_score,
            )

            best_path = run_dir / "stage-15" / "experiment_summary.json"
            existing_score = 0.0
            if best_path.exists():
                try:
                    existing = json.loads(
                        best_path.read_text(encoding="utf-8")
                    )
                    existing_score = _summary_quality_score(existing)
                except (json.JSONDecodeError, OSError):
                    pass

            repair_score = _summary_quality_score(
                repair_result.best_experiment_summary
            )

            if repair_score > existing_score:
                best_path.write_text(
                    json.dumps(
                        repair_result.best_experiment_summary, indent=2
                    ),
                    encoding="utf-8",
                )
                logger.info(
                    "[%s] Promoted repair results to stage-15 "
                    "(score %.1f > %.1f, success=%s)",
                    run_id, repair_score, existing_score,
                    repair_result.success,
                )
            else:
                logger.info(
                    "[%s] Kept existing stage-15 summary (score %.1f >= "
                    "repair score %.1f)",
                    run_id, existing_score, repair_score,
                )

        if repair_result.success:
            # Re-run diagnosis with updated results
            _run_experiment_diagnosis(run_dir, config, run_id)
        else:
            logger.info(
                "[%s] Repair loop completed without reaching full_paper quality "
                "(best mode: %s, %d cycles)",
                run_id, repair_result.final_mode.value, repair_result.total_cycles,
            )

    except Exception as exc:
        logger.warning("[%s] Experiment repair failed: %s", run_id, exc)
        print(f"[{run_id}] Experiment repair failed: {exc}")

def execute_pipeline(
    *,
    run_dir: Path,
    run_id: str,
    config: RCConfig,
    adapters: AdapterBundle,
    from_stage: Stage = Stage.TOPIC_INIT,
    to_stage: Stage | None = None,
    auto_approve_gates: bool = False,
    stop_on_gate: bool = False,
    skip_noncritical: bool = False,
    kb_root: Path | None = None,
    cancel_event: "threading.Event | None" = None,
) -> list[StageResult]:
    """Execute pipeline stages sequentially from *from_stage* to *to_stage* (inclusive)."""

    results: list[StageResult] = []
    started = False
    total_stages = len(STAGE_SEQUENCE)

    # Force the domain detector to honor a deployed profile (if any) so
    # every stage picks the same adapter.  Safe no-op when empty.
    try:
        from researchclaw.domains.detector import set_forced_profile
        forced = getattr(config.project, "profile", "") or ""
        set_forced_profile(forced)
    except Exception:  # noqa: BLE001
        pass

    # ── Integration hooks: EventLog, ExperimentMemory, CostTracker ──
    event_log = None
    try:
        from researchclaw.pipeline.event_log import EventLog, EventType, create_event
        event_log = EventLog(log_dir=run_dir)
        event_log.append(create_event(
            EventType.PIPELINE_START, run_id=run_id,
            stages=total_stages, from_stage=int(from_stage),
        ))
    except Exception:
        logger.debug("Event log initialisation skipped")

    exp_memory = None
    try:
        from researchclaw.memory.experiment_memory import ExperimentMemory
        _mem_dir = run_dir / "experiment_memory"
        _mem_dir.mkdir(parents=True, exist_ok=True)
        exp_memory = ExperimentMemory(store_dir=str(_mem_dir))
    except Exception:
        logger.debug("Experiment memory initialisation skipped")

    cost_budget = getattr(config.experiment.cli_agent, "max_budget_usd", 0.0) or 0.0

    for stage in STAGE_SEQUENCE:
        started = _should_start(stage, from_stage, started)
        if not started:
            continue

        # ── Check for cancellation before each stage ──
        if cancel_event is not None and cancel_event.is_set():
            logger.info("[%s] Pipeline cancelled before stage %s", run_id, stage.name)
            print(f"[{run_id}] Pipeline cancelled by user.")
            break

        stage_num = int(stage)
        prefix = f"[{run_id}] Stage {stage_num:02d}/{total_stages}"
        print(f"{prefix} {stage.name} — running...")

        # ── Event log: stage start ──
        if event_log:
            try:
                event_log.append(create_event(
                    EventType.STAGE_START, run_id=run_id, stage=stage.name,
                ))
            except Exception:
                pass

        # ── Cost budget check ──
        if cost_budget > 0:
            try:
                from researchclaw.cost_tracker import get_global_tracker
                if not get_global_tracker().check_budget(cost_budget):
                    logger.warning("Cost budget $%.2f exceeded — pausing pipeline", cost_budget)
                    print(f"{prefix} BUDGET EXCEEDED (${cost_budget:.2f}) — stopping")
                    break
            except Exception:
                pass

        t0 = _time.monotonic()

        result = execute_stage(
            stage,
            run_dir=run_dir,
            run_id=run_id,
            config=config,
            adapters=adapters,
            auto_approve_gates=auto_approve_gates,
        )
        elapsed = _time.monotonic() - t0

        # ── Event log: stage end ──
        if event_log:
            try:
                etype = EventType.STAGE_END if result.status == StageStatus.DONE else EventType.STAGE_FAIL
                event_log.append(create_event(
                    etype, run_id=run_id, stage=stage.name,
                    status=result.status.value, elapsed_sec=round(elapsed, 1),
                    error=result.error,
                ))
            except Exception:
                pass

        # ── ExperimentSpec: generate after design, validate after analysis ──
        if stage == Stage.EXPERIMENT_DESIGN and result.status == StageStatus.DONE:
            try:
                from researchclaw.pipeline.experiment_spec import ExperimentSpec, MetricDef, generate_spec
                spec_text = generate_spec(config.research.topic, "")
                spec_path = run_dir / f"stage-{int(stage):02d}" / "experiment_spec.md"
                spec_path.write_text(spec_text, encoding="utf-8")
                logger.info("Experiment spec generated: %s", spec_path)
            except Exception:
                logger.debug("Experiment spec generation skipped")

        if stage == Stage.RESULT_ANALYSIS and result.status == StageStatus.DONE:
            try:
                from researchclaw.pipeline.experiment_spec import parse_spec, validate_results_against_spec
                spec_path = run_dir / "stage-10" / "experiment_spec.md"
                if spec_path.exists():
                    spec = parse_spec(spec_path.read_text(encoding="utf-8"))
                    results_path = run_dir / "results.json"
                    exp_results = {}
                    if results_path.exists():
                        exp_results = json.loads(results_path.read_text(encoding="utf-8"))
                    violations = validate_results_against_spec(spec, exp_results)
                    if violations:
                        logger.warning("Spec violations: %s", violations)
                        (run_dir / f"stage-{int(stage):02d}" / "spec_violations.json").write_text(
                            json.dumps(violations, indent=2), encoding="utf-8"
                        )
            except Exception:
                logger.debug("Experiment spec validation skipped")

        # ── Pitfall detection after code generation / experiment run ──
        if stage in (Stage.CODE_GENERATION, Stage.EXPERIMENT_RUN) and result.status == StageStatus.DONE:
            try:
                from researchclaw.pipeline.pitfall_detector import PitfallDetector
                detector = PitfallDetector()
                code_path = run_dir / f"stage-{int(stage):02d}"
                code_files = list(code_path.rglob("*.py"))
                code_text = "\n".join(f.read_text(errors="ignore") for f in code_files[:5])
                pitfalls = detector.detect_all(code=code_text, results={}, experiment_config={})
                if pitfalls:
                    critical = [p for p in pitfalls if p.severity == "critical"]
                    if critical:
                        logger.warning("CRITICAL pitfalls detected: %s", [p.description for p in critical])
                    pitfall_report = [{"type": p.type.value, "severity": p.severity, "description": p.description} for p in pitfalls]
                    (run_dir / f"stage-{int(stage):02d}" / "pitfall_report.json").write_text(
                        json.dumps(pitfall_report, indent=2), encoding="utf-8"
                    )
            except Exception:
                logger.debug("Pitfall detection skipped")

        # ── Experiment memory: record outcome after experiment stages ──
        if stage in (Stage.EXPERIMENT_RUN, Stage.ITERATIVE_REFINE) and result.status == StageStatus.DONE and exp_memory:
            try:
                from researchclaw.memory.experiment_memory import ExperimentOutcome
                import time as _time_mod
                results_path = run_dir / "results.json"
                metric_val = 0.0
                if results_path.exists():
                    rdata = json.loads(results_path.read_text(encoding="utf-8"))
                    metric_val = rdata.get(config.experiment.metric_key, 0.0)
                exp_memory.record_outcome(ExperimentOutcome(
                    run_id=run_id, stage=stage.name,
                    hypothesis=config.research.topic, config={},
                    metric_name=config.experiment.metric_key,
                    metric_value=float(metric_val) if metric_val else 0.0,
                    baseline_value=0.0, improvement=0.0,
                    success=result.status == StageStatus.DONE,
                    failure_mode=result.error,
                    packages_used=[], hyperparameters={},
                    timestamp=_time_mod.time(), duration_sec=elapsed,
                ))
            except Exception:
                logger.debug("Experiment memory recording skipped")

        if result.status == StageStatus.DONE:
            arts = ", ".join(result.artifacts) if result.artifacts else "none"
            if result.decision == "degraded":
                print(
                    f"{prefix} {stage.name} — DEGRADED ({elapsed:.1f}s) "
                    f"— continuing with sanitization → {arts}"
                )
            else:
                print(f"{prefix} {stage.name} — done ({elapsed:.1f}s) → {arts}")
        elif result.status == StageStatus.FAILED:
            err = result.error or "unknown error"
            print(f"{prefix} {stage.name} — FAILED ({elapsed:.1f}s) — {err}")
        elif result.status == StageStatus.BLOCKED_APPROVAL:
            print(f"{prefix} {stage.name} — blocked (awaiting approval)")
        elif result.status == StageStatus.PAUSED:
            err = result.error or "paused"
            print(f"{prefix} {stage.name} -- PAUSED ({elapsed:.1f}s) -- {err}")
        results.append(result)

        if kb_root is not None and result.status == StageStatus.DONE:
            try:
                stage_dir = run_dir / f"stage-{int(stage):02d}"
                write_stage_to_kb(
                    kb_root,
                    stage_id=int(stage),
                    stage_name=stage.name.lower(),
                    run_id=run_id,
                    artifacts=list(result.artifacts),
                    stage_dir=stage_dir,
                    backend=config.knowledge_base.backend,
                    topic=config.research.topic,
                )
            except Exception:  # noqa: BLE001
                pass

        if result.status == StageStatus.DONE:
            _write_checkpoint(run_dir, stage, run_id, adapters=adapters)

        # ── Stop after to_stage if specified ──
        if to_stage is not None and stage == to_stage:
            logger.info("[%s] Reached --to-stage %s, stopping.", run_id, stage.name)
            print(f"[{run_id}] Reached --to-stage {stage.name}, stopping pipeline.")
            break

        # --- Experiment diagnosis + repair after Stage 15 (result_analysis) ---
        if (
            stage == Stage.RESULT_ANALYSIS
            and result.status == StageStatus.DONE
            and config.experiment.repair.enabled
            # Agent-based sandboxes (collider_agent / biology_agent / stat_agent)
            # write a canonical results.json atomically in stage 13.  Stage-14
            # repair would just iterate on python source files that the agent
            # never executed, then call sandbox.run_project() — which for agent
            # sandboxes redundantly re-spawns the whole agent.  Skip the
            # python-code repair loop entirely; the proceed-or-reject decision
            # belongs in stage 16 RESEARCH_DECISION.
            and config.experiment.mode not in ("collider_agent", "biology_agent", "stat_agent")
        ):
            _run_experiment_diagnosis(run_dir, config, run_id)

            # Check if repair loop should run
            _diag_path = run_dir / "experiment_diagnosis.json"
            if _diag_path.exists():
                try:
                    _diag_data = json.loads(_diag_path.read_text(encoding="utf-8"))
                    if _diag_data.get("repair_needed"):
                        _run_experiment_repair(run_dir, config, run_id)
                except (json.JSONDecodeError, OSError):
                    pass

        # --- Heartbeat for sentinel watchdog ---
        if result.status == StageStatus.DONE:
            _write_heartbeat(run_dir, stage, run_id)

        # --- PIVOT/REFINE decision handling ---
        if (
            stage == Stage.RESEARCH_DECISION
            and result.status == StageStatus.DONE
            and result.decision in DECISION_ROLLBACK
        ):
            pivot_count = _read_pivot_count(run_dir)
            # R6-4: Skip REFINE if experiment metrics are empty for consecutive cycles
            if pivot_count > 0 and _consecutive_empty_metrics(run_dir, pivot_count):
                logger.warning(
                    "Consecutive REFINE cycles produced empty metrics — forcing PROCEED"
                )
                print(
                    f"[{run_id}] Consecutive empty metrics across REFINE cycles — forcing PROCEED"
                )
                # BUG-211: Promote best stage-15 before proceeding with
                # empty data — an earlier iteration may have real metrics.
                _promote_best_stage15(run_dir, config)
            elif pivot_count < MAX_DECISION_PIVOTS:
                rollback_target = DECISION_ROLLBACK[result.decision]
                # Agent-based modes: REFINE means re-run the agent atomically.
                # Stage 14 ITERATIVE_REFINE is a no-op for these modes (it
                # would refine python files the agent never executed), so
                # routing REFINE there wastes a pipeline cycle.  Send REFINE
                # straight back to EXPERIMENT_RUN so the sandbox re-spawns
                # claude with the REPAIR_PROMPT.md the requirements gate
                # just wrote.
                if (
                    config.experiment.mode in ("collider_agent", "biology_agent", "stat_agent")
                    and result.decision == "refine"
                ):
                    rollback_target = Stage.EXPERIMENT_RUN
                _record_decision_history(
                    run_dir, result.decision, rollback_target, pivot_count + 1
                )
                logger.info(
                    "Decision %s: rolling back to %s (attempt %d/%d)",
                    result.decision.upper(),
                    rollback_target.name,
                    pivot_count + 1,
                    MAX_DECISION_PIVOTS,
                )
                print(
                    f"[{run_id}] Decision: {result.decision.upper()} → "
                    f"rollback to {rollback_target.name} "
                    f"(attempt {pivot_count + 1}/{MAX_DECISION_PIVOTS})"
                )
                # Version existing stage directories before overwriting.
                # Agent-mode REFINE preserves the stage-13 workspace via
                # incremental snapshot (copytree, not rename) so the
                # rerunning sandbox can read prior model files / CSVs / KO
                # tables instead of starting from a blank workspace.  This
                # is what makes the requirements-gate retry usefully
                # incremental rather than just a stochastic resample.
                _agent_refine = (
                    config.experiment.mode in ("collider_agent", "biology_agent", "stat_agent")
                    and result.decision == "refine"
                )
                _version_rollback_stages(
                    run_dir, rollback_target, pivot_count + 1,
                    incremental=_agent_refine,
                )
                # Recurse from rollback target
                pivot_results = execute_pipeline(
                    run_dir=run_dir,
                    run_id=run_id,
                    config=config,
                    adapters=adapters,
                    from_stage=rollback_target,
                    auto_approve_gates=auto_approve_gates,
                    stop_on_gate=stop_on_gate,
                    skip_noncritical=skip_noncritical,
                    kb_root=kb_root,
                    cancel_event=cancel_event,
                )
                results.extend(pivot_results)
                # BUG-211: Promote best stage-15 after REFINE completes so
                # downstream stages use the best data, not just the latest.
                _promote_best_stage15(run_dir, config)
                break  # Exit current loop; recursive call handles the rest
            else:
                # Quality gate: check if experiment results are actually usable
                _quality_ok, _quality_msg = _check_experiment_quality(
                    run_dir, pivot_count
                )
                if not _quality_ok:
                    logger.warning(
                        "Max pivot attempts (%d) reached — forcing PROCEED "
                        "with quality warning: %s",
                        MAX_DECISION_PIVOTS,
                        _quality_msg,
                    )
                    print(
                        f"[{run_id}] QUALITY WARNING: {_quality_msg}"
                    )
                    # Write quality warning to run directory
                    _qw_path = run_dir / "quality_warning.txt"
                    _qw_path.write_text(
                        f"Max pivots ({MAX_DECISION_PIVOTS}) reached.\n"
                        f"Quality gate failed: {_quality_msg}\n"
                        "Proceeding to research decision — results may have "
                        "significant issues.\n",
                        encoding="utf-8",
                    )
                else:
                    logger.warning(
                        "Max pivot attempts (%d) reached — forcing PROCEED",
                        MAX_DECISION_PIVOTS,
                    )
                print(
                    f"[{run_id}] Max pivot attempts reached — forcing PROCEED"
                )

                # BUG-205: After forced PROCEED, promote the BEST stage-15
                # experiment summary across all REFINE iterations.
                _promote_best_stage15(run_dir, config)

        # --- HITL: Handle abort decision ---
        if result.decision == "abort":
            logger.info("[%s] Pipeline aborted by user at stage %s", run_id, stage.name)
            print(f"[{run_id}] Pipeline aborted by user at {stage.name}")
            break

        if result.status == StageStatus.FAILED:
            if skip_noncritical and stage in NONCRITICAL_STAGES:
                logger.warning("Noncritical stage %s failed - skipping", stage.name)
            else:
                break

        if result.status == StageStatus.PAUSED:
            logger.warning(
                "[%s] Pipeline paused at %s: %s",
                run_id,
                stage.name,
                result.error or result.decision,
            )
            break

        # --- HITL: Handle rejected stage (from HITL review) ---
        if result.status == StageStatus.REJECTED:
            logger.info(
                "[%s] Stage %s rejected by reviewer — pipeline stopped",
                run_id, stage.name,
            )
            print(f"[{run_id}] Stage {stage.name} rejected — pipeline stopped")
            break

        if result.status == StageStatus.BLOCKED_APPROVAL and stop_on_gate:
            break

    summary = _build_pipeline_summary(
        run_id=run_id,
        results=results,
        from_stage=from_stage,
        run_dir=run_dir,
    )
    _write_pipeline_summary(run_dir, summary)

    # ── Event log: pipeline end ──
    if event_log:
        try:
            done_count = sum(1 for r in results if r.status == StageStatus.DONE)
            failed_count = sum(1 for r in results if r.status == StageStatus.FAILED)
            event_log.append(create_event(
                EventType.PIPELINE_END, run_id=run_id,
                stages_done=done_count, stages_failed=failed_count,
            ))
        except Exception:
            pass

    # --- Evolution: extract and store lessons ---
    lessons: list[object] = []
    try:
        lessons = extract_lessons(results, run_id=run_id, run_dir=run_dir)
        if lessons:
            store = EvolutionStore(run_dir / "evolution")
            store.append_many(lessons)
            logger.info("Extracted %d lessons from pipeline run", len(lessons))
    except Exception:  # noqa: BLE001
        logger.warning("Evolution lesson extraction failed (non-blocking)")

    # --- MetaClaw bridge: convert high-severity lessons to skills ---
    try:
        _metaclaw_post_pipeline(config, results, lessons, run_id, run_dir)
    except Exception:  # noqa: BLE001
        logger.warning("MetaClaw post-pipeline hook failed (non-blocking)")

    # --- Package deliverables into a single folder ---
    try:
        deliverables_dir = _package_deliverables(run_dir, run_id, config)
        if deliverables_dir is not None:
            print(f"[{run_id}] Deliverables packaged → {deliverables_dir}")
    except Exception:  # noqa: BLE001
        logger.warning("Deliverables packaging failed (non-blocking)")

    # --- HITL: Finalize session state ---
    try:
        hitl_session = getattr(adapters, "hitl", None)
        if hitl_session is not None:
            has_abort = any(
                r.decision == "abort" for r in results
            )
            has_failure = any(
                r.status == StageStatus.FAILED for r in results
            )
            if has_abort:
                hitl_session.abort()
            elif has_failure:
                hitl_session.abort()
            else:
                hitl_session.complete()
    except Exception:  # noqa: BLE001
        logger.debug("HITL session finalization failed (non-blocking)")

    return results

def _package_deliverables(
    run_dir: Path,
    run_id: str,
    config: RCConfig,
) -> Path | None:
    """Collect all final experiment deliverables into a single ``deliverables/`` folder.

    Returns the deliverables directory path, or None if nothing was packaged.

    Packaged artifacts (best-available version selected automatically):
    - experiment_summary_best.json — Best experiment summary across iterations
    - analysis.md                 — Result analysis (best iteration)
    - decision.md                 — Research decision (stage 16)
    - defect_report.md            — Baseline defect reproduction report (stage 8)
    - synthesis.md                — Literature synthesis (stage 7)
    - experiment_code/            — Experiment source code
    - charts/                     — Result visualizations
    - reproduce/                  — Baseline reproduction script (stage 8)
    """
    dest = run_dir / "deliverables"
    dest.mkdir(parents=True, exist_ok=True)

    packaged: list[str] = []

    # --- 1. Best experiment summary ---
    summary_src = run_dir / "experiment_summary_best.json"
    if not summary_src.exists():
        for _s15 in sorted(run_dir.glob("stage-15*"), reverse=True):
            _alt = _s15 / "experiment_summary.json"
            if _alt.exists():
                summary_src = _alt
                break
    if summary_src.exists() and summary_src.stat().st_size > 0:
        shutil.copy2(summary_src, dest / "experiment_summary_best.json")
        packaged.append("experiment_summary_best.json")

    # --- 2. Result analysis (best iteration) ---
    analysis_src = run_dir / "analysis_best.md"
    if not analysis_src.exists():
        for _s15 in sorted(run_dir.glob("stage-15*"), reverse=True):
            _alt = _s15 / "analysis.md"
            if _alt.exists():
                analysis_src = _alt
                break
    if analysis_src.exists() and analysis_src.stat().st_size > 0:
        shutil.copy2(analysis_src, dest / "analysis.md")
        packaged.append("analysis.md")

    # --- 3. Research decision (stage 16) ---
    decision_src = None
    for candidate in (run_dir / "stage-16" / "decision.md", run_dir / "decision.md"):
        if candidate.exists() and candidate.stat().st_size > 0:
            decision_src = candidate
            break
    if decision_src is not None:
        shutil.copy2(decision_src, dest / "decision.md")
        packaged.append("decision.md")

    # --- 4. Baseline defect report + reproduction script (stage 8) ---
    defect_src = None
    for candidate in (
        run_dir / "stage-08" / "defect_report.md",
        run_dir / "defect_report.md",
    ):
        if candidate.exists() and candidate.stat().st_size > 0:
            defect_src = candidate
            break
    if defect_src is not None:
        shutil.copy2(defect_src, dest / "defect_report.md")
        packaged.append("defect_report.md")
    repro_src = run_dir / "stage-08" / "reproduce"
    if repro_src.is_dir():
        repro_dest = dest / "reproduce"
        if repro_dest.exists():
            shutil.rmtree(repro_dest)
        shutil.copytree(repro_src, repro_dest)
        packaged.append("reproduce/")

    # --- 5. Literature synthesis (stage 7) ---
    syn_src = None
    for candidate in (
        run_dir / "stage-07" / "synthesis.md",
        run_dir / "synthesis.md",
    ):
        if candidate.exists() and candidate.stat().st_size > 0:
            syn_src = candidate
            break
    if syn_src is not None:
        shutil.copy2(syn_src, dest / "synthesis.md")
        packaged.append("synthesis.md")

    # --- 6. Experiment code package ---
    code_src = run_dir / "stage-14" / "experiment_final"
    if not code_src.is_dir():
        code_src = run_dir / "stage-11" / "experiment"
    if not code_src.is_dir():
        code_src = run_dir / "stage-11"
    if code_src.is_dir():
        code_dest = dest / "experiment_code"
        if code_dest.exists():
            shutil.rmtree(code_dest)
        shutil.copytree(code_src, code_dest)
        packaged.append("experiment_code/")

    # --- 7. Charts (from best analysis iteration) ---
    charts_src = None
    for _s15 in sorted(run_dir.glob("stage-15*"), reverse=True):
        _cand = _s15 / "charts"
        if _cand.is_dir() and any(_cand.iterdir()):
            charts_src = _cand
            break
    if charts_src is None:
        _cand = run_dir / "charts"
        if _cand.is_dir() and any(_cand.iterdir()):
            charts_src = _cand
    if charts_src is not None:
        charts_dest = dest / "charts"
        if charts_dest.exists():
            shutil.rmtree(charts_dest)
        shutil.copytree(charts_src, charts_dest)
        packaged.append("charts/")

    if not packaged:
        # Nothing to package — remove empty dir
        dest.rmdir()
        return None

    # --- Write manifest ---
    manifest = {
        "run_id": run_id,
        "files": packaged,
        "generated": _utcnow_iso(),
        "notes": {
            "experiment_summary_best.json": "Best experiment summary across iterations",
            "analysis.md": "Result analysis (best iteration)",
            "decision.md": "Research decision — PROCEED/PIVOT/REFINE",
            "defect_report.md": "Baseline defect reproduction report (stage 8)",
            "synthesis.md": "Literature synthesis (stage 7)",
            "experiment_code/": "Experiment source code",
            "charts/": "Result visualizations",
            "reproduce/": "Baseline reproduction script (stage 8)",
        },
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    logger.info(
        "Deliverables packaged: %s (%d items)",
        dest,
        len(packaged),
    )
    return dest

def _version_rollback_stages(
    run_dir: Path,
    rollback_target: Stage,
    attempt: int,
    *,
    incremental: bool = False,
) -> None:
    """Snapshot stage directories that will be re-executed by a PIVOT/REFINE
    or by an explicit incremental re-entry.

    Default behavior renames ``stage-NN/`` to ``stage-NN_v{attempt}/`` so the
    next run starts from a clean slate.

    When ``incremental=True``, directories whose number is >= EXPERIMENT_RUN (12)
    are *copied* via ``shutil.copytree`` instead of renamed, so the live
    stage-13 workspace persists across re-entries. Stages before EXPERIMENT_RUN
    in the rollback range are still renamed.
    """
    import shutil

    rollback_num = int(rollback_target)
    decision_num = int(Stage.RESEARCH_DECISION)
    exp_run_num = int(Stage.EXPERIMENT_RUN)

    for stage_num in range(rollback_num, decision_num + 1):
        stage_dir = run_dir / f"stage-{stage_num:02d}"
        if not stage_dir.exists():
            continue
        version_dir = run_dir / f"stage-{stage_num:02d}_v{attempt}"
        if version_dir.exists():
            shutil.rmtree(version_dir)
        if incremental and stage_num >= exp_run_num:
            shutil.copytree(stage_dir, version_dir, symlinks=False)
            logger.debug(
                "Snapshotted (copytree) %s → %s (incremental)",
                stage_dir.name,
                version_dir.name,
            )
        else:
            stage_dir.rename(version_dir)
            logger.debug(
                "Versioned (rename) %s → %s", stage_dir.name, version_dir.name
            )

def _consecutive_empty_metrics(run_dir: Path, pivot_count: int) -> bool:
    """R6-4: Check if the current and previous REFINE cycles both produced empty metrics."""
    # Check the most recent experiment_summary.json (stage-15) and its versioned predecessor.
    # BUG-215: When stage-15/ doesn't exist (renamed to stage-15_v{N} without
    # promotion), fall back to the latest versioned directory as "current".
    current = run_dir / "stage-15" / "experiment_summary.json"
    if not current.exists():
        # Try the latest versioned directory
        for _v in range(pivot_count + 1, 0, -1):
            alt = run_dir / f"stage-15_v{_v}" / "experiment_summary.json"
            if alt.exists():
                current = alt
                break
    prev = run_dir / f"stage-15_v{pivot_count}" / "experiment_summary.json"
    for path in (current, prev):
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Check all possible metric locations
            has_metrics = False
            ms = data.get("metrics_summary", {})
            if isinstance(ms, dict) and ms:
                has_metrics = True
            br = data.get("best_run", {})
            if isinstance(br, dict) and br.get("metrics"):
                has_metrics = True
            if has_metrics:
                return False  # At least one cycle had real metrics
        except (json.JSONDecodeError, OSError, AttributeError):
            return False
    return True  # Both cycles had empty metrics

def _promote_best_stage15(run_dir: Path, config: RCConfig) -> None:
    """BUG-205: After forced PROCEED, promote the best stage-15 experiment.

    Scans all ``stage-15*`` directories, scores them by primary metric,
    and copies the best experiment_summary.json into ``stage-15/`` if the
    current ``stage-15/`` is not already the best.
    """
    import shutil

    metric_key = config.experiment.metric_key or "primary_metric"
    metric_dir = config.experiment.metric_direction or "maximize"

    candidates: list[tuple[float, Path]] = []
    for d in sorted(run_dir.glob("stage-15*")):
        summary_path = d / "experiment_summary.json"
        if not summary_path.exists():
            continue
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        ms = data.get("metrics_summary", {})
        pm_val: float | None = None
        # BUG-DA8-03: Exact match first, then substring fallback
        # (avoids "accuracy" matching "balanced_accuracy")
        if metric_key in ms:
            _v = ms[metric_key]
            try:
                pm_val = float(_v["mean"] if isinstance(_v, dict) else _v)
            except (TypeError, ValueError, KeyError):
                pass
        if pm_val is None:
            for k, v in ms.items():
                if metric_key in k:
                    try:
                        pm_val = float(v["mean"] if isinstance(v, dict) else v)
                    except (TypeError, ValueError, KeyError):
                        pass
                    break
        if pm_val is not None:
            if math.isnan(pm_val):
                continue
            candidates.append((pm_val, d))

    if not candidates:
        return  # nothing to promote

    current_dir = run_dir / "stage-15"

    # Sort: best first
    candidates.sort(key=lambda x: x[0], reverse=(metric_dir == "maximize"))

    # BUG-226: Detect degenerate near-zero metrics (broken normalization or
    # collapsed training).  When minimising, a value >1000x smaller than the
    # second-best almost certainly comes from a degenerate iteration.
    if metric_dir == "minimize" and len(candidates) > 1:
        _bv, _bd = candidates[0]
        _sv = candidates[1][0]
        if 0 < _bv < _sv * 1e-3:
            logger.warning(
                "BUG-226: Degenerate best value %.6g is >1000× smaller than "
                "second-best %.6g — skipping degenerate iteration %s",
                _bv, _sv, _bd.name,
            )
            candidates.pop(0)

    best_val, best_dir = candidates[0]

    # BUG-223: Always write canonical best summary at run root BEFORE any
    # early return, so downstream consumers (Stage 17, Stage 20, Stage 22,
    # VerifiedRegistry) always find experiment_summary_best.json.
    _best_src = best_dir / "experiment_summary.json"
    if _best_src.exists():
        shutil.copy2(_best_src, run_dir / "experiment_summary_best.json")
        logger.info(
            "BUG-223: Wrote experiment_summary_best.json from %s (%.4f)",
            best_dir.name, best_val,
        )
        # BUG-225: Also copy analysis.md from the best iteration so Stage 17
        # doesn't read stale analysis from a degenerate non-versioned stage-15.
        _best_analysis = best_dir / "analysis.md"
        if _best_analysis.exists():
            shutil.copy2(_best_analysis, run_dir / "analysis_best.md")

    if best_dir == current_dir:
        logger.info("BUG-205: stage-15/ already has the best result (%.4f)", best_val)
        return

    # Promote: copy best summary into stage-15/
    current_summary = current_dir / "experiment_summary.json"
    best_summary = best_dir / "experiment_summary.json"
    # BUG-213: Also promote when stage-15/ is missing or empty
    if best_summary.exists():
        current_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(
            "BUG-205: Promoting %s (%.4f) over stage-15/",
            best_dir.name, best_val,
        )
        shutil.copy2(best_summary, current_summary)
        # Also copy charts, analysis, and figure plans if they exist
        for fname in [
            "analysis.md",
            "results_table.tex",
            "figure_plan.json",           # BUG-213: must travel with metrics
            "figure_plan_final.json",     # BUG-213: ditto
        ]:
            src = best_dir / fname
            if src.exists():
                shutil.copy2(src, current_dir / fname)
        # Copy charts directory
        best_charts = best_dir / "charts"
        current_charts = current_dir / "charts"
        if best_charts.is_dir():
            if current_charts.is_dir():
                shutil.rmtree(current_charts)
            shutil.copytree(best_charts, current_charts)

def _check_experiment_quality(
    run_dir: Path, pivot_count: int
) -> tuple[bool, str]:
    """Quality gate before forced PROCEED.

    Returns (ok, message). ok=False means experiment results have critical
    quality issues and the forced-PROCEED paper will likely be poor.
    """
    # BUG-DA8-18: Check experiment_summary_best.json first (repair-promoted)
    summary_path = run_dir / "experiment_summary_best.json"
    if not summary_path.exists():
        summary_path = run_dir / "stage-15" / "experiment_summary.json"
    if not summary_path.exists():
        for v in range(pivot_count, 0, -1):
            alt = run_dir / f"stage-15_v{v}" / "experiment_summary.json"
            if alt.exists():
                summary_path = alt
                break

    if not summary_path.exists():
        return False, "No experiment_summary.json found — no metrics produced"

    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, "experiment_summary.json is malformed"

    # Check 1: Are all metrics zero?
    ms = data.get("metrics_summary", {})
    if isinstance(ms, dict):
        values: list[float] = []
        for k, v in ms.items():
            if isinstance(v, (int, float)):
                values.append(float(v))
            # BUG-212: metrics_summary values are often dicts {min,max,mean,count}
            elif isinstance(v, dict) and "mean" in v:
                _mv = v["mean"]
                if isinstance(_mv, (int, float)):
                    values.append(float(_mv))
        if values and all(v == 0.0 for v in values):
            return False, "All experiment metrics are zero — experiments likely failed"

    # Check 2: Zero variance across conditions (R13-1)
    # Look for ablation_warnings or condition comparison data
    ablation_warnings = data.get("ablation_warnings", [])
    # BUG-212: Key is "condition_summaries", not "conditions"
    conditions = data.get(
        "condition_summaries", data.get("condition_metrics", {})
    )
    if isinstance(conditions, dict) and len(conditions) >= 2:
        primary_values: list[float] = []
        for cond_name, cond_data in conditions.items():
            if isinstance(cond_data, dict):
                # BUG-212: Primary metric lives inside cond_data["metrics"]
                _metrics = cond_data.get("metrics", cond_data)
                pm = _metrics.get(
                    "primary_metric",
                    _metrics.get("primary_metric_mean"),
                )
                if isinstance(pm, (int, float)):
                    primary_values.append(float(pm))
        if len(primary_values) >= 2 and len(set(primary_values)) == 1:
            return False, (
                f"All {len(primary_values)} conditions have identical primary_metric "
                f"({primary_values[0]}) — condition implementations are likely broken"
            )

    # Check 3: Too many ablation warnings
    if isinstance(ablation_warnings, list) and len(ablation_warnings) >= 3:
        return False, (
            f"{len(ablation_warnings)} ablation warnings — most conditions "
            f"produce identical results"
        )

    # Check 4: Analysis quality score (if available)
    quality = data.get("analysis_quality", data.get("quality_score"))
    if isinstance(quality, (int, float)) and quality < 3.0:
        return False, f"Analysis quality score {quality}/10 — below minimum threshold"

    return True, "Quality checks passed"

def _read_pivot_count(run_dir: Path) -> int:
    """Read how many PIVOT/REFINE decisions have been made so far."""
    history_path = run_dir / "decision_history.json"
    if not history_path.exists():
        return 0
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
    except (json.JSONDecodeError, OSError):
        pass
    return 0

def _record_decision_history(
    run_dir: Path, decision: str, rollback_target: Stage, attempt: int
) -> None:
    """Append a decision event to the history log."""
    history_path = run_dir / "decision_history.json"
    history: list[dict[str, object]] = []
    if history_path.exists():
        try:
            data = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                history = data
        except (json.JSONDecodeError, OSError):
            pass
    history.append({
        "decision": decision,
        "rollback_target": rollback_target.name,
        "rollback_stage_num": int(rollback_target),
        "attempt": attempt,
        "timestamp": _utcnow_iso(),
    })
    history_path.write_text(
        json.dumps(history, indent=2), encoding="utf-8"
    )

def _metaclaw_post_pipeline(
    config: RCConfig,
    results: list[StageResult],
    lessons: list[object],
    run_id: str,
    run_dir: Path,
) -> None:
    """MetaClaw bridge: post-pipeline hook.

    1. Convert high-severity lessons into MetaClaw skills.
    2. Record skill effectiveness feedback.
    3. Signal session end to MetaClaw proxy.
    """
    bridge = getattr(config, "metaclaw_bridge", None)
    if not bridge or not getattr(bridge, "enabled", False):
        return

    from researchclaw.llm.client import LLMClient

    # 1. Lesson-to-skill conversion
    l2s = getattr(bridge, "lesson_to_skill", None)
    if l2s and getattr(l2s, "enabled", False) and lessons:
        try:
            from researchclaw.metaclaw_bridge.lesson_to_skill import (
                convert_lessons_to_skills,
            )

            min_sev = getattr(l2s, "min_severity", "warning")
            llm = LLMClient.from_rc_config(config)
            new_skills = convert_lessons_to_skills(
                lessons,
                llm,
                getattr(bridge, "skills_dir", "~/.metaclaw/skills"),
                min_severity=min_sev,
                max_skills=getattr(l2s, "max_skills_per_run", 3),
            )
            if new_skills:
                logger.info(
                    "MetaClaw: generated %d new skills from lessons: %s",
                    len(new_skills),
                    new_skills,
                )
        except Exception:  # noqa: BLE001
            logger.warning("MetaClaw lesson-to-skill conversion failed", exc_info=True)

    # 2. Skill effectiveness feedback
    try:
        from researchclaw.metaclaw_bridge.skill_feedback import (
            SkillFeedbackStore,
            record_stage_skills,
        )
        from researchclaw.metaclaw_bridge.stage_skill_map import get_stage_config

        feedback_store = SkillFeedbackStore(run_dir / "evolution" / "skill_effectiveness.jsonl")
        for result in results:
            stage_num = int(getattr(result, "stage", 0))
            stage_name = {
                1: "topic_init", 2: "problem_decompose", 3: "search_strategy",
                4: "literature_collect", 5: "literature_screen", 6: "knowledge_extract",
                7: "synthesis", 8: "baseline_reproduce", 9: "hypothesis_gen",
                10: "experiment_design", 11: "code_generation", 12: "resource_planning",
                13: "experiment_run", 14: "iterative_refine", 15: "result_analysis",
                16: "research_decision",
            }.get(stage_num, "")
            if not stage_name:
                continue

            stage_config = get_stage_config(stage_name)
            active_skills = stage_config.get("skills", [])
            status = str(getattr(result, "status", ""))
            success = "done" in status.lower()

            if active_skills:
                record_stage_skills(
                    feedback_store,
                    stage_name,
                    run_id,
                    success,
                    active_skills,
                )
    except Exception:  # noqa: BLE001
        logger.warning("MetaClaw skill feedback recording failed")

    # 3. Signal session end (fire-and-forget)
    try:
        from researchclaw.metaclaw_bridge.session import MetaClawSession
        import json as _json
        import urllib.request as _urllib_req

        session = MetaClawSession(run_id)
        end_headers = session.end()
        # Send a minimal request to signal session end
        proxy_url = getattr(bridge, "proxy_url", "http://localhost:30000")
        url = f"{proxy_url.rstrip('/')}/v1/chat/completions"
        body = _json.dumps({
            "model": "session-end",
            "messages": [{"role": "user", "content": "session complete"}],
            "max_tokens": 1,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        headers.update(end_headers)
        req = _urllib_req.Request(url, data=body, headers=headers)
        try:
            _urllib_req.urlopen(req, timeout=5)
        except Exception:  # noqa: BLE001
            pass  # Best-effort signal
    except Exception:  # noqa: BLE001
        pass
