---
name: researchclaw
description: Run ResearchClaw's 16-stage experiment pipeline as a toolbox — each stage (topic → decide) is an independent command into a shared workspace, plus batch mode via `researchclaw run`.
---

# ResearchClaw — Experiment Toolbox Skill

## Description

ResearchClaw is an **experiment toolbox**: the research process (选题 → 文献 → 综合 → 复现 baseline 缺陷 → 假设 → 实验设计 → 代码 → 执行 → 迭代 → 分析 → 决策) is a 16-stage pipeline. Two modes:

- **Toolset (推荐)**: run any single stage on demand with `researchclaw tools <step> --run-dir <dir>`. You decide the order, review artifacts between steps, and gate approval is explicit.
- **Batch**: `researchclaw run` runs stages 1–16 in sequence (with `--from-stage` / `--to-stage` / `--resume`).

Paper-writing stages are **removed**. The AGENTS.md research directives are auto-injected into every LLM prompt.

## Trigger Conditions

Activate this skill when the user:
- Wants to run a single research/experiment step (e.g. "screen the papers", "reproduce the baseline defect")
- Wants to run the full experiment pipeline on a topic
- Mentions "ResearchClaw", "researchclaw tools", or "做实验工具箱"

## Instructions

### 1. Workspace setup

```bash
researchclaw tools init --run-dir <dir> --topic "YOUR TOPIC"
# Creates <dir>/ with tools.json, a config snapshot, and a knowledge/ root.
# Point experiment.sandbox.python_path at your Python 3.12 venv (AGENTS.md §14),
# or create <dir>/.venv and it is picked up automatically.
```

### 2. Inspect

```bash
researchclaw tools list                      # all 16 steps, I/O contracts, GATE markers
researchclaw tools status --run-dir <dir>    # which stages have artifacts, next step
```

### 3. Run a step

```bash
researchclaw tools <step> --run-dir <dir> [--topic ...] [--auto-approve] [--baseline <name>]
```

Steps: `topic decompose search collect screen extract synthesize reproduce hypothesize design codegen plan experiment refine analyze decide`

- `reproduce` accepts `--baseline <name>` to pin the baseline the defect is reproduced against.
- **Gate steps** (`screen`, `reproduce`, `design`) require explicit approval: without `--auto-approve` they return `blocked_approval` and you review the stage artifacts (e.g. `stage-08/defect_report.md`) before approving/rejecting.

### 4. Gate review pattern (AGENTS.md §6)

| Gate step | Artifact to review | Decision |
|-----------|--------------------|----------|
| `screen` (5) | `stage-05/shortlist.jsonl` — Research Opportunity Gate | approve → continue; reject → rerun `collect` |
| `reproduce` (8) | `stage-08/defect_report.md` — defect CONFIRMED? algorithmic? | approve → `hypothesize`; reject → rerun `synthesize` (rollback 8→7) |
| `design` (10) | `stage-10/exp_plan.yaml` — novelty gate: why insufficient / what changed / why effective | approve → `codegen`; reject → rerun `hypothesize` |

### 5. Batch mode

```bash
researchclaw run --topic "YOUR TOPIC" --auto-approve      # stages 1–16
researchclaw run --from-stage EXPERIMENT_DESIGN --to-stage RESULT_ANALYSIS
researchclaw run --resume
```

### Output structure

```
<run-dir>/
├── stage-01/…                # topic_init: goal.md, hardware_profile.json
├── stage-05/…                # literature_screen [GATE]: shortlist.jsonl
├── stage-08/…                # baseline_reproduce [GATE]: defect_report.md, reproduce/
├── stage-10/…                # experiment_design [GATE]: exp_plan.yaml
├── stage-11/experiment/      # code_generation: generated project + main.py
├── stage-13/runs/            # experiment_run: results
├── stage-14/experiment_final/# iterative_refine: best run
├── stage-15/analysis.md      # result_analysis
├── stage-16/decision.md      # research_decision: PROCEED/PIVOT
└── knowledge/                # per-stage KB entries
```

## Troubleshooting

- **Config validation error**: `researchclaw validate --config config.yaml`
- **Gate blocked**: run the step with `--auto-approve`, or use `researchclaw approve <run-dir>`.
- **Sandbox can't find Python**: set `experiment.sandbox.python_path` (or create `<run-dir>/.venv`).
- **No LLM configured**: steps run in no-LLM fallback (template) mode; pass `--config config.yaml` with your `llm.*` settings to enable model calls.
