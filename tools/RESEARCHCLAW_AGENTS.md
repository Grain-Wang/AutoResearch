# ResearchClaw — Experiment Toolbox Agent Configuration

## Overview

ResearchClaw is an **experiment toolbox**: a 16-stage research-to-experiment pipeline
(选题 → 文献 → 综合 → 复现 baseline 缺陷 → 假设 → 实验设计 → 代码 → 执行 → 迭代 →
分析 → 决策).  Paper-writing stages are removed.  Each stage can be invoked on demand
as an independent command (`researchclaw tools <step> --run-dir <dir>`), or run in
sequence (`researchclaw run`).

In this repository, `tools/` is a regular subdirectory of the outer
**AutoResearch** main repository. It is not a separate research project or Git
repository. Research plans, stage artifacts, and paper materials belong in an
outer `paper*/` workspace, while commands and dependency installation run from
`tools/`.

Research rules have two complementary sources:

1. The nearest workspace `AGENTS.md` is discovered at runtime and injected in
   full as authoritative policy into stage prompts and repair sub-prompts.
2. `researchclaw/prompts/agents_directives.yaml` adds concise, stage-specific
   operating instructions for all 16 stages.

A governed LLM proxy also injects the workspace policy into legacy direct
`llm.chat()` calls that bypass `PromptManager`.

`prompts.extra_prompts` can add domain guidance, but cannot replace either rule
layer. Each stage records `agents_context.json` (source path and SHA-256) and an
`AGENTS.md` snapshot so nested experiment agents inherit the same constraints.

## Agent Role: Experiment Orchestrator

You are an AI research assistant operating ResearchClaw as a toolbox. Your job:

1. **Clarify the research question** — topic, scope, constraints (AGENTS.md §3/§4)
2. **Set up the workspace** — `researchclaw tools init --run-dir <dir> --topic "..."`
3. **Drive the experiment step by step** — run a stage, review artifacts, approve gates
4. **Enforce the gates** — screen (5), reproduce (8), design (10) require review
5. **Deliver** — the final decision (`decision.md`), experiment summary, and analysis

## Quick Setup

```bash
pip install -e .
cp config.researchclaw.example.yaml config.yaml   # set llm.* and experiment.mode

researchclaw tools init --run-dir ../paper1/steps/my-run --topic "YOUR TOPIC"
researchclaw tools status --run-dir ../paper1/steps/my-run
```

## Pipeline Stages (16 stages, 6 phases)

| Phase | Stages | Description |
|-------|--------|-------------|
| A: Research Scoping | 1–2 | `topic` `decompose` — define topic, decompose into sub-problems |
| B: Literature Discovery | 3–6 | `search` `collect` `screen`[GATE] `extract` |
| C: Synthesis & Defect | 7–8 | `synthesize` `reproduce`[GATE] — confirm a real algorithmic baseline defect |
| D: Experiment Design | 9–12 | `hypothesize` `design`[GATE] `codegen` `plan` |
| E: Experiment Execution | 13–14 | `experiment` `refine` |
| F: Analysis & Decision | 15–16 | `analyze` `decide` |

## Gate Stages (require explicit approval unless `--auto-approve`)

| Step (stage) | Artifact reviewed | Rollback on reject |
|--------------|-------------------|--------------------|
| `screen` (5) | `stage-05/shortlist.jsonl` | → `collect` (4) |
| `reproduce` (8) | `stage-08/defect_report.md` — defect confirmed? algorithmic? | → `synthesize` (7) |
| `design` (10) | `stage-10/exp_plan.yaml` — novelty gate | → `hypothesize` (9) |

Use `researchclaw tools <step> --run-dir <dir> --auto-approve` for the step, or
`researchclaw approve <run-dir>` to approve a paused gate.

## Step Reference

```
tools topic        # 1  TOPIC_INIT          goal.md, hardware_profile.json
tools decompose    # 2  PROBLEM_DECOMPOSE   problem_tree.md
tools search       # 3  SEARCH_STRATEGY     search_plan.yaml, sources.json, queries.json
tools collect      # 4  LITERATURE_COLLECT  candidates.jsonl
tools screen       # 5  LITERATURE_SCREEN   shortlist.jsonl              [GATE]
tools extract      # 6  KNOWLEDGE_EXTRACT   cards/
tools synthesize   # 7  SYNTHESIS           synthesis.md
tools reproduce    # 8  BASELINE_REPRODUCE  defect_report.md, reproduce/ [GATE]
tools hypothesize  # 9  HYPOTHESIS_GEN      hypotheses.md
tools design       # 10 EXPERIMENT_DESIGN   exp_plan.yaml                [GATE]
tools codegen      # 11 CODE_GENERATION     experiment/, experiment_spec.md
tools plan         # 12 RESOURCE_PLANNING   schedule.json
tools experiment   # 13 EXPERIMENT_RUN      runs/
tools refine       # 14 ITERATIVE_REFINE    refinement_log.json, experiment_final/
tools analyze      # 15 RESULT_ANALYSIS     analysis.md
tools decide       # 16 RESEARCH_DECISION   decision.md
```

## Experiment Modes

- `simulated`: no code execution (framework dev only — do not use for real results)
- `sandbox`: execute generated code in a local subprocess (Python 3.12 venv, AGENTS.md §14)
- `docker` / `ssh_remote` / `colab_drive`: remote/containerized execution

## Key Files

| File | Purpose |
|------|---------|
| `researchclaw/tools_cli.py` | `researchclaw tools` implementation |
| `researchclaw/prompts/agents_directives.yaml` | AGENTS.md per-stage directives (auto-injected) |
| workspace `AGENTS.md` | Authoritative project scope, research gates, compute and code rules |
| `researchclaw/pipeline/executor.py` | `execute_stage()` — the single-stage engine |
| `researchclaw/pipeline/stages.py` | 16-stage enum, gates, rollbacks |
| `researchclaw/pipeline/contracts.py` | per-stage I/O contracts |
| `researchclaw/pipeline/stage_impls/_reproduce_defect.py` | stage 8 executor |
| `researchclaw/experiment/validator.py` | code validation (AST + security) |
| `researchclaw/experiment/sandbox.py` | sandbox execution |

## Verify Rule Loading

```bash
researchclaw tools list
researchclaw tools init --run-dir lab --topic "YOUR TOPIC"
```

The commands print the discovered workspace `AGENTS.md`. After a stage runs,
inspect `lab/stage-NN/agents_context.json` to verify the exact source and digest.

## Decision Guide

| Situation | Action |
|-----------|--------|
| User gives a topic | `tools init --run-dir lab --topic ...`, then drive steps 1→16 |
| Need to review a gate | run the gate step **without** `--auto-approve`; inspect the artifact |
| Gate rejected | roll back per the table above and rerun the appropriate prior step |
| Want full automation | `researchclaw run --topic "..." --auto-approve` |
| Resume mid-way | `researchclaw run --resume`, or rerun the individual step |
| No LLM configured | steps run in no-LLM template fallback; set `llm.*` in config for real calls |
