# 028 BAR-Depth generic algorithm novelty audit

## Decision

`STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER /
RESEARCH_OPPORTUNITY_JOINT_SET_PROBE_ONLY / W08_CURRENT_CONTRACT_STOPPED /
NOT_PAPER_CANDIDATE`.

The 13-work, 10-axis evidence matrix is
[`bar_depth_algorithmic_nearest_neighbor_matrix_v2.md`](../ideas/bar_depth_algorithmic_nearest_neighbor_matrix_v2.md).
It covers selective regression, risk calibration, learning to defer, heterogeneous
cost routing, and spatially adaptive inference in addition to depth-specific
neighbors.

## What is already covered

- SelectiveNet already learns regression rejection under coverage constraints.
- Post-hoc deferral and multi-expert regression already learn when the base
  model's error exceeds the cost/error of an extra expert.
- Learn then Test and Conformal Decision Theory already calibrate model or
  decision parameters against explicit statistical risk.
- GFNet, AdaFocus, SaccadeCam, LASNet, DynamicViT, and LookWhere already learn
  where to spend spatial computation from cheaper features.
- FrugalML already solves a heterogeneous-cost sequential routing problem under
  an explicit budget; BAR v2 currently has identical unit action costs.

Consequently, `point utility regression + Top-K + one train-calibrated threshold`
is not a defensible algorithmic contribution. The objective/risk contract in
Step 027 remains useful as a fair diagnostic contract, but it cannot authorize
the preregistered W08 as a paper-method experiment.

## Why the Research Opportunity is not yet closed

The frozen canary still establishes a baseline defect: patch utility is signed
and heterogeneous, simple selectors leave oracle headroom, and some selected
sets harm the final image. This scientific fact is independent of the failed
novelty claim.

One non-equivalent mechanism probe remains: estimate a joint, budget-conditioned
distribution for the **sum of utilities of the adaptively selected set**, with a
selection-aware lower confidence bound. It must beat three generic killers using
the same features and folds:

1. point utility Top-K;
2. Learn-then-Test calibration of the point-score decision family;
3. direct conformal decision calibration of that family.

The probe must demonstrate that within-image dependence changes selected-set
risk and useful utility. Otherwise it collapses to generic calibration and the
fixed decision is final `STOP_NOVELTY`.

## Execution boundary

No DIODE-train patch-label generation or router training is authorized by this
step. Formal W07 v2 and replicate-wise baseline-envelope analysis remain useful
G0 falsifiers. A new joint-set protocol may be preregistered only after those
gates show that accuracy--latency space still exists.
