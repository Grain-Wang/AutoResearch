# 024 BAR-Depth merge and no-forward-control protocol

## Frozen question

W06 tests whether the apparent regional utility requires information from a
second patch-model forward, rather than being reproducible by sharpening the
base prediction or by RGB-guided post-processing.  The machine-readable
contract is
[`merge_ablation_v1.json`](../configs/bar_depth/merge_ablation_v1.json).

## Variants

All five variants share the v2 DIODE manifest, DAV2-S base prediction,
positive-median metric alignment, 3x4 action grid, and `K=3` RGB/base-rank
selector:

1. high-pass residual patch merge used by the v2 oracle;
2. affine-aligned patch replacement;
3. aligned patch high frequency without subtracting the base high frequency;
4. RGB-guided joint-bilateral sharpening of the base prediction, with no model
   forward;
5. Gaussian unsharp masking of the base prediction, with no model forward.

The same base and 12 patch predictions are reused across patch variants.  The
two no-forward controls use only the RGB image and base disparity.  Fixed
selector, at-most-three positive-action oracle, and all-12 execution are all
reported with signed utility and scan-cluster confidence intervals.

## Preregistered decision

The strongest no-forward control is selected by fixed-selector primary
reduction.  W06 passes only if the high-pass patch merge has a larger point
estimate and the paired 10,000-replicate scan-bootstrap 95% CI lower bound of
the difference is above zero.

- `GO_PATCH_INFORMATION_NECESSARY`: patch inference contributes information
  not reproduced by the two frozen cheap controls.
- `STOP_PATCH_INFERENCE_NOT_NECESSARY`: the claimed patch mechanism is not
  necessary under the frozen selector and should not proceed to router work.

This gate does not claim that high-pass residual is the best possible merge;
the other patch variants diagnose whether any result is specific to that merge.

## Outcome

`GO_PATCH_INFORMATION_NECESSARY`.

With the fixed RGB/base-rank selector, high-pass residual improves the primary
metric by `6.6236%`; the strongest no-forward control, RGB-guided bilateral
sharpening, changes it by `-0.5948%`.  Their paired difference is `7.2184`
percentage points with scan-cluster 95% CI `[3.7250, 10.3745]`.  The full
machine-readable result is
[`merge_ablation_v1.json`](../results/bar_depth/merge_ablation_v1.json).
