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
    }
)
ALLOWED_SOURCE_KINDS = frozenset({"image", "candidate", "caption_content"})
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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
        source_sha256 = str(column.get("source_file_sha256", "")).strip().lower()
        if _SHA256_PATTERN.fullmatch(source_sha256) is None:
            raise ValueError(f"feature {name!r} has invalid source_file_sha256")

        seen_names.add(normalized_name)
        normalized_columns.append(
            {
                "name": name,
                "source_fields": [str(value) for value in source_fields],
                "source_kind": source_kind,
                "source_function": source_function,
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
