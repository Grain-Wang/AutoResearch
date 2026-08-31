# Response to Review Round 3

We accept the central Round 2--3 diagnosis.  The repository now contains machine-run
soundness-chain and operator implementation canaries, but it still lacks theorem-level
novelty closure, B2-strong, a matched component ladder, and the nonlinear M2 signal
needed for a Paper Candidate.  This response reports the generated evidence without
turning canary success into a theorem, novelty, or efficiency claim.

## 1. Deduplicated review diagnosis

The Round 2--3 requests reduce to five gate-changing obligations:

1. **Close the soundness premise.**  The real preconditioner operator must be
   checker-verifiably nonsingular.  The old A5 permits `C = 0`; for
   `F(x) = x + 2`, `X = [-1, 1]`, and `x_bar = 0`, this yields a strict image inclusion
   despite the absence of a root.  The Decimal special-function canary is not a
   rigorous certificate backend.
2. **Create one executable algorithmic object.**  BlockStamp must have a single frozen
   definition of `M`, `D_k`, `L_k`, `R_k`, `U_k`, and `C`, an outward-rounded recursive
   operator, an exact-real enclosure argument, and a dense-action cross-check.  A
   generic block forward solve is not claimed as novel.
3. **Complete the minimum transient semantics.**  R/C/source/diode Backward Euler
   residuals, history terms, point Jacobians, and interval Jacobians must be checked
   against analytic or independent multiprecision roots before a circuit certificate
   is reported.
4. **Use a component-matched killer baseline.**  B2-strong must share the arithmetic
   backend, device/MNA semantics, candidate, tube, scaling, ordering, factor operator,
   thread count, and hardware with BlockStamp.  Dense-slab and a verified-sparse linear
   kernel are correctness and efficiency comparators, not straw baselines.
5. **Show a nonlinear transient signal before expanding scope.**  Diode-RC and a
   three-stage ring oscillator are the minimum two workloads.  Results must include
   rejected/unsupported runs and the complete generation, check, and fallback cost.

The newly identified Chen--Hashimoto block-Krawczyk, Schwandt interval cyclic
reduction, and Frommer--Hashemi factorized-Krawczyk lines are treated as high-threat
prior art.  Until their proof objects are compared against the frozen recurrence, the
algorithmic novelty status remains `POTENTIAL / UNVERIFIED`.

## 2. Scope of this execution

This response and `steps/008_next_round_gate.md` freeze the evidence contract.  The
authorized execution produced the arithmetic, minimum MNA, pointwise-checker, and
operator canaries listed below.  It did not run the matched nonlinear M2 experiment.
The implementation scope was limited to:

- the nonsingular-`C` soundness correction and counterexample regression;
- a directed-rounded rigorous arithmetic microkernel;
- the BlockStamp operator and independent dense-action canary;
- minimum BE MNA and a dense pointwise B2 canary; and
- only after those pass, the matched diode-RC/ring-oscillator component ladder.

We do not expand to SRAM, op-amps, Verilog-A, BSIM, BDF2, a second producer, a general
certificate format, or large benchmark matrices at this gate.  Recovery and discrete
specification monitoring remain downstream system work.

## 3. Generated evidence registry

All values below are read from the named machine-generated JSON files.  The artifacts
bind source/configuration hashes to commit `1fc3d6dd2eb2f38f7df2025fe27e9969017f40ae`,
but each records `dirty_worktree=true`; clean independent replay remains outstanding.

| Evidence object | Artifact | Machine-reported result | Claim boundary |
| --- | --- | --- | --- |
| Numerical-defect motivation | `results/blockstamp/numerical_defect_cases.csv` + `.manifest.json` | `PASS`: 24 actual float32/float64 residual-stopped solves all stopped at iteration 0 with the exact root outside the tube and 1 V forward error; the executable checker returned `UNKNOWN` in all 24 cases and had 0 false accepts. | Static diagonal passive-MNA motivation only; not a nonlinear transient defect or method advantage. |
| Directed-rounding arithmetic | `results/blockstamp/rigorous_backend_summary.json` | `PASS`: 400,056 attempted; 400,044 supported; 12 structured unsupported; 0 containment violations.  Eight operations each ran 50,000 random and 7 fixed edge cases. | Directed-rounding implementation audit, not a formal proof of MPFR or the full TCB. |
| Restricted BE MNA | `results/blockstamp/mna_canary.json` | `PASS`: RC 100/100 and diode-RC 100/100 steps `ACCEPT`; 1,800 Jacobian samples with 0 violations; 17 negative cases with 0 false accepts. | Restricted BE MNA plus dense pointwise-checker canary, not B2-strong or general SPICE soundness. |
| BlockStamp operator | `results/blockstamp/operator_canary.json` | `PASS`: 2,400 supported nonsingular systems over all 12 dimension/slab cells, including 24 nonzero-width interval-RHS cases checked against exact Fraction coordinate hulls; 0 containment violations; one singular system returned `UNSUPPORTED`.  The largest absolute enclosure inflation over the exact hull was 0.1321725812626729. | `CLAIM-I: IMPLEMENTATION-CANARY-PASS`; the scale-dependent inflation observation does not establish Claim W, novelty, or efficiency. |
| B2 fairness | `results/blockstamp/b2_fairness.json` | `ITERATE / B2-CANARY-ONLY`: 200 easy accepts and 17 known-bad cases with 0 confirmed false accepts; required matched hashes are incomplete and verified-sparse B2-strong is unimplemented. | Cannot support killer-baseline fairness or M2. |
| Claim-level decision | `results/blockstamp/next_round_gate.json` | `M0 PASS-CANARY`; `M1 ITERATE`; `M2 NOT-STARTED`; `Paper Candidate FAIL-UNVERIFIED`. | No performance claim. |
| Four-level attribution ladder | `results/blockstamp/component_ladder.csv` | Not generated. | Claims W/D/E untested. |
| Nonlinear transient probe | `results/blockstamp/minimal_probe.csv` | Not generated. | Real nonlinear mechanism and utility untested. |

### Reproduction commands

Run from `paper2/` under Python 3.12 with the recorded MPFR backend available:

```bash
python3 -m experiments.generate_numerical_defects --output results/blockstamp/numerical_defect_cases.csv --seed 17
python3 -m experiments.run_rigorous_backend --samples 50000 --seed 20260831
python3 -m experiments.run_mna_canary --steps 100 --step-size 1e-05
python3 -m experiments.run_operator_canary --cases-per-grid 200 --dense-canary-cases 2 --seed 20260831
python3 -m experiments.run_next_round_gate
```

The first three commands regenerate their canary artifacts; the final command reads
the current artifacts and regenerates the claim-separated gate decision.

## 4. Claims after consolidation

- **Baseline defect:** `PASS-CANARY / REAL-WORKLOAD-UNVERIFIED`.  The regenerated
  24-case grid now performs actual per-operation float32/float64 producer arithmetic,
  uses an exact-Fraction root oracle, and obtains verdicts only from the executable
  pointwise checker.  Loose residual stopping yields 24 roots outside the declared
  tube with 1 V forward error; all receive `UNKNOWN`, with 0 false accepts.  A strict
  threshold control performs one Newton update and is accepted at the exact root.
  This remains a static diagonal linear motivation canary, not evidence that nonlinear
  transient SPICE commonly fails or that BlockStamp outperforms a baseline.
- **Claim S:** `M0 PASS-CANARY`.  The checker-verifiable `C=M^{-1}` premise,
  directed-rounding audit, restricted BE semantics, and registered negative cases have
  machine implementation evidence with no observed violation.  The Krawczyk theorem
  remains conditional on the stated TCB; this is not a formal proof or a general-SPICE
  soundness result.
- **Claim C:** a downstream standard composition consequence of a corrected S-param
  contract, not headline novelty.
- **Claim I:** `IMPLEMENTATION-CANARY-PASS` on the registered 2,400 nonsingular systems
  and one fail-closed singular case.  This supports the tested implementation's exact
  dense-action containment property, not theorem-level novelty, device-aware benefit,
  or efficiency.
- **Claim W:** no present claim of reduced wrapping.  The strengthened operator canary
  includes 24 nonzero-width interval-RHS cases and remains sound, but its largest
  absolute excess width over the exact coordinate hull is 0.1321725812626729 on this
  unnormalized synthetic scale.  This is a diagnostic warning, not a matched B2
  comparison.  Reordering the same interval expression is insufficient unless a
  dependency-preserving representation or a matched empirical advantage is shown.
- **Claim E and Claim D:** hypotheses only.  Runtime, memory, certificate-size, and
  device-locality language must remain conditional until the component ladder passes.
- **Claim R:** only the dependency rule is retained: recovery starts at the failed slab
  and cached suffix certificates are replayed only while every new outgoing enclosure
  is contained in the stored next-slab incoming assumption.  Lower fallback cost is
  unverified.
- **Claim P:** a non-novel discrete monitor consequence and outside the current gate.

The intended scope is fixed-step BE, supported regular index-1 MNA, supported devices,
and local roots of the declared discrete equations.  No continuous-time, global-root,
general-SPICE, modern-compact-model, or silicon guarantee is made.

## 5. Gate and paper status

The project remains:

- `Research Opportunity: PASS` under the narrow fixed-discretization certification
  formulation;
- `M0 soundness chain: PASS-CANARY`;
- `M1 operator gate: ITERATE` because novelty is unresolved even though Claim I's
  implementation canary passed;
- `M2 matched nonlinear probe: NOT-STARTED` because B2-strong, complete fairness hashes,
  and the component ladder do not exist;
- `Paper Candidate: FAIL / UNVERIFIED`.

Step 008 retains the preregistered `STOP-S`, `STOP-W`, `STOP-E`, and `STOP-D` rules.
The immediate gate-changing work is recurrence-specific novelty closure and a genuine
verified-sparse B2-strong/fairness path, followed by the matched M2 ladder.  Passing M2
can justify at most `PRE_PAPER_CANDIDATE`; full Paper Candidate still requires clean
independent replay, stable nonlinear evidence under killer baselines, end-to-end
accounting, and evidence that gains are not implementation artifacts.
