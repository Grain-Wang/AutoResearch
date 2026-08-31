# Step 003: Formal Soundness Contract

## 1. Scope, objects, and verdicts

This contract concerns roots of fixed-step Backward Euler (BE) equations, not
continuous-time DAE error, physical-model error, or silicon behavior.  The checker
returns `ACCEPT`, `UNKNOWN`, or `UNSUPPORTED`; failure of an inclusion test is not a
proof that a tube contains no root.  Every result below is conditional on correct
checker semantics, outward-rounded interval arithmetic, input binding, and certificate
parsing.

For a slab `S = {a, ..., b}`, let `y` be the incoming interface state and

\[
G_S(y,z) = (F_a(y,x_a), F_{a+1}(x_a,x_{a+1}),\ldots,
F_b(x_{b-1},x_b)),\qquad z=(x_a,\ldots,x_b).
\]

`Y` and `X` are closed, bounded, nonempty real interval boxes, and `X` has positive
width in every coordinate.  `int(X)` is its ordinary Euclidean interior, and the
outgoing projection is `P_b z = x_b`.  A center `z_bar` must lie in `int(X)`.

The first-version preconditioner has one meaning only.  After the checker has applied
the input-bound permutation and nonzero diagonal scaling, it reconstructs a finite
point midpoint matrix `M` from its own slab Jacobian enclosure.  Each stored binary
floating-point entry of `M` denotes its exact dyadic real value.  Producer-supplied
permutations, scaling, factors, or approximate inverses are untrusted hints: they may
accelerate verification, but they do not define `M`.  Once the checker proves `M`
nonsingular, the theorem's fixed real operator is

\[
C := M^{-1}.
\]

The checker need not form `C`; it applies this exact real inverse through verified
block solves as specified in `007_blockstamp_operator_spec.md`.

## 2. Executable assumptions

| ID | Mathematical assumption | Checker obligation |
| --- | --- | --- |
| A1 | The normalized netlist has the supported regular index-1 BE structure. | Reject unsupported topology, device, state layout, inconsistent initial state, or singular structural pattern. |
| A2 | `G_S` is continuously differentiable in `z` on an open neighborhood of `Y x X`. | Use only supported smooth device regions; split a box crossing a piecewise-model boundary or return `UNKNOWN`. |
| A3 | `[J_z G](Y,X)` encloses every real `J_z G(y,z)`. | Reconstruct all device-local interval stamps with outward rounding. |
| A4 | `[G](Y,z_bar)` encloses every `G(y,z_bar)`. | Reconstruct values and BE history terms independently of the producer. |
| A5 | The checker-defined point matrix `M` is nonsingular, and `C` is exactly `M^{-1}`. | Recompute `M`; verify every diagonal-block invertibility witness and the permutation/scaling semantics; reject or return `UNKNOWN` if any witness is inconclusive. |
| A6 | Every reported `VSolve(D,B)` encloses `{D^{-1}b : b in B}` and every assembled remainder/operator bound is outward rounded. | Validate dimensions, sparse indices, triangular operations, interval products, and rounding bounds.  A small ordinary `D-LU` residual is insufficient. |
| A7 | The certificate, normalized netlist, method, grid, semantics, ordering, scaling, and checker-reconstructed `M` are bound to the accepted digest; all interval endpoints are finite and ordered. | Recompute canonical hashes; reject mismatches, NaNs, reversed intervals, unsupported infinities, or a different matrix bit pattern. |

`A1` is a support condition, not a theorem that every SPICE netlist is index-1.  The
first implementation may conservatively return `UNSUPPORTED` whenever its structural
test is inconclusive.

### 2.1 Machine-checkable invertibility witness

In the block-lower-bidiagonal ordering, `M` has diagonal blocks `D_k`.  The frozen
first implementation applies outward-rounded interval Gaussian elimination to each
exact-dyadic point block.  The checker records its deterministic row swaps and an
interval enclosing every exact elimination pivot.  It may report a supported solve
only when every pivot interval strictly excludes zero.  Induction over the elimination
steps then proves that exact elimination has a nonzero pivot in every column, so
`D_k` is nonsingular.  Since a block-lower-triangular matrix is nonsingular exactly
when all diagonal blocks are, these per-block witnesses prove `M` nonsingular and make
`C=M^{-1}` well-defined.

An optimized kernel may instead use an untrusted point approximate inverse `Q_k` and
prove, with outward rounding,

\[
\overline{\lVert I-Q_kD_k\rVert_\infty}<1,
\]

or use another verified factorization theorem.  Such a kernel is admissible only if it
proves the same two postconditions: `D_k` is nonsingular and its returned interval
encloses the exact real inverse action.  Merely observing nonzero floating-point pivots
without enclosing their rounding error, or a small ordinary factor residual, does not
discharge A5--A6.

## 3. Why nonsingularity is necessary

The former condition “the checker encloses `C v` and `C A`” was insufficient.  In one
dimension, take

\[
F(x)=x+2,\qquad X=[-1,1],\qquad z_bar=0,\qquad C=0.
\]

Then the nominal Krawczyk image is `K(X)={0}`, which lies strictly inside `X`, although
`F` has no zero in `X`.  Thus strict inclusion alone cannot compensate for a singular
`C`.  Under the present contract, `C=0` cannot equal `M^{-1}`; a missing or failed
invertibility witness must stop the checker before inclusion and yield
`UNKNOWN/UNSUPPORTED`, never `ACCEPT`.

## 4. Strict inclusion and theorem version

For boxes `[K]=[k_lo,k_hi]` and `X=[x_lo,x_hi]`, the checker proves

\[
[K]\subset\operatorname{int}(X)
\]

only when, for every coordinate `i`, the outward-rounded endpoints satisfy the strict
real inequalities

\[
x_{lo,i}<k_{lo,i}\quad\text{and}\quad k_{hi,i}<x_{hi,i}.
\]

Equality at either boundary, an unbounded endpoint, or an undecidable comparison does
not pass.  No implementation epsilon may replace these strict comparisons.

The theorem used here is the finite-dimensional Krawczyk inclusion theorem with a
nonsingular fixed real preconditioner, as catalogued in
`004_theorem_prior_art_closure.md` (Krawczyk and Neumaier, *An Improved Interval Newton
Operator*, JMAA 118(1), 1986, DOI `10.1016/0022-247X(86)90303-3`).  The contract uses
its componentwise strict-inclusion existence-and-uniqueness conclusion.  It does not
silently substitute an arbitrary singular linear map for the theorem's
preconditioner.

## 5. Theorem S-fixed

Fix `y0 in Y`.  Let `z_bar in int(X)`, let the checker-defined `M` satisfy A5, and set
`C=M^{-1}`.  Define

\[
K_{y_0}(X)=z_bar-CG_S(y_0,z_bar)
 +(I-C[J_zG](\{y_0\},X))(X-z_bar).
\]

**Theorem S-fixed.** Under A1--A7, if an outward-rounded checker enclosure
`[K_{y0}]` contains the exact Krawczyk image above and the checker proves
`[K_{y0}] subset int(X)`, then `G_S(y0, .)` has exactly one zero in `X`.  The checker
may emit `P_b X` as an enclosure of that root's outgoing state.

The uniqueness conclusion is only for roots of the fixed discrete equation with this
fixed `y0` inside the declared box `X`.  It says neither that no root exists outside
`X` nor that a continuous-time trajectory is enclosed.

### Proof skeleton

A2--A4 provide the hypotheses and mean-value enclosure required by the cited
Krawczyk theorem.  A5 supplies its missing nonsingular fixed real operator, while A6
ensures the checker result contains that operator's exact real action.  The checked
strict inclusion therefore yields existence and uniqueness in `X`; projection
preserves containment.  A7 binds this statement to the accepted instance.

This proof does not use, and the checker does not currently claim, a separate theorem
that every member of `[J_zG]` is nonsingular or that a solution map is continuous.

## 6. Theorem S-param

For a non-singleton incoming box `Y`, one checker-reconstructed `M`, and the same fixed
`C=M^{-1}` for every `y in Y`, define the uniform image

\[
K_Y(X)=z_bar-C[G](Y,z_bar)
 +(I-C[J_zG](Y,X))(X-z_bar).
\]

**Theorem S-param.** Under A1--A7, if an outward-rounded `[K_Y]` contains the exact
uniform image and `[K_Y] subset int(X)`, then, for every `y in Y`, there exists exactly
one `z(y) in X` satisfying `G_S(y,z(y))=0`.  Consequently,

\[
\{P_bz(y):y\in Y\}\subseteq P_bX.
\]

This means uniqueness in `X` separately for each fixed `y`; it does not say roots for
different inputs are equal, globally unique, injectively parameterized, or continuous
in `y`.

### Proof skeleton

Fix an arbitrary `y in Y`.  Inclusion monotonicity and the use of one fixed `C` give
`K_y(X) subset K_Y(X) subset int(X)`.  Apply S-fixed to this `y`, then universally
quantify over `Y` and project the common box `X`.  Checking only the midpoint of `Y`,
or changing `C` with `y` without rebuilding a uniform enclosure, cannot establish
S-param.

## 7. Compositional contract

Let slab `j` accept under incoming assumption `Y_j` and emit `O_j`.  Composition is
valid only if the certified initial set is contained in `Y_1` and
`O_j subset Y_{j+1}` at every boundary.  Induction with S-param then establishes a
locally unique discrete continuation inside each declared slab tube for every allowed
initial state.  Dependency is directional: changing `O_j` may invalidate every later
slab, as specified in `006_selective_recovery_contract.md`.

## 8. Accepted implementation claims

- Fault injection is an implementation regression test, not a proof of soundness.
- A producer hint can influence acceptance only through checker-verified premises; it
  never changes the exact definition `C=M^{-1}`.
- “Bad hints only cause rejection or extra work” remains conditional on the TCB and
  supported semantics being correct.
- Piecewise Level-1 MOS boxes crossing cutoff/triode/saturation boundaries must be
  split into smooth regions or yield `UNKNOWN`; a center-point branch is invalid.
- Discrete monitors reason only about certified sample-point boxes.  Inter-sample peak
  and settling claims remain unsupported.

## 9. Open implementation obligations

This document instantiates established Krawczyk reasoning; neither S-fixed nor S-param
is a novelty claim.  The mathematical contract still requires executable regression
tests for the singular-`C` counterexample, a directed-rounded arithmetic backend,
complete BE MNA semantics, and zero false accepts on known corrupt certificates.
`007_blockstamp_operator_spec.md` defines the next algorithmic obligation: prove and
cross-check that the block recurrence encloses the exact action of this same fixed
operator `M^{-1}`, then isolate any efficiency or enclosure-strength benefit against
component-matched baselines.
