"""Small deterministic I/O helpers for BAR-Depth experiments."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def file_digest(path: Path, algorithm: str = "sha256") -> str:
    """Return the hexadecimal digest of a file without loading it in memory."""
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_digest(payload: Any) -> str:
    """Hash a JSON-compatible object under a deterministic serialization."""
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object and reject non-object roots."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def write_json_atomic(path: Path, payload: Any) -> None:
    """Atomically write a formatted JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    """Atomically write deterministic JSON Lines rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                + "\n"
            )
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSON Lines file into object rows."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Expected object at {path}:{line_number}")
            rows.append(row)
    return rows


def write_csv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    """Atomically write object rows to CSV with a stable column order."""
    if not rows:
        raise ValueError("Cannot write an empty CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    fieldnames = list(rows[0])
    if any(list(row) != fieldnames for row in rows):
        raise ValueError("CSV rows do not share an identical ordered schema")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
