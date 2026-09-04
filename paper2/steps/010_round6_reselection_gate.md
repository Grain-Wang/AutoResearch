# Step 010: Round-6 P0 Mechanism Reselection Gate

## 1. Intake and authorization boundary

This step incorporates Review Round 5 as the latest reviewer input and performs only
the authorized P0 literature/formula audit.

```text
Round 5 artifact commit = e04011003e519510b52fe2b954e3fdf43ac2bc46
Review Round 5 commit   = 1aeb372386e5df2682d90578222c716b9ee42cc2
Review Round 5 file     = paper2/responce_from_reviewer/review_round5.md
Git intake              = fast-forward, no merge/rebase/force push
Pre-edit working tree   = clean
```

The Round-5 scientific baseline is frozen and is not reinterpreted here:

```text
CURRENT_METHOD = ARCHIVED
Claim W = FAIL-CANARY
Claim D = STOP
Claim E = STOP
Paper Candidate = FAIL-UNVERIFIED
```

No prototype was implemented, no canary or research experiment was run, no M2 result was
regenerated, and no Round-5 artifact was modified.  This step does not authorize P1.

## 2. Gate contract

The two hypotheses admitted to the gate were:

- **A:** a correlation-preserving sparse interface representation, provisionally written
  as \(x=c+A\xi+\Delta\), with a possible charge/history-subspace interpretation;
- **B:** verified factor-witness reuse under local/sparse/low-rank changes of the transient
  MNA system.

A candidate may be selected only if all of the following are already concrete at P0:

1. at least eight highly relevant papers have been checked at full-text formula level;
2. a one-sentence formula-level difference from the closest prior art exists;
3. the representation/witness and exact update are specified rather than named;
4. truncation, compression, or reuse has a sound fail-closed rule;
5. a circuit-specific theorem is needed and is not a generic method with MNA labels;
6. complexity and a programmatic oracle make a minimal canary feasible within scope;
7. the mechanism attacks the current blocker rather than a downstream cost that has no
   value while all full traces remain uncertified.

The detailed 10-paper A matrix and 11-paper B matrix are in
`research/round6_mechanism_prior_art.md`.  Papers without a soundness theorem remain
useful novelty killers but are not misrepresented as verified baselines.

## 3. Candidate A gate

### 3.1 Formula-level equivalence

The proposed normal form is not a new set family:

\[
c+A\xi+[-d,d]
=c+[A\;\operatorname{diag}(d)]
\begin{bmatrix}\xi\\\eta\end{bmatrix},
\qquad (\xi,\eta)\in[-1,1]^{r+n}.
\]

It is simultaneously a zonotope, a vector of affine forms, the degree-one case of a
Taylor model, and a doubleton-style retained linear image plus remainder.  A real
charge/history projection \(T\) has the ordinary exact update

\[
(c,A,\Delta)\mapsto(Tc,TA,T\Delta).
\]

Discarding columns \(A_D\) and paying

\[
[-|A_D|\mathbf1,|A_D|\mathbf1]
\]

into the remainder is standard sound affine/zonotope reduction.  QR reconditioning,
Taylor-model shrink wrapping, constrained latent subspaces, persistent factor IDs, and
bounded-order generator reduction all have direct prior art.

### 3.2 Killer prior art

The most dangerous papers close complementary parts of the proposed story:

- Zgliczyński supplies the doubleton recurrence and QR reconditioning;
- Kochdumper--Althoff supplies sparse dependency IDs, exact addition, and sound order
  reduction;
- Scott et al. supplies exact linear-subspace constraints over zonotope symbols;
- Althoff--Krogh supplies sound zonotope propagation for nonlinear index-1 DAEs;
- Grabowski--Olbrich--Barke supplies transistor-level nonlinear transient circuit
  simulation in which \(x_{n-1},x_{n-2},\ldots\) are explicitly included in the shared
  affine parameter vector;
- Ni et al. supplies charge-form MNA, implicit Euler, zonotope propagation, and
  Krylov/QR reduced history, though its generator deletion is not sound;
- Immler supplies a formally verified affine ODE solver with sound small-symbol
  summarization.

Together these invalidate “affine interface,” “history correlation,” “QR wrapping
reduction,” “sparse shared symbols,” and “drop-to-interval remainder” as contributions.

### 3.3 Missing non-equivalent mechanism

A circuit-specific generator-selection objective could in principle be different, for
example a budgeted choice that maximizes a certified Krawczyk inclusion margin and whose
loss decomposes over device incidence or circuit separators.  Paper2 currently has no
such choice function, no approximation theorem, no charge/history closure theorem, and
no complexity result.  Calling a top-\(k\) norm rule “charge-aware” would not repair this
gap.  Candidate A therefore fails items 2, 3, and 5 of the gate contract.

## 4. Candidate B gate

### 4.1 Formula-level equivalence

For a stamp update \(A_1=A_0+U\Lambda V^T\), exact reuse is already given by

\[
A_1^{-1}=A_0^{-1}-A_0^{-1}U
(\Lambda^{-1}+V^TA_0^{-1}U)^{-1}V^TA_0^{-1}.
\]

For rank one, the family is regular when the verified denominator
\(1+v^TA_0^{-1}u\) excludes zero.  Alternatively, an old inverse action or factor can
be treated as an untrusted preconditioner \(R\), while the checker recomputes

\[
K=\widetilde x-R(A_1\widetilde x-b)
+(I-RA_1)(X-\widetilde x)
\]

with outward rounding and accepts only strict inclusion.  Both are established
verified-numerics patterns.

### 4.2 Killer prior art

- Dreyer writes analog-circuit uncertainty as
  \(A(p)=A_0+\sum_i p_i u_iv_i^T\) and gives interval Sherman--Morrison regularity and
  solution enclosures.  This is direct circuit-stamp verified-update prior art.
- Popova gives optimal rank-one LDR parameter families, verified Woodbury regularity,
  reduced solves, and a parametric Krawczyk method sharing one inverse across multiple
  right-hand sides.
- Carr--de Sturler--Gugercin and Anzt et al. cover sparse preconditioner/factor recycling
  for matrix sequences, although they do not verify solution enclosures.
- Ogita--Rump--Oishi already use an ordinary sparse LU as an untrusted inverse-action
  witness and prove nonsingularity/error bounds from checked residuals.
- Minamihata et al., Frommer--Hashemi, Rump's `VerifyLinSys`, and Rump's current sparse
  solver work provide additional verified witness/fresh-solve killers.

Thus exact cache reuse, old-factor warm starts, symbolic ordering reuse, Woodbury, and
“LU plus checked residual” cannot be the new algorithm.

### 4.3 Missing non-equivalent mechanism and wrong bottleneck

A defensible B would need a new nonlinear-transient circuit theorem: persistent
device/state dependency IDs, an elimination-tree-local verified update rule, a proved
work bound, and deterministic rebase, with acceptance not reducible to Dreyer/Popova
followed by a standard residual checker.  No such rule or theorem is defined.

Moreover, B optimizes factor cost after Round 5 produced zero full-trace `ACCEPT`
configuration verdicts and stopped Claim E.  It does not explain how the certificate
becomes composable.  Candidate B therefore fails items 2, 3, 5, and 7 of the gate
contract.  P0 does not switch from A to B merely because A failed.

## 5. P0 decision

Both literature-count requirements pass, but neither mechanism has a presently
defensible formula-level novelty statement.  Selecting an undefined future theorem
would evade rather than pass the gate.  The only admissible result is:

```text
ROUND6_P0_GATE = ARCHIVE-PAPER2
```

This decision archives the current paper2 algorithm route.  It preserves all frozen
Round-5 artifacts and conclusions and does not claim that independent checking of
transient MNA is an unimportant problem.

## 6. Counterfactual minimal P1 question

There is no authorized P1 because no mechanism was selected.  If the user later reopens
paper2 after supplying or authorizing a *newly specified* non-equivalent theorem, the
first canary must answer one falsifiable question:

> Does the circuit-specific operator itself, under the same saved inputs and outward
> arithmetic, strictly improve the relevant certificate margin/continuous prefix or
> verified-update work over the strongest generic instantiation, while preserving exactly
> the same fail-closed soundness and charging every compression/update/fallback cost?

For an A-like reopening, the mandatory ladder would be contractive pointwise, dense
doubleton/Lohner, generic sound sparse affine reduction, constrained-zonotope invariant
handling, and the circuit-structured rule.  For a B-like reopening, it would be fresh
verified sparse solve, exact matrix cache, ordering-only reuse, stale factor plus full
residual verification, Dreyer/Popova low-rank family verification, and the proposed
local update.  These comparator definitions are a future falsification requirement, not
an experiment plan or permission to implement them.

## 7. Lifecycle lock

After this file is written:

- do not implement either candidate;
- do not run a canary, M2, clean replay, or any other research experiment;
- do not tune parameters or add circuits, BSIM, Verilog-A, SRAM, or another producer;
- do not create a paper draft or `review_round5.md` replacement;
- do not enter P1 or another research round without explicit user authorization.
