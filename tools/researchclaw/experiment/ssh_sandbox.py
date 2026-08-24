"""Key-authenticated SSH backend for real experiment execution."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from researchclaw.config import SshRemoteConfig
from researchclaw.experiment.sandbox import (
    SandboxResult,
    parse_metrics,
    validate_entry_point,
    validate_entry_point_resolved,
)

_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _remote_shell_path(path: str) -> str:
    if path.startswith("~/"):
        return '"$HOME"/' + shlex.quote(path[2:])
    return shlex.quote(path)


class SshRemoteSandbox:
    """Execute an experiment project on a configured SSH host."""

    def __init__(self, config: SshRemoteConfig, workdir: Path) -> None:
        config.validate()
        self.config = config
        self.workdir = workdir.expanduser().resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def check_ssh_available(config: SshRemoteConfig) -> tuple[bool, str]:
        """Check that noninteractive key-authenticated SSH succeeds."""

        try:
            config.validate()
            completed = subprocess.run(
                SshRemoteSandbox._ssh_base(config) + ["true"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=min(config.timeout_sec, 30),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            return False, str(error)
        if completed.returncode != 0:
            return False, completed.stderr.strip() or "ssh returned a nonzero status"
        return True, "ok"

    def run(self, code: str, *, timeout_sec: int = 300) -> SandboxResult:
        """Run one Python source string on the remote host."""

        local_project = self.workdir / f"source-{uuid.uuid4().hex}"
        local_project.mkdir(parents=True)
        try:
            (local_project / "main.py").write_text(code, encoding="utf-8")
            return self.run_project(
                local_project,
                entry_point="main.py",
                timeout_sec=timeout_sec,
            )
        finally:
            shutil.rmtree(local_project, ignore_errors=True)

    def run_project(
        self,
        project_dir: Path,
        *,
        entry_point: str = "main.py",
        timeout_sec: int = 300,
        args: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Copy a project to a unique remote directory and execute it."""

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
                    f"project contains a symlink, which SSH execution rejects: {path}",
                    started,
                )

        staging = self.workdir / f"project-{uuid.uuid4().hex}"
        remote_dir = f"{self.config.remote_workdir.rstrip('/')}/run-{uuid.uuid4().hex}"
        try:
            shutil.copytree(source, staging)
            harness = Path(__file__).with_name("harness_template.py")
            shutil.copy2(harness, staging / "experiment_harness.py")
            error = validate_entry_point_resolved(staging, entry_point)
            if error:
                return self._failure(error, started)
            if not (staging / entry_point).is_file():
                return self._failure(
                    f"entry point {entry_point} not found in project", started
                )

            create = self._run_ssh(
                f"set -eu\nmkdir -p -- {_remote_shell_path(remote_dir)}\n",
                timeout_sec=min(timeout_sec, self.config.timeout_sec),
            )
            if create.returncode != 0:
                return self._completed_result(create, started)
            copied = subprocess.run(
                self._scp_base(self.config)
                + [f"{staging}/.", f"{self._target()}:{remote_dir}/"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=min(timeout_sec, self.config.timeout_sec),
                check=False,
            )
            if copied.returncode != 0:
                return self._completed_result(copied, started)
            script = self._execution_script(
                remote_dir,
                entry_point,
                args or [],
                env_overrides or {},
            )
            completed = self._run_ssh(
                script,
                timeout_sec=min(timeout_sec, self.config.timeout_sec),
            )
            return self._completed_result(completed, started)
        except (OSError, ValueError) as error:
            return self._failure(str(error), started)
        except subprocess.TimeoutExpired as error:
            stdout = _text(error.stdout)
            return SandboxResult(
                returncode=-1,
                stdout=stdout,
                stderr=_text(error.stderr),
                elapsed_sec=time.monotonic() - started,
                metrics=parse_metrics(stdout),
                timed_out=True,
            )
        finally:
            shutil.rmtree(staging, ignore_errors=True)
            self._cleanup_remote(remote_dir)

    def _execution_script(
        self,
        remote_dir: str,
        entry_point: str,
        args: list[str],
        env_overrides: dict[str, str],
    ) -> str:
        for name in env_overrides:
            if not _ENV_NAME.fullmatch(name):
                raise ValueError(f"invalid environment variable name: {name}")
        exports = {**env_overrides, "PYTHONUNBUFFERED": "1"}
        if self.config.gpu_ids:
            exports["CUDA_VISIBLE_DEVICES"] = ",".join(
                str(gpu_id) for gpu_id in self.config.gpu_ids
            )
        lines = ["set -eu", f"cd -- {_remote_shell_path(remote_dir)}"]
        lines.extend(self.config.setup_commands)
        lines.extend(
            f"export {name}={shlex.quote(value)}"
            for name, value in sorted(exports.items())
        )
        command = [self.config.remote_python, "-u", entry_point, *args]
        lines.append(" ".join(shlex.quote(item) for item in command))
        return "\n".join(lines) + "\n"

    def _run_ssh(
        self,
        script: str,
        *,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self._ssh_base(self.config) + ["bash", "-s"],
            input=script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
        )

    def _cleanup_remote(self, remote_dir: str) -> None:
        prefix = self.config.remote_workdir.rstrip("/") + "/run-"
        if not remote_dir.startswith(prefix):
            return
        try:
            self._run_ssh(
                f"set -eu\nrm -rf -- {_remote_shell_path(remote_dir)}\n",
                timeout_sec=min(self.config.timeout_sec, 30),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _target(self) -> str:
        return (
            f"{self.config.user}@{self.config.host}"
            if self.config.user
            else self.config.host
        )

    @staticmethod
    def _ssh_base(config: SshRemoteConfig) -> list[str]:
        command = ["ssh", "-o", "BatchMode=yes", "-p", str(config.port)]
        if config.key_path:
            command.extend(["-i", os.path.expanduser(config.key_path)])
        target = f"{config.user}@{config.host}" if config.user else config.host
        return [*command, target]

    @staticmethod
    def _scp_base(config: SshRemoteConfig) -> list[str]:
        command = ["scp", "-r", "-p", "-P", str(config.port)]
        if config.key_path:
            command.extend(["-i", os.path.expanduser(config.key_path)])
        return command

    @staticmethod
    def _completed_result(
        completed: subprocess.CompletedProcess[str], started: float
    ) -> SandboxResult:
        return SandboxResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            elapsed_sec=time.monotonic() - started,
            metrics=parse_metrics(completed.stdout),
        )

    @staticmethod
    def _failure(message: str, started: float) -> SandboxResult:
        return SandboxResult(
            returncode=-1,
            stdout="",
            stderr=message,
            elapsed_sec=time.monotonic() - started,
            metrics={},
        )
