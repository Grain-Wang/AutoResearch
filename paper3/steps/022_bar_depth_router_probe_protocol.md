# 022 BAR-Depth router-probe protocol

## Status

`PREREGISTERED / EXECUTION_PENDING / NOT_PAPER_CANDIDATE`.

The machine-readable contract is
[`router_probe_v1.json`](../configs/bar_depth/router_probe_v1.json).  This step
freezes the evaluation before building DIODE-train labels or inspecting router
results.  The existing 200-image DIODE validation manifest is a one-time final
evaluation set and must not be used for feature choice, hyperparameter choice,
abstention calibration, or model selection.

## Data isolation

- Build a DIODE-train manifest with seed `271828`, selecting at most 20 frames
  per scan by stable content hash.
- Use scan-grouped five-fold cross-fitting inside DIODE train.
- Require a zero intersection between train and validation `scan_id` values.
- Patch predictions and GT are permitted only for producing training labels and
  evaluating frozen predictions.  The inference router cannot read them.
- The frozen validation manifest SHA256 is
  `602b5886af89fa3389705a2c61e7b32e71ce5d6b6d049d4d3dd984855fd817ff`.

## Action and target

The candidate space remains the frozen 3x4 grid.  Report `K` in `{1, 3, 6}`,
with `K=3` primary.  Two tracks prevent a selective method from receiving an
unfair advantage:

1. `exact_k_ranking`: every selector executes exactly K actions;
2. `at_most_k_train_calibrated_abstention`: learned and heuristic thresholds
   are calibrated on train scans only, and every method reports actual action
   count.

For cell `i`, the regression label is
`primary_utility_sum / weight_sum`.  It is signed: negative labels are harmful
actions and cannot be truncated during training or evaluation.

## Inference firewall

Allowed features are frozen RGB/base-gradient histograms, base-disparity
summary statistics, normalized cell position, and pooled features already
computed by the base encoder.  GT depth/mask, patch predictions, patch affine
parameters, observed utility, paths, dataset/scene/scan identifiers, and any
post-action information are forbidden.  A code-level assertion must validate
the feature schema before every fit and prediction.

## Diagnostic models and killers

Ridge and the frozen two-layer MLP are routability diagnostics, not the paper
method.  Every result must compare random Top-K with 100 fixed seeds, fixed
spatially uniform Top-K, RGB/base/rank-gradient selectors, budget-matched
Boosting-MDE edge-density selector adapted to frozen BAR actions, point-utility
Ridge/MLP, oracle at-most-K, and all 12 actions.

The primary metric is signed primary-error reduction divided by base primary
error.  Also report signed ordinary-AbsRel reduction, harmful-selection rate,
oracle regret, actual selected count, and diagnostic-only positive capture.
All method differences use 10,000 paired scan-cluster bootstrap draws.

## Frozen gate

At `K=3`, all of the following are required:

- point improvement over the strongest budget-matched baseline of at least
  1.0 primary-reduction percentage point;
- paired 95% CI lower bound for that improvement greater than zero;
- recovery of at least 80% of oracle signed gain;
- paired ordinary-AbsRel relative-degradation CI upper bound at most 1%;
- selector p50 overhead at most 5% of end-to-end latency;
- all five seeds reported, without choosing a favorable seed.

Passing returns `GO_ROUTABILITY_ALGORITHM_GATE_PENDING`, not Paper Candidate.
Failure returns the first applicable frozen STOP reason.  A diagnostic MLP that
passes this gate still requires the novelty mechanism in Step 026.
