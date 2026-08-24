"""Artifact validation plus the two real executable research stages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from researchclaw.config import RCConfig
from researchclaw.experiment.factory import create_sandbox
from researchclaw.literature.search import search_papers_multi_query
from researchclaw.pipeline.contracts import CONTRACTS
from researchclaw.pipeline.stages import GATE_STAGES, Stage, StageStatus
from researchclaw.policy import WorkspacePolicy, record_policy

_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True)
class StageResult:
    """Result of validating or executing one stage."""

    stage: Stage
    status: StageStatus
    artifacts: tuple[str, ...] = ()
    error: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stage_dir(run_dir: Path, stage: Stage) -> Path:
    return run_dir / f"stage-{int(stage):02d}"


def _artifact_present(path: Path) -> bool:
    if path.is_file():
        return True
    return path.is_dir() and any(path.iterdir())


def find_prior_artifact(run_dir: Path, stage: Stage, name: str) -> Path | None:
    """Find an input artifact in the nearest completed earlier stage."""

    for previous in reversed(tuple(item for item in Stage if item < stage)):
        candidate = _stage_dir(run_dir, previous) / name.rstrip("/")
        if _artifact_present(candidate):
            return candidate
    return None


def _write_health(
    stage_dir: Path,
    result: StageResult,
    policy: WorkspacePolicy,
) -> None:
    payload = {
        "stage": result.stage.name,
        "status": result.status.value,
        "artifacts": list(result.artifacts),
        "error": result.error,
        "agents_sha256": policy.sha256,
        "updated_at": _utc_now(),
    }
    (stage_dir / "stage_health.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )


def _validate_previous_gates(run_dir: Path, stage: Stage) -> str | None:
    for gate_stage in sorted(GATE_STAGES, key=int):
        if gate_stage >= stage:
            continue
        gate_path = _stage_dir(run_dir, gate_stage) / "gate.json"
        if not gate_path.is_file():
            return f"prior gate {gate_stage.name} has no gate.json"
        try:
            payload = json.loads(gate_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            return f"prior gate {gate_stage.name} is invalid: {error}"
        if not isinstance(payload, dict) or payload.get("status") != "PASS":
            return f"prior gate {gate_stage.name} did not PASS"
    return None


def _validate_inputs(run_dir: Path, stage: Stage) -> str | None:
    gate_error = _validate_previous_gates(run_dir, stage)
    if gate_error:
        return gate_error
    missing = [
        name
        for name in CONTRACTS[stage].input_files
        if find_prior_artifact(run_dir, stage, name) is None
    ]
    if missing:
        return f"missing prior artifacts: {', '.join(missing)}"
    return None


def _validate_gate(run_dir: Path, stage_dir: Path) -> tuple[StageStatus, str | None]:
    gate_path = stage_dir / "gate.json"
    try:
        payload = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return StageStatus.FAILED, f"invalid gate.json: {error}"
    if not isinstance(payload, dict):
        return StageStatus.FAILED, "gate.json must be an object"
    status = payload.get("status")
    if status not in {"PASS", "STOP"}:
        return StageStatus.FAILED, "gate.status must be PASS or STOP"
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return StageStatus.FAILED, "gate.reason must be a nonempty string"
    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return StageStatus.FAILED, "gate.evidence must be a nonempty list"
    root = run_dir.resolve()
    for raw_path in evidence:
        if not isinstance(raw_path, str) or not raw_path:
            return StageStatus.FAILED, "gate evidence paths must be strings"
        candidate = (run_dir / raw_path).resolve()
        if not candidate.is_relative_to(root) or not _artifact_present(candidate):
            return StageStatus.FAILED, f"gate evidence is missing or unsafe: {raw_path}"
    if status == "STOP":
        return StageStatus.REJECTED, reason.strip()
    return StageStatus.DONE, None


def _validate_outputs(run_dir: Path, stage: Stage) -> StageResult:
    stage_dir = _stage_dir(run_dir, stage)
    missing = [
        name
        for name in CONTRACTS[stage].output_files
        if not _artifact_present(stage_dir / name.rstrip("/"))
    ]
    if missing:
        return StageResult(
            stage,
            StageStatus.FAILED,
            error=f"missing stage outputs: {', '.join(missing)}",
        )
    artifacts = tuple(
        str((stage_dir / name.rstrip("/")).relative_to(run_dir))
        for name in CONTRACTS[stage].output_files
    )
    if stage in GATE_STAGES:
        status, error = _validate_gate(run_dir, stage_dir)
        return StageResult(stage, status, artifacts=artifacts, error=error)
    if stage is Stage.RESEARCH_DECISION:
        try:
            decision = json.loads(
                (stage_dir / "decision.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as error:
            return StageResult(stage, StageStatus.FAILED, error=str(error))
        allowed = {"STOP", "REFINE", "PIVOT", "PAPER_CANDIDATE"}
        if not isinstance(decision, dict) or decision.get("decision") not in allowed:
            return StageResult(
                stage,
                StageStatus.FAILED,
                error=f"decision.json decision must be one of {sorted(allowed)}",
            )
    return StageResult(stage, StageStatus.DONE, artifacts=artifacts)


def _load_queries(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_queries = payload.get("queries") if isinstance(payload, dict) else payload
    if not isinstance(raw_queries, list):
        raise ValueError("queries.json must be a list or an object with queries")
    queries = [
        item.strip() for item in raw_queries if isinstance(item, str) and item.strip()
    ]
    if not queries:
        raise ValueError("queries.json contains no nonempty queries")
    return queries


def _collect_literature(run_dir: Path, config: RCConfig) -> None:
    stage = Stage.LITERATURE_COLLECT
    query_path = find_prior_artifact(run_dir, stage, "queries.json")
    if query_path is None:
        raise FileNotFoundError("queries.json")
    queries = _load_queries(query_path)
    settings = config.literature_search
    papers = search_papers_multi_query(
        queries,
        limit_per_query=settings.max_results_per_query,
        sources=settings.sources,
        year_min=settings.year_min,
        s2_api_key=config.semantic_scholar_api_key(),
        openalex_email=settings.openalex_email,
        openalex_api_key=config.openalex_api_key(),
    )
    output = _stage_dir(run_dir, stage) / "candidates.jsonl"
    output.write_text(
        "".join(json.dumps(paper.to_dict(), sort_keys=True) + "\n" for paper in papers),
        encoding="utf-8",
    )


def _task_mapping(value: object, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"schedule task {index} must be an object")
    return {str(key): item for key, item in value.items()}


def _run_experiments(run_dir: Path, config: RCConfig) -> None:
    stage = Stage.EXPERIMENT_RUN
    schedule_path = find_prior_artifact(run_dir, stage, "schedule.json")
    project_root = find_prior_artifact(run_dir, stage, "experiment/")
    if schedule_path is None or project_root is None:
        raise FileNotFoundError("schedule.json or experiment/")
    payload = json.loads(schedule_path.read_text(encoding="utf-8"))
    raw_tasks = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError("schedule.json tasks must be a nonempty list")
    stage_dir = _stage_dir(run_dir, stage)
    runs_dir = stage_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    sandbox = create_sandbox(config.experiment, stage_dir / "sandbox")
    summary: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    project_base = project_root.resolve()
    for index, raw_task in enumerate(raw_tasks):
        task = _task_mapping(raw_task, index)
        task_id = str(task.get("id", "")).strip()
        if not _TASK_ID.fullmatch(task_id) or task_id in seen_ids:
            raise ValueError(f"schedule task {index} has an unsafe or duplicate id")
        seen_ids.add(task_id)
        subdir = str(task.get("project", "."))
        project = (project_base / subdir).resolve()
        if not project.is_relative_to(project_base) or not project.is_dir():
            raise ValueError(
                f"task {task_id} project is missing or escapes experiment/"
            )
        entry_point = str(task.get("entry_point", "main.py"))
        raw_args = task.get("args", [])
        raw_env = task.get("env", {})
        if not isinstance(raw_args, list) or not all(
            isinstance(arg, str) for arg in raw_args
        ):
            raise TypeError(f"task {task_id} args must be a list of strings")
        if not isinstance(raw_env, dict):
            raise TypeError(f"task {task_id} env must be an object")
        env = {str(key): str(value) for key, value in raw_env.items()}
        timeout = int(task.get("timeout_seconds", config.experiment.time_budget_sec))
        if timeout <= 0:
            raise ValueError(f"task {task_id} timeout_seconds must be positive")
        result = sandbox.run_project(
            project,
            entry_point=entry_point,
            timeout_sec=timeout,
            args=list(raw_args),
            env_overrides=env,
        )
        task_dir = runs_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=False)
        (task_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (task_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
        record = {
            "id": task_id,
            "returncode": result.returncode,
            "timed_out": result.timed_out,
            "elapsed_sec": result.elapsed_sec,
            "metrics": result.metrics,
            "entry_point": entry_point,
            "args": raw_args,
            "env_keys": sorted(env),
        }
        (task_dir / "result.json").write_text(
            json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
        )
        summary.append(record)
    (stage_dir / "run_summary.json").write_text(
        json.dumps({"tasks": summary}, indent=2, sort_keys=True), encoding="utf-8"
    )
    failed = [item["id"] for item in summary if item["returncode"] != 0]
    if failed:
        raise RuntimeError(f"experiment tasks failed: {failed}")


def execute_stage(
    stage: Stage,
    *,
    run_dir: Path,
    config: RCConfig,
    policy: WorkspacePolicy,
) -> StageResult:
    """Execute a real stage action when available, then validate its contract."""

    run_dir = run_dir.expanduser().resolve()
    stage_dir = _stage_dir(run_dir, stage)
    stage_dir.mkdir(parents=True, exist_ok=True)
    record_policy(stage_dir, policy)
    input_error = _validate_inputs(run_dir, stage)
    if input_error:
        result = StageResult(stage, StageStatus.FAILED, error=input_error)
        _write_health(stage_dir, result, policy)
        return result
    try:
        if stage is Stage.LITERATURE_COLLECT:
            _collect_literature(run_dir, config)
        elif stage is Stage.EXPERIMENT_RUN:
            _run_experiments(run_dir, config)
        result = _validate_outputs(run_dir, stage)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        result = StageResult(stage, StageStatus.FAILED, error=str(error))
    _write_health(stage_dir, result, policy)
    return result
