# 025 BAR-Depth matched-latency protocol

## Frozen question

W07 asks whether the regional action space retains any accuracy advantage over
simply spending the same latency on a larger whole-image Depth Anything V2-S
forward.  The machine-readable contract is
[`matched_latency_v1.json`](../configs/bar_depth/matched_latency_v1.json).
This is a G0 killer test, not a router result.

## Accuracy comparison

The 200-image DIODE v2 manifest, positive-median alignment, boundary-weighted
AbsRel primary metric, and DAV2-S revision/weights remain unchanged.  Regional
accuracy uses the frozen high-pass residual merge at `K=3`; both the fixed
RGB/base-rank selector and the at-most-three positive-action oracle are
reported.  Whole-image candidates use input sizes 518 through 1022 in steps of
56.  Each whole-image prediction receives its own positive median scale, as is
standard for a relative-depth prediction; regional patches remain aligned to
the base prediction and therefore retain the base scale.

## Latency comparison

Formal timing requires one exclusive GPU.  RGB is preloaded, while model
preprocessing, synchronized forward, output resize, regional scoring, patch
extraction, the three-patch batch, and merge are timed end to end.  Disk I/O and
GT metric computation are excluded from both methods.  Five images warm each
shape before one measurement on each of 20 fixed cross-scan images.

A whole-image point is latency-feasible only if both its p50 and p95 do not
exceed the corresponding regional pipeline values.  Among feasible candidates,
the one with the lowest aggregate primary error is the killer; this deliberately
gives direct inference its strongest admissible result.

## Preregistered decision

- `GO_REGIONAL_ORACLE_PARETO`: the regional `K=3` oracle beats the best feasible
  whole-image candidate and the paired scan-bootstrap 95% CI lower bound of the
  reduction difference is above zero.
- `STOP_DIRECT_RESOLUTION_DOMINATES`: the point difference or its paired lower
  bound is non-positive.
- A fixed heuristic win is reported but is not required at G0, because W09-W11
  test whether a learned harm-aware selector can close the oracle gap.

Passing this gate does not establish algorithmic novelty or router learnability.

## Shared diagnostic outcome

At the user's explicit request, the same benchmark was also run while sharing a
GPU.  The artifact is permanently labeled
`COMPLETE_SHARED_DIAGNOSTIC_MATCHED_LATENCY`; it records the foreign compute
PIDs observed before and after the run, and the default analyzer rejects it.

The shared diagnostic gives regional `K=3` p50/p95 latency of
`2565.70/3419.24 ms`.  Whole-image 518 is `93.22/229.05 ms`, and even 1022 is
`320.10/680.46 ms`, so all ten direct candidates are provisionally feasible.
The best direct accuracy remains the 518 baseline at `0%`; every larger input
is worse.  The regional fixed selector is `6.6236%` with scan-cluster 95% CI
`[3.2989%, 9.6459%]`; the regional oracle is `9.6600%`, and its paired margin
over the best feasible direct point has CI `[6.5125%, 12.3499%]`.

This yields
`PROVISIONAL_SHARED_DIAGNOSTIC_GO_REGIONAL_ORACLE_PARETO`, with
`formal_gate_completed=false`.  It validates the code path and strongly
predicts the formal decision, but it does not complete G0.  The exclusive queue
remains the required formal evidence.
