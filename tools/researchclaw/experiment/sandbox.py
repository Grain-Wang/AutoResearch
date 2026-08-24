"""Real local experiment execution in an isolated staging directory."""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Protocol

from researchclaw.config import SandboxConfig
from researchclaw.hardware import is_metric_name

_FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_PLAIN_METRIC = re.compile(rf"^(\w[\w.]*)\s*:\s*({_FLOAT})\s*$")
_CONDITION_METRIC = re.compile(
    rf"^condition=(\S+)\s+(?:\S+=\S+\s+)*(\w[\w.]*)\s*:\s*({_FLOAT})\s*$"
)
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def validate_entry_point(entry_point: str) -> str | None:
    """Return an error when an entry point is not a safe relative path."""

    if not entry_point or not entry_point.strip():
        return "entry point is empty"
    path = Path(entry_point)
    if (
        path.is_absolute()
        or PurePosixPath(entry_point).is_absolute()
        or PureWindowsPath(entry_point).is_absolute()
        or ".." in path.parts
    ):
        return f"entry point must be a contained relative path: {entry_point}"
    return None


def validate_entry_point_resolved(staging: Path, entry_point: str) -> str | None:
    """Return an error when a staged entry point escapes its project root."""

    root = staging.resolve()
    resolved = (root / entry_point).resolve()
    if not resolved.is_relative_to(root):
        return f"entry point escapes staging directory: {entry_point}"
    return None


def parse_metrics(stdout: str) -> dict[str, float]:
    """Parse finite scalar metrics from standard experiment output."""

    metrics: dict[str, float] = {}
    for line in stdout.splitlines():
        stripped = line.strip()
        condition = _CONDITION_METRIC.fullmatch(stripped)
        if condition:
            condition_name, name, value = condition.groups()
            key = f"{condition_name}/{name}"
        else:
            plain = _PLAIN_METRIC.fullmatch(stripped)
            if plain is None:
                continue
            name, value = plain.groups()
            key = name
        if not is_metric_name(name):
            continue
        parsed = float(value)
        if math.isfinite(parsed):
            metrics[key] = parsed
            metrics[name] = parsed
    return metrics


@dataclass(frozen=True)
class SandboxResult:
    """Captured outcome of one real experiment process."""

    returncode: int
    stdout: str
    stderr: str
    elapsed_sec: float
    metrics: dict[str, float]
    timed_out: bool = False


class SandboxProtocol(Protocol):
    """Shared interface for local and SSH experiment execution."""

    def run(self, code: str, *, timeout_sec: int = 300) -> SandboxResult:
        """Execute one Python source string."""

        ...

    def run_project(
        self,
        project_dir: Path,
        *,
        entry_point: str = "main.py",
        timeout_sec: int = 300,
        args: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute one staged project."""

        ...


class ExperimentSandbox:
    """Execute Python locally; this is process staging, not OS isolation."""

    def __init__(self, config: SandboxConfig, workdir: Path) -> None:
        self.config = config
        self.workdir = workdir.expanduser().resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)

    def run(self, code: str, *, timeout_sec: int = 300) -> SandboxResult:
        """Run source code with the configured Python interpreter."""

        script = self.workdir / f"source-{uuid.uuid4().hex}.py"
        script.write_text(code, encoding="utf-8")
        result = self._execute(script, script.parent, timeout_sec, [], {})
        if result.returncode == 0 and not result.timed_out:
            script.unlink(missing_ok=True)
        return result

    def run_project(
        self,
        project_dir: Path,
        *,
        entry_point: str = "main.py",
        timeout_sec: int = 300,
        args: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Copy and run a project without following source symlinks."""

        started = time.monotonic()
        error = validate_entry_point(entry_point)
        if error:
            return self._failure(error, started)
        source = project_dir.expanduser().resolve()
        if not source.is_dir():
            return self._failure(f"project directory not found: {source}", started)
        for path in source.rglob("*"):
            if path.is_symlink():
                return self._failure(
                    f"project contains a symlink, which execution rejects: {path}",
                    started,
                )
        staging = self.workdir / f"project-{uuid.uuid4().hex}"
        shutil.copytree(source, staging)
        harness = Path(__file__).with_name("harness_template.py")
        shutil.copy2(harness, staging / "experiment_harness.py")
        error = validate_entry_point_resolved(staging, entry_point)
        if error:
            return self._failure(error, started)
        entry = staging / entry_point
        if not entry.is_file():
            return self._failure(f"entry point not found: {entry_point}", started)
        return self._execute(
            entry,
            staging,
            timeout_sec,
            args or [],
            env_overrides or {},
            started=started,
        )

    def _execute(
        self,
        script: Path,
        cwd: Path,
        timeout_sec: int,
        args: list[str],
        env_overrides: dict[str, str],
        *,
        started: float | None = None,
    ) -> SandboxResult:
        if timeout_sec <= 0:
            return self._failure("timeout_sec must be positive", time.monotonic())
        for name in env_overrides:
            if not _ENV_NAME.fullmatch(name):
                return self._failure(
                    f"invalid environment variable name: {name}",
                    started or time.monotonic(),
                )
        begin = started if started is not None else time.monotonic()
        command = [self.config.python_path, "-u", str(script), *args]
        env = {**os.environ, **env_overrides, "PYTHONUNBUFFERED": "1"}
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
                cwd=cwd,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            stdout = _text(error.stdout)
            return SandboxResult(
                -1,
                stdout,
                _text(error.stderr),
                time.monotonic() - begin,
                parse_metrics(stdout),
                timed_out=True,
            )
        except OSError as error:
            return self._failure(str(error), begin)
        return SandboxResult(
            completed.returncode,
            completed.stdout,
            completed.stderr,
            time.monotonic() - begin,
            parse_metrics(completed.stdout),
        )

    @staticmethod
    def _failure(message: str, started: float) -> SandboxResult:
        return SandboxResult(-1, "", message, time.monotonic() - started, {})
