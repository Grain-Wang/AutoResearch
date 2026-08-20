"""Experiment toolset CLI: run each pipeline stage as an independent command.

``researchclaw tools`` turns the 16-stage experiment pipeline into a toolbox
where every stage is invoked on demand and writes into a shared run directory.
The orchestrator (e.g. Claude Code under AGENTS.md) inspects ``tools status``,
runs the next step, and reviews gate artifacts before approving them.

Commands
--------
tools list                     Show all 16 stages, contracts and gate markers
tools init --run-dir <dir>     Create a workspace (run_dir + config snapshot)
tools status --run-dir <dir>   Show which stages have produced artifacts
tools <step> [flags]           Execute one stage (thin wrapper over
                               ``pipeline.executor.execute_stage``)
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any, cast

from researchclaw.adapters import AdapterBundle
from researchclaw.pipeline.contracts import CONTRACTS
from researchclaw.pipeline.stages import GATE_STAGES, Stage
from researchclaw.prompts import PromptManager

DEFAULT_RUN_DIR = Path("artifacts/workspace")

# step aliases -> Stage enum member name (canonical snake_case also accepted)
_STEP_ALIASES: dict[str, str] = {
    "topic": "TOPIC_INIT",
    "decompose": "PROBLEM_DECOMPOSE",
    "search": "SEARCH_STRATEGY",
    "collect": "LITERATURE_COLLECT",
    "screen": "LITERATURE_SCREEN",
    "extract": "KNOWLEDGE_EXTRACT",
    "synthesize": "SYNTHESIS",
    "reproduce": "BASELINE_REPRODUCE",
    "baseline": "BASELINE_REPRODUCE",
    "hypothesize": "HYPOTHESIS_GEN",
    "design": "EXPERIMENT_DESIGN",
    "codegen": "CODE_GENERATION",
    "plan": "RESOURCE_PLANNING",
    "experiment": "EXPERIMENT_RUN",
    "refine": "ITERATIVE_REFINE",
    "analyze": "RESULT_ANALYSIS",
    "decide": "RESEARCH_DECISION",
}

# all accepted step spellings (argparse choices)
TOOLS_STEPS: list[str] = sorted(set(_STEP_ALIASES) | {s.name for s in Stage})


def resolve_step(step: str) -> Stage | None:
    """Map a CLI step name / alias to a ``Stage`` (None if unknown)."""
    key = _STEP_ALIASES.get(step, step.upper())
    try:
        return Stage[key]
    except KeyError:
        return None


def _canonical_step(stage: Stage) -> str:
    """Return the preferred CLI alias for a stage (e.g. reproduce, analyze)."""
    for alias, value in _STEP_ALIASES.items():
        if value == stage.name:
            return alias
    return stage.name.lower()


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def _default_config(run_dir: Path, topic: str) -> Any:
    """Minimal RCConfig for a tools-only workspace (no config file needed).

    The sandbox prefers the workspace's own Python 3.12 venv (AGENTS.md §14);
    falls back to the package default python_path otherwise.
    """
    import os as _os

    from researchclaw.config import DEFAULT_PYTHON_PATH, RCConfig

    venv_py = run_dir / ".venv" / (
        "Scripts/python.exe" if _os.name == "nt" else "bin/python3"
    )
    python_path = str(venv_py) if venv_py.exists() else DEFAULT_PYTHON_PATH

    data = {
        "project": {"name": "tools-workspace", "mode": "docs-first"},
        "research": {"topic": topic or "Unspecified research topic"},
        "runtime": {"timezone": "UTC"},
        "notifications": {"channel": "local"},
        "knowledge_base": {"backend": "markdown", "root": str(run_dir / "knowledge")},
        "openclaw_bridge": {},
        # Placeholder LLM config: passes validation but yields llm=None at
        # runtime (no api_key set), so executors run in no-LLM fallback mode.
        # Pass --config with a real LLM setup to enable model calls.
        "llm": {
            "provider": "openai-compatible",
            "base_url": "http://localhost:1234/v1",
            "api_key_env": "UNSET_LLM_API_KEY",
            "api_key": "",
        },
        "experiment": {
            "mode": "sandbox",
            "time_budget_sec": 300,
            "sandbox": {"python_path": python_path},
        },
    }
    return RCConfig.from_dict(data, project_root=run_dir, check_paths=False)


def _load_config(args: Any, run_dir: Path) -> Any:
    """Load RCConfig: --config path, else auto-detect, else defaults."""
    from researchclaw.config import RCConfig, resolve_config_path

    path = resolve_config_path(getattr(args, "config", None))
    if path is not None and path.exists():
        config = RCConfig.load(path, check_paths=False)
    else:
        config = _default_config(run_dir, getattr(args, "topic", "") or "")
    return config


# ---------------------------------------------------------------------------
# tools list
# ---------------------------------------------------------------------------


def tools_list() -> int:
    """Print every stage with its contract, gate marker, and AGENTS.md directive."""
    pm = PromptManager(agents_search_start=Path.cwd())
    gate_nums = {int(s) for s in GATE_STAGES}
    print(f"{'#':>3}  {'stage':<24} {'gate':<5} inputs/outputs")
    print("-" * 92)
    for stage in Stage:
        contract = CONTRACTS[stage]
        gate = "GATE" if int(stage) in gate_nums else ""
        ins = ", ".join(contract.input_files) or "—"
        outs = ", ".join(contract.output_files) or "—"
        print(f"{int(stage):>3}  {stage.name:<24} {gate:<5} {ins} → {outs}")
    print("-" * 92)
    print(f"\nSteps ({len(list(Stage))}):")
    for stage in Stage:
        aliases = [a for a, v in _STEP_ALIASES.items() if v == stage.name]
        print(f"  {aliases[0] if aliases else stage.name:<14} → {stage.name}")
    print(
        "\nRun any step into a shared workspace:\n"
        "  researchclaw tools init --run-dir <dir> --topic \"...\"\n"
        "  researchclaw tools reproduce --run-dir <dir>\n"
        "  researchclaw tools status --run-dir <dir>\n"
        "\nBundled AGENTS.md stage directives are auto-injected into every LLM "
        f"prompt ({len(pm.directives())} stages covered).\n"
        f"Workspace rules: {pm.agents_path or 'not found (bundled directives only)'}"
    )
    return 0


# ---------------------------------------------------------------------------
# tools status
# ---------------------------------------------------------------------------


def _stage_status(run_dir: Path, stage: Stage) -> str:
    """Best-effort status for one stage from its decision/health artifacts."""
    stage_dir = run_dir / f"stage-{int(stage):02d}"
    if not stage_dir.is_dir():
        return "not-run"
    health = stage_dir / "stage_health.json"
    if health.exists():
        try:
            import json as _json

            return str(_json.loads(health.read_text(encoding="utf-8")).get("status", "?"))
        except Exception:  # noqa: BLE001
            pass
    decision = stage_dir / "decision.json"
    if decision.exists():
        try:
            import json as _json

            return str(_json.loads(decision.read_text(encoding="utf-8")).get("status", "?"))
        except Exception:  # noqa: BLE001
            pass
    contract = CONTRACTS[stage]
    present = 0
    for out in contract.output_files:
        if out.endswith("/"):
            p = stage_dir / out.rstrip("/")
            if p.is_dir() and any(p.iterdir()):
                present += 1
        elif (stage_dir / out).exists():
            present += 1
    return f"partial ({present}/{len(contract.output_files)} outputs)" if present else "empty"


def tools_status(run_dir: Path) -> int:
    """Show which stages have produced artifacts and the next runnable step."""
    if not run_dir.is_dir():
        print(f"Error: run directory not found: {run_dir}", file=sys.stderr)
        print("Hint: run 'researchclaw tools init --run-dir <dir>' first.", file=sys.stderr)
        return 1

    gate_nums = {int(s) for s in GATE_STAGES}
    print(f"Workspace: {run_dir}")
    print(f"{'#':>3}  {'stage':<24} {'gate':<5} status")
    print("-" * 60)
    done = 0
    next_step: Stage | None = None
    for stage in Stage:
        status = _stage_status(run_dir, stage)
        gate = "GATE" if int(stage) in gate_nums else ""
        print(f"{int(stage):>3}  {stage.name:<24} {gate:<5} {status}")
        if status in ("done",):
            done += 1
        elif next_step is None and status in ("not-run", "empty"):
            next_step = stage
    print("-" * 60)
    print(f"Completed: {done}/{len(list(Stage))}")
    if next_step is not None:
        contract = CONTRACTS[next_step]
        step_name = _canonical_step(next_step)
        print(f"\nNext step: researchclaw tools {step_name} --run-dir {run_dir}")
        if contract.input_files:
            print(f"  requires: {', '.join(contract.input_files)}")
    else:
        print("\nAll stages have produced artifacts. Run 'researchclaw report --run-dir .' "
              "for the experiment report.")
    return 0


# ---------------------------------------------------------------------------
# tools init
# ---------------------------------------------------------------------------


def tools_init(run_dir: Path, topic: str, config_path: str | None) -> int:
    """Create a workspace: run_dir, config snapshot, KB root, tools marker."""
    run_dir.mkdir(parents=True, exist_ok=True)

    # Config snapshot (best-effort, like cmd_run).
    if config_path and Path(config_path).exists():
        import shutil

        try:
            shutil.copy2(Path(config_path), run_dir / "config.yaml")
        except OSError as exc:
            print(f"Warning: config snapshot failed: {exc}", file=sys.stderr)
    else:
        from researchclaw.config import resolve_config_path

        detected = resolve_config_path(None)
        if detected and detected.exists():
            try:
                import shutil

                shutil.copy2(detected, run_dir / "config.yaml")
            except OSError:
                pass

    from researchclaw.config import RCConfig, resolve_config_path as _rcp

    _path = _rcp(config_path)
    cfg: Any
    if _path and _path.exists():
        cfg = RCConfig.load(_path, check_paths=False)
        if topic:
            cfg = dataclasses.replace(
                cfg, research=dataclasses.replace(cfg.research, topic=topic)
            )
    else:
        cfg = _default_config(run_dir, topic)

    if cfg.knowledge_base.root:
        Path(cfg.knowledge_base.root).mkdir(parents=True, exist_ok=True)

    import json as _json

    marker = {
        "tool": "researchclaw tools",
        "stages": 16,
        "topic": cfg.research.topic,
        "run_dir": str(run_dir),
    }
    pm = PromptManager(agents_search_start=run_dir)
    marker["agents_file"] = str(pm.agents_path) if pm.agents_path else None
    marker["agents_sha256"] = pm.agents_sha256 or None
    (run_dir / "tools.json").write_text(
        _json.dumps(marker, indent=2), encoding="utf-8"
    )

    print(f"Workspace ready: {run_dir}")
    print(f"  Topic: {cfg.research.topic}")
    print(f"  Knowledge base: {cfg.knowledge_base.root or '(none)'}")
    print(f"  AGENTS.md: {pm.agents_path or '(not found; bundled directives only)'}")
    print("\nRun a step, e.g.:")
    print(f"  researchclaw tools screen --run-dir {run_dir}")
    print(f"  researchclaw tools status --run-dir {run_dir}")
    return 0


# ---------------------------------------------------------------------------
# tools <step>
# ---------------------------------------------------------------------------


def tools_run_step(
    args: Any,
    stage: Stage,
    run_dir: Path,
    config: Any,
    adapters: AdapterBundle,
) -> int:
    """Execute one stage via ``execute_stage`` and print the outcome."""
    from researchclaw.pipeline.executor import execute_stage

    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_dir.name
    result = execute_stage(
        stage,
        run_dir=run_dir,
        run_id=run_id,
        config=config,
        adapters=adapters,
        auto_approve_gates=bool(getattr(args, "auto_approve", False)),
    )

    print(f"Stage {int(stage):02d} {stage.name}: {result.status.value}")
    if result.decision:
        print(f"  decision: {result.decision}")
    if result.error:
        print(f"  error: {result.error}")
    if result.artifacts:
        print("  outputs:")
        for art in result.artifacts:
            print(f"    - {art}")
    if result.status.value == "done":
        print("  ✓ OK — inspect artifacts, then run the next step.")
        return 0
    print(
        "  ✗ Not done — review the stage directory and the messages above. "
        "Gates must be approved explicitly (or --auto-approve)."
    )
    return 1


def cmd_tools(args: Any) -> int:
    """Dispatch ``researchclaw tools ...``."""
    action = cast(str, args.tools_action)

    if action == "list":
        return tools_list()

    run_dir = Path(cast(str, getattr(args, "run_dir", None) or DEFAULT_RUN_DIR))

    if action == "init":
        return tools_init(run_dir, cast(str, args.topic or ""), getattr(args, "config", None))

    if action == "status":
        return tools_status(run_dir)

    stage = resolve_step(action)
    if stage is None:
        print(f"Error: unknown step '{action}'.", file=sys.stderr)
        print("Valid steps:", ", ".join(sorted(set(_STEP_ALIASES))), file=sys.stderr)
        return 1

    config = _load_config(args, run_dir)
    if getattr(args, "topic", None):
        config = dataclasses.replace(
            config, research=dataclasses.replace(config.research, topic=args.topic)
        )
    domains = getattr(args, "domains", None)
    if domains:
        config = dataclasses.replace(
            config, research=dataclasses.replace(config.research, domains=tuple(domains))
        )

    # --baseline hint consumed by the reproduce executor.
    if stage is Stage.BASELINE_REPRODUCE:
        baseline = getattr(args, "baseline", None)
        if baseline:
            try:
                (run_dir / "baseline_hint.txt").write_text(
                    str(baseline), encoding="utf-8"
                )
                print(f"  baseline hint: {baseline}")
            except OSError as exc:
                print(f"Warning: could not write baseline hint: {exc}", file=sys.stderr)

    return tools_run_step(args, stage, run_dir, config, AdapterBundle())


__all__ = [
    "TOOLS_STEPS",
    "cmd_tools",
    "resolve_step",
    "tools_init",
    "tools_list",
    "tools_status",
]
