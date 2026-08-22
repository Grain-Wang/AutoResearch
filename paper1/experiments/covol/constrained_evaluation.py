"""Dev-only operating-point selection for the primary CoVoL comparison."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from paper1.experiments.covol.bootstrap import PolicyImageOutcome
    from paper1.experiments.covol.metrics import (
        clean_gain_retention,
        corruption_metrics,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from bootstrap import PolicyImageOutcome  # type: ignore[no-redef]
    from metrics import (  # type: ignore[no-redef]
        clean_gain_retention,
        corruption_metrics,
    )


@dataclass(frozen=True)
class FrozenOperatingPoint:
    """One threshold selected exclusively from development outcomes."""

    method: str
    threshold_id: str
    threshold_index: int
    retention: float
    cvar: float
    worst_of_n: float
    minimum_retention: float
    clean_gain: float
    image_count: int
    cluster_count: int


def select_constrained_operating_point(
    method: str,
    outcomes: Sequence[PolicyImageOutcome],
    *,
    threshold_ids: Sequence[str],
    minimum_retention: float = 0.80,
    minimum_clean_gain: float,
) -> FrozenOperatingPoint:
    """Select minimum dev CVaR among thresholds satisfying clean retention."""

    method = method.strip()
    if not method:
        raise ValueError("method must be nonempty")
    if not outcomes:
        raise ValueError("development outcomes must not be empty")
    threshold_count = len(outcomes[0].routed_clean_losses)
    normalized_ids = [str(value).strip() for value in threshold_ids]
    if (
        len(normalized_ids) != threshold_count
        or any(not value for value in normalized_ids)
        or len(set(normalized_ids)) != len(normalized_ids)
    ):
        raise ValueError("threshold_ids must uniquely cover the frozen grid")
    if not math.isfinite(minimum_retention) or not 0.0 <= minimum_retention <= 1.0:
        raise ValueError("minimum_retention must be finite and in [0, 1]")
    if not math.isfinite(minimum_clean_gain) or minimum_clean_gain < 0.0:
        raise ValueError("minimum_clean_gain must be finite and nonnegative")

    d0_losses = [row.d0_clean_loss for row in outcomes]
    d1_losses = [row.d1_clean_loss for row in outcomes]
    clean_gain = sum(
        d0_loss - d1_loss for d0_loss, d1_loss in zip(d0_losses, d1_losses, strict=True)
    ) / len(outcomes)
    if clean_gain <= minimum_clean_gain:
        raise ValueError("STOP_UNSTABLE_CLEAN_GAIN")

    candidates: list[FrozenOperatingPoint] = []
    for threshold_index, threshold_id in enumerate(normalized_ids):
        if any(
            len(row.routed_clean_losses) != threshold_count
            or len(row.routed_variant_losses) != threshold_count
            for row in outcomes
        ):
            raise ValueError("all outcomes must use the same threshold grid")
        retention = clean_gain_retention(
            d0_losses,
            d1_losses,
            [row.routed_clean_losses[threshold_index] for row in outcomes],
            clean_gain_ci_lower=clean_gain,
        )
        risks = corruption_metrics(
            d0_losses,
            [row.routed_variant_losses[threshold_index] for row in outcomes],
        )
        if retention >= minimum_retention:
            candidates.append(
                FrozenOperatingPoint(
                    method=method,
                    threshold_id=threshold_id,
                    threshold_index=threshold_index,
                    retention=retention,
                    cvar=risks.cvar,
                    worst_of_n=risks.worst_of_n,
                    minimum_retention=minimum_retention,
                    clean_gain=clean_gain,
                    image_count=len(outcomes),
                    cluster_count=len({row.cluster_id for row in outcomes}),
                )
            )
    if not candidates:
        raise ValueError("STOP_NO_FEASIBLE_DEV_THRESHOLD")
    return min(
        candidates,
        key=lambda point: (point.cvar, -point.retention, point.threshold_id),
    )


def write_operating_point_artifact(
    point: FrozenOperatingPoint,
    output_path: Path,
    *,
    dev_manifest_sha256: str,
    method_config_sha256: str,
) -> dict[str, object]:
    """Write a hash-addressed threshold artifact before internal-test access."""

    for name, value in (
        ("dev_manifest_sha256", dev_manifest_sha256),
        ("method_config_sha256", method_config_sha256),
    ):
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError(f"{name} must be a lowercase SHA256")
    payload: dict[str, object] = {
        "schema_version": "covol-dev-operating-point-v1",
        "selection_scope": "DEV_ONLY_INTERNAL_TEST_UNREAD",
        "dev_manifest_sha256": dev_manifest_sha256,
        "method_config_sha256": method_config_sha256,
        "operating_point": asdict(point),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload["artifact_sha256"] = hashlib.sha256(encoded).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload
