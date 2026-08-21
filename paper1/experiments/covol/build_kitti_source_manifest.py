"""Adapt common KITTI split lists to the leakage-auditable source schema."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

DATASET_NAME = "KITTI"
ADAPTER_VERSION = "kitti-source-v1"
ANONYMOUS_BENCHMARK_SEQUENCE = "official_depth_benchmark_test_anonymous"
SIDE_TO_CAMERA = {
    "2": "image_02",
    "3": "image_03",
    "l": "image_02",
    "left": "image_02",
    "r": "image_03",
    "right": "image_03",
}
IMAGE_EXTENSIONS = ("png", "jpg", "jpeg")

_DRIVE_PATTERN = r"(?P<drive>\d{4}_\d{2}_\d{2}_drive_\d{4}_sync)"
_DRIVE_RE = re.compile(rf"^{_DRIVE_PATTERN}$")
_DATE_RE = re.compile(r"^\d{4}_\d{2}_\d{2}$")
_RAW_RGB_PATH_RE = re.compile(
    rf"(?:^|/){_DRIVE_PATTERN}/(?P<camera>image_0[23])/data/"
    r"(?P<frame>\d{10})\.(?:png|jpe?g)$",
    re.IGNORECASE,
)
_SELECTION_FILENAME_RE = re.compile(
    rf"^{_DRIVE_PATTERN}_(?:[a-z0-9]+_)*?"
    r"(?P<frame>\d{10})_(?P<camera>image_0[23])\.(?:png|jpe?g)$",
    re.IGNORECASE,
)
_ANONYMOUS_RGB_PATH_RE = re.compile(
    r"(?:^|/)(?:test_depth_prediction_anonymous/)?image/"
    r"(?P<frame>\d{10})\.(?:png|jpe?g)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _KittiImageReference:
    rgb_path: Path
    scene_id: str
    sequence_id: str
    camera_id: str
    frame_index: int
    frame_index_semantics: str
    identity_resolution: str
    source_split_format: str

    @property
    def image_id(self) -> str:
        """Return an encoding-independent identity for the physical capture."""

        return f"{self.sequence_id}/{self.camera_id}/{self.frame_index:010d}"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_parts(value: str) -> tuple[str, ...]:
    normalized = value.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or not path.parts
        or path.is_absolute()
        or re.match(r"^[a-zA-Z]:/", normalized)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"expected a safe relative path, got {value!r}")
    return path.parts


def _canonical_drive(folder: str) -> tuple[str, tuple[str, ...]]:
    parts = _relative_parts(folder)
    drive = parts[-1]
    match = _DRIVE_RE.fullmatch(drive)
    if match is None:
        raise ValueError(f"invalid KITTI drive {folder!r}")

    date = drive[:10]
    if len(parts) >= 2 and _DATE_RE.fullmatch(parts[-2]) and parts[-2] != date:
        raise ValueError(
            f"KITTI drive date {date!r} conflicts with parent {parts[-2]!r}"
        )
    return f"{date}/{drive}", parts


def _extension_order(image_extension: str) -> tuple[str, ...]:
    normalized = image_extension.lower().lstrip(".")
    if normalized == "auto":
        return IMAGE_EXTENSIONS
    if normalized not in IMAGE_EXTENSIONS:
        raise ValueError("image_extension must be one of auto, png, jpg, or jpeg")
    return (normalized,)


def _select_existing_path(candidates: list[Path], *, description: str) -> Path:
    unique_candidates = list(dict.fromkeys(candidates))
    existing = [candidate for candidate in unique_candidates if candidate.is_file()]
    if not existing:
        rendered = ", ".join(path.as_posix() for path in unique_candidates[:8])
        raise FileNotFoundError(f"{description}: no RGB file found; tried {rendered}")
    if len(existing) > 1:
        rendered = ", ".join(path.as_posix() for path in existing)
        raise ValueError(f"{description}: ambiguous RGB files: {rendered}")
    return existing[0]


def _raw_tuple_reference(
    data_root: Path,
    *,
    folder: str,
    frame_token: str,
    side_token: str,
    image_extension: str,
) -> _KittiImageReference:
    sequence_id, folder_parts = _canonical_drive(folder)
    try:
        frame_index = int(frame_token)
    except ValueError as error:
        raise ValueError(f"invalid KITTI frame index {frame_token!r}") from error
    if frame_index < 0:
        raise ValueError(f"invalid KITTI frame index {frame_token!r}")

    camera_id = SIDE_TO_CAMERA.get(side_token.lower())
    if camera_id is None:
        raise ValueError(f"invalid KITTI camera side {side_token!r}")

    date, drive = sequence_id.split("/", maxsplit=1)
    base_parts = [
        folder_parts,
        (date, drive),
        (drive,),
        ("raw", date, drive),
        ("raw_data", date, drive),
        ("data_raw", date, drive),
    ]
    candidates = [
        data_root.joinpath(*base, camera_id, "data", f"{frame_index:010d}.{ext}")
        for base in base_parts
        for ext in _extension_order(image_extension)
    ]
    rgb_path = _select_existing_path(
        candidates,
        description=f"{sequence_id} {frame_index} {camera_id}",
    )
    return _KittiImageReference(
        rgb_path=rgb_path,
        scene_id=sequence_id,
        sequence_id=sequence_id,
        camera_id=camera_id,
        frame_index=frame_index,
        frame_index_semantics="raw_drive_frame",
        identity_resolution="raw_drive_camera_frame",
        source_split_format="eigen_drive_frame_side",
    )


def _anonymous_benchmark_reference(
    data_root: Path,
    *,
    frame_token: str,
    image_extension: str,
) -> _KittiImageReference:
    try:
        benchmark_index = int(frame_token)
    except ValueError as error:
        raise ValueError(
            f"invalid anonymous benchmark index {frame_token!r}"
        ) from error
    if benchmark_index < 0:
        raise ValueError(f"invalid anonymous benchmark index {frame_token!r}")

    directory_options = (
        ("test_depth_prediction_anonymous", "image"),
        ("depth_selection", "test_depth_prediction_anonymous", "image"),
        ("data_depth_selection", "test_depth_prediction_anonymous", "image"),
        ("image",),
    )
    candidates = [
        data_root.joinpath(*directory, f"{benchmark_index:010d}.{ext}")
        for directory in directory_options
        for ext in _extension_order(image_extension)
    ]
    rgb_path = _select_existing_path(
        candidates,
        description=f"anonymous KITTI benchmark image {benchmark_index}",
    )
    return _KittiImageReference(
        rgb_path=rgb_path,
        scene_id=ANONYMOUS_BENCHMARK_SEQUENCE,
        sequence_id=ANONYMOUS_BENCHMARK_SEQUENCE,
        camera_id="anonymous_camera",
        frame_index=benchmark_index,
        frame_index_semantics="anonymous_benchmark_index",
        identity_resolution="anonymous_index_rgb_hash_only",
        source_split_format="official_anonymous_index",
    )


def _reference_from_rgb_path(
    data_root: Path,
    *,
    path_token: str,
) -> _KittiImageReference:
    path_parts = _relative_parts(path_token)
    rgb_path = data_root.joinpath(*path_parts)
    if not rgb_path.is_file():
        raise FileNotFoundError(f"RGB file does not exist: {rgb_path}")
    relative_path = PurePosixPath(*path_parts).as_posix()

    raw_match = _RAW_RGB_PATH_RE.search(relative_path)
    if raw_match is not None:
        drive = raw_match.group("drive")
        sequence_id = f"{drive[:10]}/{drive}"
        return _KittiImageReference(
            rgb_path=rgb_path,
            scene_id=sequence_id,
            sequence_id=sequence_id,
            camera_id=raw_match.group("camera").lower(),
            frame_index=int(raw_match.group("frame")),
            frame_index_semantics="raw_drive_frame",
            identity_resolution="raw_drive_camera_frame",
            source_split_format="direct_raw_rgb_path",
        )

    filename_match = _SELECTION_FILENAME_RE.fullmatch(path_parts[-1])
    if (
        filename_match is not None
        and len(path_parts) >= 2
        and path_parts[-2].lower() == "image"
    ):
        drive = filename_match.group("drive")
        sequence_id = f"{drive[:10]}/{drive}"
        return _KittiImageReference(
            rgb_path=rgb_path,
            scene_id=sequence_id,
            sequence_id=sequence_id,
            camera_id=filename_match.group("camera").lower(),
            frame_index=int(filename_match.group("frame")),
            frame_index_semantics="raw_drive_frame",
            identity_resolution="raw_drive_camera_frame",
            source_split_format="official_selection_rgb_path",
        )

    anonymous_match = _ANONYMOUS_RGB_PATH_RE.search(relative_path)
    if anonymous_match is not None:
        return _KittiImageReference(
            rgb_path=rgb_path,
            scene_id=ANONYMOUS_BENCHMARK_SEQUENCE,
            sequence_id=ANONYMOUS_BENCHMARK_SEQUENCE,
            camera_id="anonymous_camera",
            frame_index=int(anonymous_match.group("frame")),
            frame_index_semantics="anonymous_benchmark_index",
            identity_resolution="anonymous_index_rgb_hash_only",
            source_split_format="official_anonymous_rgb_path",
        )

    raise ValueError(
        "cannot derive KITTI drive/camera/frame identity from RGB path "
        f"{path_token!r}"
    )


def _parse_split_line(
    line: str,
    *,
    data_root: Path,
    official_split: str,
    image_extension: str,
) -> _KittiImageReference:
    tokens = line.split()
    if len(tokens) >= 3 and _DRIVE_RE.fullmatch(
        PurePosixPath(tokens[0].replace("\\", "/")).name
    ):
        return _raw_tuple_reference(
            data_root,
            folder=tokens[0],
            frame_token=tokens[1],
            side_token=tokens[2],
            image_extension=image_extension,
        )
    if len(tokens) == 2 and tokens[0].lower() == "image":
        if official_split != "test":
            raise ValueError(
                "anonymous KITTI benchmark indices are only valid for "
                "official_split=test"
            )
        return _anonymous_benchmark_reference(
            data_root,
            frame_token=tokens[1],
            image_extension=image_extension,
        )
    if tokens:
        reference = _reference_from_rgb_path(data_root, path_token=tokens[0])
        if (
            reference.frame_index_semantics == "anonymous_benchmark_index"
            and official_split != "test"
        ):
            raise ValueError(
                "anonymous KITTI benchmark RGBs are only valid for official_split=test"
            )
        return reference
    raise ValueError("empty KITTI split line")


def _selection_provenance(
    audit_path: Path,
    *,
    selected_split_sha256: str,
) -> dict[str, object]:
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("KITTI selection audit must be a JSON object")
    canonical_hash = str(
        payload.get("input", {}).get("canonical_training_split_sha256", "")
    ).lower()
    revision = str(payload.get("repository_revision", "")).lower()
    if (
        payload.get("status") != "PASS_PREFREEZE_NO_TEST_ACCESS"
        or str(payload.get("selected_split_sha256", "")).lower()
        != selected_split_sha256
        or len(canonical_hash) != 64
        or any(char not in "0123456789abcdef" for char in canonical_hash)
        or re.fullmatch(r"[0-9a-f]{40}", revision) is None
    ):
        raise ValueError("KITTI selection audit provenance is invalid")
    return {
        "canonical_training_split_sha256": canonical_hash,
        "repository_id": str(payload.get("repository_id", "")),
        "repository_revision": revision,
        "selection_audit_sha256": _file_sha256(audit_path),
        "selection_record_count": int(payload.get("record_count", -1)),
    }


def build_kitti_source_manifest(
    data_root: Path,
    split_list_path: Path,
    output_path: Path,
    *,
    official_split: str,
    image_extension: str = "auto",
    allow_official_test_read: bool = False,
    selection_audit_path: Path | None = None,
) -> list[dict[str, object]]:
    """Build a unified source JSONL from a KITTI split list and local RGB files."""

    if official_split not in {"train", "test"}:
        raise ValueError("official_split must be train or test")
    if official_split == "test" and not allow_official_test_read:
        raise PermissionError(
            "official KITTI test reads are frozen until Step 008; pass "
            "allow_official_test_read=True only after the method is frozen"
        )
    _extension_order(image_extension)
    data_root = data_root.resolve()
    split_list_path = split_list_path.resolve()
    output_path = output_path.resolve()
    if not data_root.is_dir():
        raise NotADirectoryError(f"KITTI data root does not exist: {data_root}")
    if not split_list_path.is_file():
        raise FileNotFoundError(f"KITTI split list does not exist: {split_list_path}")
    if output_path == split_list_path:
        raise ValueError("output path must not overwrite the KITTI split list")

    split_list_sha256 = _file_sha256(split_list_path)
    provenance = (
        _selection_provenance(
            selection_audit_path.resolve(),
            selected_split_sha256=split_list_sha256,
        )
        if selection_audit_path is not None
        else None
    )
    records: list[dict[str, object]] = []
    seen_images: dict[str, int] = {}
    seen_rgb_hashes: dict[str, int] = {}
    with split_list_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.partition("#")[0].strip()
            if not line:
                continue
            try:
                reference = _parse_split_line(
                    line,
                    data_root=data_root,
                    official_split=official_split,
                    image_extension=image_extension,
                )
            except (FileNotFoundError, ValueError) as error:
                raise type(error)(
                    f"{split_list_path}:{line_number}: {error}"
                ) from error

            image_id = reference.image_id
            if output_path == reference.rgb_path.resolve():
                raise ValueError(
                    f"{split_list_path}:{line_number}: output path must not "
                    "overwrite a source RGB"
                )
            if image_id in seen_images:
                raise ValueError(
                    f"{split_list_path}:{line_number}: duplicate canonical image_id "
                    f"{image_id!r}; first seen on line {seen_images[image_id]}"
                )
            rgb_sha256 = _file_sha256(reference.rgb_path)
            if rgb_sha256 in seen_rgb_hashes:
                raise ValueError(
                    f"{split_list_path}:{line_number}: duplicate RGB content hash "
                    f"{rgb_sha256!r}; first seen on line "
                    f"{seen_rgb_hashes[rgb_sha256]}"
                )
            seen_images[image_id] = line_number
            seen_rgb_hashes[rgb_sha256] = line_number

            records.append(
                {
                    "adapter": ADAPTER_VERSION,
                    "annotation_available": False,
                    "annotation_sha256": None,
                    "annotation_source": None,
                    "annotation_status": "instance_masks_unavailable",
                    "camera_id": reference.camera_id,
                    "dataset": DATASET_NAME,
                    "depth_available": False,
                    "depth_sha256": None,
                    "depth_source": None,
                    "entities": [],
                    "frame_index": reference.frame_index,
                    "frame_index_semantics": reference.frame_index_semantics,
                    "identity_resolution": reference.identity_resolution,
                    "image_id": image_id,
                    "official_split": official_split,
                    "rgb_path": reference.rgb_path.relative_to(data_root).as_posix(),
                    "rgb_sha256": rgb_sha256,
                    "scene_id": reference.scene_id,
                    "sequence_id": reference.sequence_id,
                    "source_split_format": reference.source_split_format,
                    "source_split_list_sha256": split_list_sha256,
                    **(
                        {
                            "canonical_split_source_sha256": provenance[
                                "canonical_training_split_sha256"
                            ],
                            "selection_audit_sha256": provenance[
                                "selection_audit_sha256"
                            ],
                            "source_repository_id": provenance["repository_id"],
                            "source_repository_revision": provenance[
                                "repository_revision"
                            ],
                        }
                        if provenance is not None
                        else {}
                    ),
                }
            )

    if not records:
        raise ValueError(f"KITTI split list contains no records: {split_list_path}")
    if provenance is not None and len(records) != provenance["selection_record_count"]:
        raise ValueError("KITTI selection audit record_count does not match split list")

    records.sort(key=lambda record: str(record["image_id"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split-list", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--official-split",
        choices=("train", "test"),
        required=True,
    )
    parser.add_argument(
        "--image-extension",
        choices=("auto", *IMAGE_EXTENSIONS),
        default="auto",
        help="extension for drive/frame split rows; auto requires one unique match",
    )
    parser.add_argument(
        "--allow-official-test-read",
        action="store_true",
        help="explicitly unlock official-test RGB reads after the Step 008 freeze",
    )
    parser.add_argument(
        "--selection-audit",
        type=Path,
        help="Step-003 subset audit that links a reduced list to its canonical split",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    build_kitti_source_manifest(
        args.data_root,
        args.split_list,
        args.output,
        official_split=args.official_split,
        image_extension=args.image_extension,
        allow_official_test_read=args.allow_official_test_read,
        selection_audit_path=args.selection_audit,
    )


if __name__ == "__main__":
    main()
