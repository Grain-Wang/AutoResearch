from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
QUEUE_CONFIG = REPOSITORY_ROOT / "paper1/configs/covol/remote_queue.example.yaml"
STEP003_MODULES = {
    "step003-build-training-pilot": (
        "paper1.experiments.covol.build_training_pilot_manifest"
    ),
    "step003-coverage": "paper1.experiments.covol.audit_annotation_coverage",
    "step003-conditional-detectability": ("paper1.experiments.covol.power_analysis"),
}


def test_step003_queue_uses_importable_module_entrypoints() -> None:
    payload = yaml.safe_load(QUEUE_CONFIG.read_text(encoding="utf-8"))
    tasks = {task["id"]: task for task in payload["tasks"]}

    for task_id, module in STEP003_MODULES.items():
        assert tasks[task_id]["command"][:3] == ["python", "-m", module]


def test_step003_queue_pytest_basetemp_uses_scheduler_created_root() -> None:
    payload = yaml.safe_load(QUEUE_CONFIG.read_text(encoding="utf-8"))
    tasks = {task["id"]: task for task in payload["tasks"]}
    command = tasks["qa-pytest"]["command"]
    basetemp = Path(command[command.index("--basetemp") + 1])
    run_root = Path(payload["run_root"])

    assert not basetemp.is_absolute()
    assert basetemp.parts[0] == ".local-deps"
    assert ".local-deps" in run_root.parts


def test_step003_module_entrypoints_show_help_from_repository_root() -> None:
    for module in STEP003_MODULES.values():
        completed = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 0, completed.stderr
        assert "usage:" in completed.stdout
