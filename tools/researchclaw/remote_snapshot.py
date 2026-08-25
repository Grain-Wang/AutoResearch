"""Standalone, standard-library-only remote server status collector."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA_VERSION = 1
MAX_RESULT_FILES = 200
MAX_STAGE_TABLE_ROWS = 80
MAX_JSON_FIELDS = 40
MAX_HASH_BYTES = 16 * 1024 * 1024
CHECKPOINT_SUFFIXES = frozenset({".pt", ".pth", ".ckpt", ".safetensors"})
SENSITIVE_PARTS = frozenset(
    {
        ".ssh",
        ".env",
        "credentials",
        "credential",
        "password",
        "private_key",
        "secret",
        "sshconfig",
        "token",
    }
)
TREE_SKIP_DIRS = frozenset(
    {
        ".git",
        ".ssh",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "download-parts",
        "raw",
    }
)
RESULT_KEYS = frozenset(
    {
        "status",
        "decision",
        "dataset",
        "gate_pass",
        "claim_f",
        "claim_m",
        "claim_status",
        "record_count",
        "image_count",
        "eligible_image_count",
        "eligible_pair_count",
        "independent_clusters_with_eligible_pair",
        "local_claim_datasets",
        "kitti_role",
        "virtual_kitti2_role",
    }
)


def _run(args: Sequence[str], *, timeout: int = 15) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, str(error)
    output = completed.stdout.strip()
    if completed.returncode != 0 and completed.stderr.strip():
        output = completed.stderr.strip()
    return completed.returncode, output


def _is_sensitive(path: Path) -> bool:
    for part in path.parts:
        lowered = part.lower()
        if lowered in SENSITIVE_PARTS:
            return True
        if any(word in lowered for word in ("password", "private_key", "secret")):
            return True
        if lowered.endswith((".pem", ".key")):
            return True
    return False


def _is_regular_file(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode)


def _is_real_directory(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISDIR(mode)


def _relative(path: Path, root: Path) -> str:
    try:
        return "~/whr/" + path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _safe_text(value: str, *, limit: int = 200) -> str:
    rendered = value.replace(str(Path.home()), "~")
    lowered = rendered.lower()
    if any(part in lowered for part in SENSITIVE_PARTS):
        return "<redacted>"
    return rendered[:limit]


def _human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def _mtime(path: Path) -> str:
    try:
        timestamp = path.lstat().st_mtime
    except OSError:
        return "UNAVAILABLE"
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_HASH_BYTES:
            return "SKIPPED_LARGE_FILE"
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return "UNAVAILABLE"


def _disk_usage(path: Path) -> str:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return "UNAVAILABLE"
    return (
        f"{_human_bytes(usage.used)} used / {_human_bytes(usage.total)} total "
        f"({_human_bytes(usage.free)} free)"
    )


def _directory_size(path: Path) -> str:
    code, output = _run(["du", "-sh", "--", str(path)], timeout=20)
    if code != 0 or not output:
        return "UNAVAILABLE"
    return output.split(maxsplit=1)[0]


def _memory_summary() -> str:
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", maxsplit=1)
            if key in {"MemTotal", "MemAvailable"}:
                values[key] = int(raw.strip().split()[0]) * 1024
        return (
            f"{_human_bytes(values['MemTotal'] - values['MemAvailable'])} used / "
            f"{_human_bytes(values['MemTotal'])} total"
        )
    except (OSError, KeyError, ValueError):
        return "UNAVAILABLE"


def _uptime() -> str:
    try:
        seconds = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return "UNAVAILABLE"
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return f"{days}d {hours}h {minutes}m"


def _gpu_rows() -> list[str]:
    fields = (
        "index,name,driver_version,memory.used,memory.total,"
        "utilization.gpu,temperature.gpu"
    )
    code, output = _run(
        [
            "nvidia-smi",
            f"--query-gpu={fields}",
            "--format=csv,noheader,nounits",
        ]
    )
    if code != 0:
        return [f"- GPU probe: `UNAVAILABLE` ({output[:160]})"]
    rows = [
        "| GPU | Model | Driver | Memory MiB | Utilization | Temp |",
        "| ---: | --- | --- | ---: | ---: | ---: |",
    ]
    for line in output.splitlines():
        values = [part.strip() for part in line.split(",")]
        if len(values) != 7:
            continue
        index, name, driver, used, total, utilization, temperature = values
        rows.append(
            f"| {index} | {name} | {driver} | {used}/{total} | "
            f"{utilization}% | {temperature} C |"
        )
    process_code, process_output = _run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,used_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    process_count = (
        len([line for line in process_output.splitlines() if line.strip()])
        if process_code == 0
        else 0
    )
    rows.append("")
    rows.append(f"- Active GPU compute processes: {process_count}")
    return rows


def _research_process_rows() -> list[str]:
    code, output = _run(["ps", "-u", str(os.getuid()), "-o", "pid=,etime=,comm="])
    if code != 0:
        return ["- Research processes: `UNAVAILABLE`"]
    allowed = ("python", "pytest", "researchclaw")
    rows = []
    for line in output.splitlines():
        if any(name in line.lower() for name in allowed):
            rows.append(f"- `{line.strip()}`")
    return rows or ["- Research processes: none detected"]


def _python_version(path: Path) -> str:
    if not _is_regular_file(path) and not path.is_symlink():
        return "UNAVAILABLE"
    code, output = _run([str(path), "--version"], timeout=10)
    return output.splitlines()[0] if code == 0 and output else "UNAVAILABLE"


def _environment_display_path(path: Path, root: Path) -> str:
    try:
        if path.is_relative_to(root):
            return _relative(path, root)
    except OSError:
        return "<external>/" + path.name
    home = Path.home()
    if path.is_relative_to(home):
        return "~/" + path.relative_to(home).as_posix()
    return "<external>/" + path.name


def _environment_rows(root: Path) -> list[str]:
    environments: dict[Path, str] = {}
    conda = shutil.which("conda")
    if conda:
        code, output = _run([conda, "env", "list", "--json"], timeout=30)
        if code == 0:
            try:
                payload = json.loads(output)
                for raw_path in payload.get("envs", []):
                    path = Path(str(raw_path)).expanduser()
                    environments[path] = path.name or "base"
            except (json.JSONDecodeError, TypeError):
                pass
    for pattern in ("paper*/envs/*/bin/python", "envs/*/bin/python"):
        for python_path in root.glob(pattern):
            if _is_sensitive(python_path) or not python_path.exists():
                continue
            environments[python_path.parent.parent] = python_path.parent.parent.name
    rows = [
        "| Environment | Path | Python |",
        "| --- | --- | --- |",
    ]
    for path, name in sorted(environments.items(), key=lambda item: str(item[0]))[:50]:
        python_path = path / "bin" / "python"
        display = _environment_display_path(path, root)
        rows.append(f"| {name} | `{display}` | {_python_version(python_path)} |")
    if len(rows) == 2:
        rows.append("| — | — | UNAVAILABLE |")
    return rows


def _tree_rows(root: Path, output: Path, max_depth: int) -> list[str]:
    rows = [
        "| Path | Type | Size | Modified UTC |",
        "| --- | --- | ---: | --- |",
    ]

    def visit(directory: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError:
            return
        for child in children:
            if child == output or _is_sensitive(child) or child.name in TREE_SKIP_DIRS:
                continue
            if child.is_symlink():
                rows.append(
                    f"| `{_relative(child, root)}` | symlink-skipped | — | {_mtime(child)} |"
                )
                continue
            if _is_real_directory(child):
                size = _directory_size(child) if depth == 1 else "—"
                rows.append(
                    f"| `{_relative(child, root)}` | directory | {size} | {_mtime(child)} |"
                )
                visit(child, depth + 1)
            elif _is_regular_file(child):
                try:
                    size = _human_bytes(child.stat().st_size)
                except OSError:
                    size = "UNAVAILABLE"
                rows.append(
                    f"| `{_relative(child, root)}` | file | {size} | {_mtime(child)} |"
                )

    visit(root, 1)
    return rows


def _candidate_result_files(root: Path, recent_runs: int) -> list[Path]:
    candidates: set[Path] = set()
    patterns = (
        "paper*/AutoResearch/paper*/results/**/*",
        "paper*/runs/*/repo/paper*/results/**/*",
        "paper*/artifacts/**/*",
        "paper*/queue/*",
        "paper*/runs/*/repo/paper*/data/queue/*.sqlite",
        "paper*/runs/*/repo/paper*/steps/README.md",
        "paper*/AutoResearch/paper*/steps/README.md",
    )
    for pattern in patterns:
        for path in root.glob(pattern):
            if _is_regular_file(path) and not _is_sensitive(path):
                candidates.add(path)
    ordered = sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)
    run_names: list[str] = []
    selected: list[Path] = []
    for path in ordered:
        relative = path.relative_to(root).parts
        run_name = ""
        if "runs" in relative:
            index = relative.index("runs")
            if index + 1 < len(relative):
                run_name = "/".join(relative[: index + 2])
        if run_name and run_name not in run_names:
            if len(run_names) >= recent_runs:
                continue
            run_names.append(run_name)
        selected.append(path)
        if len(selected) >= MAX_RESULT_FILES:
            break
    return selected


def _flatten_result_fields(value: object, prefix: str = "") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            name = str(key)
            child_prefix = f"{prefix}.{name}" if prefix else name
            if name in RESULT_KEYS and isinstance(item, (str, int, float, bool, list)):
                rendered = json.dumps(item, ensure_ascii=False)
                rows.append((child_prefix, _safe_text(rendered)))
            rows.extend(_flatten_result_fields(item, child_prefix))
            if len(rows) >= MAX_JSON_FIELDS:
                break
    elif isinstance(value, list):
        for index, item in enumerate(value[:20]):
            rows.extend(_flatten_result_fields(item, f"{prefix}[{index}]"))
            if len(rows) >= MAX_JSON_FIELDS:
                break
    return rows[:MAX_JSON_FIELDS]


def _json_result_rows(path: Path, root: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    rows = []
    for key, value in _flatten_result_fields(payload):
        rows.append(f"  - `{key}`: `{value}`")
    return rows


def _queue_rows(path: Path) -> list[str]:
    try:
        uri = f"file:{path}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }
        required = {"task_id", "status", "attempts"}
        if not required.issubset(columns):
            connection.close()
            return []
        records = connection.execute(
            "SELECT task_id, status, attempts FROM tasks ORDER BY rowid"
        ).fetchall()
        connection.close()
    except sqlite3.Error:
        return []
    return [
        f"  - `{row['task_id']}`: {row['status']} (attempts={row['attempts']})"
        for row in records
    ]


def _stage_rows(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    rows = []
    for line in lines:
        if not line.startswith("|"):
            continue
        rendered = _safe_text(line, limit=500)
        if rendered != "<redacted>":
            rows.append(rendered)
        if len(rows) >= MAX_STAGE_TABLE_ROWS:
            break
    return rows


def _result_rows(root: Path, recent_runs: int) -> list[str]:
    rows: list[str] = []
    for path in _candidate_result_files(root, recent_runs):
        relative = _relative(path, root)
        try:
            size = _human_bytes(path.stat().st_size)
        except OSError:
            size = "UNAVAILABLE"
        rows.append(
            f"### `{relative}`\n\n"
            f"- Size: {size}\n"
            f"- Modified: {_mtime(path)}\n"
            f"- SHA256: `{_sha256(path)}`"
        )
        if path.suffix.lower() == ".json":
            rows.extend(_json_result_rows(path, root))
        elif path.suffix.lower() == ".sqlite":
            rows.extend(_queue_rows(path))
        elif path.name == "README.md" and path.parent.name == "steps":
            stage_rows = _stage_rows(path)
            if stage_rows:
                rows.extend(["", *stage_rows])
    return rows or ["No structured research results were discovered."]


def _qa_rows(root: Path) -> list[str]:
    logs = list(
        root.glob("paper*/runs/*/repo/.local-deps/paper1-gpu-queue/runs/qa-*/*/*.log")
    )
    latest: dict[str, Path] = {}
    for path in logs:
        if not _is_regular_file(path) or _is_sensitive(path):
            continue
        task = next((part for part in path.parts if part.startswith("qa-")), "qa")
        previous = latest.get(task)
        if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
            latest[task] = path
    rows = []
    patterns = (
        re.compile(r"\d+ passed in [0-9.]+s"),
        re.compile(r"All checks passed!"),
        re.compile(r"\d+ files? would be left unchanged"),
    )
    for task, path in sorted(latest.items()):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        summary = next(
            (
                match.group(0)
                for pattern in patterns
                if (match := pattern.search(content))
            ),
            "log present; no recognized summary",
        )
        rows.append(f"- `{task}`: {summary} ({_relative(path, root)})")
    return rows or ["- QA logs: none discovered"]


def _checkpoint_rows(root: Path) -> list[str]:
    roots = list(root.glob("paper*/artifacts"))
    roots.extend(root.glob("paper*/runs/*/repo/paper*/artifacts"))
    checkpoints: list[Path] = []
    for artifact_root in roots:
        if not _is_real_directory(artifact_root):
            continue
        for path in artifact_root.rglob("*"):
            if (
                _is_regular_file(path)
                and not _is_sensitive(path)
                and path.suffix.lower() in CHECKPOINT_SUFFIXES
            ):
                checkpoints.append(path)
    total = sum(path.stat().st_size for path in checkpoints)
    rows = [f"- Checkpoints: {len(checkpoints)} ({_human_bytes(total)})"]
    for path in sorted(
        checkpoints, key=lambda item: item.stat().st_mtime, reverse=True
    )[:20]:
        rows.append(
            f"  - `{_relative(path, root)}` ({_human_bytes(path.stat().st_size)})"
        )
    return rows


def render_snapshot(root: Path, output: Path, max_depth: int, recent_runs: int) -> str:
    """Collect bounded server state and render a secret-conscious Markdown report."""

    generated_at = dt.datetime.now(tz=dt.timezone.utc).isoformat()
    lines = [
        "# A800 Server Status",
        "",
        f"- Schema version: {SCHEMA_VERSION}",
        f"- Generated UTC: {generated_at}",
        f"- Hostname: {platform.node()}",
        "- Evidence scope: operational snapshot only; not a scientific conclusion",
        "",
        "## System",
        "",
        f"- Platform: {platform.platform()}",
        f"- CPU logical cores: {os.cpu_count() or 'UNAVAILABLE'}",
        f"- Memory: {_memory_summary()}",
        f"- Uptime: {_uptime()}",
        f"- `~/whr` storage: {_disk_usage(root)}",
        "",
        "## GPUs",
        "",
        *_gpu_rows(),
        "",
        "## User Research Processes",
        "",
        *_research_process_rows(),
        "",
        "## Python and Conda Environments",
        "",
        *_environment_rows(root),
        "",
        "## `~/whr` Inventory",
        "",
        *_tree_rows(root, output, max_depth),
        "",
        "## QA Summaries",
        "",
        *_qa_rows(root),
        "",
        "## Checkpoints",
        "",
        *_checkpoint_rows(root),
        "",
        "## Structured Research Results and Queues",
        "",
        "Result sources are ordered by modification time. Older step tables do not "
        "override newer structured artifacts.",
        "",
        *_result_rows(root, recent_runs),
        "",
    ]
    return "\n".join(lines)


def _validate_paths(root_value: str, output_value: str) -> tuple[Path, Path]:
    raw_root = Path(root_value).expanduser()
    if raw_root.is_symlink() or not _is_real_directory(raw_root):
        raise ValueError("snapshot root must be an existing non-symlink directory")
    root = raw_root.resolve(strict=True)
    raw_output = Path(output_value).expanduser()
    if raw_output.exists() and raw_output.is_symlink():
        raise ValueError("snapshot output must not be a symlink")
    parent = raw_output.parent.resolve(strict=True)
    if parent != root:
        raise ValueError("snapshot output must be a direct child of snapshot root")
    return root, raw_output


def write_snapshot(root: Path, output: Path, content: str) -> str:
    """Atomically replace the status file and return its SHA256."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=root
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
        output.chmod(0o600)
    finally:
        if temporary.exists():
            temporary.unlink()
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone collector parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--recent-runs", type=int, default=10)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Collect and atomically persist the remote status snapshot."""

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if not 1 <= args.max_depth <= 4:
        raise ValueError("max-depth must be between 1 and 4")
    if not 1 <= args.recent_runs <= 50:
        raise ValueError("recent-runs must be between 1 and 50")
    root, output = _validate_paths(args.root, args.output)
    content = render_snapshot(root, output, args.max_depth, args.recent_runs)
    digest = write_snapshot(root, output, content)
    print(f"WROTE {args.output} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
