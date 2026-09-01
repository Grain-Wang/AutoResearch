# 027 BAR-Depth objective and harm-risk contract

## Decision

`PASS_OBJECTIVE_CONTRACT_V2 / REDEFINE_RANK_PRESERVING_TARGET /
W08_BLOCKED_BY_NOVELTY_AND_FORMAL_PARETO / NOT_PAPER_CANDIDATE`.

The frozen target-alignment audit is implemented by
[`audit_router_target_alignment.py`](../experiments/bar_depth/audit_router_target_alignment.py).
It reads the byte-bound `oracle_patch_utility_v2.csv`; v1 artifacts and the v1
router contract remain unchanged.

## Target-alignment result

For each image and `K in {1,3,6}`, the audit compares exact Top-K sets obtained
from raw utility `primary_utility_sum` and the v1 label
`primary_utility_sum / weight_sum`. All reported reductions and recovery values
are evaluated with raw utility, and uncertainty resamples the 20 complete scan
clusters 10,000 times.

At the primary `K=3`, mean set Jaccard is `0.927`, but the normalized target
recovers only `0.93696` of the raw-utility oracle, below the preregistered
`0.95` threshold. The two targets choose different sets on `14%` of images.
Moreover, 32 of 2,400 regions across 14 images have `weight_sum=0`; their raw
utility is exactly zero, making the literal v1 ratio `0/0`. The audit assigns
those scores zero only to quantify disagreement. It does not retroactively make
the v1 label well-defined.

The gate therefore returns `REDEFINE_RANK_PRESERVING_TARGET`. The v2 training
target is

$$
t_i(x)=\frac{u_i(x)}{E_0(x)},
$$

where `E_0(x)>0` is the image-level base primary error summed over all 12
non-overlapping cells. The denominator is constant for every action in one
image, so `t_i` and raw `u_i` have identical within-image order. Ground truth is
used to construct training labels only; `E_0` is not an inference feature.

## Unified utility and set objective

Only `u_i` denotes action utility:

$$
u_i=E_i(D_0)-E_i(D^{(i)}),\qquad
U(S)=\sum_{i\in S}u_i.
$$

The v2 probe has unit action cost `c_i=1` and reports `K in {1,3,6}` from one
fitted score model. It is therefore **selective regional refinement**, not a
claim of heterogeneous-cost allocation. Exact-K is a ranking diagnostic. The
primary track chooses at most K actions and may abstain.

## Harm-risk calibration

The primary harm event is image-level net degradation,

$$
H(S)=\mathbf 1[U(S)<0].
$$

For every score-based method, 101 thresholds are the quantiles `0.00, 0.01,
..., 1.00` of train out-of-fold scores. A threshold is feasible only when the
one-sided 95% Clopper--Pearson upper bound on `Pr[H(S)=1]` is at most `0.10`.
Among feasible thresholds, train-OOF raw signed utility is maximized; ties use
the higher quantile and then fewer actions. Candidate scores equal to the
threshold are included, score ties use ascending region id, and Top-K truncation
is stable. If no threshold is feasible, the frozen fallback is `abstain_all`.

The same calibration is applied to every score-based baseline. In addition to
the event rate and its upper bound, evaluation reports negative-utility mass,
90% harm CVaR, harmful-action count, raw signed reduction, AbsRel safety, oracle
regret, and actual action count.

## Execution dependency

The machine-readable contract is
[`router_probe_v2.json`](../configs/bar_depth/router_probe_v2.json). W08 remains
blocked until the generic-algorithm novelty audit returns CONTINUE and formal
exclusive W07 v2 returns `GO_REGIONAL_ORACLE_PARETO_FORMAL_V2`. Passing this
objective contract does not establish routability or algorithmic novelty.
