"""Download the revision-locked KITTI RGB subset from a public repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _safe_relative_path(value: object) -> PurePosixPath:
    path = PurePosixPath(str(value).strip().replace("\\", "/"))
    if (
        not path.parts
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"unsafe relative path: {value!r}")
    return path


def _read_plan(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_local_paths: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            repository_path = _safe_relative_path(value.get("repository_path"))
            local_path = _safe_relative_path(value.get("rgb_relative_path"))
            if local_path.as_posix() in seen_local_paths:
                raise ValueError(f"duplicate local RGB path: {local_path}")
            seen_local_paths.add(local_path.as_posix())
            records.append(
                {
                    **value,
                    "repository_path": repository_path.as_posix(),
                    "rgb_relative_path": local_path.as_posix(),
                }
            )
    if not records:
        raise ValueError("KITTI download plan must not be empty")
    return records


def _download_bytes(url: str, *, timeout: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "AutoResearch-KITTI-Subset/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", response.getcode()))
        if status != 200:
            raise RuntimeError(f"expected HTTP 200, received {status}")
        return bytes(response.read())


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_png(payload: bytes, *, source: str) -> None:
    if len(payload) <= len(PNG_SIGNATURE) or not payload.startswith(PNG_SIGNATURE):
        raise ValueError(f"downloaded object is not a PNG: {source}")


def _download_one(
    record: Mapping[str, Any],
    *,
    base_url: str,
    output_root: Path,
    timeout: float,
    max_retries: int,
) -> dict[str, Any]:
    relative = _safe_relative_path(record["rgb_relative_path"])
    destination = output_root.joinpath(*relative.parts)
    if destination.exists():
        if not destination.is_file():
            raise ValueError(f"download destination is not a file: {destination}")
        with destination.open("rb") as handle:
            _validate_png(handle.read(len(PNG_SIGNATURE) + 1), source=str(destination))
    else:
        repository_path = _safe_relative_path(record["repository_path"])
        encoded_path = "/".join(
            urllib.parse.quote(part, safe="") for part in repository_path.parts
        )
        url = f"{base_url.rstrip('/')}/{encoded_path}"
        last_error: BaseException | None = None
        for attempt in range(max_retries + 1):
            try:
                payload = _download_bytes(url, timeout=timeout)
                _validate_png(payload, source=url)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as handle:
                    handle.write(payload)
                last_error = None
                break
            except (
                urllib.error.URLError,
                TimeoutError,
                ConnectionError,
                OSError,
                RuntimeError,
                ValueError,
            ) as error:
                last_error = error
                if destination.exists():
                    raise
                if attempt == max_retries:
                    break
                time.sleep(min(2**attempt, 16))
        if last_error is not None:
            raise RuntimeError(f"failed to download {relative}") from last_error
    return {
        "dataset": "KITTI",
        "image_id": str(record["image_id"]),
        "repository_path": str(record["repository_path"]),
        "rgb_relative_path": relative.as_posix(),
        "rgb_sha256": _file_sha256(destination),
        "size_bytes": destination.stat().st_size,
    }


def download_kitti_subset(
    plan_path: Path,
    *,
    output_root: Path,
    output_manifest: Path,
    repository_id: str,
    repository_revision: str,
    base_host: str = "https://huggingface.co",
    workers: int = 16,
    timeout: float = 60.0,
    max_retries: int = 5,
) -> list[dict[str, Any]]:
    """Download every planned RGB and write a deterministic integrity manifest."""

    if workers <= 0 or timeout <= 0 or max_retries < 0:
        raise ValueError("workers/timeout/retries are outside their valid ranges")
    if not repository_id.strip() or not repository_revision.strip():
        raise ValueError("repository_id and repository_revision must be explicit")
    records = _read_plan(plan_path)
    quoted_repository = "/".join(
        urllib.parse.quote(part, safe="") for part in repository_id.strip().split("/")
    )
    quoted_revision = urllib.parse.quote(repository_revision.strip(), safe="")
    base_url = (
        f"{base_host.rstrip('/')}/datasets/{quoted_repository}/resolve/"
        f"{quoted_revision}"
    )
    completed: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(records))) as executor:
        futures = [
            executor.submit(
                _download_one,
                record,
                base_url=base_url,
                output_root=output_root,
                timeout=timeout,
                max_retries=max_retries,
            )
            for record in records
        ]
        for future in as_completed(futures):
            completed.append(future.result())
    completed.sort(key=lambda record: str(record["image_id"]))
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    with output_manifest.open("w", encoding="utf-8", newline="\n") as handle:
        for record in completed:
            enriched = {
                **record,
                "repository_id": repository_id.strip(),
                "repository_revision": repository_revision.strip(),
            }
            handle.write(json.dumps(enriched, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return completed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--repository-revision", required=True)
    parser.add_argument("--base-host", default="https://huggingface.co")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    download_kitti_subset(
        args.plan,
        output_root=args.output_root,
        output_manifest=args.output_manifest,
        repository_id=args.repository_id,
        repository_revision=args.repository_revision,
        base_host=args.base_host,
        workers=args.workers,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )


if __name__ == "__main__":
    main()
