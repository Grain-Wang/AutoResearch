"""CLI for the compact, AGENTS-governed research stage toolbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from researchclaw.config import RCConfig, load_config, resolve_config_path
from researchclaw.pipeline.contracts import CONTRACTS
from researchclaw.pipeline.executor import execute_stage
from researchclaw.pipeline.stages import GATE_STAGES, Stage
from researchclaw.policy import discover_policy, record_policy

DEFAULT_RUN_DIR = Path("artifacts/workspace")
_STEP_ALIASES = {
    "topic": Stage.TOPIC_INIT,
    "decompose": Stage.PROBLEM_DECOMPOSE,
    "search": Stage.SEARCH_STRATEGY,
    "collect": Stage.LITERATURE_COLLECT,
    "screen": Stage.LITERATURE_SCREEN,
    "extract": Stage.KNOWLEDGE_EXTRACT,
    "synthesize": Stage.SYNTHESIS,
    "reproduce": Stage.BASELINE_REPRODUCE,
    "hypothesize": Stage.HYPOTHESIS_GEN,
    "design": Stage.EXPERIMENT_DESIGN,
    "codegen": Stage.CODE_GENERATION,
    "plan": Stage.RESOURCE_PLANNING,
    "experiment": Stage.EXPERIMENT_RUN,
    "refine": Stage.ITERATIVE_REFINE,
    "analyze": Stage.RESULT_ANALYSIS,
    "decide": Stage.RESEARCH_DECISION,
}
TOOLS_STEPS = tuple(_STEP_ALIASES)


def resolve_step(value: str) -> Stage | None:
    """Resolve an alias or canonical stage name."""

    if value in _STEP_ALIASES:
        return _STEP_ALIASES[value]
    try:
        return Stage[value.upper()]
    except KeyError:
        return None


def _alias(stage: Stage) -> str:
    return next(name for name, candidate in _STEP_ALIASES.items() if candidate is stage)


def tools_list() -> int:
    """Print the sixteen retained stages and artifact contracts."""

    print(f"{'#':>3}  {'stage':<24} {'mode':<8} outputs")
    print("-" * 88)
    for stage in Stage:
        contract = CONTRACTS[stage]
        mode = "execute" if contract.executes else "verify"
        if stage in GATE_STAGES:
            mode = "gate"
        outputs = ", ".join(contract.output_files)
        print(f"{int(stage):>3}  {_alias(stage):<24} {mode:<8} {outputs}")
    policy = discover_policy(Path.cwd())
    print(f"\nAuthoritative policy: {policy.path} ({policy.sha256[:12]})")
    return 0


def _marker_path(run_dir: Path) -> Path:
    return run_dir / "tools.json"


def _read_marker(run_dir: Path) -> dict[str, object]:
    path = _marker_path(run_dir)
    if not path.is_file():
        raise FileNotFoundError(f"workspace marker not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("tools.json must be an object")
    return payload


def _validated_config_path(
    config_path: str | None,
    policy_root: Path,
) -> Path | None:
    resolved = resolve_config_path(config_path)
    if resolved is not None and not resolved.is_relative_to(policy_root.resolve()):
        raise ValueError("configuration must stay inside the AGENTS.md workspace")
    return resolved


def tools_init(
    run_dir: Path,
    *,
    topic: str,
    config_path: str | None,
) -> int:
    """Initialize a research workspace without copying credentials."""

    run_dir = run_dir.expanduser().resolve()
    policy = discover_policy(run_dir.parent)
    resolved_config = _validated_config_path(config_path, policy.path.parent)
    config = load_config(
        str(resolved_config) if resolved_config is not None else None,
        topic=topic,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    record_policy(run_dir, policy)
    config_sha256: str | None = None
    if resolved_config is not None:
        config_sha256 = hashlib.sha256(resolved_config.read_bytes()).hexdigest()
    marker = {
        "tool": "researchclaw",
        "workflow_version": 1,
        "stages": len(tuple(Stage)),
        "topic": config.research.topic,
        "experiment_mode": config.experiment.mode,
        "config_sha256": config_sha256,
        "agents_sha256": policy.sha256,
    }
    _marker_path(run_dir).write_text(
        json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Workspace ready: {run_dir}")
    print(f"Topic: {config.research.topic}")
    print(f"Policy: {policy.path}")
    return 0


def _stage_status(run_dir: Path, stage: Stage) -> str:
    stage_dir = run_dir / f"stage-{int(stage):02d}"
    health = stage_dir / "stage_health.json"
    if health.is_file():
        try:
            payload = json.loads(health.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return str(payload.get("status", "invalid"))
        except (OSError, ValueError):
            return "invalid"
    present = sum(
        (stage_dir / name.rstrip("/")).exists()
        for name in CONTRACTS[stage].output_files
    )
    if present:
        return f"unverified ({present}/{len(CONTRACTS[stage].output_files)})"
    return "not-run"


def tools_status(run_dir: Path) -> int:
    """Show stage state derived from artifacts and health records."""

    run_dir = run_dir.expanduser().resolve()
    marker = _read_marker(run_dir)
    print(f"Workspace: {run_dir}")
    print(f"Topic: {marker.get('topic', '')}")
    print(f"{'#':>3}  {'stage':<24} status")
    print("-" * 56)
    for stage in Stage:
        print(f"{int(stage):>3}  {_alias(stage):<24} {_stage_status(run_dir, stage)}")
    return 0


def _config_for_stage(
    args: argparse.Namespace,
    run_dir: Path,
    policy_root: Path,
) -> RCConfig:
    marker = _read_marker(run_dir)
    topic = str(args.topic or marker.get("topic", ""))
    config_path = _validated_config_path(args.config, policy_root)
    return load_config(
        str(config_path) if config_path is not None else None,
        topic=topic,
    )


def tools_run_step(args: argparse.Namespace, stage: Stage, run_dir: Path) -> int:
    """Execute a real action or verify agent-produced artifacts for one stage."""

    run_dir = run_dir.expanduser().resolve()
    policy = discover_policy(run_dir.parent)
    config = _config_for_stage(args, run_dir, policy.path.parent)
    result = execute_stage(stage, run_dir=run_dir, config=config, policy=policy)
    print(f"Stage {int(stage):02d} {stage.name}: {result.status.value}")
    if result.error:
        print(f"Error: {result.error}", file=sys.stderr)
    for artifact in result.artifacts:
        print(f"- {artifact}")
    return (
        0
        if result.status.value == "done"
        else 2 if result.status.value == "rejected" else 1
    )


def cmd_tools(args: argparse.Namespace) -> int:
    """Dispatch the ``researchclaw tools`` command family."""

    action = str(args.tools_action)
    if action == "list":
        return tools_list()
    run_dir = Path(args.run_dir or DEFAULT_RUN_DIR)
    if action == "init":
        return tools_init(run_dir, topic=str(args.topic or ""), config_path=args.config)
    if action == "status":
        return tools_status(run_dir)
    stage = resolve_step(action)
    if stage is None:
        raise ValueError(f"unknown research stage: {action}")
    return tools_run_step(args, stage, run_dir)
