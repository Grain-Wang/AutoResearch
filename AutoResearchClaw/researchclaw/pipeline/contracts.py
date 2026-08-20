"""Stage I/O contracts for the 16-stage experiment pipeline.

Each StageContract declares:
  - input_files: artifacts this stage reads (produced by prior stages)
  - output_files: artifacts this stage must produce
  - dod: Definition of Done — human-readable acceptance criterion
  - error_code: unique error identifier for diagnostics
  - max_retries: how many times the stage may be retried on failure
"""

from __future__ import annotations

from dataclasses import dataclass

from researchclaw.pipeline.stages import Stage


@dataclass(frozen=True)
class StageContract:
    stage: Stage
    input_files: tuple[str, ...]
    output_files: tuple[str, ...]
    dod: str
    error_code: str
    max_retries: int = 1
    collider_output_files: tuple[str, ...] = ()


CONTRACTS: dict[Stage, StageContract] = {
    # Phase A: Research Scoping
    Stage.TOPIC_INIT: StageContract(
        stage=Stage.TOPIC_INIT,
        input_files=(),
        output_files=("goal.md", "hardware_profile.json"),
        dod="SMART goal statement with topic, scope, and constraints",
        error_code="E01_INVALID_GOAL",
        max_retries=0,
    ),
    Stage.PROBLEM_DECOMPOSE: StageContract(
        stage=Stage.PROBLEM_DECOMPOSE,
        input_files=("goal.md",),
        output_files=("problem_tree.md",),
        dod=">=3 prioritized sub-questions identified",
        error_code="E02_DECOMP_FAIL",
    ),
    # Phase B: Literature Discovery
    Stage.SEARCH_STRATEGY: StageContract(
        stage=Stage.SEARCH_STRATEGY,
        input_files=("problem_tree.md",),
        output_files=("search_plan.yaml", "sources.json", "queries.json"),
        dod=">=2 search strategies defined with verified data sources",
        error_code="E03_STRATEGY_BAD",
    ),
    Stage.LITERATURE_COLLECT: StageContract(
        stage=Stage.LITERATURE_COLLECT,
        input_files=("search_plan.yaml",),
        output_files=("candidates.jsonl",),
        dod=">=N candidate papers collected from specified sources",
        error_code="E04_COLLECT_EMPTY",
        max_retries=2,
    ),
    Stage.LITERATURE_SCREEN: StageContract(
        stage=Stage.LITERATURE_SCREEN,
        input_files=("candidates.jsonl",),
        output_files=("shortlist.jsonl",),
        dod="Relevance + quality dual screening completed and approved",
        error_code="E05_GATE_REJECT",
        max_retries=0,
    ),
    Stage.KNOWLEDGE_EXTRACT: StageContract(
        stage=Stage.KNOWLEDGE_EXTRACT,
        input_files=("shortlist.jsonl",),
        output_files=("cards/",),
        dod="Structured knowledge card per shortlisted paper",
        error_code="E06_EXTRACT_FAIL",
    ),
    # Phase C: Knowledge Synthesis & Defect Baseline
    Stage.SYNTHESIS: StageContract(
        stage=Stage.SYNTHESIS,
        input_files=("cards/",),
        output_files=("synthesis.md",),
        dod="Topic clusters + >=2 research gaps identified",
        error_code="E07_SYNTHESIS_WEAK",
    ),
    Stage.BASELINE_REPRODUCE: StageContract(
        stage=Stage.BASELINE_REPRODUCE,
        input_files=("synthesis.md",),
        output_files=("defect_report.md", "reproduce/"),
        dod="Baseline defect minimally reproduced with evidence, or refuted",
        error_code="E08_BASELINE_REPRO_FAIL",
        max_retries=0,
    ),
    Stage.HYPOTHESIS_GEN: StageContract(
        stage=Stage.HYPOTHESIS_GEN,
        input_files=("synthesis.md", "defect_report.md"),
        output_files=("hypotheses.md",),
        dod=">=2 falsifiable research hypotheses on confirmed defects",
        error_code="E09_HYP_INVALID",
    ),
    # Phase D: Experiment Design
    Stage.EXPERIMENT_DESIGN: StageContract(
        stage=Stage.EXPERIMENT_DESIGN,
        input_files=("hypotheses.md",),
        output_files=("exp_plan.yaml",),
        dod="Experiment plan with baselines, ablations, metrics approved",
        error_code="E10_GATE_REJECT",
        max_retries=0,
    ),
    Stage.CODE_GENERATION: StageContract(
        stage=Stage.CODE_GENERATION,
        input_files=("exp_plan.yaml",),
        output_files=("experiment/", "experiment_spec.md"),
        collider_output_files=("collider_plan.md",),
        dod="Multi-file experiment project + spec document",
        error_code="E11_CODEGEN_FAIL",
        max_retries=2,
    ),
    Stage.RESOURCE_PLANNING: StageContract(
        stage=Stage.RESOURCE_PLANNING,
        input_files=("exp_plan.yaml",),
        output_files=("schedule.json",),
        dod="Resource schedule with GPU/time estimates",
        error_code="E12_SCHED_CONFLICT",
    ),
    # Phase E: Experiment Execution
    Stage.EXPERIMENT_RUN: StageContract(
        stage=Stage.EXPERIMENT_RUN,
        input_files=("schedule.json", "experiment/"),
        output_files=("runs/",),
        dod="All scheduled experiment runs completed with artifacts",
        error_code="E13_RUN_FAIL",
        max_retries=2,
    ),
    Stage.ITERATIVE_REFINE: StageContract(
        stage=Stage.ITERATIVE_REFINE,
        input_files=("runs/",),
        output_files=("refinement_log.json", "experiment_final/"),
        dod="Edit-run-eval loop converged or max iterations reached",
        error_code="E14_REFINE_FAIL",
        max_retries=2,
    ),
    # Phase F: Analysis & Decision
    Stage.RESULT_ANALYSIS: StageContract(
        stage=Stage.RESULT_ANALYSIS,
        input_files=("runs/",),
        output_files=("analysis.md",),
        dod="Metrics analyzed with statistical tests and conclusions",
        error_code="E15_ANALYSIS_ERR",
    ),
    Stage.RESEARCH_DECISION: StageContract(
        stage=Stage.RESEARCH_DECISION,
        input_files=("analysis.md",),
        output_files=("decision.md",),
        dod="PROCEED/PIVOT decision with evidence-based justification",
        error_code="E16_DECISION_FAIL",
    ),
}
