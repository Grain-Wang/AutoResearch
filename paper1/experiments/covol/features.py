"""Feature-schema provenance and intervention-metadata leakage checks."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

INTERVENTION_METADATA_DENYLIST = frozenset(
    {
        "error_type",
        "template_id",
        "generator",
        "generator_revision",
        "variant_id",
        "machine_check",
        "source_caption_hash",
        "split",
        "ground_truth",
        "depth_gt",
        "target",
        "label",
        "advantage",
        "a_p",
        "d0_loss",
        "d1_loss",
        "oracle",
        "test_metric",
    }
)
ALLOWED_SOURCE_KINDS = frozenset({"image", "candidate", "caption_content"})
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _normalize_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _matches_denied_name(value: object) -> str | None:
    normalized = _normalize_name(value)
    for denied in INTERVENTION_METADATA_DENYLIST:
        if (
            normalized == denied
            or normalized.startswith(f"{denied}_")
            or normalized.endswith(f"_{denied}")
            or f"_{denied}_" in normalized
        ):
            return denied
    return None


def validate_feature_schema(
    columns: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Validate feature names, source fields, and immutable provenance."""

    normalized_columns: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for index, column in enumerate(columns):
        name = str(column.get("name", "")).strip()
        if not name:
            raise ValueError(f"column {index} has no name")
        normalized_name = _normalize_name(name)
        if normalized_name in seen_names:
            raise ValueError(f"duplicate feature name: {name}")
        denied = _matches_denied_name(name)
        if denied is not None:
            raise ValueError(f"feature {name!r} exposes denied metadata {denied!r}")

        source_fields = column.get("source_fields")
        if not isinstance(source_fields, list) or not source_fields:
            raise ValueError(f"feature {name!r} must list source_fields")
        for source_field in source_fields:
            denied = _matches_denied_name(source_field)
            if denied is not None:
                raise ValueError(
                    f"feature {name!r} derives from denied metadata {denied!r}"
                )

        source_kind = str(column.get("source_kind", "")).strip()
        if source_kind not in ALLOWED_SOURCE_KINDS:
            raise ValueError(
                f"feature {name!r} has invalid source_kind {source_kind!r}"
            )
        source_function = str(column.get("source_function", "")).strip()
        if not source_function:
            raise ValueError(f"feature {name!r} has no source_function")
        source_path = Path(str(column.get("source_file_path", "")).strip())
        if not str(source_path) or source_path.is_absolute():
            raise ValueError(
                f"feature {name!r} must use a repository-relative source_file_path"
            )
        resolved_source_path = (REPOSITORY_ROOT / source_path).resolve(strict=True)
        try:
            portable_source_path = resolved_source_path.relative_to(REPOSITORY_ROOT)
        except ValueError as error:
            raise ValueError(
                f"feature {name!r} source_file_path escapes the repository"
            ) from error
        if not resolved_source_path.is_file():
            raise ValueError(f"feature {name!r} source_file_path is not a file")
        digest = hashlib.sha256()
        with resolved_source_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        source_sha256 = digest.hexdigest()
        declared_sha256 = column.get("source_file_sha256")
        if declared_sha256 is not None and str(declared_sha256).strip().lower() != (
            source_sha256
        ):
            raise ValueError(
                f"feature {name!r} source_file_sha256 does not match the local file"
            )

        seen_names.add(normalized_name)
        normalized_columns.append(
            {
                "name": name,
                "source_fields": [str(value) for value in source_fields],
                "source_kind": source_kind,
                "source_function": source_function,
                "source_file_path": portable_source_path.as_posix(),
                "source_file_sha256": source_sha256,
            }
        )

    if not normalized_columns:
        raise ValueError("feature schema must not be empty")
    return normalized_columns


def feature_schema_payload(
    columns: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return a canonical, hash-addressed feature-schema payload."""

    validated = validate_feature_schema(columns)
    hash_input = {
        "version": 1,
        "denylist": sorted(INTERVENTION_METADATA_DENYLIST),
        "columns": validated,
    }
    encoded = json.dumps(
        hash_input,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **hash_input,
        "schema_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def write_feature_schema(
    columns: Iterable[Mapping[str, Any]],
    output_path: Path,
) -> None:
    """Validate and write a canonical feature schema."""

    payload = feature_schema_payload(columns)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
