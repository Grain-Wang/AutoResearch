"""Dev-frozen constrained evaluation for the primary CoVoL comparison."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from paper1.experiments.covol.bootstrap import (
        PolicyImageOutcome,
        cluster_bootstrap_retention,
    )
    from paper1.experiments.covol.metrics import (
        cluster_balanced_weights,
        corruption_metrics,
        weighted_mean,
    )
except ModuleNotFoundError:  # Direct script consumers in this directory.
    from bootstrap import (  # type: ignore[no-redef]
        PolicyImageOutcome,
        cluster_bootstrap_retention,
    )
    from metrics import (  # type: ignore[no-redef]
        cluster_balanced_weights,
        corruption_metrics,
        weighted_mean,
    )


@dataclass(frozen=True)
class FrozenOperatingPoint:
    """One threshold selected exclusively from one training seed's dev rows."""

    method: str
    threshold_id: str
    threshold_index: int
    training_seed: int
    retention: float
    retention_lcb: float
    retention_ci_lower: float
    retention_ci_upper: float
    cvar: float
    worst_of_n: float
    minimum_retention: float
    clean_gain: float
    image_count: int
    cluster_count: int
    bootstrap_replicates: int
    bootstrap_seed: int


@dataclass(frozen=True)
class InternalTestEvaluation:
    """Internal-test result at a dev-frozen operating point."""

    status: str
    method: str
    threshold_id: str
    training_seed: int
    retention_metric: str
    retention: float | None
    retention_lcb: float | None
    retention_ci_lower: float | None
    retention_ci_upper: float | None
    cvar_metric: str
    cvar: float | None
    worst_of_n_metric: str
    worst_of_n: float | None
    minimum_retention: float
    image_count: int
    cluster_count: int


def _validate_outcome_table(outcomes: Sequence[PolicyImageOutcome]) -> int:
    if not outcomes:
        raise ValueError("outcomes must not be empty")
    training_seeds = {row.training_seed for row in outcomes}
    if len(training_seeds) != 1:
        raise ValueError("one outcome table must contain exactly one training seed")
    if any(not row.image_id or not row.cluster_id for row in outcomes):
        raise ValueError("image_id and cluster_id must be nonempty")
    if len({row.image_id for row in outcomes}) != len(outcomes):
        raise ValueError("image_id must be unique within an outcome table")
    return next(iter(training_seeds))


def _cluster_balanced_clean_gain(outcomes: Sequence[PolicyImageOutcome]) -> float:
    weights = cluster_balanced_weights([row.cluster_id for row in outcomes])
    return weighted_mean(
        [row.d0_clean_loss - row.d1_clean_loss for row in outcomes],
        weights,
    )


def select_constrained_operating_point(
    method: str,
    outcomes: Sequence[PolicyImageOutcome],
    *,
    threshold_ids: Sequence[str],
    minimum_retention: float = 0.80,
    minimum_clean_gain: float,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 20260821,
    confidence: float = 0.95,
) -> FrozenOperatingPoint:
    """Minimize dev CVaR subject to a cluster-bootstrap retention LCB."""

    method = method.strip()
    if not method:
        raise ValueError("method must be nonempty")
    training_seed = _validate_outcome_table(outcomes)
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
    if any(
        len(row.routed_clean_losses) != threshold_count
        or len(row.routed_variant_losses) != threshold_count
        for row in outcomes
    ):
        raise ValueError("all outcomes must use the same threshold grid")

    clean_gain = _cluster_balanced_clean_gain(outcomes)
    if clean_gain <= minimum_clean_gain:
        raise ValueError("STOP_UNSTABLE_CLEAN_GAIN")

    d0_losses = [row.d0_clean_loss for row in outcomes]
    cluster_ids = [row.cluster_id for row in outcomes]
    candidates: list[FrozenOperatingPoint] = []
    for threshold_index, threshold_id in enumerate(normalized_ids):
        retention = cluster_bootstrap_retention(
            outcomes,
            threshold_index=threshold_index,
            minimum_clean_gain=minimum_clean_gain,
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
            confidence=confidence,
        )
        if retention.status != "PASS" or retention.estimate is None:
            continue
        if (
            retention.one_sided_lower is None
            or retention.one_sided_lower < minimum_retention
        ):
            continue
        risks = corruption_metrics(
            d0_losses,
            [row.routed_variant_losses[threshold_index] for row in outcomes],
            cluster_ids=cluster_ids,
        )
        assert retention.ci_lower is not None and retention.ci_upper is not None
        candidates.append(
            FrozenOperatingPoint(
                method=method,
                threshold_id=threshold_id,
                threshold_index=threshold_index,
                training_seed=training_seed,
                retention=retention.estimate,
                retention_lcb=retention.one_sided_lower,
                retention_ci_lower=retention.ci_lower,
                retention_ci_upper=retention.ci_upper,
                cvar=risks.cvar,
                worst_of_n=risks.worst_of_n,
                minimum_retention=minimum_retention,
                clean_gain=clean_gain,
                image_count=len(outcomes),
                cluster_count=len(set(cluster_ids)),
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed,
            )
        )
    if not candidates:
        raise ValueError("STOP_NO_FEASIBLE_DEV_THRESHOLD")
    return min(
        candidates,
        key=lambda point: (
            point.cvar,
            -point.retention_lcb,
            -point.retention,
            point.threshold_id,
        ),
    )


def evaluate_internal_test_operating_point(
    operating_point_artifact: Path,
    outcomes: Sequence[PolicyImageOutcome],
    *,
    repository_root: Path,
    minimum_clean_gain: float,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 20260821,
    confidence: float = 0.95,
) -> InternalTestEvaluation:
    """Evaluate the dev-frozen threshold and stop on test retention violation."""

    point = load_operating_point_artifact(
        operating_point_artifact,
        repository_root=repository_root,
    )
    training_seed = _validate_outcome_table(outcomes)
    if training_seed != point.training_seed:
        raise ValueError("internal-test rows must match the operating-point seed")
    if point.threshold_index >= len(outcomes[0].routed_clean_losses):
        raise ValueError("frozen threshold lies outside the internal-test grid")
    cluster_ids = [row.cluster_id for row in outcomes]
    common = {
        "method": point.method,
        "threshold_id": point.threshold_id,
        "training_seed": training_seed,
        "retention_metric": "Ret@Dev-LCB>=0.80",
        "cvar_metric": "CVaR@Dev-LCB-Ret>=0.80",
        "worst_of_n_metric": "Worst-of-N@Dev-LCB-Ret>=0.80",
        "minimum_retention": point.minimum_retention,
        "image_count": len(outcomes),
        "cluster_count": len(set(cluster_ids)),
    }
    retention = cluster_bootstrap_retention(
        outcomes,
        threshold_index=point.threshold_index,
        minimum_clean_gain=minimum_clean_gain,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
        confidence=confidence,
    )
    if retention.status != "PASS" or retention.estimate is None:
        return InternalTestEvaluation(
            status="STOP_UNSTABLE_CLEAN_GAIN",
            retention=None,
            retention_lcb=None,
            retention_ci_lower=None,
            retention_ci_upper=None,
            cvar=None,
            worst_of_n=None,
            **common,
        )
    risks = corruption_metrics(
        [row.d0_clean_loss for row in outcomes],
        [row.routed_variant_losses[point.threshold_index] for row in outcomes],
        cluster_ids=cluster_ids,
    )
    status = (
        "PASS"
        if retention.estimate >= point.minimum_retention
        else "STOP_TEST_RETENTION_VIOLATION"
    )
    return InternalTestEvaluation(
        status=status,
        retention=retention.estimate,
        retention_lcb=retention.one_sided_lower,
        retention_ci_lower=retention.ci_lower,
        retention_ci_upper=retention.ci_upper,
        cvar=risks.cvar,
        worst_of_n=risks.worst_of_n,
        **common,
    )


_LINEAGE_FILES = (
    "dev_manifest",
    "method_config",
    "raw_outcome",
    "coverage_grid",
    "expert_cache",
    "metric_spec",
    "minimum_clean_gain",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bound_repository_file(repository_root: Path, path: Path) -> tuple[str, str]:
    root = repository_root.resolve(strict=True)
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(
            "operating-point lineage file escapes repository root"
        ) from error
    if not resolved.is_file():
        raise ValueError("operating-point lineage path is not a file")
    return relative.as_posix(), _sha256(resolved)


def write_operating_point_artifact(
    point: FrozenOperatingPoint,
    output_path: Path,
    *,
    repository_root: Path,
    dev_manifest_path: Path,
    method_config_path: Path,
    raw_outcome_path: Path,
    coverage_grid_path: Path,
    expert_cache_path: Path,
    metric_spec_path: Path,
    minimum_clean_gain_path: Path,
    code_commit: str,
) -> dict[str, object]:
    """Write a lineage-bound threshold artifact before internal-test access."""

    raw_paths = {
        "dev_manifest": dev_manifest_path,
        "method_config": method_config_path,
        "raw_outcome": raw_outcome_path,
        "coverage_grid": coverage_grid_path,
        "expert_cache": expert_cache_path,
        "metric_spec": metric_spec_path,
        "minimum_clean_gain": minimum_clean_gain_path,
    }
    lineage = {
        name: dict(
            zip(
                ("path", "sha256"),
                _bound_repository_file(repository_root, path),
                strict=True,
            )
        )
        for name, path in raw_paths.items()
    }
    if len(code_commit) != 40 or any(
        char not in "0123456789abcdef" for char in code_commit
    ):
        raise ValueError("code_commit must be a full lowercase Git object ID")
    payload: dict[str, object] = {
        "schema_version": "covol-dev-operating-point-v2",
        "selection_scope": "DEV_ONLY_INTERNAL_TEST_UNREAD",
        "lineage": lineage,
        "code_commit": code_commit,
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


def load_operating_point_artifact(
    artifact_path: Path,
    *,
    repository_root: Path,
) -> FrozenOperatingPoint:
    """Rehash every lineage file and load the only permitted test threshold."""

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("operating-point artifact must contain a JSON object")
    if payload.get("schema_version") != "covol-dev-operating-point-v2":
        raise ValueError("unsupported operating-point artifact schema")
    if payload.get("selection_scope") != "DEV_ONLY_INTERNAL_TEST_UNREAD":
        raise ValueError("operating-point selection scope is invalid")
    declared_artifact_hash = payload.pop("artifact_sha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != declared_artifact_hash:
        raise ValueError("operating-point artifact SHA256 mismatch")
    code_commit = str(payload.get("code_commit", ""))
    if len(code_commit) != 40 or any(
        char not in "0123456789abcdef" for char in code_commit
    ):
        raise ValueError("operating-point code commit is invalid")
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict) or set(lineage) != set(_LINEAGE_FILES):
        raise ValueError("operating-point lineage is incomplete")
    root = repository_root.resolve(strict=True)
    for name in _LINEAGE_FILES:
        binding = lineage[name]
        if not isinstance(binding, dict):
            raise ValueError(f"operating-point {name} binding is invalid")
        relative = Path(str(binding.get("path", "")).strip())
        if not str(relative) or relative.is_absolute():
            raise ValueError(f"operating-point {name} path must be relative")
        resolved = (root / relative).resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ValueError(f"operating-point {name} path escapes root") from error
        if not resolved.is_file() or _sha256(resolved) != binding.get("sha256"):
            raise ValueError(f"operating-point {name} lineage mismatch")
    point = payload.get("operating_point")
    if not isinstance(point, dict):
        raise ValueError("operating-point payload is missing")
    try:
        return FrozenOperatingPoint(**point)
    except TypeError as error:
        raise ValueError("operating-point fields are invalid") from error
