"""Audit the budget-matched Boosting MDE score against official source code."""

from __future__ import annotations

import argparse
import ast
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .core import make_regions
from .io_utils import file_digest, write_json_atomic
from .selectors.boosting2021_selector import score_fixed_regions

OFFICIAL_REPOSITORY = "https://github.com/compphoto/BoostingMonocularDepth.git"


def _load_official_utility_functions(
    source_path: Path,
) -> tuple[
    Callable[[np.ndarray], np.ndarray], Callable[[np.ndarray, list[int]], float]
]:
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"rgb2gray", "getGF_fromintegral"}
    ]
    if {node.name for node in selected} != {"rgb2gray", "getGF_fromintegral"}:
        raise ValueError("Official selector utility functions were not found")
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {"np": np}
    exec(compile(module, str(source_path), "exec"), namespace)
    return namespace["rgb2gray"], namespace["getGF_fromintegral"]


def _official_reference_scores(
    image_rgb: np.ndarray,
    *,
    rgb2gray: Callable[[np.ndarray], np.ndarray],
    get_gradient_sum: Callable[[np.ndarray, list[int]], float],
) -> np.ndarray:
    gray = rgb2gray(image_rgb.astype(np.float64) / 255.0)
    gradient = np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)) + np.abs(
        cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    )
    positive = gradient[gradient > 0]
    if positive.size == 0:
        return np.zeros(12, dtype=np.float64)
    gradient[gradient < positive.mean()] = 0
    global_density = float(gradient.mean())
    integral = cv2.integral(gradient)
    regions = make_regions(
        image_rgb.shape[0], image_rgb.shape[1], 3, 4, context_scale=1.0
    )
    return np.asarray(
        [
            get_gradient_sum(
                integral,
                [
                    region.x0,
                    region.y0,
                    region.x1 - region.x0,
                    region.y1 - region.y0,
                ],
            )
            / ((region.x1 - region.x0) * (region.y1 - region.y0))
            / global_density
            for region in regions
        ],
        dtype=np.float64,
    )


def audit_official_examples(official_repo: Path, output_path: Path) -> dict[str, Any]:
    """Compare frozen-cell scores on official examples and write a fidelity audit."""
    utils_path = official_repo / "utils.py"
    run_path = official_repo / "run.py"
    rgb2gray, get_gradient_sum = _load_official_utility_functions(utils_path)
    revision = subprocess.run(
        ["git", "-C", str(official_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    sample_paths = sorted((official_repo / "inputs").glob("*"))
    records: list[dict[str, Any]] = []
    for sample_path in sample_paths:
        image_bgr = cv2.imread(str(sample_path), cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise ValueError(f"Could not read official sample {sample_path.name}")
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        regions = make_regions(
            image_rgb.shape[0], image_rgb.shape[1], 3, 4, context_scale=1.0
        )
        actual, _ = score_fixed_regions(image_rgb, regions)
        reference = _official_reference_scores(
            image_rgb,
            rgb2gray=rgb2gray,
            get_gradient_sum=get_gradient_sum,
        )
        actual_ranking = np.argsort(-actual, kind="stable").tolist()
        reference_ranking = np.argsort(-reference, kind="stable").tolist()
        records.append(
            {
                "sample_name": sample_path.name,
                "sample_sha256": file_digest(sample_path),
                "max_absolute_score_difference": float(
                    np.max(np.abs(actual - reference))
                ),
                "ranking_identical": actual_ranking == reference_ranking,
                "top3_region_ids": actual_ranking[:3],
            }
        )
    all_pass = bool(records) and all(
        record["max_absolute_score_difference"] <= 1e-12 and record["ranking_identical"]
        for record in records
    )
    audit = {
        "schema_version": 1,
        "status": "PASS" if all_pass else "FAIL",
        "adaptation": (
            "official thresholded-Sobel local/global density ratio evaluated "
            "on the frozen 3x4 BAR target cells"
        ),
        "official_repository": OFFICIAL_REPOSITORY,
        "official_revision": revision,
        "official_utils_sha256": file_digest(utils_path),
        "official_run_sha256": file_digest(run_path),
        "records": records,
    }
    write_json_atomic(output_path, audit)
    return audit


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Run the official-example fidelity audit."""
    args = parse_args()
    audit = audit_official_examples(args.official_repo, args.output)
    print(audit["status"])


if __name__ == "__main__":
    main()
