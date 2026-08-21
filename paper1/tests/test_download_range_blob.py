from __future__ import annotations

import hashlib
import http.client
from pathlib import Path

import pytest
from paper1.experiments.covol import download_range_blob as downloader


def test_range_plan_uses_prefix_and_covers_total_without_gaps() -> None:
    parts = downloader.plan_ranges(
        25,
        start_offset=5,
        part_count=3,
    )

    assert parts == (
        downloader.ByteRange(index=0, start=5, end=11),
        downloader.ByteRange(index=1, start=12, end=18),
        downloader.ByteRange(index=2, start=19, end=24),
    )
    assert downloader.part_filename(parts[0]) == "part_00_5_11.bin"


def test_range_parsers_validate_filename_and_content_range() -> None:
    assert downloader.parse_part_filename(
        "part_07_1606130182_1757897696.bin"
    ) == downloader.ByteRange(
        index=7,
        start=1_606_130_182,
        end=1_757_897_696,
    )
    assert downloader.parse_content_range("bytes 10-19/100") == downloader.ContentRange(
        start=10, end=19, total_size=100
    )

    with pytest.raises(ValueError, match="invalid range part filename"):
        downloader.parse_part_filename("part_7_10_19.tmp")
    with pytest.raises(downloader.ProtocolError, match="outside"):
        downloader.parse_content_range("bytes 90-100/100")


def test_discovered_plan_and_partial_file_length_determine_resume_range(
    tmp_path: Path,
) -> None:
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    first_path = parts_dir / "part_00_5_11.bin"
    first_path.write_bytes(b"abc")
    (parts_dir / "part_01_12_18.bin").write_bytes(b"")
    (parts_dir / "part_02_19_24.bin").write_bytes(b"")

    parts = downloader.discover_range_plan(
        parts_dir,
        start_offset=5,
        total_size=25,
    )

    assert downloader.remaining_range(parts[0], first_path) == downloader.ByteRange(
        index=0,
        start=8,
        end=11,
    )
    first_path.write_bytes(b"1234567")
    assert downloader.remaining_range(parts[0], first_path) is None
    first_path.write_bytes(b"12345678")
    with pytest.raises(ValueError, match="expected at most 7"):
        downloader.remaining_range(parts[0], first_path)


def test_protocol_validation_rejects_status_and_total_size_mismatch() -> None:
    class Response:
        status = 206
        headers = {
            "Content-Range": "bytes 5-9/11",
            "Content-Length": "5",
        }

    requested = downloader.ByteRange(index=0, start=5, end=9)
    with pytest.raises(downloader.ProtocolError, match="total size changed"):
        downloader._validated_response_range(
            Response(),
            requested,
            total_size=10,
        )

    Response.status = 200
    with pytest.raises(downloader.ProtocolError, match="expected HTTP 206"):
        downloader._validated_response_range(
            Response(),
            requested,
            total_size=11,
        )


def test_connection_failure_preserves_partial_bytes_and_resumes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        status = 206

        def __init__(
            self,
            content_range: str,
            content_length: int,
            reads: list[bytes | BaseException],
        ) -> None:
            self.headers = {
                "Content-Range": content_range,
                "Content-Length": str(content_length),
            }
            self.reads = reads
            self.closed = False

        def read(self, size: int) -> bytes:
            del size
            item = self.reads.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item

        def close(self) -> None:
            self.closed = True

    responses = [
        Response(
            "bytes 5-9/10",
            5,
            [b"ab", http.client.IncompleteRead(b"c", 2)],
        ),
        Response("bytes 8-9/10", 2, [b"de"]),
    ]
    requested_ranges: list[tuple[int, int]] = []

    def open_response(
        url: str,
        requested: downloader.ByteRange,
        *,
        timeout: float,
        user_agent: str,
    ) -> object:
        del url, timeout, user_agent
        requested_ranges.append((requested.start, requested.end))
        return responses.pop(0)

    monkeypatch.setattr(downloader, "_open_range_response", open_response)
    part = downloader.ByteRange(index=0, start=5, end=9)
    part_path = tmp_path / downloader.part_filename(part)

    downloader.download_part(
        "https://example.invalid/blob",
        part,
        part_path,
        total_size=10,
        timeout=1.0,
        max_retries=1,
        retry_delay=0.0,
        io_chunk_size=8,
        user_agent="offline-test",
    )

    assert part_path.read_bytes() == b"abcde"
    assert requested_ranges == [(5, 9), (8, 9)]
    assert responses == []


def test_assembly_checks_size_hash_and_never_overwrites(tmp_path: Path) -> None:
    prefix = tmp_path / "prefix.bin"
    prefix.write_bytes(b"prefix")
    parts = downloader.plan_ranges(15, start_offset=6, part_size=5)
    part_paths = {
        parts[0]: tmp_path / downloader.part_filename(parts[0]),
        parts[1]: tmp_path / downloader.part_filename(parts[1]),
    }
    part_paths[parts[0]].write_bytes(b"-part")
    part_paths[parts[1]].write_bytes(b"-end")
    expected = b"prefix-part-end"
    expected_hash = hashlib.sha256(expected).hexdigest()
    output = tmp_path / "source.bin"

    assert (
        downloader.assemble_blob(
            prefix,
            parts,
            part_paths,
            output,
            total_size=len(expected),
            expected_sha256=expected_hash,
        )
        == expected_hash
    )
    assert output.read_bytes() == expected
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        downloader.assemble_blob(
            prefix,
            parts,
            part_paths,
            output,
            total_size=len(expected),
            expected_sha256=expected_hash,
        )

    bad_output = tmp_path / "bad-source.bin"
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        downloader.assemble_blob(
            prefix,
            parts,
            part_paths,
            bad_output,
            total_size=len(expected),
            expected_sha256="0" * 64,
        )
    assert not bad_output.exists()
