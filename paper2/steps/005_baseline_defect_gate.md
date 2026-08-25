# Step 005: Baseline Defect Gate

## Canary mechanism

The first non-corruption case is the passive nodal system
`diag(1, epsilon) x = (1, epsilon)`.  It corresponds to two uncoupled Norton branches
with conductances `1` and `epsilon` siemens and unit source voltage.  Thus its bad
conditioning is a circuit parameter mechanism, not a modified Jacobian, permutation,
or stamp.  The exact root is `(1,1)`.

A loose producer returning `(1,0)` has normalized infinity residual `epsilon` while
its infinity-norm forward error is one volt.  For `epsilon <= 1e-5`, a residual-only
threshold of `1e-5` accepts it.  A declared radius-`1e-3` tube excludes the analytic
root, so a sound local-root checker must not accept that certificate.

## Current evidence and boundary

The deterministic sweep contains 24 unfiltered cases: 12 conductance/condition levels
times two center-precision labels.  It establishes the narrow fact that a natural
near-singular MNA mechanism can separate residual from forward error.  It does not yet
establish prevalence in mature SPICE workloads or demonstrate nonlinear transient
severity.  Gate 1 is therefore **PASS-CANARY / REAL-WORKLOAD-UNVERIFIED**.  The next
required extension is a nonlinear diode or ring-oscillator tolerance sweep using an
independent high-precision root.

Rebuild with:

```bash
PYTHONPATH=paper2 python3 -m experiments.generate_numerical_defects \
  --output paper2/results/blockstamp/numerical_defect_cases.csv
```
