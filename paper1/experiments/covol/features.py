"""Feature-schema provenance and intervention-metadata leakage checks."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
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
ALLOWED_SOURCE_FUNCTIONS = {
    "paper1.experiments.covol.features.candidate_features": {
        "source_kind": "candidate",
        "source_fields": frozenset(
            {
                "d0_depth",
                "d1_depth",
                "d0_uncertainty",
                "d1_uncertainty",
                "candidate_residual",
            }
        ),
    },
    "paper1.experiments.covol.features.caption_region_features": {
        "source_kind": "caption_content",
        "source_fields": frozenset(
            {"raw_caption", "caption_embedding", "region_embedding", "region_mask"}
        ),
    },
    "paper1.experiments.covol.features.image_features": {
        "source_kind": "image",
        "source_fields": frozenset({"rgb", "image_embedding", "image_statistics"}),
    },
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _require_registered_inputs(
    inputs: Mapping[str, Any],
    *,
    source_function: str,
) -> None:
    contract = ALLOWED_SOURCE_FUNCTIONS[source_function]
    unexpected = sorted(set(inputs) - set(contract["source_fields"]))
    if unexpected:
        raise ValueError(
            f"extractor received fields outside its allowlist: {unexpected}"
        )


def _numeric_values(value: Any, *, name: str) -> list[float]:
    if isinstance(value, bool):
        return [float(value)]
    if isinstance(value, (int, float)):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(f"{name} contains a non-finite value")
        return [numeric]
    if isinstance(value, Mapping):
        values: list[float] = []
        for key in sorted(value, key=str):
            values.extend(_numeric_values(value[key], name=f"{name}.{key}"))
        return values
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values = []
        for index, item in enumerate(value):
            values.extend(_numeric_values(item, name=f"{name}[{index}]"))
        return values
    if hasattr(value, "tolist"):
        return _numeric_values(value.tolist(), name=name)
    raise ValueError(f"{name} must contain only numeric values")


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("numeric feature source must not be empty")
    return sum(values) / len(values)


def _norm(values: Sequence[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def candidate_features(inputs: Mapping[str, Any]) -> dict[str, float]:
    """Extract deterministic candidate-only depth and uncertainty summaries."""

    function = "paper1.experiments.covol.features.candidate_features"
    _require_registered_inputs(inputs, source_function=function)
    features: dict[str, float] = {}
    flattened: dict[str, list[float]] = {}
    for field in sorted(inputs):
        values = _numeric_values(inputs[field], name=field)
        flattened[field] = values
        features[f"{field}_mean"] = _mean(values)
        features[f"{field}_l1_mean"] = _mean([abs(value) for value in values])
    if "d0_depth" in flattened and "d1_depth" in flattened:
        d0 = flattened["d0_depth"]
        d1 = flattened["d1_depth"]
        if len(d0) != len(d1):
            raise ValueError("d0_depth and d1_depth must have identical shapes")
        features["candidate_depth_disagreement_l1"] = _mean(
            [abs(left - right) for left, right in zip(d0, d1, strict=True)]
        )
    return features


def caption_region_features(inputs: Mapping[str, Any]) -> dict[str, float]:
    """Extract caption-content and region-alignment summaries without metadata."""

    function = "paper1.experiments.covol.features.caption_region_features"
    _require_registered_inputs(inputs, source_function=function)
    features: dict[str, float] = {}
    caption = inputs.get("raw_caption")
    if caption is not None:
        if not isinstance(caption, str):
            raise ValueError("raw_caption must be a string")
        features["caption_token_count"] = float(len(caption.split()))
        features["caption_character_count"] = float(len(caption))
    embeddings: dict[str, list[float]] = {}
    for field in ("caption_embedding", "region_embedding"):
        if field in inputs:
            values = _numeric_values(inputs[field], name=field)
            embeddings[field] = values
            features[f"{field}_norm"] = _norm(values)
    if len(embeddings) == 2:
        left = embeddings["caption_embedding"]
        right = embeddings["region_embedding"]
        if len(left) != len(right):
            raise ValueError("caption and region embeddings must have equal length")
        denominator = _norm(left) * _norm(right)
        features["caption_region_cosine"] = (
            sum(a * b for a, b in zip(left, right, strict=True)) / denominator
            if denominator > 0.0
            else 0.0
        )
    if "region_mask" in inputs:
        mask = _numeric_values(inputs["region_mask"], name="region_mask")
        if any(value < 0.0 or value > 1.0 for value in mask):
            raise ValueError("region_mask values must be in [0, 1]")
        features["region_mask_coverage"] = _mean(mask)
    return features


def image_features(inputs: Mapping[str, Any]) -> dict[str, float]:
    """Extract image-only summaries from pixels, embeddings, or statistics."""

    function = "paper1.experiments.covol.features.image_features"
    _require_registered_inputs(inputs, source_function=function)
    features: dict[str, float] = {}
    for field in ("rgb", "image_embedding"):
        if field in inputs:
            values = _numeric_values(inputs[field], name=field)
            mean = _mean(values)
            features[f"{field}_mean"] = mean
            features[f"{field}_std"] = math.sqrt(
                _mean([(value - mean) ** 2 for value in values])
            )
            if field == "image_embedding":
                features["image_embedding_norm"] = _norm(values)
    if "image_statistics" in inputs:
        statistics = inputs["image_statistics"]
        if not isinstance(statistics, Mapping):
            raise ValueError("image_statistics must be a numeric mapping")
        for key in sorted(statistics, key=str):
            values = _numeric_values(statistics[key], name=f"image_statistics.{key}")
            features[f"image_stat_{_normalize_name(key)}"] = _mean(values)
    return features


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
        function_contract = ALLOWED_SOURCE_FUNCTIONS.get(source_function)
        if function_contract is None:
            raise ValueError(
                f"feature {name!r} uses unregistered source_function "
                f"{source_function!r}"
            )
        module_name, function_name = source_function.rsplit(".", maxsplit=1)
        extractor = getattr(importlib.import_module(module_name), function_name, None)
        if not callable(extractor):
            raise ValueError(
                f"feature {name!r} source_function is not an importable callable"
            )
        if function_contract["source_kind"] != source_kind:
            raise ValueError(
                f"feature {name!r} source_kind conflicts with source_function"
            )
        allowed_fields = function_contract["source_fields"]
        unexpected_fields = sorted(
            str(field) for field in source_fields if str(field) not in allowed_fields
        )
        if unexpected_fields:
            raise ValueError(
                f"feature {name!r} source_fields are outside the extractor "
                f"allowlist: {unexpected_fields}"
            )
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


def sanitize_feature_inputs(
    record: Mapping[str, Any],
    *,
    source_function: str,
    source_fields: Iterable[str],
) -> dict[str, Any]:
    """Return the only raw fields that a registered extractor may observe."""

    contract = ALLOWED_SOURCE_FUNCTIONS.get(source_function)
    if contract is None:
        raise ValueError(f"unregistered source_function {source_function!r}")
    requested = tuple(str(field) for field in source_fields)
    unexpected = sorted(
        field for field in requested if field not in contract["source_fields"]
    )
    if unexpected:
        raise ValueError(
            f"source_fields are outside the extractor allowlist: {unexpected}"
        )
    missing = sorted(field for field in requested if field not in record)
    if missing:
        raise ValueError(f"feature input is missing fields: {missing}")
    return {field: record[field] for field in requested}


def feature_schema_payload(
    columns: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return a canonical, hash-addressed feature-schema payload."""

    validated = validate_feature_schema(columns)
    hash_input = {
        "version": 1,
        "denylist": sorted(INTERVENTION_METADATA_DENYLIST),
        "source_function_allowlist": {
            name: {
                "source_kind": value["source_kind"],
                "source_fields": sorted(value["source_fields"]),
            }
            for name, value in sorted(ALLOWED_SOURCE_FUNCTIONS.items())
        },
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
