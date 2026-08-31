# 026 BAR-Depth novelty audit

## Decision

`CONDITIONAL_CONTINUE / SIMPLE_TOPK_ROUTER_NOT_NOVEL / NOT_PAPER_CANDIDATE`.

The nearest-neighbor matrix is recorded in
[`bar_depth_nearest_neighbor_matrix.md`](../ideas/bar_depth_nearest_neighbor_matrix.md).
It changes the order of work from the reviewer draft: the literature gate is a
P0 gate and must precede router training.

## Findings

1. Boosting MDE already performs content-adaptive patch filtering and expansion
   from image edges.  RGB/base-gradient selectors are therefore killer
   baselines, not weak diagnostics.
2. SaccadeCam already learns an attention map for allocating a fixed number of
   high-resolution foveae for monocular depth.  Replacing an edge score with an
   MLP and taking Top-K would not be a defensible algorithmic contribution.
3. PatchFusion, PatchRefiner, PRO, PatchRefiner V2, and URGT cover learned
   fusion, fixed/random patch processing, and efficient multi-patch inference.
   InfiniDepth covers arbitrary-resolution prediction.  BAR-Depth cannot claim
   novelty in any of those components.
4. Depth Pro makes matched-latency whole-image high-resolution inference a
   mandatory killer and shows why the current per-image GT scale-aligned DAV2-S
   canary cannot support an absolute metric-depth claim.

## Gate

The opportunity may continue only as a signed, harm-aware, budgeted action
selection problem.  The Ridge/MLP probe is diagnostic: it can establish whether
cheap base features carry routable signal, but it cannot upgrade the direction
to a Paper Candidate.

The method gate requires all of the following:

- a calibrated signed-utility distribution rather than only a point score;
- budget-conditioned selection with train-only calibrated abstention;
- an explicit harmful-action risk constraint;
- a measurable advantage over point regression/ranking, Boosting MDE,
  base-gradient selection, and matched-latency whole-image inference.

If the final method collapses to point prediction plus Top-K, the fixed decision
is `STOP_NOVELTY`.  If the oracle itself is dominated by matched-latency direct
inference, the fixed decision is `STOP_NO_PARETO_SPACE`.
