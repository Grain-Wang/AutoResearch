"""Tests for artifact gates and the two executable stages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from researchclaw.config import RCConfig
from researchclaw.literature.models import Paper
from researchclaw.pipeline.executor import execute_stage
from researchclaw.pipeline.stages import Stage, StageStatus
from researchclaw.policy import discover_policy


def _workspace(tmp_path: Path) -> tuple[Path, object]:
    root = tmp_path / "repo"
    run_dir = root / "paper1" / "run"
    run_dir.mkdir(parents=True)
    (root / "AGENTS.md").write_text("authoritative\n", encoding="utf-8")
    return run_dir, discover_policy(run_dir)


def _config(tmp_path: Path) -> RCConfig:
    return RCConfig.from_dict(
        {
            "research": {"topic": "algorithm gap"},
            "experiment": {
                "sandbox": {"python_path": sys.executable},
            },
        },
        project_root=tmp_path,
    )


def _write_pass_gate(run_dir: Path, stage: Stage) -> None:
    stage_dir = run_dir / f"stage-{int(stage):02d}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    evidence = stage_dir / "evidence.txt"
    evidence.write_text("measured", encoding="utf-8")
    (stage_dir / "gate.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "reason": "evidence supports proceeding",
                "evidence": [str(evidence.relative_to(run_dir))],
            }
        ),
        encoding="utf-8",
    )


def test_gate_requires_existing_contained_evidence(tmp_path: Path) -> None:
    run_dir, policy = _workspace(tmp_path)
    stage4 = run_dir / "stage-04"
    stage4.mkdir()
    (stage4 / "candidates.jsonl").write_text("{}\n", encoding="utf-8")
    stage5 = run_dir / "stage-05"
    stage5.mkdir()
    (stage5 / "shortlist.jsonl").write_text("{}\n", encoding="utf-8")
    (stage5 / "gate.json").write_text(
        '{"status":"PASS","reason":"probe","evidence":["../outside"]}',
        encoding="utf-8",
    )

    result = execute_stage(
        Stage.LITERATURE_SCREEN,
        run_dir=run_dir,
        config=_config(tmp_path),
        policy=policy,
    )

    assert result.status is StageStatus.FAILED
    assert "missing or unsafe" in (result.error or "")


def test_literature_stage_records_real_search_objects(tmp_path: Path) -> None:
    run_dir, policy = _workspace(tmp_path)
    stage3 = run_dir / "stage-03"
    stage3.mkdir()
    (stage3 / "queries.json").write_text(
        '{"queries":["direct neighbor"]}', encoding="utf-8"
    )
    paper = Paper(paper_id="p1", title="A Real Paper")

    with patch(
        "researchclaw.pipeline.executor.search_papers_multi_query",
        return_value=[paper],
    ):
        result = execute_stage(
            Stage.LITERATURE_COLLECT,
            run_dir=run_dir,
            config=_config(tmp_path),
            policy=policy,
        )

    candidate = json.loads(
        (run_dir / "stage-04" / "candidates.jsonl").read_text(encoding="utf-8")
    )
    assert result.status is StageStatus.DONE
    assert candidate["title"] == "A Real Paper"


def test_experiment_stage_executes_schedule_and_redacts_environment(
    tmp_path: Path,
) -> None:
    run_dir, policy = _workspace(tmp_path)
    for gate_stage in (
        Stage.LITERATURE_SCREEN,
        Stage.BASELINE_REPRODUCE,
        Stage.EXPERIMENT_DESIGN,
    ):
        _write_pass_gate(run_dir, gate_stage)
    project = run_dir / "stage-11" / "experiment"
    project.mkdir(parents=True)
    (project / "main.py").write_text(
        "import os\nprint('score: 0.8')\nassert os.environ['PRIVATE_VALUE']\n",
        encoding="utf-8",
    )
    stage12 = run_dir / "stage-12"
    stage12.mkdir()
    (stage12 / "schedule.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "seed-0",
                        "entry_point": "main.py",
                        "env": {"PRIVATE_VALUE": "do-not-record"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = execute_stage(
        Stage.EXPERIMENT_RUN,
        run_dir=run_dir,
        config=_config(tmp_path),
        policy=policy,
    )

    summary_path = run_dir / "stage-13" / "run_summary.json"
    summary_text = summary_path.read_text(encoding="utf-8")
    summary = json.loads(summary_text)
    assert result.status is StageStatus.DONE
    assert summary["tasks"][0]["metrics"] == {"score": 0.8}
    assert summary["tasks"][0]["env_keys"] == ["PRIVATE_VALUE"]
    assert "do-not-record" not in summary_text


def test_invalid_task_id_cannot_escape_runs_directory(tmp_path: Path) -> None:
    run_dir, policy = _workspace(tmp_path)
    for gate_stage in (
        Stage.LITERATURE_SCREEN,
        Stage.BASELINE_REPRODUCE,
        Stage.EXPERIMENT_DESIGN,
    ):
        _write_pass_gate(run_dir, gate_stage)
    project = run_dir / "stage-11" / "experiment"
    project.mkdir(parents=True)
    (project / "main.py").write_text("print('score: 1')", encoding="utf-8")
    stage12 = run_dir / "stage-12"
    stage12.mkdir()
    (stage12 / "schedule.json").write_text(
        '{"tasks":[{"id":"../escape"}]}', encoding="utf-8"
    )

    result = execute_stage(
        Stage.EXPERIMENT_RUN,
        run_dir=run_dir,
        config=_config(tmp_path),
        policy=policy,
    )

    assert result.status is StageStatus.FAILED
    assert "unsafe" in (result.error or "")
