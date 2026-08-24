"""Tests for authoritative AGENTS.md discovery and snapshots."""

import json
from pathlib import Path

from researchclaw.policy import discover_policy, record_policy


def test_discovers_nearest_policy_and_records_no_absolute_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "paper1" / "run"
    nested.mkdir(parents=True)
    (root / "AGENTS.md").write_text("root policy\n", encoding="utf-8")

    policy = discover_policy(nested)
    context_path = record_policy(nested, policy)
    context = json.loads(context_path.read_text(encoding="utf-8"))

    assert policy.path == root / "AGENTS.md"
    assert (nested / "AGENTS.md").read_text(encoding="utf-8") == "root policy\n"
    assert context["source"] == "AGENTS.md"
    assert str(root) not in context_path.read_text(encoding="utf-8")
