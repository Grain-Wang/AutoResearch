# Round 6 P0: Mechanism Prior-Art Audit

## 1. Scope and audit rule

This document records the literature-only mechanism reselection requested after Review
Round 5.  No implementation, canary, M2 replay, parameter tuning, or new circuit was
used.  The frozen Round-5 result is unchanged:

```text
CURRENT_METHOD = ARCHIVED
Claim W = FAIL-CANARY
Claim D = STOP
Claim E = STOP
Paper Candidate = FAIL-UNVERIFIED
```

Candidate A is a correlation-preserving sparse interface representation.  Candidate B
is verified factor-witness reuse.  A paper counts toward the minimum only when its full
text was inspected and the following eight questions could be answered:

1. What state or witness does it represent?
2. What is the exact update equation?
3. What soundness guarantee is proved, if any?
4. How is truncation, compression, or reuse controlled?
5. What complexity is stated, or what cost is left unstated?
6. How are dependencies or correlations represented?
7. How does the formula relate to the proposed mechanism?
8. What genuinely circuit-specific gap remains?

The audit deliberately seeks killer prior art.  A difference in application vocabulary,
storage layout, or certificate serialization does not count as a formula-level algorithmic
difference.

## 2. Candidate A: correlation-preserving sparse interface representation

### 2.1 Candidate normal form and immediate equivalences

The candidate sketch is

\[
Z=c+G\xi+\Delta,\qquad \xi\in[-1,1]^r,
\quad \Delta=[-d,d].
\]

It is already a zonotope/affine form because

\[
\Delta=\operatorname{diag}(d)\eta,\quad \eta\in[-1,1]^n,
\qquad
Z=c+[G\;\operatorname{diag}(d)]
\begin{bmatrix}\xi\\\eta\end{bmatrix}.
\]

For any real linear interface map \(T\), including a charge or history projection,

\[
T Z=T c+(T G)\xi+T\Delta.
\]

Thus naming \(T\) after an MNA charge/history subspace does not change the set algebra.
Likewise, if \(G=[G_S\;G_D]\) and the columns \(G_D\) are discarded, the standard sound
box compensation is

\[
\Delta' = \Delta\oplus
[-|G_D|\mathbf 1,\;|G_D|\mathbf 1],
\qquad Z\subseteq c+G_S\xi_S+\Delta'.
\]

The novelty question is therefore not whether the representation or compensation is
sound.  It is whether a *specified* circuit-dependent choice of \(S\), update rule, and
theorem is non-equivalent to generic affine, doubleton, constrained-zonotope, Taylor-model,
or zonotope reduction.

### 2.2 Full-text evidence matrix (10 papers)

#### A1. Zgliczyński, *C1-Lohner Algorithm* (2002)

Full text: [author PDF](https://ww2.ii.uj.edu.pl/~zgliczyn/papers/ks/c1lohner.pdf),
DOI `10.1007/s102080010025`.

1. **Representation.** Equations (41)--(48) use a center plus interval remainder,
   parallelepiped/QR coordinates, and the doubleton
   \([r_k]=C_k[r_0]+[\widetilde r_k]\).
2. **Exact update.** Equation (42) gives
   \([r_{k+1}]=[A_k][r_k]+[z_{k+1}]\); equations (48)--(53) update the retained initial
   deviation and local remainder separately.
3. **Soundness.** Every operation is an interval enclosure.  Replacing the interval
   matrix by a real center \(C_{k+1}\) is sound because
   \(([A_k]C_k-C_{k+1})[r_0]\) is explicitly returned to the remainder.
4. **Compression.** QR reconditioning changes coordinates to limit wrapping; the
   doubleton keeps a fixed-dimensional box plus dense real transforms.
5. **Complexity.** The paper does not state a closed big-O bound.  Dense matrix products
   and QR imply \(O(n^3)\) time and \(O(n^2)\) storage per reconditioning step; this is
   an inference from the displayed operations, not an author claim.
6. **Dependency.** Initial-set dependence remains in \([r_0]\), while fresh local error
   remains in \([\widetilde r_k]\).
7. **Formula relation.** This is directly \(c+C_k\xi+\Delta_k\), including a sound
   update of the dropped/nonlinear part.
8. **Circuit-specific gap.** It is a generic smooth-ODE/Poincare algorithm and has no
   MNA stamp incidence, charge/history-specific selection, or external certificate
   checker.  Those missing nouns do not make the shared representation new.

#### A2. Messine, *Extensions of Affine Arithmetic: Application to Unconstrained Global Optimization* (2002)

Full text: [JUCS PDF](https://www.jucs.org/jucs_8_11/extentions_of_affine_arithmetic/Messine_F.pdf).

1. **Representation.** Equation (5) uses
   \(\widehat x=x_0+\sum_i x_i\epsilon_i\).  AF1/AF2 add one or three aggregate error
   symbols while retaining the original source symbols.
2. **Exact update.** Affine operations are coefficientwise; equation (9) preserves
   linear terms of multiplication and appends a bounded nonlinear-error symbol.
3. **Soundness.** Proposition 3 and Theorem 4 establish inclusion for the aggregate
   forms.  The floating-point discussion requires rounded interval coefficients for a
   machine-level guarantee.
4. **Compression.** Several nonlinear symbols are replaced by one or three symbols whose
   radii include the sum of the removed coefficient magnitudes.
5. **Complexity.** No global big-O is stated.  An AF1 operation scans its coefficient
   vector, hence is linear in the retained symbol count; quadratic forms add pair terms.
6. **Dependency.** Shared original \(\epsilon_i\) preserve linear correlation; only the
   accumulated nonlinear errors lose their identities.
7. **Formula relation.** AF1 is precisely \(c+G\xi+\Delta\), and its aggregation is the
   candidate's drop-to-outward-remainder rule.
8. **Circuit-specific gap.** It has no temporal or circuit structure, but it removes
   generic reliable generator aggregation as a possible novelty claim.

#### A3. Rump and Kashiwagi, *Implementation and Improvements of Affine Arithmetic* (2015)

Full text: [publisher open-access PDF](https://www.jstage.jst.go.jp/article/nolta/6/3/6_341/_pdf),
DOI `10.1587/nolta.6.341`.

1. **Representation.** Equation (1) is \(c+\sum_i\gamma_i\epsilon_i\); the implementation
   stores sparse coefficient matrices plus interval range and rounding-error fields.
2. **Exact update.** Equations (6)--(15) bound nonlinear operations.  Equations (20)--(27)
   combine affine and interval evaluation and tighten multiplication.
3. **Soundness.** Primitive results are first enclosed by interval operations; midpoint
   and radius extraction moves machine error into the explicit rounding component.
4. **Compression.** Section 3.7 garbage-collects zero or selected small symbols and moves
   their magnitude to a sound error component.
5. **Complexity.** Pairwise coefficient multiplication is quadratic in symbol count;
   the paper discusses cheaper linear-time bounds and sparse storage.
6. **Dependency.** Common symbol identities preserve correlation until a selected term
   is deliberately absorbed into the uncorrelated remainder.
7. **Formula relation.** This is an implementation-level sparse
   \(c+G\xi+\Delta\) with reliable cleanup.
8. **Circuit-specific gap.** There is no MNA or history policy, but sparse storage,
   directed rounding, and sound garbage collection are already generic machinery.

#### A4. Berz and Makino, *Suppression of the Wrapping Effect by Taylor Model-Based Validated Integrators: Long-Term Stabilization by Shrink Wrapping* (2005)

Full text: [author PDF](https://www.bmtdynamics.org/pub/papers/VIShrink06/VIShrink06.pdf).

1. **Representation.** The propagated set is
   \(A=I_0\oplus\mathcal M_0(B)\), a multivariate Taylor polynomial image plus interval
   remainder.
2. **Exact update.** The polynomial flow map is composed stepwise; normalization uses
   the inverse of its linear part, and shrink wrapping rescales the map so that the
   interval error is absorbed into polynomial variables.
3. **Soundness.** Theorems 1--2 use validated remainder inclusion; Theorem 6 proves the
   shrink-wrapping containment rather than heuristically deleting the remainder.
4. **Compression.** Interval remainder and floating-point/truncation error are absorbed
   into a scaled existing polynomial domain when the shrinkability conditions hold.
5. **Complexity.** No single big-O is stated; dense inverse/derivative bounds and the
   number of multivariate monomials dominate.
6. **Dependency.** Initial-condition variables remain symbolic to high order instead of
   being replaced by a new independent box at every step.
7. **Formula relation.** A degree-one Taylor model reduces to
   \(c+G\xi+\Delta\); its wrapping control is strictly more general.
8. **Circuit-specific gap.** The method is a generic validated integrator without MNA
   structure.  Taylor remainder absorption and QR-like anti-wrapping are not available
   as circuit novelty.

#### A5. Kochdumper and Althoff, *Sparse Polynomial Zonotopes: A Novel Set Representation for Reachability Analysis* (2021)

Full text: [arXiv PDF](https://arxiv.org/pdf/1901.01780),
DOI `10.1109/TAC.2020.3024348`.

1. **Representation.** Definition 1 stores dependent polynomial generators with an
   exponent matrix and identifier vector, plus independent zonotope generators.
2. **Exact update.** The paper gives exact affine maps and exact addition after aligning
   identifiers, as well as polynomial/quadratic maps.
3. **Soundness.** All stated reduction operations return supersets.  The nonlinear
   reachability step enlarges a remainder until its fixed-point containment succeeds.
4. **Compression.** `compact` exactly merges duplicate monomials; Proposition 16 performs
   sound order reduction, and Proposition 17 restructures independent generators.
5. **Complexity.** The paper reports polynomial costs for the major operations; for
   example, compacting is \(O(n^2\log n)\), while nonlinear maps depend polynomially on
   state and generator counts.
6. **Dependency.** Persistent identifiers preserve repeated factors across sets; exact
   addition avoids the dependency loss of ordinary Minkowski addition.
7. **Formula relation.** Degree-one sparse polynomial zonotopes strictly contain
   \(c+G\xi+\Delta\), with the independent generators playing the role of \(\Delta\).
8. **Circuit-specific gap.** It does not choose generators from MNA stamps or verify an
   external transient result, but it is the strongest generic killer for “sparse,
   correlation-preserving, soundly reduced set representation.”

#### A6. Scott et al., *Constrained Zonotopes: A New Tool for Set-Based Estimation and Fault Detection* (2016)

Full text: [author PDF](https://web.mit.edu/braatzgroup/Scott_Automatica_2016.pdf),
DOI `10.1016/j.automatica.2016.02.036`.

1. **Representation.** Definition 3 uses
   \(\{G\xi+c:\|\xi\|_\infty\le1,\ A\xi=b\}\).
2. **Exact update.** Proposition 1 gives exact linear maps, Minkowski sums, and generalized
   intersections by updating \(G,c,A,b\).
3. **Soundness.** Those operations are set equalities; the reduction routines are stated
   as outer approximations.  Theorem 1 shows exact representability of convex polytopes.
4. **Compression.** Rescaling, constraint elimination, and lift-and-reduce control both
   generators and equality constraints.
5. **Complexity.** Constraint elimination is cubic in generator/constraint count; the
   generator-reduction expressions are polynomial in dimension and generator count.
6. **Dependency.** Equality constraints over the latent symbols exactly preserve linear
   invariants and correlations induced by intersections.
7. **Formula relation.** It augments \(c+G\xi+\Delta\) with latent linear constraints;
   an interval remainder is simply another block of box generators.
8. **Circuit-specific gap.** It has no nonlinear implicit MNA step, but a “charge/history
   subspace” expressed only as linear equalities is already covered.

#### A7. Althoff and Krogh, *Reachability Analysis of Nonlinear Differential-Algebraic Systems* (2014)

Full text: [author-archive PDF](https://mediatum.ub.tum.de/doc/1281529/770926.pdf),
DOI `10.1109/TAC.2013.2285751`.

1. **Representation.** Reachable sets are zonotopes \((c,g^{(1)},\ldots,g^{(p)})\) for
   differential and algebraic variables, with interval/Hessian remainder sets.
2. **Exact update.** Equations (9)--(16) linearize the index-1 DAE, eliminate algebraic
   deviations, and propagate the resulting linear differential inclusion.
3. **Soundness.** Proposition 1 and the subsequent enclosure theorem guarantee that the
   original nonlinear DAE trajectories lie in the computed supersets when the remainder
   inclusion closes.
4. **Compression.** Bounded-order zonotope reduction, boxes, and splitting control set
   growth; a failed or too-wide enclosure is split rather than accepted unsoundly.
5. **Complexity.** The paper reports \(O(n^5)\) for the general method and \(O(n^3)\) for
   mildly nonlinear systems; splitting can add exponential dependence on split variables.
6. **Dependency.** Common generators preserve correlation between differential and
   algebraic variables rather than taking their Cartesian interval hull.
7. **Formula relation.** Zonotope plus nonlinear remainder is exactly the candidate's set
   family, embedded in a sound nonlinear-DAE propagation algorithm.
8. **Circuit-specific gap.** The application is an electrical-network DAE, not a SPICE
   charge-form external-result checker.  It nevertheless kills generic DAE-affine
   propagation as novelty.

#### A8. Grabowski, Olbrich, and Barke, *Analog Circuit Simulation Using Range Arithmetics* (2008)

Full text: [ASP-DAC PDF](https://www.cecs.uci.edu/~papers/aspdac08/pdf/p762_9A-2.pdf),
DOI `10.1109/ASPDAC.2008.4484053`.

1. **Representation.** Equation (1) is an affine form with shared deviation symbols;
   Section IV extends it to quadratic forms.
2. **Exact update.** Equations (9)--(13) turn the nonlinear circuit DAE into an implicit
   Euler/trapezoid equation and set
   \(p_x^T=[p,x_{n-1},x_{n-2},\ldots]^T\).  Algorithm 1 propagates the associated
   sensitivities through \(J^{-1}P\) and adds extended deviations.
3. **Soundness.** The affine primitives enclose their real ranges, and the nonlinear
   solver seeks a conservative polytope.  The paper does not provide a modern
   directed-rounding Krawczyk existence/uniqueness theorem, so it is a novelty killer but
   not a drop-in sound checker baseline.
4. **Compression.** It does not give a sound general pruning theorem; nonlinear operations
   grow symbols and quadratic forms trade additional storage/time for tighter ranges.
5. **Complexity.** No asymptotic bound is stated.  The reported timing is empirical and
   reaches circuits with 242 equations.
6. **Dependency.** Shared symbols preserve parameter correlation, and equation (11)
   explicitly carries previous transient states as history parameters.
7. **Formula relation.** This is a transistor-level circuit instance of
   \(c+G\xi+\Delta\) with history-state correlation.
8. **Circuit-specific gap.** A sound stamp-aware selection/compression theorem and an
   independent external-result checker remain absent.  “First affine/history transient
   circuit interface,” however, is untenable.

#### A9. Ni et al., *A Zonotoped Macromodeling for Eye-Diagram Verification of High-Speed I/O Links With Jitter and Parameter Variations* (2016)

Full text: [author PDF](https://mason.gmu.edu/~spudukot/Files/TCAD16.pdf),
DOI `10.1109/TCAD.2015.2481873`.

1. **Representation.** Equation (4) is a state zonotope; equation (13) is a matrix
   zonotope carrying circuit-parameter generators.
2. **Exact update.** Equations (6), (14)--(16) use charge-form MNA
   \(d q(x)/dt+f(x)+Bu=0\) and implicit Euler.  Equations (22)--(30) construct
   parameterized Krylov/QR subspaces and propagate reduced history.
3. **Soundness.** It is not a validated-numerics guarantee: equation (27) discards
   higher-order variation products, and small generators are dropped without an outward
   remainder.  Monte Carlo coverage is empirical.
4. **Compression.** Krylov model reduction and a hard generator cap/drop reduce state and
   generator counts, but the deletion is not sound.
5. **Complexity.** No asymptotic theorem is stated; the paper reports empirical speedups
   as the reduced order varies.
6. **Dependency.** Generators bind jitter and circuit parameters across matrix, input,
   state, and reduced subspace until terms are discarded.
7. **Formula relation.** It already combines charge-form MNA, zonotopes, implicit Euler,
   history propagation, and QR-based reduction.
8. **Circuit-specific gap.** Sound outward compensation and a checker theorem are missing.
   Merely repairing the deletion with the standard box rule would still need a new
   circuit-specific selection objective to escape generic reduction prior art.

#### A10. Immler, *A Verified ODE Solver and the Lorenz Attractor* (2018)

Full text: [open-access article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6044317/),
DOI `10.1007/s10817-017-9448-y`.

1. **Representation.** Vectors are lists of affine forms
   \(A_0+\sum_i\epsilon_iA_i\), hence zonotopes with shared symbols.
2. **Exact update.** Linear operations transform coefficients exactly; multiplication
   preserves affine terms and adds a fresh bounded symbol.  A second-order Runge--Kutta
   enclosure propagates these forms.
3. **Soundness.** The approximation hierarchy, Runge--Kutta remainder, flow relation,
   and final Lorenz computation are formally verified in Isabelle/HOL.
4. **Compression.** The implementation computes componentwise total deviation and
   soundly summarizes selected small symbols, explicitly trading their correlation for a
   bounded fresh component.
5. **Complexity.** The article gives implementation sizes and empirical feasibility, not
   a general asymptotic cost for affine propagation/compression.
6. **Dependency.** Shared affine symbols track linear dependence; adaptive set splitting
   and symbol summarization control growth.
7. **Formula relation.** It formally verifies both the candidate representation and the
   essential “remove selected correlations, pay an outward remainder” operation.
8. **Circuit-specific gap.** It has no circuit semantics, but it removes any claim that
   sound sparse affine cleanup or verified long-horizon propagation is new in itself.

### 2.3 Candidate-A killer conclusion

No single paper needs to contain every proposed noun for the generic mathematical object
to be anticipated.  The formula chain is already closed:

- Zgliczyński gives the doubleton/QR recurrence;
- Messine, Rump--Kashiwagi, Kochdumper--Althoff, and Immler give sound dependency
  aggregation or generator reduction;
- constrained zonotopes encode a retained linear subspace;
- Althoff--Krogh gives sound nonlinear-DAE zonotope propagation;
- Grabowski et al. explicitly put previous circuit states in the affine parameter vector;
- Ni et al. combine charge-form MNA, zonotopes, implicit Euler, Krylov/QR projection, and
  history update, although their deletion is not sound.

The only potentially non-equivalent object would be a rule that does not yet exist in
paper2, for example

\[
S_k^*=\arg\max_{\operatorname{cost}(S)\le B}
\underline m_{\mathrm K}
\bigl(\operatorname{Reduce}_S(q(Z_k),H_k)\bigr),
\]

where a device-incidence or circuit-separator theorem makes the certified Krawczyk-margin
loss decomposable, submodular, or approximable, and every unselected mode is outwardly
residualized.  A norm-based top-\(k\), sparse storage, a charge/history label, or the
standard box compensation is not such a difference.  Because no concrete decision rule,
update equation, approximation theorem, or complexity result is presently defined,
Candidate A does not pass the P0 novelty gate.

## 3. Candidate B: verified factor-witness reuse

### 3.1 Candidate normal form and immediate equivalences

For adjacent systems

\[
A_1=A_0+U\Lambda V^T,
\]

the exact inverse relation is the Sherman--Morrison--Woodbury identity

\[
A_1^{-1}=A_0^{-1}-A_0^{-1}U
(\Lambda^{-1}+V^TA_0^{-1}U)^{-1}V^TA_0^{-1}.
\]

For a rank-one update, regularity reduces to excluding zero from
\(1+v^TA_0^{-1}u\).  Independently, any cached approximate inverse action \(R\) may be
reused in the standard Krawczyk map for the *new* matrix,

\[
K(\widetilde x,X;R)=\widetilde x-R(A_1\widetilde x-b)
+(I-RA_1)(X-\widetilde x).
\]

Recomputing the residual and contraction with outward rounding makes stale \(R\) a mere
untrusted preconditioner: strict inclusion proves the result or the checker fails closed.
Thus “cache a factor/inverse and verify the new residual” is already generic verified
numerics.  The novelty question is whether there is a new circuit-specific acceptance
decision or local update theorem, not whether the old bytes are called a reusable witness.

### 3.2 Full-text evidence matrix (11 papers)

#### B1. Dreyer, *Interval Methods for Analog Circuits* (2006)

Full text: [German National Library PDF](https://d-nb.info/1027387926/34),
DOI `10.24406/publica-fhg-293017`.

1. **Representation.** The circuit matrix is decomposed as
   \(A(p)=A_0+\sum_i p_i u_iv_i^T\), retaining each component parameter as a rank-one
   stamp and caching nominal inverse actions.
2. **Exact update.** Section 4.2 equations (12)--(16) use Sherman--Morrison.  For one
   parameter,
   \(d(p)=1+(p-p_0)v^TA_0^{-1}u\), followed by an exact inverse/solution update;
   equation (19) applies rank-one changes sequentially.
3. **Soundness.** Theorem 4.6 proves regularity of the whole interval family when
   \(0\notin d([p])\); outward interval evaluation then encloses its solutions.
4. **Compression/reuse.** It stores \(A_0^{-1}b\) and \(A_0^{-1}u_i\) rather than solving
   every parameter corner independently.
5. **Complexity.** The report gives \(O(n^2n_p)\), in contrast to enumeration over
   \(2^{n_p}\) corners.
6. **Dependency.** Parameter identity is retained through the rank-one stamps.  The report
   also identifies dependency loss when a complex component contributes correlated real
   rank-one terms.
7. **Formula relation.** This is verified, component-stamp, low-rank inverse-witness reuse
   in the analog-circuit domain: the most direct killer prior art for B.
8. **Circuit-specific gap.** It treats linear small-signal/frequency tolerance families,
   not nonlinear BE Newton Jacobians or a portable untrusted certificate.  That narrower
   setting does not leave generic “verified stamp update” novel.

#### B2. Popova, *Rank One Interval Enclosure of the Parametric United Solution Set* (2019)

Full text: [author PDF](https://www.math.bas.bg/~epopova/papers/19-EPopova-BIT-preprint.pdf),
DOI `10.1007/s10543-018-0739-4`.

1. **Representation.** An affine family is written in optimal rank-one form
   \(A(p)=A_0+L D_{g(p)}R\), where the reduced size is the sum of coefficient ranks.
2. **Exact update.** Woodbury reduces the parametric inverse/solution problem to
   \(G(p_0,p)=I-R A(p_0)^{-1}L D_{g(p_0-p)}\), followed by a reduced solve and exact
   reconstruction.
3. **Soundness.** Theorem 3.1 and the spectral-radius/H-matrix tests prove regularity for
   the entire parameter box; Section 4 gives a united-solution enclosure.
4. **Compression/reuse.** One nominal inverse action and an \(s\times s\) reduced family
   replace repeated full \(n\times n\) solves.
5. **Complexity.** No single big-O is claimed.  The displayed method requires one nominal
   factorization/inverse action plus a reduced verified solve; the paper notes that finding
   optimal rank decompositions can be costly.
6. **Dependency.** The map \(g(p)\) retains repeated parameter identities and both row and
   column dependencies.
7. **Formula relation.** It already provides verified Woodbury reuse for a whole low-rank
   parameter family.
8. **Circuit-specific gap.** There is no nonlinear time sequence or independent
   producer/checker protocol.  Device naming alone cannot distinguish the formula.

#### B3. Popova, *Enclosing the Solution Set of Parametric Interval Matrix Equation A(p)X=B(p)* (2018)

Full text: [author PDF](https://www.math.bas.bg/~epopova/papers/18-EPopova-NumAlgo-preprint.pdf),
DOI `10.1007/s11075-017-0382-1`.

1. **Representation.** A single \(R\approx A(\check p)^{-1}\), approximate matrix
   solution, parametric residual \(Z\), contraction \(C\), and interval enclosure are
   shared by a matrix equation with multiple right-hand sides.
2. **Exact update.** Algorithm 1 forms
   \(Z=R(B_0-A_0\widetilde X)+\sum_kp_kR(B_k-A_k\widetilde X)\) and
   \(C=I-RA_0-\sum_kp_kRA_k\), then performs componentwise Krawczyk/Gauss--Seidel
   updates.  The later LDR algorithm performs a reduced update.
3. **Soundness.** Strict inclusion proves regularity of every \(A(p)\) and encloses the
   unique \(X(p)\); Theorem 1 handles shared parameters across all right-hand sides.
4. **Compression/reuse.** It avoids an \(mn\times mn\) augmented inverse and reuses one
   \(m\times m\) inverse; LDR further reduces the parameter family.
5. **Complexity.** The paper states
   \(O(c(K+1)I_{tr}m^2\max(m,n))\) for Algorithm 1 and
   \(O(m^3+I_{tr}(ms\max(m,s)+s^2n))\) for Algorithm 2.
6. **Dependency.** The same parameter symbols are retained across \(A\) and every column
   of \(B\).
7. **Formula relation.** A reusable inverse witness for an entire family and many right
   sides is already explicit.
8. **Circuit-specific gap.** The family is static and affine, with no transient stamp
   sequence or serialized checker witness.

#### B4. Garloff, Popova, and Smith, *Solving Linear Systems with Polynomial Parameter Dependency by Means of Bernstein Expansion* (2013)

Full text: [author PDF](https://www.math.bas.bg/~epopova/papers/13-GarloffEtAl-preprint.pdf),
DOI `10.1007/978-1-4614-5131-0_19`.

1. **Representation.** A nominal inverse \(R\), approximate solution, interval residual
   \(z\), contraction \(C\), and an implicit Bernstein representation cover polynomial
   parameter dependence.
2. **Exact update.** Theorem 1 forms hulls of
   \(R(d(x)-A(x)\widetilde s)\) and \(I-RA(x)\), followed by a componentwise
   Gauss--Seidel enclosure update.
3. **Soundness.** Strict interior inclusion proves regularity and a unique enclosed
   solution for every parameter value; roundoff is included interval-wise.
4. **Compression/reuse.** Implicit Bernstein coefficients avoid materializing the full
   multidimensional coefficient tensor while sharing \(R\) over the parameter domain.
5. **Complexity.** The paper reports polynomial implicit storage/time versus exponential
   \(O((\widehat l+1)^n)\) explicit expansion.
6. **Dependency.** Arbitrary shared polynomial parameter dependence is retained.
7. **Formula relation.** It is a stronger non-affine family-preconditioner baseline than
   merely rechecking one low-rank stamp delta.
8. **Circuit-specific gap.** Its applications are static parametric systems, not a sparse
   transient-MNA witness protocol.

#### B5. Carr, de Sturler, and Gugercin, *Preconditioning Parametrized Linear Systems* (2021)

Full text: [arXiv PDF](https://arxiv.org/pdf/1601.05883),
DOI `10.1137/20M1331123`.

1. **Representation.** A previous preconditioner \(P_0\) is combined with a sparse map
   \(N_k\) having a chosen pattern.
2. **Exact update.** Equations (2.3)--(2.4) define
   \(N_k=\arg\min_{N\in\mathcal S}\|A_kN-A_0\|_F\) and \(P_k=N_kP_0\);
   later equations chain maps and specialize to changed rows/columns.
3. **Soundness.** It is not a verified solver.  Norm and field-of-values conditions bound
   preconditioned quality but do not enclose the solution.
4. **Compression/reuse.** The sparsity pattern splits the update into small independent
   least-squares problems and amortizes the original preconditioner.
5. **Complexity.** No universal big-O is stated; for a fixed local pattern the update is a
   collection of small least-squares solves, with empirical costs reported.
6. **Dependency.** It handles a slowly varying matrix sequence and incremental maps; it
   does not retain interval parameter identity.
7. **Formula relation.** Sparse mapping/recycling is an obligatory nonverified performance
   baseline for any reuse claim.
8. **Circuit-specific gap.** An outward-rounded acceptance certificate is absent.  Adding
   a conventional residual verifier, however, risks being a mechanical composition.

#### B6. Anzt et al., *Updating Incomplete Factorization Preconditioners for Model Order Reduction* (2016)

Full text: [author PDF](https://faculty.cc.gatech.edu/~echow/pubs/anzt-chow-saak-dongarra.pdf),
DOI `10.1007/s11075-016-0110-2`.

1. **Representation.** The previous matrix's sparse incomplete \(L/U\) factors and a
   fixed sparsity pattern initialize the next factorization.
2. **Exact update.** Equations (6)--(9) give fixed-point factor equations and entrywise
   updates; a small fixed number of sweeps updates the old factors for the new matrix.
3. **Soundness.** It offers convergence conditions and empirical preconditioner quality,
   not a verified solution enclosure.
4. **Compression/reuse.** Only entries in the fixed incomplete-factor pattern are stored;
   one old factor state is reused.
5. **Complexity.** Each sweep scales with the retained factor graph and local products;
   the paper reports GPU timings rather than one closed asymptotic expression.
6. **Dependency.** It follows shifted/parametric matrix sequences; a distant old factor
   may become a worse initializer.
7. **Formula relation.** Reusing an old sparse factor as a warm start is plainly prior art.
8. **Circuit-specific gap.** The method is approximate, primarily SPD/MOR-oriented, and
   has no directed-rounding certificate or circuit stamp semantics.

#### B7. Ogita, Rump, and Oishi, *Verified Solutions of Sparse Linear Systems by LU Factorization* (2005)

Full text: [author PDF](https://www.tuhh.de/ti3/paper/rump/OgRuOi05a.pdf).

1. **Representation.** A conventional sparse \(PA\approx LU\) factorization is treated as
   an untrusted inverse-action oracle; transpose solves construct approximate inverse rows,
   and rigorous residual scalars certify them.
2. **Exact update.** Theorem 1 computes
   \(\alpha\ge\max_j\|A^Ty^{(j)}-e_j\|_1\).  If \(\alpha<1\), equation (8) bounds the
   solution error from residual dot products.
3. **Soundness.** \(\alpha<1\) proves \(A\) nonsingular and gives a rigorous
   infinity-norm error enclosure.
4. **Compression/reuse.** It reuses the sparse LU already produced for solving and need
   not store a dense explicit inverse, though it performs \(n\) transpose solves.
5. **Complexity.** The paper gives measured overhead rather than a closed big-O; cost is
   the sparse factorization plus blockable triangular solves and residual evaluation.
6. **Dependency.** It treats a point matrix and is independent of its ordering; no shared
   cross-matrix parameter model is stored.
7. **Formula relation.** “LU factor plus independently checked residual as witness” is
   already a verified-numerics construction.
8. **Circuit-specific gap.** It does not update the factor across matrices.  That is a
   narrower gap than inventing factor witnesses themselves.

#### B8. Minamihata et al., *Fast Verified Solutions of Sparse Linear Systems with H-matrices* (2013)

Full text: [journal PDF](https://interval.louisiana.edu/reliable-computing-journal/volume-19/reliable-computing-19-pp-127-141.pdf).

1. **Representation.** A positive vector \(v\), comparison-matrix lower bound, approximate
   solution/correction, and rigorous residual scalars replace a dense inverse witness.
2. **Exact update.** Theorem 5.2 and Algorithms 5.1--5.2 use
   \(\langle A\rangle v>0\) and the residual to produce componentwise bounds such as
   \(\alpha v\).
3. **Soundness.** The positive-vector test proves the comparison matrix is an M-matrix,
   hence \(A\) is an H-matrix and nonsingular; outward calculations enclose the error.
4. **Compression/reuse.** The witness is \(O(n)\) vectors plus sparse \(A\); no complete LU
   or inverse is required.
5. **Complexity.** Sparse matrix-vector products and iterative solves dominate, with
   \(O(\operatorname{nnz}(A)+n)\) storage; no single iteration-count bound is claimed.
6. **Dependency.** It covers a point/H-matrix enclosure and does not preserve a shared
   parameter model.
7. **Formula relation.** For applicable matrices it is a substantially smaller reusable
   verified witness than a cached numerical factor.
8. **Circuit-specific gap.** General MNA Jacobians need not be H-matrices, so applicability
   must be proved rather than assumed.

#### B9. Frommer and Hashemi, *Verified Error Bounds for Solutions of Sylvester Matrix Equations* (2012)

Full text: [author PDF](https://www-ai.math.uni-wuppertal.de/SciComp/preprints/SC1003.pdf),
DOI `10.1016/j.laa.2010.12.002`.

1. **Representation.** Verified inverse enclosures for eigenvector transforms, diagonal or
   block-triangular factors, an approximate solution, and an interval correction box form
   a structured inverse-action witness.
2. **Exact update.** The generic map is
   \(k=-R(A\widetilde x-b)+(I-RA)z\); equations (15)--(18) transform the Sylvester
   residual and apply elementwise or block-triangular correction updates.
3. **Soundness.** Interior inclusion proves operator nonsingularity and encloses the unique
   solution; the verified transforms map the correction back safely.
4. **Compression/reuse.** It uses factorized Kronecker structure rather than constructing
   the full \(mn\times mn\) inverse.
5. **Complexity.** The structured method is \(O(m^3+n^3)\), compared with a generic
   vectorized cubic cost in \(mn\); fixed block width reduces substitution cost further.
6. **Dependency.** Repeated interval block substitution can duplicate right-hand-side
   dependence and widen exponentially, a limitation explicitly discussed.
7. **Formula relation.** Factorized Krawczyk and verified structured inverse actions are
   established mechanisms.
8. **Circuit-specific gap.** The structure is Sylvester/Kronecker rather than transient
   MNA and has no stamp-local cross-step update.

#### B10. Rump, *Fast Interval Matrix Multiplication* (2012)

Full text: [author PDF](https://grouper.ieee.org/groups/1788/email/pdfUDuSDSsrNx.pdf),
DOI `10.1007/s11075-011-9524-z`.

1. **Representation.** `VerifyLinSys` uses one \(R=\operatorname{inv}(\operatorname{mid}A)\),
   an approximate solution, interval residual \(Z\), contraction \(C=I-R[A]\), and an
   inflated interval correction.
2. **Exact update.** Section 5 iterates \(X\leftarrow Z+C Y\) and accepts only when
   \(X\subset\operatorname{int}Y\).
3. **Soundness.** Success proves every matrix in \([A]\) nonsingular and encloses all
   corresponding solutions; failure returns no verified answer.
4. **Compression/reuse.** A single dense approximate inverse is reused for the interval
   family and can process multiple right-hand sides together.
5. **Complexity.** With a vector right-hand side, the only interval-by-interval product is
   quadratic in \(n\); matrix right-hand sides restore matrix-multiplication cost.
6. **Dependency.** Entrywise interval input loses shared parameter identities and may
   widen compared with a parametric formulation.
7. **Formula relation.** Caching \(R\) and revalidating the new residual/contraction is the
   standard verified inverse-reuse baseline.
8. **Circuit-specific gap.** It is dense and nonparametric, without stamp incidence or a
   serialized cross-step certificate.

#### B11. Rump, *Verified Error Bounds for Sparse Systems, Part I: The Splitting of a Matrix into Two Factors* (2026, to appear)

Full text: [author preprint](https://www.tuhh.de/ti3/paper/rump/sparselss_I_submitted.pdf).

1. **Representation.** A general sparse matrix is split into factors \(L_1L_2\) with
   matched singular values; approximate solutions and accurate residuals accompany a
   rigorous lower bound on the factors' smallest singular values.
2. **Exact update.** The paper derives separate sparse factorizations for positive
   definite, symmetric-indefinite, and general matrices, then bounds the solution error
   using the residual and certified singular-value lower bound.
3. **Soundness.** The computed bound proves solvability and gives mathematically correct
   error bounds, including for matrices with condition numbers approaching binary64's
   natural limit in the reported cases.
4. **Compression/reuse.** Sparse factors are retained; the method avoids the generally
   dense approximate inverse required by classical Krawczyk verification.
5. **Complexity.** Sparse factorization/fill and accurate dot products dominate.  The
   preprint provides algorithms and measurements, not one structure-independent big-O.
6. **Dependency.** It verifies a point matrix (and can handle interval right-hand-side
   reductions); it does not encode a shared device parameter across a sequence.
7. **Formula relation.** It strengthens the mandatory fresh verified-sparse baseline and
   removes “verified sparse factorization is unavailable” as a defensible premise.
8. **Circuit-specific gap.** It does not reuse a witness across a stamp update, but any
   reuse method must beat it after charging update verification and fallback.

### 3.3 Candidate-B killer conclusion

Dreyer already gives a circuit-stamp rank-one family, interval Sherman--Morrison update,
regularity test, and solution enclosure.  Popova gives the generic LDR/Woodbury family
version and a multiple-right-hand-side parametric Krawczyk method.  Carr and Anzt cover
matrix-sequence preconditioner/factor recycling; Ogita--Rump--Oishi, Minamihata et al.,
Frommer--Hashemi, Rump, and current sparse-verification work cover the independent
verification side.

A possible new theorem would need all of the following, none of which is currently
defined in paper2:

1. a nonlinear transient-MNA stamp-delta decomposition with persistent shared parameter
   identities, not merely an entrywise \(U,V\) factorization;
2. an untrusted portable old-factor/inverse-action witness and a new local checker whose
   acceptance theorem is not ordinary Woodbury followed by ordinary residual/Krawczyk
   verification;
3. an elimination-tree- or device-incidence-local update rule with a proved work bound
   and deterministic fail-closed rebase;
4. an end-to-end reason to pursue factor cost despite Round 5 having no full-trace
   acceptance and no Claim-E advantage.

Exact-matrix caching, symbolic-order reuse, old-LU warm starts, Sherman--Morrison/Woodbury,
or serializing an LU plus its residual are all directly covered.  Candidate B therefore
does not pass the P0 novelty gate.

## 4. Cross-candidate verdict

The independent-checking problem remains legitimate, but neither candidate presently
contains a formula-level circuit-specific algorithmic difference.  Candidate A names a
standard affine/zonotope family and standard sound reduction, while its only possible
new selection theorem has not been defined.  Candidate B combines already-known
circuit rank-one interval updates with already-known residual/factor verification, and
it addresses cost before the Round-5 acceptance failure is repaired.

The evidence therefore supports archiving the current paper2 algorithm route rather than
promoting an unspecified future theorem into P1.  This is a Round-6 prior-art conclusion;
it does not rewrite or relabel any Round-5 artifact.
