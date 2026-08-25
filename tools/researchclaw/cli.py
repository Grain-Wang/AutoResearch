"""Command-line entry point for the compact AutoResearch toolbox."""

from __future__ import annotations

import argparse
import sys

from researchclaw.tools_cli import TOOLS_STEPS, cmd_tools


def build_parser() -> argparse.ArgumentParser:
    """Build the compact public CLI."""

    parser = argparse.ArgumentParser(prog="researchclaw", description=__doc__)
    subparsers = parser.add_subparsers(dest="command")

    tools_parser = subparsers.add_parser(
        "tools", help="Validate and execute the 16-stage research workflow"
    )
    tools_parser.add_argument(
        "tools_action",
        choices=("list", "init", "status", *TOOLS_STEPS),
    )
    tools_parser.add_argument("--run-dir", default=None)
    tools_parser.add_argument("--topic", default=None)
    tools_parser.add_argument("--config", "-c", default=None)

    queue_parser = subparsers.add_parser(
        "gpu-queue", help="Run a durable cooperative GPU task queue"
    )
    queue_parser.add_argument(
        "gpu_queue_action",
        choices=("validate", "run", "status", "stop", "retry"),
    )
    queue_parser.add_argument("task_id", nargs="?", default=None)
    queue_parser.add_argument("--config", "-c", default=None)
    queue_parser.add_argument("--state", default="queue-state.sqlite")
    queue_parser.add_argument("--dry-run", action="store_true")
    queue_parser.add_argument("--json", action="store_true")

    remote_parser = subparsers.add_parser(
        "remote", help="Safely inspect a key-authenticated research server"
    )
    remote_parser.add_argument(
        "remote_action", choices=("check", "connect", "snapshot", "show")
    )
    remote_parser.add_argument("--profile", default=".local-deps/ssh/a800.yaml")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch a compact ResearchClaw command and return an exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "tools":
            return cmd_tools(args)
        if args.command == "gpu-queue":
            from researchclaw.gpu_queue.cli import cmd_gpu_queue

            return cmd_gpu_queue(args)
        if args.command == "remote":
            from researchclaw.remote_cli import cmd_remote

            return cmd_remote(args)
        parser.print_help()
        return 0
    except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
