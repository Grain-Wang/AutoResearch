"""CLI for strict key-authenticated remote checks and status snapshots."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from researchclaw.remote_profile import RemoteProfile


def _remote_path(path: str) -> str:
    if path.startswith("~/"):
        return '"$HOME"/' + shlex.quote(path[2:])
    return shlex.quote(path)


def _ssh_base(profile: RemoteProfile, *, tty: bool = False) -> list[str]:
    command = [
        "ssh",
        "-F",
        str(profile.ssh_config),
        "-o",
        "BatchMode=yes",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "KbdInteractiveAuthentication=no",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ClearAllForwardings=yes",
    ]
    if tty:
        command.append("-t")
    return [*command, profile.host]


def _run(
    command: Sequence[str],
    *,
    timeout: int | None,
    input_text: str | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        input=input_text,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _print_completed(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)


def _check(profile: RemoteProfile) -> int:
    command = (
        "set -eu; "
        f"test -d {_remote_path(profile.root)}; "
        'printf "CONNECTED\\n"; hostname; '
        f"{_remote_path(profile.remote_python)} --version; "
        "nvidia-smi -L"
    )
    completed = _run(
        [*_ssh_base(profile), command], timeout=min(profile.timeout_seconds, 30)
    )
    _print_completed(completed)
    return completed.returncode


def _connect(profile: RemoteProfile) -> int:
    completed = _run(
        _ssh_base(profile, tty=sys.stdin.isatty()),
        timeout=None,
        capture=False,
    )
    return completed.returncode


def _snapshot(profile: RemoteProfile) -> int:
    collector = Path(__file__).with_name("remote_snapshot.py")
    source = collector.read_text(encoding="utf-8")
    command = " ".join(
        (
            _remote_path(profile.remote_python),
            "-",
            "--root",
            shlex.quote(profile.root),
            "--output",
            shlex.quote(profile.output),
            "--max-depth",
            str(profile.max_depth),
            "--recent-runs",
            str(profile.recent_runs),
        )
    )
    completed = _run(
        [*_ssh_base(profile), command],
        timeout=profile.timeout_seconds,
        input_text=source,
    )
    _print_completed(completed)
    return completed.returncode


def _show(profile: RemoteProfile) -> int:
    command = (
        f"set -eu; test -f {_remote_path(profile.output)}; "
        f"cat -- {_remote_path(profile.output)}"
    )
    completed = _run(
        [*_ssh_base(profile), command], timeout=min(profile.timeout_seconds, 30)
    )
    _print_completed(completed)
    return completed.returncode


def cmd_remote(args: argparse.Namespace) -> int:
    """Dispatch a remote action using an ignored machine-private profile."""

    profile = RemoteProfile.load(Path(args.profile))
    if args.remote_action == "check":
        return _check(profile)
    if args.remote_action == "connect":
        return _connect(profile)
    if args.remote_action == "snapshot":
        return _snapshot(profile)
    if args.remote_action == "show":
        return _show(profile)
    raise ValueError(f"unknown remote action: {args.remote_action}")
