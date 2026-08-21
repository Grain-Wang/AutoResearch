"""Resume concurrent HTTP Range downloads and assemble a verified source blob."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

LOGGER = logging.getLogger(__name__)

_PART_FILENAME_PATTERN = re.compile(
    r"^part_(?P<index>\d+)_(?P<start>\d+)_(?P<end>\d+)\.bin$"
)
_CONTENT_RANGE_PATTERN = re.compile(
    r"^\s*bytes\s+(?P<start>\d+)-(?P<end>\d+)/(?P<total>\d+)\s*$",
    re.IGNORECASE,
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RETRYABLE_HTTP_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


class DownloadError(RuntimeError):
    """Base error for a failed range download or assembly."""


class ProtocolError(DownloadError):
    """Raised before writing bytes from an invalid HTTP Range response."""


class RetryableDownloadError(DownloadError):
    """Raised for a transient network failure that can be resumed."""


@dataclass(frozen=True, order=True)
class ByteRange:
    """An inclusive byte range assigned to one numbered part."""

    index: int
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("range index must be nonnegative")
        if self.start < 0:
            raise ValueError("range start must be nonnegative")
        if self.end < self.start:
            raise ValueError("range end must not precede range start")

    @property
    def size(self) -> int:
        """Return the inclusive range length."""

        return self.end - self.start + 1


@dataclass(frozen=True)
class ContentRange:
    """A parsed HTTP Content-Range value."""

    start: int
    end: int
    total_size: int

    @property
    def size(self) -> int:
        """Return the inclusive response range length."""

        return self.end - self.start + 1


def part_filename(part: ByteRange) -> str:
    """Return the stable filename used for a range part."""

    return f"part_{part.index:02d}_{part.start}_{part.end}.bin"


def parse_part_filename(filename: str | Path) -> ByteRange:
    """Parse ``part_<idx>_<start>_<end>.bin`` into an inclusive range."""

    name = Path(filename).name
    match = _PART_FILENAME_PATTERN.fullmatch(name)
    if match is None:
        raise ValueError(f"invalid range part filename: {name!r}")
    return ByteRange(
        index=int(match.group("index")),
        start=int(match.group("start")),
        end=int(match.group("end")),
    )


def parse_content_range(value: str) -> ContentRange:
    """Parse a concrete HTTP ``Content-Range`` header."""

    match = _CONTENT_RANGE_PATTERN.fullmatch(value)
    if match is None:
        raise ProtocolError(f"invalid Content-Range header: {value!r}")

    parsed = ContentRange(
        start=int(match.group("start")),
        end=int(match.group("end")),
        total_size=int(match.group("total")),
    )
    if parsed.end < parsed.start:
        raise ProtocolError("Content-Range end precedes its start")
    if parsed.total_size <= 0 or parsed.end >= parsed.total_size:
        raise ProtocolError("Content-Range lies outside the reported total size")
    return parsed


def plan_ranges(
    total_size: int,
    *,
    start_offset: int = 0,
    part_size: int | None = None,
    part_count: int | None = None,
) -> tuple[ByteRange, ...]:
    """Plan contiguous ranges after a prefix using one sizing strategy."""

    if isinstance(total_size, bool) or total_size < 0:
        raise ValueError("total_size must be a nonnegative integer")
    if isinstance(start_offset, bool) or not 0 <= start_offset <= total_size:
        raise ValueError("start_offset must lie within the blob")
    if (part_size is None) == (part_count is None):
        raise ValueError("specify exactly one of part_size or part_count")

    remaining_size = total_size - start_offset
    if remaining_size == 0:
        return ()

    if part_count is not None:
        if isinstance(part_count, bool) or part_count <= 0:
            raise ValueError("part_count must be a positive integer")
        effective_part_size = (remaining_size + part_count - 1) // part_count
    else:
        if isinstance(part_size, bool) or part_size is None or part_size <= 0:
            raise ValueError("part_size must be a positive integer")
        effective_part_size = part_size

    parts: list[ByteRange] = []
    start = start_offset
    while start < total_size:
        end = min(total_size - 1, start + effective_part_size - 1)
        parts.append(ByteRange(index=len(parts), start=start, end=end))
        start = end + 1
    return tuple(parts)


def _validate_range_plan(
    parts: Sequence[ByteRange],
    *,
    start_offset: int,
    total_size: int,
) -> None:
    expected_start = start_offset
    for expected_index, part in enumerate(parts):
        if part.index != expected_index:
            raise ValueError("range part indices must be contiguous and start at zero")
        if part.start != expected_start:
            raise ValueError("range parts must be contiguous after the prefix")
        if part.end >= total_size:
            raise ValueError("range part exceeds the expected total size")
        expected_start = part.end + 1
    if expected_start != total_size:
        raise ValueError("range plan does not cover the complete source blob")


def _part_files(parts_dir: Path) -> tuple[Path, ...]:
    if not parts_dir.exists():
        return ()
    if not parts_dir.is_dir():
        raise NotADirectoryError(f"parts path is not a directory: {parts_dir}")
    return tuple(sorted(parts_dir.glob("part_*.bin")))


def discover_range_plan(
    parts_dir: Path,
    *,
    start_offset: int,
    total_size: int,
) -> tuple[ByteRange, ...]:
    """Recover and validate a complete range plan from existing filenames."""

    paths = _part_files(parts_dir)
    if not paths:
        if start_offset == total_size:
            return ()
        raise FileNotFoundError(f"no range part filenames found beneath {parts_dir}")

    by_index: dict[int, ByteRange] = {}
    for path in paths:
        part = parse_part_filename(path)
        if part.index in by_index:
            raise ValueError(f"duplicate range part index {part.index}")
        by_index[part.index] = part

    parts = tuple(by_index[index] for index in sorted(by_index))
    _validate_range_plan(
        parts,
        start_offset=start_offset,
        total_size=total_size,
    )
    return parts


def resolve_part_paths(
    parts_dir: Path,
    parts: Sequence[ByteRange],
) -> dict[ByteRange, Path]:
    """Match planned ranges to existing filenames or stable new paths."""

    expected_by_index = {part.index: part for part in parts}
    if len(expected_by_index) != len(parts):
        raise ValueError("range plan contains duplicate indices")

    discovered: dict[int, Path] = {}
    for path in _part_files(parts_dir):
        parsed = parse_part_filename(path)
        expected = expected_by_index.get(parsed.index)
        if expected is None:
            raise ValueError(
                f"unexpected range part index {parsed.index} in {path.name}"
            )
        if parsed != expected:
            raise ValueError(
                f"range boundaries in {path.name} conflict with the active plan"
            )
        if parsed.index in discovered:
            raise ValueError(f"duplicate filenames for range part {parsed.index}")
        discovered[parsed.index] = path

    return {
        part: discovered.get(part.index, parts_dir / part_filename(part))
        for part in parts
    }


def remaining_range(part: ByteRange, part_path: Path) -> ByteRange | None:
    """Return the request range implied by the current on-disk part length."""

    if part_path.exists() and not part_path.is_file():
        raise ValueError(f"range part is not a regular file: {part_path}")
    current_size = part_path.stat().st_size if part_path.exists() else 0
    if current_size > part.size:
        raise ValueError(
            f"range part {part_path} has {current_size} bytes; expected at most "
            f"{part.size}"
        )
    if current_size == part.size:
        return None
    return ByteRange(
        index=part.index,
        start=part.start + current_size,
        end=part.end,
    )


def _response_status(response: object) -> int:
    status = getattr(response, "status", None)
    if status is None:
        getcode = getattr(response, "getcode", None)
        if getcode is None:
            raise ProtocolError("HTTP response has no status code")
        status = getcode()
    try:
        return int(status)
    except (TypeError, ValueError) as error:
        raise ProtocolError(f"invalid HTTP status code: {status!r}") from error


def _validated_response_range(
    response: object,
    requested: ByteRange,
    *,
    total_size: int,
) -> ContentRange:
    status = _response_status(response)
    if status != 206:
        raise ProtocolError(f"expected HTTP 206, received {status}")

    headers = getattr(response, "headers", None)
    if headers is None:
        raise ProtocolError("HTTP response has no headers")
    raw_content_range = headers.get("Content-Range")
    if raw_content_range is None:
        raise ProtocolError("HTTP 206 response omitted Content-Range")
    parsed = parse_content_range(str(raw_content_range))
    if parsed.total_size != total_size:
        raise ProtocolError(
            f"source total size changed: expected {total_size}, "
            f"received {parsed.total_size}"
        )
    if parsed.start != requested.start or parsed.end > requested.end:
        raise ProtocolError(
            "Content-Range does not match the requested resume boundary"
        )

    raw_content_length = headers.get("Content-Length")
    if raw_content_length is not None:
        try:
            content_length = int(raw_content_length)
        except (TypeError, ValueError) as error:
            raise ProtocolError(
                f"invalid Content-Length header: {raw_content_length!r}"
            ) from error
        if content_length != parsed.size:
            raise ProtocolError(
                "Content-Length does not match the declared Content-Range"
            )
    return parsed


def _write_all(handle: BinaryIO, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = handle.write(view)
        if written is None or written <= 0:
            raise OSError("failed to append range response bytes")
        view = view[written:]


def _append_response(
    response: object,
    part_path: Path,
    *,
    response_size: int,
    io_chunk_size: int,
) -> None:
    read = getattr(response, "read", None)
    if read is None:
        raise ProtocolError("HTTP response has no byte stream")

    remaining = response_size
    with part_path.open("ab", buffering=0) as handle:
        while remaining:
            try:
                payload = read(min(io_chunk_size, remaining))
            except http.client.IncompleteRead as error:
                partial = bytes(error.partial)
                if len(partial) > remaining:
                    raise ProtocolError(
                        "HTTP response exceeded its Content-Range"
                    ) from error
                if partial:
                    _write_all(handle, partial)
                    remaining -= len(partial)
                raise RetryableDownloadError(
                    "connection ended before the declared Content-Range"
                ) from error
            except (OSError, http.client.HTTPException) as error:
                raise RetryableDownloadError(
                    "connection failed while reading a range response"
                ) from error

            if not payload:
                raise RetryableDownloadError(
                    "connection ended before the declared Content-Range"
                )
            payload = bytes(payload)
            if len(payload) > remaining:
                raise ProtocolError("HTTP response exceeded its Content-Range")
            _write_all(handle, payload)
            remaining -= len(payload)


def _open_range_response(
    url: str,
    requested: ByteRange,
    *,
    timeout: float,
    user_agent: str,
) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "Range": f"bytes={requested.start}-{requested.end}",
            "User-Agent": user_agent,
        },
        method="GET",
    )
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code in _RETRYABLE_HTTP_CODES:
            raise RetryableDownloadError(
                f"range request received transient HTTP {error.code}"
            ) from error
        raise DownloadError(f"range request failed with HTTP {error.code}") from error
    except (
        urllib.error.URLError,
        TimeoutError,
        ConnectionError,
        http.client.HTTPException,
        OSError,
    ) as error:
        raise RetryableDownloadError("range request connection failed") from error


def _close_response(response: object) -> None:
    close = getattr(response, "close", None)
    if close is not None:
        try:
            close()
        except OSError:
            LOGGER.debug("connection close failed after range response", exc_info=True)


def download_part(
    url: str,
    part: ByteRange,
    part_path: Path,
    *,
    total_size: int,
    timeout: float,
    max_retries: int,
    retry_delay: float,
    io_chunk_size: int,
    user_agent: str,
) -> None:
    """Download one part, resuming from its current file length."""

    no_progress_failures = 0
    while True:
        requested = remaining_range(part, part_path)
        if requested is None:
            return
        size_before = part_path.stat().st_size if part_path.exists() else 0
        response: object | None = None
        try:
            response = _open_range_response(
                url,
                requested,
                timeout=timeout,
                user_agent=user_agent,
            )
            declared = _validated_response_range(
                response,
                requested,
                total_size=total_size,
            )
            _append_response(
                response,
                part_path,
                response_size=declared.size,
                io_chunk_size=io_chunk_size,
            )
            no_progress_failures = 0
        except RetryableDownloadError as error:
            size_after = part_path.stat().st_size if part_path.exists() else 0
            if size_after > size_before:
                no_progress_failures = 0
            else:
                no_progress_failures += 1
                if no_progress_failures > max_retries:
                    raise DownloadError(
                        f"part {part.index} exhausted {max_retries} "
                        "no-progress retries"
                    ) from error
            delay_exponent = min(max(no_progress_failures - 1, 0), 5)
            delay = retry_delay * (2**delay_exponent)
            LOGGER.warning(
                "part %d retained %d/%d bytes after a transient failure; "
                "retrying in %.1fs",
                part.index,
                size_after,
                part.size,
                delay,
            )
            if delay:
                time.sleep(delay)
        finally:
            if response is not None:
                _close_response(response)


def download_ranges(
    url: str,
    parts_dir: Path,
    parts: Sequence[ByteRange],
    *,
    total_size: int,
    workers: int = 4,
    timeout: float = 60.0,
    max_retries: int = 12,
    retry_delay: float = 1.0,
    io_chunk_size: int = 1024 * 1024,
    user_agent: str = "AutoResearch-RangeDownloader/1.0",
) -> dict[ByteRange, Path]:
    """Download all ranges concurrently and return their exact paths."""

    if workers <= 0:
        raise ValueError("workers must be positive")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_retries < 0:
        raise ValueError("max_retries must be nonnegative")
    if retry_delay < 0:
        raise ValueError("retry_delay must be nonnegative")
    if io_chunk_size <= 0:
        raise ValueError("io_chunk_size must be positive")

    parts_dir.mkdir(parents=True, exist_ok=True)
    part_paths = resolve_part_paths(parts_dir, parts)
    if not parts:
        return part_paths

    with ThreadPoolExecutor(
        max_workers=min(workers, len(parts)),
        thread_name_prefix="range-download",
    ) as executor:
        futures = {
            executor.submit(
                download_part,
                url,
                part,
                part_paths[part],
                total_size=total_size,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
                io_chunk_size=io_chunk_size,
                user_agent=user_agent,
            ): part
            for part in parts
        }
        for future in as_completed(futures):
            part = futures[future]
            future.result()
            LOGGER.info("part %d complete (%d bytes)", part.index, part.size)
    return part_paths


def _copy_exact(
    source_path: Path,
    output: BinaryIO,
    digest: object,
    *,
    expected_size: int,
    io_chunk_size: int,
) -> int:
    if not source_path.is_file():
        raise FileNotFoundError(f"assembly input is missing: {source_path}")
    actual_size = source_path.stat().st_size
    if actual_size != expected_size:
        raise ValueError(
            f"assembly input {source_path} has {actual_size} bytes; "
            f"expected {expected_size}"
        )

    copied = 0
    with source_path.open("rb") as source:
        while copied < expected_size:
            payload = source.read(min(io_chunk_size, expected_size - copied))
            if not payload:
                raise ValueError(f"assembly input was truncated: {source_path}")
            _write_all(output, payload)
            digest.update(payload)
            copied += len(payload)
        if source.read(1):
            raise ValueError(f"assembly input grew while reading: {source_path}")
    return copied


def _normalized_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise ValueError("expected_sha256 must contain exactly 64 hex digits")
    return normalized


def assemble_blob(
    prefix_path: Path | None,
    parts: Sequence[ByteRange],
    part_paths: Mapping[ByteRange, Path],
    output_path: Path,
    *,
    total_size: int,
    expected_sha256: str,
    io_chunk_size: int = 1024 * 1024,
) -> str:
    """Assemble prefix plus ordered parts into a new size/hash-verified file."""

    expected_hash = _normalized_sha256(expected_sha256)
    if io_chunk_size <= 0:
        raise ValueError("io_chunk_size must be positive")
    if os.path.lexists(output_path):
        raise FileExistsError(f"refusing to overwrite output: {output_path}")

    if prefix_path is None:
        prefix_size = 0
    else:
        if not prefix_path.is_file():
            raise FileNotFoundError(f"prefix is missing: {prefix_path}")
        prefix_size = prefix_path.stat().st_size
    _validate_range_plan(
        parts,
        start_offset=prefix_size,
        total_size=total_size,
    )
    if set(part_paths) != set(parts):
        raise ValueError("part path mapping does not exactly match the range plan")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    written = 0
    created = False
    try:
        with output_path.open("xb", buffering=0) as output:
            created = True
            if prefix_path is not None:
                written += _copy_exact(
                    prefix_path,
                    output,
                    digest,
                    expected_size=prefix_size,
                    io_chunk_size=io_chunk_size,
                )
            for part in parts:
                written += _copy_exact(
                    part_paths[part],
                    output,
                    digest,
                    expected_size=part.size,
                    io_chunk_size=io_chunk_size,
                )
        if written != total_size:
            raise ValueError(
                f"assembled size mismatch: expected {total_size}, got {written}"
            )
        actual_hash = digest.hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                f"assembled SHA256 mismatch: expected {expected_hash}, "
                f"got {actual_hash}"
            )
    except BaseException:
        if created:
            output_path.unlink(missing_ok=True)
        raise
    return expected_hash


def download_blob(
    url: str,
    output_path: Path,
    *,
    parts_dir: Path,
    total_size: int,
    expected_sha256: str,
    prefix_path: Path | None = None,
    part_size: int | None = None,
    part_count: int | None = None,
    workers: int = 4,
    timeout: float = 60.0,
    max_retries: int = 12,
    retry_delay: float = 1.0,
    io_chunk_size: int = 1024 * 1024,
    user_agent: str = "AutoResearch-RangeDownloader/1.0",
) -> str:
    """Resume, download, assemble, and verify one HTTP source blob."""

    if os.path.lexists(output_path):
        raise FileExistsError(f"refusing to overwrite output: {output_path}")
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("url must use HTTP or HTTPS")
    _normalized_sha256(expected_sha256)
    if isinstance(total_size, bool) or total_size < 0:
        raise ValueError("total_size must be a nonnegative integer")

    if prefix_path is None:
        prefix_size = 0
    else:
        if not prefix_path.is_file():
            raise FileNotFoundError(f"prefix is missing: {prefix_path}")
        prefix_size = prefix_path.stat().st_size
    if prefix_size > total_size:
        raise ValueError("prefix is larger than the expected source blob")

    if part_size is None and part_count is None:
        parts = discover_range_plan(
            parts_dir,
            start_offset=prefix_size,
            total_size=total_size,
        )
    else:
        parts = plan_ranges(
            total_size,
            start_offset=prefix_size,
            part_size=part_size,
            part_count=part_count,
        )
    _validate_range_plan(
        parts,
        start_offset=prefix_size,
        total_size=total_size,
    )

    output_identity = output_path.resolve(strict=False)
    if output_identity == parts_dir.resolve(strict=False):
        raise ValueError("output path must not be the parts directory")
    if prefix_path is not None and output_identity == prefix_path.resolve():
        raise ValueError("output path must not overwrite the prefix")
    planned_paths = resolve_part_paths(parts_dir, parts)
    if output_identity in {
        path.resolve(strict=False) for path in planned_paths.values()
    }:
        raise ValueError("output path must not overwrite a range part")

    part_paths = download_ranges(
        url,
        parts_dir,
        parts,
        total_size=total_size,
        workers=workers,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        io_chunk_size=io_chunk_size,
        user_agent=user_agent,
    )
    return assemble_blob(
        prefix_path,
        parts,
        part_paths,
        output_path,
        total_size=total_size,
        expected_sha256=expected_sha256,
        io_chunk_size=io_chunk_size,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--prefix", type=Path)
    parser.add_argument("--parts-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--total-size", type=int, required=True)
    parser.add_argument(
        "--expected-sha256",
        "--sha256",
        dest="expected_sha256",
        required=True,
    )
    plan_group = parser.add_mutually_exclusive_group()
    plan_group.add_argument("--part-size", type=int)
    plan_group.add_argument("--part-count", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-retries", type=int, default=12)
    parser.add_argument("--retry-delay", type=float, default=1.0)
    parser.add_argument("--io-chunk-size", type=int, default=1024 * 1024)
    parser.add_argument(
        "--user-agent",
        default="AutoResearch-RangeDownloader/1.0",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    digest = download_blob(
        args.url,
        args.output,
        parts_dir=args.parts_dir,
        total_size=args.total_size,
        expected_sha256=args.expected_sha256,
        prefix_path=args.prefix,
        part_size=args.part_size,
        part_count=args.part_count,
        workers=args.workers,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        io_chunk_size=args.io_chunk_size,
        user_agent=args.user_agent,
    )
    LOGGER.info("verified output %s (sha256=%s)", args.output, digest)


if __name__ == "__main__":
    main()
