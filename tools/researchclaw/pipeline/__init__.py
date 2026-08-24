"""Artifact contracts for the sixteen-stage research workflow."""

from researchclaw.pipeline.contracts import CONTRACTS, StageContract
from researchclaw.pipeline.executor import StageResult, execute_stage
from researchclaw.pipeline.stages import GATE_STAGES, Stage, StageStatus

__all__ = [
    "CONTRACTS",
    "GATE_STAGES",
    "Stage",
    "StageContract",
    "StageResult",
    "StageStatus",
    "execute_stage",
]
