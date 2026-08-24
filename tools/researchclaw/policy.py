"""Discovery and recording of the authoritative workspace AGENTS.md."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePolicy:
    """Resolved root policy and its stable digest."""

    path: Path
    text: str
    sha256: str


def discover_policy(start: Path) -> WorkspacePolicy:
    """Find the nearest AGENTS.md while walking toward the filesystem root."""

    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        candidate = directory / "AGENTS.md"
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            return WorkspacePolicy(
                path=candidate,
                text=text,
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            )
    raise FileNotFoundError(f"no authoritative AGENTS.md found from {start}")


def record_policy(run_dir: Path, policy: WorkspacePolicy) -> Path:
    """Record a policy snapshot and digest inside a research workspace."""

    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot = run_dir / "AGENTS.md"
    snapshot.write_text(policy.text, encoding="utf-8")
    context = run_dir / "agents_context.json"
    context.write_text(
        json.dumps(
            {
                "source": policy.path.name,
                "sha256": policy.sha256,
                "authoritative": True,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return context
