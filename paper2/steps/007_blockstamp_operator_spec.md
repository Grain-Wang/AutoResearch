# Step 007: BlockStamp Operator Specification

## 1. Status and purpose

This file fixes the first executable BlockStamp mathematical object.  It specifies how
to enclose the action of the exact real preconditioner `C=M^{-1}` required by
`003_formal_soundness_contract.md` without forming a slab inverse.  The recurrence and
lemma below are a soundness specification, not evidence that the implementation
exists, is faster, gives a tighter interval, or is novel.

The specification deliberately separates four questions:

- **I (implicit action):** does the recurrence enclose the same exact real operator
  action as dense application of `M^{-1}`?
- **W (slab coupling):** does joint-slab certification improve certified prefix or
  acceptance relative to pointwise propagation?
- **E (efficiency):** does implicit application reduce check time, peak memory, or
  certificate bytes relative to component-matched baselines?
- **D (device locality):** does streaming device stamps add a benefit beyond temporal
  block recursion alone?

Only I has a mathematical lemma in this document.  W, E, and D remain falsifiable
experimental hypotheses.

## 2. Fixed mathematical objects

Let `S={a,...,b}` contain `p=b-a+1` BE steps.  Write

\[
X=X_a\times\cdots\times X_b,\qquad
\bar z=(\bar x_a,\ldots,\bar x_b),\qquad
\Delta X_k=X_k-\bar x_k.
\]

After checker-validated permutation and nonzero diagonal scaling, the interval slab
Jacobian is block lower bidiagonal:

\[
[J_zG](Y,X)=
\begin{bmatrix}
[D_a] & 0 & \cdots & 0\\
[L_{a+1}] & [D_{a+1}] & \ddots & \vdots\\
0 & \ddots & \ddots & 0\\
0 & \cdots & [L_b] & [D_b]
\end{bmatrix}.
\]

The checker deterministically reconstructs the point midpoint matrix

\[
M=
\begin{bmatrix}
D_a & 0 & \cdots & 0\\
L_{a+1} & D_{a+1} & \ddots & \vdots\\
0 & \ddots & \ddots & 0\\
0 & \cdots & L_b & D_b
\end{bmatrix}.
\]

Here `[D_k]` and `[L_k]` are interval Jacobian blocks, while `D_k` and `L_k`
are fixed point blocks of `M`.  Their dimensions and bit patterns are bound to the
input digest.  A producer factor or approximate inverse is only an untrusted witness;
it does not replace these checker-defined blocks.

Let outward-rounded residual enclosures at the center be

\[
[g_a]\supseteq\{F_a(y,\bar x_a):y\in Y\},\qquad
[g_k]\supseteq F_k(\bar x_{k-1},\bar x_k)\quad(k>a).
\]

Define the block remainder enclosure

\[
[R_a]=-[g_a]+(D_a-[D_a])\Delta X_a,
\]

and, for `k>a`,

\[
[R_k]=-[g_k]
 +(L_k-[L_k])\Delta X_{k-1}
 +(D_k-[D_k])\Delta X_k.
\]

Equivalently, with `[R]=([R_a],..., [R_b])`,

\[
[R]\supseteq-[G](Y,\bar z)
 +(M-[J_zG](Y,X))(X-\bar z).
\]

The block formulas are the normative definition.  A device-local streaming
implementation may avoid materializing `[J_zG]` only if its outward-rounded sums
enclose these same mathematical expressions.

Algebraically, the Krawczyk image with `C=M^{-1}` satisfies

\[
K_Y(X)\subseteq \bar z+M^{-1}[R].
\]

This rewrite fixes the dependency between the theorem and implementation: BlockStamp
must apply the inverse of the same checker-defined `M`, not a producer-defined LU/ILU
operator.

## 3. Invertibility and verified-solve contract

Before recurrence, every square diagonal block `D_k` must pass the machine-checkable
invertibility witness in Step 003.  The frozen first kernel uses outward-rounded
interval elimination and requires every interval pivot to strictly exclude zero.  An
optimized approximate-inverse or factor kernel may replace it only after proving an
equivalent nonsingularity condition, such as
`upper_norm(I-Q_kD_k)<1`, with reliable arithmetic.  Once all `D_k` pass, the
block-lower-triangular `M` is nonsingular.  The primitive

```text
VSolve(D_k, [B_k], witness_k) -> [V_k]
```

has one required postcondition:

\[
\{D_k^{-1}b:b\in[B_k]\}\subseteq[V_k].
\]

It must also bind the exact point block, witness, backend, precision, permutation, and
scaling to the run digest.  A fast triangular solve without a verified residual/error
bound is not `VSolve`.

## 4. BlockStamp recurrence

The implicit action is

\[
[U_a]=\operatorname{VSolve}(D_a,[R_a]),
\]

\[
[U_k]=\operatorname{VSolve}
\left(D_k,[R_k]-L_k[U_{k-1}]\right),\qquad k=a+1,\ldots,b.
\]

The checker returns

\[
[K]_{\mathrm{BS}}=\bar z+([U_a],\ldots,[U_b])
\]

as an enclosure of the slab Krawczyk image.  `ACCEPT` is permitted only if the strict
componentwise test from Step 003 proves

\[
[K]_{\mathrm{BS}}\subset\operatorname{int}(X).
\]

Normative pseudocode is:

```text
BLOCKSTAMP-APPLY(Y, X, z_bar, checker_semantics, untrusted_hints):
    bind and validate semantics, ordering, scaling, dimensions, and finite endpoints
    reconstruct [g_k], [D_k], [L_k], and checker-defined point D_k, L_k
    for k = a..b:
        prove D_k nonsingular and initialize its VSolve witness
    outward-round the device-local remainder blocks [R_k]
    [U_a] <- VSolve(D_a, [R_a])
    for k = a+1..b:
        [B_k] <- outward_sub([R_k], outward_matvec(L_k, [U_{k-1}]))
        [U_k] <- VSolve(D_k, [B_k])
    [K]_BS <- outward_add(z_bar, product_box([U_a], ..., [U_b]))
    if [K]_BS is strictly inside X:
        return ACCEPT([K]_BS)
    return UNKNOWN(first failing block, machine-checkable reason)
```

The algorithm may stream blocks, but it may not silently change interval evaluation,
drop a device remainder, reuse a factor for a different `M`, or replace strict
inclusion by a tolerance.

## 5. Containment lemma

**Lemma I (implicit exact-action containment).**  Assume Step 003 A1--A7, the
remainder definitions above, and the `VSolve` postcondition at every block.  For every
exact real remainder vector `r` represented by the semantic Krawczyk expression and
therefore contained in `[R]`, the recurrence returns intervals satisfying

\[
M^{-1}r\in[U_a]\times\cdots\times[U_b].
\]

Consequently, `[K]_BS` contains the exact real Krawczyk operator action used in
S-fixed or S-param.

### Proof

Let `u=M^{-1}r`, so `Mu=r`.  In the first block row,

\[
D_au_a=r_a.
\]

Because `r_a in [R_a]`, the `VSolve` postcondition gives `u_a in [U_a]`.
Assume inductively that `u_{k-1} in [U_{k-1}]`.  The `k`-th block row is

\[
D_ku_k=r_k-L_ku_{k-1}.
\]

Outward interval subtraction and multiplication place its exact right-hand side in
`[R_k]-L_k[U_{k-1}]`; the next `VSolve` therefore contains `u_k`.  Induction reaches
`b`.  The definition of `[R]` contains every exact residual/Jacobian remainder, and
outward addition of `z_bar` proves the final statement.

This is an enclosure theorem, not endpoint equality.  A separately evaluated dense
interval expression and the recursive interval expression may have incomparable
widths because of evaluation order; both must contain the same exact real action.

## 6. Complexity contract

Let `F_k`, `S_k`, and `H_k` denote, respectively, the cost of verifying/factoring
`D_k`, one verified interval solve with `D_k`, and multiplying `L_k[U_{k-1}]`.
Ignoring device-stamp construction, BlockStamp costs

\[
O\!\left(\sum_{k=a}^{b}(F_k+S_k+H_k)\right)
\]

and can use one diagonal block, one history block, and two state intervals as working
memory.  Storing the returned slab enclosure still necessarily costs
`O(sum_k n_k)`.

For homogeneous dense blocks of dimension `n`, independently verified per-step
factors give the conservative bound `O(p n^3)` verification/factor cost plus
`O(p n^2)` recurrence cost and `O(n^2)` streaming workspace, excluding the output.
Explicitly storing a dense `(pn) x (pn)` inverse costs `O(p^2 n^2)` memory and generic
dense factorization costs `O(p^3 n^3)`.  These dense figures do **not** imply an
advantage over a competent verified sparse or block-triangular solver; B2/B5 and a
temporal-only implementation remain mandatory baselines.  Certificate bytes may also
remain `O(p n^2)` if every block needs a separate factor witness.

Thus the asymptotic statement is only that the recurrence avoids an explicit full
slab inverse/operator.  Runtime, memory, certificate-size, and acceptance advantages
are empirical claims and must include stamp assembly and witness verification.

## 7. Fail-closed conditions

The checker must not continue to inclusion after any of the following:

- unsupported topology, device region, state layout, BE history, or nonsmooth box;
- digest, dimension, ordering, scaling, or checker-reconstructed `M` mismatch;
- a nonfinite/reversed interval or unsupported arithmetic domain;
- failure to prove a diagonal block nonsingular;
- a `VSolve` failure or an unbounded operator/remainder enclosure;
- a missing stamp, factor-witness mismatch, or unsupported fill/index pattern.

Malformed or unsupported semantics yield `UNSUPPORTED`; a supported instance whose
invertibility, solve, or strict inclusion cannot be proved yields `UNKNOWN`.  Failure
of strict inclusion never becomes `REJECT_NO_ROOT` without a separate exclusion
theorem.  The first failing block is diagnostic only: recovery starts there, but a
cached suffix is reusable only through the boundary-containment replay contract in
Step 006.

## 8. Cross-check and component gates

Before any circuit performance claim, the implementation must:

1. use identical `M`, `[R]`, tube, scaling, ordering, and rigorous backend for recursive
   and dense references;
2. test block dimensions `{1,2,4,8}` and slab lengths `{2,4,8}`, with at least 200
   nonsingular seeded instances per pair;
3. show every independently evaluated high-precision dense exact action lies in the
   recursive enclosure, recording failures and maximum enclosure inflation in
   `operator_canary.json`;
4. exercise singular/near-singular blocks, malformed witnesses, overflow, and strict
   boundary equality, with zero false accepts; and
5. isolate `dense-slab generic`, `device-local pointwise`, `temporal-only`, and
   `temporal+device BlockStamp` under a shared input/fairness hash.

Passing this gate supports the implementation of Claim I.  It does not by itself show
that BlockStamp is a new algorithm or that W/E/D hold.

## 9. Novelty boundary and non-claims

The following are established methodology and are not contributions by themselves:

- Krawczyk/interval-Newton inclusion and S-param quantification;
- block forward substitution or a lower-bidiagonal solve;
- block Krawczyk decomposition, interval cyclic reduction, or factorized verified
  linear computation;
- verified factor witnesses, time-slab composition, and proof-carrying interfaces.

The remaining research opportunity is narrower: a circuit-specific joint
device-stamp/time representation or bound, plus a component-matched advantage that
cannot be explained by ordinary sparsity, caching, language, precision, or unfair tube
initialization.  Until the recurrence-specific prior-art audit and component ladder
both pass, novelty is `POTENTIAL / UNVERIFIED`.

In particular, this specification does not claim:

- that recursion is tighter than dense evaluation or reduces wrapping;
- that joint slabs certify more steps than B2 pointwise propagation;
- lower runtime, memory, certificate bytes, or end-to-end cost;
- equality between recursive and dense interval endpoints;
- support for arbitrary compact models, higher-index DAEs, or continuous-time error;
- that a failure proves absence of a discrete root; or
- that only the failed slab can be recomputed while its dependent suffix is reused.

If Claim I passes but W/E/D show no stable component-matched benefit, the recurrence
must be described as a standard verified block-solve instantiation and the BlockStamp
algorithm headline must be stopped or reframed.
