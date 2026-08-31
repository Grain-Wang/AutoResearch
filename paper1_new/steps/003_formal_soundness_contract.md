# Step 003: Formal Soundness Contract

## 1. Scope and verdicts

This contract concerns roots of the fixed-step Backward Euler (BE) equations, not
continuous-time DAE error or physical-model error.  The checker returns `ACCEPT`,
`UNKNOWN`, or `UNSUPPORTED`; it never infers soundness from a producer convergence
flag.  Every theorem below is conditional on correct checker semantics, outward-rounded
interval arithmetic, input binding, and certificate parsing.

For a slab `S = {a, ..., b}`, let `y` denote the incoming interface state and

\[
G_S(y,z) = (F_a(y,x_a), F_{a+1}(x_a,x_{a+1}),\ldots,
F_b(x_{b-1},x_b)),\qquad z=(x_a,\ldots,x_b).
\]

The boxes `Y` and `X` are closed, bounded, nonempty real interval boxes.  `int(X)`
denotes the ordinary interior.  The outgoing projection is `P_b z = x_b`.

## 2. Executable assumptions

| ID | Mathematical assumption | Checker obligation |
| --- | --- | --- |
| A1 | The normalized netlist has the supported regular index-1 BE structure. | Reject unsupported topology, device, state layout, inconsistent initial state, or singular structural pattern. |
| A2 | `G_S` is continuously differentiable in `z` on an open neighborhood of `Y x X`. | Use only supported smooth device regions; split a box crossing a piecewise-model boundary or return `UNKNOWN`. |
| A3 | `[J_z G](Y,X)` encloses every real `J_z G(y,z)`. | Reconstruct all device-local interval stamps with outward rounding. |
| A4 | `[G](Y, z_bar)` encloses every `G(y,z_bar)`. | Reconstruct values and BE history terms independently of the producer. |
| A5 | The real matrix `C` used by the proof is represented by an interval operator whose evaluation encloses `C v` and `C A`. | Validate dimensions, permutations, sparse indices, triangular operations, and every rounding/error bound; a small ordinary LU residual alone is insufficient. |
| A6 | Certificate and netlist semantics are bound to the accepted input digest. | Recompute canonical hashes and reject mismatches. |
| A7 | All interval endpoints are finite and ordered. | Reject NaN, reversed, or unsupported infinite results. |

`A1` is deliberately a support condition, not a theorem that all SPICE netlists are
index-1.  The first implementation may conservatively return `UNSUPPORTED` whenever
its structural test is inconclusive.

## 3. Theorem S-fixed

Fix `y0 in Y`, a center `z_bar in int(X)`, and a real linear operator `C`.  Define

\[
K_{y_0}(X)=z_bar-CG_S(y_0,z_bar)
 +(I-C[J_zG](\{y_0\},X))(X-z_bar).
\]

**Theorem S-fixed.** Under A1--A7, if the checker proves
`K_{y0}(X) subset int(X)`, then `G_S(y0, .)` has exactly one zero in `X`.
The checker may emit the outward-rounded projection `P_b X` as an enclosure of that
root's outgoing state.

This is local uniqueness in the declared box.  It says neither that no other root
exists outside `X` nor that the continuous-time solution is enclosed.

### Proof skeleton

The interval Jacobian contains every derivative on `X` by A2--A3.  The checker
evaluation contains the exact Krawczyk image by A4--A5.  Strict inclusion therefore
permits the standard Krawczyk fixed-point argument, giving existence in `X` and
uniqueness in `X`.  Projection preserves containment.  A6--A7 bind this mathematical
statement to the accepted instance and prevent malformed arithmetic objects from
entering the premise.

## 4. Theorem S-param

For a non-singleton incoming box `Y`, define the uniform image

\[
K_Y(X)=z_bar-C[G](Y,z_bar)
 +(I-C[J_zG](Y,X))(X-z_bar).
\]

**Theorem S-param.** Under A1--A7, if the checker proves
`K_Y(X) subset int(X)`, then for every `y in Y` there exists exactly one
`z(y) in X` satisfying `G_S(y,z(y))=0`.  Consequently
`{P_b z(y): y in Y} subset P_b X`.

This theorem does not assert that `z(y)` is globally unique.  Continuity of the local
solution map follows from A2 and nonsingularity implied by strict Krawczyk inclusion,
but continuity is not needed for the stated enclosure.

### Proof skeleton

Fix an arbitrary `y in Y`.  Inclusion monotonicity gives
`K_y(X) subset K_Y(X) subset int(X)`.  Apply S-fixed to this `y`.  Since `y` was
arbitrary, universal generalization yields the quantified claim.  Finally project the
common box `X`.  Notice that checking only a center value of `Y` cannot establish this
theorem.

## 5. Compositional contract

Let slab `j` accept under incoming assumption `Y_j` and emit `O_j`.  Composition is
valid only if the certified initial set is contained in `Y_1` and
`O_j subset Y_{j+1}` for every boundary.  Induction with S-param then establishes one
locally unique BE continuation for every allowed initial state.  Dependency is
directional: changing `O_j` may invalidate every later slab.

## 6. Accepted implementation claims

- Fault injection is an implementation regression test, not a proof of soundness.
- A producer hint can only influence acceptance through the verified premises above.
- The phrase “bad hints only cause rejection or extra work” is conditional on the TCB
  and supported semantics being correct.
- Piecewise Level-1 MOS boxes crossing cutoff/triode/saturation boundaries must be
  split into smooth regions or yield `UNKNOWN`; a floating-point branch at the center
  is not a valid interval stamp.
- Discrete monitors reason only about certified sample-point boxes.  Inter-sample peak
  and settling claims remain unsupported.

## 7. Open proof obligations

This document instantiates standard Krawczyk reasoning.  It does not yet establish
novelty or efficiency of BlockStamp's implicit operator evaluation.  The next theorem
obligation is to prove that the block-recursive outward-rounded bound encloses the same
real operator action used in `K_Y`, followed by a complexity and wrapping comparison
against a component-matched pointwise checker.
