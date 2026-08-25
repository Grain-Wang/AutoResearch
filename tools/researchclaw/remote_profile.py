"""Private profile loading for safe, key-authenticated remote access."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import yaml

_HOST_ALIAS = re.compile(r"^[A-Za-z0-9_.-]+$")
_REMOTE_PATH = re.compile(r"^(?:/|~/)[A-Za-z0-9_./-]*$")


def _mapping(value: object, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} must be a nonempty string")
    return value.strip()


def _reject_unknown(value: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{name} contains unsupported keys: {unknown}")


def _normalize_remote(path: str) -> str:
    if path.startswith("~/"):
        return "~/" + posixpath.normpath(path[2:]).lstrip("/")
    return posixpath.normpath(path)


@dataclass(frozen=True)
class RemoteProfile:
    """Validated machine-private settings for remote inspection."""

    ssh_config: Path
    host: str
    remote_python: str
    root: str
    output: str
    max_depth: int = 2
    recent_runs: int = 10
    timeout_seconds: int = 90

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load a versioned YAML profile without accepting unknown fields."""

        source = path.expanduser().resolve()
        raw_value = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        if not isinstance(raw_value, dict):
            raise TypeError("remote profile must be a mapping")
        raw = {str(key): value for key, value in raw_value.items()}
        _reject_unknown(raw, {"version", "ssh", "snapshot"}, "remote profile")
        if raw.get("version") != 1:
            raise ValueError("remote profile version must be 1")

        ssh = _mapping(raw.get("ssh"), "ssh")
        _reject_unknown(ssh, {"config", "host"}, "ssh")
        config_value = _string(ssh.get("config"), "ssh.config")
        config_path = Path(config_value).expanduser()
        if not config_path.is_absolute():
            config_path = source.parent / config_path

        snapshot = _mapping(raw.get("snapshot"), "snapshot")
        _reject_unknown(
            snapshot,
            {
                "remote_python",
                "root",
                "output",
                "max_depth",
                "recent_runs",
                "timeout_seconds",
            },
            "snapshot",
        )
        profile = cls(
            ssh_config=config_path.resolve(),
            host=_string(ssh.get("host"), "ssh.host"),
            remote_python=_string(
                snapshot.get("remote_python"), "snapshot.remote_python"
            ),
            root=_normalize_remote(_string(snapshot.get("root"), "snapshot.root")),
            output=_normalize_remote(
                _string(snapshot.get("output"), "snapshot.output")
            ),
            max_depth=int(snapshot.get("max_depth", 2)),
            recent_runs=int(snapshot.get("recent_runs", 10)),
            timeout_seconds=int(snapshot.get("timeout_seconds", 90)),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        """Validate paths and keep the status file inside the configured root."""

        if not self.ssh_config.is_file():
            raise FileNotFoundError(f"SSH config not found: {self.ssh_config}")
        if not _HOST_ALIAS.fullmatch(self.host):
            raise ValueError("ssh.host must be a safe OpenSSH alias")
        for name, value in (
            ("snapshot.remote_python", self.remote_python),
            ("snapshot.root", self.root),
            ("snapshot.output", self.output),
        ):
            if not _REMOTE_PATH.fullmatch(value):
                raise ValueError(f"{name} must be a safe absolute or ~/ path")
        root_prefix = self.root.rstrip("/") + "/"
        if not self.output.startswith(root_prefix):
            raise ValueError("snapshot.output must be below snapshot.root")
        if not 1 <= self.max_depth <= 4:
            raise ValueError("snapshot.max_depth must be between 1 and 4")
        if not 1 <= self.recent_runs <= 50:
            raise ValueError("snapshot.recent_runs must be between 1 and 50")
        if not 10 <= self.timeout_seconds <= 600:
            raise ValueError("snapshot.timeout_seconds must be between 10 and 600")
