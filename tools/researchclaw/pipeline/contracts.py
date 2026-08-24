"""Artifact contracts for the sixteen-stage research workflow."""

from __future__ import annotations

from dataclasses import dataclass

from researchclaw.pipeline.stages import Stage


@dataclass(frozen=True)
class StageContract:
    """Required prior artifacts and outputs for one stage."""

    stage: Stage
    input_files: tuple[str, ...]
    output_files: tuple[str, ...]
    definition_of_done: str
    executes: bool = False


CONTRACTS: dict[Stage, StageContract] = {
    Stage.TOPIC_INIT: StageContract(
        Stage.TOPIC_INIT,
        (),
        ("goal.md", "hardware_profile.json"),
        "A scoped research goal and recorded compute constraints.",
    ),
    Stage.PROBLEM_DECOMPOSE: StageContract(
        Stage.PROBLEM_DECOMPOSE,
        ("goal.md",),
        ("problem_tree.md",),
        "Prioritized algorithmic questions with falsifiable probes.",
    ),
    Stage.SEARCH_STRATEGY: StageContract(
        Stage.SEARCH_STRATEGY,
        ("problem_tree.md",),
        ("search_plan.yaml", "queries.json"),
        "Queries target recent direct neighbors and explicit algorithmic gaps.",
    ),
    Stage.LITERATURE_COLLECT: StageContract(
        Stage.LITERATURE_COLLECT,
        ("queries.json",),
        ("candidates.jsonl",),
        "Real scholarly API results are recorded and deduplicated.",
        executes=True,
    ),
    Stage.LITERATURE_SCREEN: StageContract(
        Stage.LITERATURE_SCREEN,
        ("candidates.jsonl",),
        ("shortlist.jsonl", "gate.json"),
        "At most five research opportunities pass the documented gate.",
    ),
    Stage.KNOWLEDGE_EXTRACT: StageContract(
        Stage.KNOWLEDGE_EXTRACT,
        ("shortlist.jsonl",),
        ("cards/",),
        "Each neighbor has an evidence-linked method and limitation card.",
    ),
    Stage.SYNTHESIS: StageContract(
        Stage.SYNTHESIS,
        ("cards/",),
        ("synthesis.md",),
        "The baseline assumption, gap, and non-equivalent solution paths are clear.",
    ),
    Stage.BASELINE_REPRODUCE: StageContract(
        Stage.BASELINE_REPRODUCE,
        ("synthesis.md",),
        ("defect_report.md", "reproduce/", "gate.json"),
        "A real algorithmic defect is reproduced or the direction is stopped.",
    ),
    Stage.HYPOTHESIS_GEN: StageContract(
        Stage.HYPOTHESIS_GEN,
        ("defect_report.md",),
        ("hypotheses.md",),
        "Mechanistically distinct, falsifiable algorithm hypotheses are ranked.",
    ),
    Stage.EXPERIMENT_DESIGN: StageContract(
        Stage.EXPERIMENT_DESIGN,
        ("hypotheses.md",),
        ("exp_plan.yaml", "gate.json"),
        "Novelty, killer baselines, ablations, outcomes, and budgets are frozen.",
    ),
    Stage.CODE_GENERATION: StageContract(
        Stage.CODE_GENERATION,
        ("exp_plan.yaml",),
        ("experiment/", "experiment_spec.md"),
        "Command-line experiment code reproduces the frozen design.",
    ),
    Stage.RESOURCE_PLANNING: StageContract(
        Stage.RESOURCE_PLANNING,
        ("experiment/", "exp_plan.yaml"),
        ("schedule.json",),
        "An executable, seeded task schedule stays within the compute budget.",
    ),
    Stage.EXPERIMENT_RUN: StageContract(
        Stage.EXPERIMENT_RUN,
        ("experiment/", "schedule.json"),
        ("runs/", "run_summary.json"),
        "Every scheduled real task has logs, exit status, and metrics.",
        executes=True,
    ),
    Stage.ITERATIVE_REFINE: StageContract(
        Stage.ITERATIVE_REFINE,
        ("run_summary.json",),
        ("refinement_log.json", "experiment_final/"),
        "Mechanism diagnosis justifies each retained algorithm iteration.",
    ),
    Stage.RESULT_ANALYSIS: StageContract(
        Stage.RESULT_ANALYSIS,
        ("run_summary.json", "refinement_log.json"),
        ("analysis.md",),
        "Strong baselines, uncertainty, ablations, efficiency, and failures are analyzed.",
    ),
    Stage.RESEARCH_DECISION: StageContract(
        Stage.RESEARCH_DECISION,
        ("analysis.md",),
        ("decision.json", "decision.md"),
        "A supported STOP/REFINE/PIVOT/PAPER_CANDIDATE decision is recorded.",
    ),
}
