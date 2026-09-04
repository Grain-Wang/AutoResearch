# Step 009: Round-5 M2 Result and Contractive-Interface Killer Gate

## 1. Decision

The frozen M2 is complete, but its positive Claim-W result does not survive the next
strong simple baseline.

```text
frozen M2 integrity = PASS (2,250/2,250 measured rows)
original Claim W vs noncontractive B2 = PASS
Claim D = STOP
Claim E = STOP
Claim W vs contractive-interface B2 = FAIL-CANARY
adaptive largest-first partition = NO-CANARY-GAIN
algorithm novelty = NOT ESTABLISHED
Paper Candidate = FAIL-UNVERIFIED
```

The M2 files remain valid historical evidence for the exact methods they measured.
They are not relabeled or filtered.  The promotion interpretation is superseded because
the original pointwise B2 discarded its accepted Krawczyk image and fed the full
producer tube into the next point.  A stronger pointwise checker can instead propagate
the accepted image, exactly as a compositional slab checker propagates its endpoint.

## 2. Frozen M2 facts

`results/blockstamp/minimal_probe.csv` and its manifest contain the complete declared
grid: six circuit instances, `steps={100,300,1000}`, `slab={1,2,4,8,16}`, five fresh
process replicates, and five recorded methods.  All 2,250 configuration verdicts are
`UNKNOWN`; there are no `UNSUPPORTED` configurations and no confirmed false accepts.
The original aggregate rule reports:

- Claim W `PASS` at slab lengths 2 and 4 against `device_local_pointwise_b2`;
- Claim D `STOP` against `temporal_only`;
- Claim E `STOP` against pointwise and dense resource baselines;
- 1,800 primary non-accept rows invoke whole-run strict fallback, with zero recovered
  `ACCEPT` rows.

The positive W observation is narrow: it concerns accepted step slots or the continuous
prefix under a baseline that always uses the declared predecessor tube.  It does not
show that joint-slab coupling beats a pointwise checker that propagates its own verified
contraction.

## 3. Strengthened killer baseline

For a pointwise accepted obligation at step `k`, let `K_k` be the checker-computed
Krawczyk image.  Strict inclusion proves `K_k` lies inside the declared tube `X_k`.
The strengthened baseline uses `K_k`, rather than all of `X_k`, as the incoming interval
for step `k+1`.  It stops at the first non-`ACCEPT` result.  The fixed-slab comparisons
receive the same treatment by propagating the final image of each accepted slab.

This is a stronger baseline, not a proposed contribution.  Interval contraction and
propagation are standard validated-numerics operations.  The implementation records
every accepted boundary and outgoing interface in
`results/blockstamp/interface_contraction_canary.json`.

The complete six-instance, 100-step canary gives:

| Workload / instance | old pointwise prefix | contractive pointwise | slab 1 | slab 2 | slab 4 | slab 8 | slab 16 | greedy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| diode-RC / nominal | 10 | 25 | 25 | 24 | 24 | 24 | 16 | 25 |
| diode-RC / fast-load | 1 | 13 | 13 | 12 | 12 | 8 | 0 | 13 |
| diode-RC / slow-hot-start | 1 | 6 | 6 | 6 | 4 | 0 | 0 | 6 |
| ring / balanced | 1 | 8 | 8 | 8 | 8 | 8 | 0 | 8 |
| ring / light-load | 4 | 5 | 5 | 4 | 4 | 0 | 0 | 5 |
| ring / slow-load | 1 | 6 | 6 | 6 | 4 | 0 | 0 | 6 |

The contractive pointwise baseline improves the legacy pointwise prefix on all six
instances.  No fixed slab length beats it on any instance.  A largest-first policy over
`{16,8,4,2,1}`, with pointwise fallback and contracted interfaces, also beats it on zero
of six instances.  All accepted interface images contain the Decimal-160 test reference;
that reference is non-rigorous and therefore this is only a diagnostic, not a soundness
oracle.

## 4. Adaptive-partition prior-art boundary

Failure-driven slab splitting or adaptive slab length cannot be introduced as the new
algorithm:

- Kearfott and Xing, [*An Interval Step Control for Continuation Methods*](https://doi.org/10.1137/0731048), SIAM J. Numer. Anal. 31(3), 1994, rigorously choose large continuation steps subject to interval uniqueness verification.
- Duff and Lee, [*Certified homotopy tracking using the Krawczyk method*](https://doi.org/10.1145/3666000.3669699), ISSAC 2024, use a parametric Krawczyk method for certified path tracking and adaptive step selection.
- Lee, [*A priori bounds for certified Krawczyk homotopy tracking*](https://arxiv.org/abs/2512.01355), 2025 preprint, explicitly contrasts repeated adaptive Krawczyk evaluation with a priori step bounds and provides a path-length complexity analysis.
- Immler, [*A Verified ODE Solver and the Lorenz Attractor*](https://doi.org/10.1007/s10817-017-9448-y), JAR 2018, formally verifies a rigorous ODE solver using adaptive step-size control and set splitting.

These works do not target fixed-BE MNA result certificates, but they remove adaptive
verified step/slab selection and failure-driven splitting as stand-alone novelty.  The
current largest-first canary also supplies no empirical reason to pursue that standard
mechanism as the headline.

## 5. Scientific ruling

The current BlockStamp recurrence remains a tested implementation of standard verified
block forward substitution.  Direct device locality and resource efficiency failed the
frozen M2 rules.  The only positive mechanism claim, W, is now explained by an omitted
pointwise contraction baseline on the six-instance canary.

Therefore:

1. Do not use `novel BlockStamp algorithm`, `less wrapping`, `faster checker`, or
   `adaptive certified partition` as contribution statements.
2. Treat the manifest's original `W=PASS` as a result against the registered legacy B2,
   not as a promotion-ready claim.
3. Keep Claim W at `FAIL-CANARY / ITERATE` until a non-equivalent dependency
   representation beats contractive pointwise on the full frozen grid.
4. Keep D and E at `STOP` for the current implementation.
5. Do not run a clean replay or larger circuit matrix for the present method: neither
   can repair the missing algorithmic difference.

The current direction remains a Research Opportunity only at the restricted system
level.  It is not a Paper Candidate.  Reopening the algorithm track requires a new
mathematical state representation or optimization mechanism, theorem-level separation
from validated path tracking/Lohner-style propagation, and a low-cost canary against
contractive pointwise B2 before any further full-grid experiment.

## 6. Reproduction

From `paper2/` with Python 3.12 and MPFR 4.2 or newer:

```bash
python3 -m experiments.run_interface_contraction_canary --steps 100
python3 -m experiments.run_next_round_gate
ruff check .
black --check .
pytest tests/
```
