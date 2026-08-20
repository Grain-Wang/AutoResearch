"""Artifact publisher — extracts and publishes research artifacts from pipeline runs."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from researchclaw.collaboration.repository import ResearchRepository

logger = logging.getLogger(__name__)


class ArtifactPublisher:
    """Extracts artifacts from pipeline run directories and publishes them.

    Scans stage output directories for relevant files and publishes
    structured summaries to the shared repository.
    """

    def __init__(self, repository: ResearchRepository) -> None:
        self._repo = repository

    def publish_from_run_dir(
        self,
        run_id: str,
        run_dir: Path,
    ) -> int:
        """Extract and publish all artifacts from a pipeline run directory.

        Args:
            run_id: Unique run identifier.
            run_dir: Path to the pipeline run output directory.

        Returns:
            Number of artifacts published.
        """
        artifacts: dict[str, Any] = {}

        # Literature summary (from stage 7 - synthesis)
        lit_summary = self._extract_literature(run_dir)
        if lit_summary:
            artifacts["literature_summary"] = lit_summary

        # Experiment results (from stage 15 - result_analysis)
        exp_results = self._extract_experiments(run_dir)
        if exp_results:
            artifacts["experiment_results"] = exp_results

        # Code template (from stage 11 - code_generation)
        code_template = self._extract_code(run_dir)
        if code_template:
            artifacts["code_template"] = code_template

        # Research decision (from stage 16 - research_decision)
        decision = self._extract_decision(run_dir)
        if decision:
            artifacts["research_decision"] = decision

        if not artifacts:
            logger.info("No artifacts found in run dir: %s", run_dir)
            return 0

        return self._repo.publish(run_id, artifacts)

    def _extract_literature(self, run_dir: Path) -> Any:
        """Extract literature summary from stage 7."""
        for stage_dir in run_dir.glob("stage-07*"):
            for name in ("synthesis.md", "synthesis.json"):
                path = stage_dir / name
                if path.exists():
                    return path.read_text(encoding="utf-8")[:5000]
        return None

    def _extract_experiments(self, run_dir: Path) -> Any:
        """Extract experiment results from stage 15."""
        for stage_dir in run_dir.glob("stage-15*"):
            summary = stage_dir / "experiment_summary.json"
            if summary.exists():
                try:
                    return json.loads(summary.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
        return None

    def _extract_code(self, run_dir: Path) -> Any:
        """Extract code template from stage 11."""
        for stage_dir in run_dir.glob("stage-11*"):
            main_py = stage_dir / "main.py"
            if main_py.exists():
                return main_py.read_text(encoding="utf-8")[:10000]
        return None

    def _extract_decision(self, run_dir: Path) -> Any:
        """Extract research decision from stage 16."""
        for stage_dir in run_dir.glob("stage-16*"):
            decision = stage_dir / "decision.md"
            if decision.exists():
                return decision.read_text(encoding="utf-8")[:5000]
        return None
