"""Tests for the deliberately small public CLI."""

from pathlib import Path

import pytest

from researchclaw.cli import build_parser, main


@pytest.mark.parametrize("removed", ["run", "serve", "skills", "web", "voice"])
def test_removed_product_commands_are_not_parseable(removed: str) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([removed])


def test_tools_init_records_authoritative_policy(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "AGENTS.md").write_text("policy\n", encoding="utf-8")
    run_dir = repository / "paper1" / "run"

    exit_code = main(
        [
            "tools",
            "init",
            "--run-dir",
            str(run_dir),
            "--topic",
            "test algorithm",
        ]
    )

    assert exit_code == 0
    assert (run_dir / "tools.json").is_file()
    assert (run_dir / "AGENTS.md").read_text(encoding="utf-8") == "policy\n"
