"""Portable provenance helpers for machine-generated research artifacts."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_file_hashes(paper_root: Path, files: tuple[Path, ...]) -> dict[str, str]:
    """Return stable paper-relative source-file digests."""

    return {
        path.relative_to(paper_root).as_posix(): sha256_file(path)
        for path in sorted(files)
    }


def canonical_sha256(payload: Any) -> str:
    """Hash a canonical JSON encoding of a serializable object."""

    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_state(repository_root: Path, pathspec: str) -> dict[str, object]:
    """Return commit identity and scoped dirty-worktree status."""

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", pathspec],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"git_commit": commit, "dirty_worktree": bool(status.strip())}


def runtime_provenance() -> dict[str, str]:
    """Return portable generation time and Python/platform identity."""

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
