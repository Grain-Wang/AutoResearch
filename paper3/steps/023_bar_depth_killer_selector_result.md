# 023 BAR-Depth killer-selector result

## Status

`PARTIAL_G0_PASS / PARETO_PENDING / NOT_PAPER_CANDIDATE`.

This step replaces the earlier positive-capture-only heuristic interpretation
with signed, budget-matched results.  It uses the frozen 2,400-row v2 utility
CSV and does not rerun the depth model.  The machine-readable outputs are:

- [`budget_baselines_v1.json`](../results/bar_depth/budget_baselines_v1.json)
- [`budget_baselines_v1.csv`](../results/bar_depth/budget_baselines_v1.csv)
- [`budget_baselines_v1.json`](../configs/bar_depth/budget_baselines_v1.json)
  (analysis contract)

## K=3 signed result

| Selector | Signed primary reduction | Scan-cluster 95% CI | Harmful selected regions | Mean actions |
| --- | ---: | ---: | ---: | ---: |
| Random, 100 fixed seeds | 2.16% | [0.36%, 4.49%] | 43.87% | 3.00 |
| Fixed spatial uniform | 2.27% | [0.92%, 3.51%] | 43.33% | 3.00 |
| RGB gradient | 4.97% | [2.05%, 7.85%] | 44.00% | 3.00 |
| Base-depth gradient | 6.54% | [3.83%, 9.09%] | 41.00% | 3.00 |
| RGB/base rank combination | **6.62%** | [3.30%, 9.67%] | 43.33% | 3.00 |
| Boosting MDE 2021, exact K | 5.10% | [2.17%, 7.91%] | 44.67% | 3.00 |
| Boosting MDE 2021, official threshold | 5.10% | [2.17%, 7.91%] | 44.48% | 2.99 |
| Oracle, at most three positive actions | **9.66%** | [6.58%, 12.45%] | 0.00% | 2.96 |

The old `uniform_primary_reduction_ratio=8.84%` was all 12 actions and is not a
K=3 uniform baseline.  The corrected all-12 label is preserved in the new
summary without rewriting the historical hash-bound v2 summary.

## G0 oracle-margin gate

At K=3, the strongest current non-oracle selector is RGB/base rank combination.
The budget-matched Boosting MDE score was extracted from official revision
`fa16de03ec985c74aa4a0109b7235d78a4e598e7`.  On both official example images,
the extracted 3x4 scores have maximum absolute difference at most `1e-12` and
identical ranking relative to the official `rgb2gray` and integral-gradient
functions.  The exact-K result is weaker than the existing RGB/base rank
combination, so that rank combination remains the strongest current killer.

The paired oracle-minus-selector primary-reduction difference is 3.04
percentage points with scan-cluster 95% CI `[1.81, 4.44]`.  It passes the frozen
necessary-condition gate of a point margin at least 1.0 percentage point and a
paired CI lower bound above zero.

This is not evidence that a learned router works.  It only establishes that the
oracle retains enough room that a router is not mathematically ruled out by the
currently executable simple selectors.  The high harmful-selection rate gives
a concrete target for signed, risk-aware abstention, but does not prove that the
harm is predictable from permitted features.

## Remaining G0 blockers

W06 has now completed.  Under the fixed RGB/base-rank selector, high-pass
residual obtains `6.6236%` signed primary reduction.  The strongest frozen
no-extra-forward control is RGB-guided bilateral sharpening at `-0.5948%`.
The paired difference is `7.2184` percentage points with scan-cluster 95% CI
`[3.7250, 10.3745]`, so W06 returns `GO_PATCH_INFORMATION_NECESSARY`.

The mechanism controls are informative beyond the gate: affine-aligned patch
replacement obtains `6.1108%`, whereas patch high frequency without subtracting
the base high frequency collapses to `-26.4953%`.  Thus a second patch forward
contains useful information, but removing redundant base-frequency content is
essential.  The optimized shared-intermediate implementation reproduces every
high-pass v2 region row exactly (maximum absolute difference `0` in all utility,
error, and affine columns).

G0 now has one remaining blocker:

1. exclusive-GPU, end-to-end matched-latency whole-image resolution baselines.

No router training or Paper Build is authorized by this partial gate alone.
