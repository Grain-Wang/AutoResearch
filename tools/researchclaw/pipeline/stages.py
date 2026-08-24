"""The AGENTS-aligned sixteen-stage research workflow."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Stage(IntEnum):
    """Ordered research stages ending at the paper-candidate decision."""

    TOPIC_INIT = 1
    PROBLEM_DECOMPOSE = 2
    SEARCH_STRATEGY = 3
    LITERATURE_COLLECT = 4
    LITERATURE_SCREEN = 5
    KNOWLEDGE_EXTRACT = 6
    SYNTHESIS = 7
    BASELINE_REPRODUCE = 8
    HYPOTHESIS_GEN = 9
    EXPERIMENT_DESIGN = 10
    CODE_GENERATION = 11
    RESOURCE_PLANNING = 12
    EXPERIMENT_RUN = 13
    ITERATIVE_REFINE = 14
    RESULT_ANALYSIS = 15
    RESEARCH_DECISION = 16


class StageStatus(StrEnum):
    """Observable stage states derived from artifacts."""

    PENDING = "pending"
    READY = "ready"
    DONE = "done"
    FAILED = "failed"
    REJECTED = "rejected"


STAGE_SEQUENCE = tuple(Stage)
GATE_STAGES = frozenset(
    {Stage.LITERATURE_SCREEN, Stage.BASELINE_REPRODUCE, Stage.EXPERIMENT_DESIGN}
)
NEXT_STAGE = {
    stage: STAGE_SEQUENCE[index + 1] if index + 1 < len(STAGE_SEQUENCE) else None
    for index, stage in enumerate(STAGE_SEQUENCE)
}


def gate_required(stage: Stage) -> bool:
    """Return whether the stage requires a machine-readable PASS/STOP gate."""

    return stage in GATE_STAGES
