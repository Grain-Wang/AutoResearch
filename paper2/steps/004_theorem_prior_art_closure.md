# Step 004: Theorem Prior-Art Closure

## 1. Question, evidence rule, and access audit

Round 4 asks whether the current `D_k/L_k/R_k/U_k` construction is a new
structured Krawczyk algorithm or an application of established verified structured
linear algebra inside a new certifying system.  The audit uses only papers and
publisher/author/institutional primary records.  `FULL-TEXT/THEOREM` means that the
formula or theorem was inspected in the paper itself.  `PUBLISHER-ABSTRACT` and
`OFFICIAL-METADATA` support only the bibliographic and method-description facts stated
there; an inaccessible paper is never treated as evidence of formula-level non-overlap.

| Target | Evidence obtained by 2026-09-01 | Formula-level status |
| --- | --- | --- |
| Chen & Hashimoto, [*Verification methods for nonlinear equations with saddle point functions*](https://doi.org/10.1016/S0377-0427(03)00570-3), JCAM 159(1), 13–24 (2003) | `PUBLISHER-ABSTRACT + OFFICIAL-METADATA`.  The [publisher page](https://www.sciencedirect.com/science/article/pii/S0377042703005703) and [PolyU record](https://research.polyu.edu.hk/en/publications/verification-methods-for-nonlinear-equations-with-saddle-point-fu/) state that the fast nonlinear verification algorithm is based on a block decomposition of a Krawczyk-type interval operator.  Official full-text endpoints did not yield a readable article without an API/account gate; no legitimate public author copy was found. | **NOT VERIFIED**: operator formula, block partition, dependency representation, theorem hypotheses, complexity proof, and reusable witness are unknown.  There is no local PDF. |
| Schwandt, [*A truncated cyclic reduction algorithm for interval arithmetic tridiagonal systems of equations*](https://doi.org/10.1080/00207168708803564), IJCM 21(2), 161–184 (1987) | `PUBLISHER-ABSTRACT + OFFICIAL-METADATA`.  The [T&F abstract](https://www.tandfonline.com/doi/abs/10.1080/00207168708803564) states that cyclic reduction for interval tridiagonal systems may be truncated in both phases by replacing omitted computations with easily computed intervals while retaining inclusion.  The [author bibliography](https://page.math.tu-berlin.de/~schwandt/publikationen.html) confirms the record.  No readable legitimate full text was located. | **NOT VERIFIED** beyond the abstract: recurrence, truncation formulas, dependency treatment, theorem premises, exact operation count, and witness format are unknown. |
| Schwandt, [*Cyclic Reduction for Tridiagonal Systems of Equations with Interval Coefficients on Vector Computers*](https://doi.org/10.1137/0726039), SINUM 26(3), 661–680 (1989) | `PUBLISHER-ABSTRACT + OFFICIAL-METADATA`.  The [SIAM abstract](https://epubs.siam.org/doi/10.1137/0726039) states that interval-arithmetic cyclic-reduction algorithms and their numerical/vectorization behavior are studied.  No readable legitimate full text was located. | **NOT VERIFIED** beyond the abstract. |
| Schwandt, [*Truncated interval arithmetic block cyclic reduction*](https://doi.org/10.1016/0168-9274(89)90047-0), ANM 5(6), 495–527 (1989) | `OFFICIAL-METADATA`.  The DOI/publisher record and author bibliography confirm the block-cyclic-reduction title and publication data.  A target full text or an official abstract exposing its formulas was not obtained. | **NOT VERIFIED**.  The title establishes a close block-structured family, not formula equivalence or a theorem conclusion. |
| Frommer & Hashemi, [*Verified error bounds for solutions of Sylvester matrix equations*](https://doi.org/10.1016/j.laa.2010.12.002), LAA 436(2), 405–420 (2012) | `FULL-TEXT/THEOREM`.  The legal [Wuppertal author preprint BUW-SC 10/03](https://www-ai.math.uni-wuppertal.de/SciComp/preprints/SC1003.pdf) is archived as `reference_papers_origin/frommer_hashemi2012_sylvester.pdf` (SHA-256 `5dec1a9b01321a1f8b7ebfea86570f4976e7f0d04fa62e9f16c5bfee9c4c6e80`).  Theorems 1–2, Proposition 1, Algorithm 1, Proposition 2, and the block-diagonalization discussion were inspected. | **VERIFIED** at formula and proof-object level. |

The failed Chen/Schwandt retrievals are an access limitation, not negative novelty
evidence.  Their exact relation to the proposed recurrence remains unknown.

## 2. Correct Krawczyk theorem version

Rump, [*Verification methods: Rigorous results using floating-point arithmetic*](https://doi.org/10.1017/S096249291000005X),
Acta Numerica 19 (2010), Theorem 13.3, p. 89, was checked in the archived full text.
For continuously differentiable `f`, a centered interval box `X`, and an arbitrary
fixed real matrix `R`, it defines

\[
S(X,\tilde x)=-R f(\tilde x)+(I-R[Jf(\tilde x+X)])X.
\]

Strict inclusion `S(X,tilde x) subset int(X)` implies that `R` and every matrix in
the interval Jacobian are nonsingular and that the root is unique in the declared
box.  Thus nonsingularity of the preconditioner is a conclusion, not a prior premise,
for this theorem version.  Step 003's `C=M^{-1}` remains a conservative checker
profile that selects an auditable inverse action; it is not a general theorem
requirement.  Frommer--Hashemi Theorem 2 (article p. 4) gives the same conclusion in
the linear convex-set setting: strict inclusion forces both the coefficient matrix
and the chosen preconditioner to be nonsingular.

## 3. Formula-level operator comparison

| Work / evidence | Operator | Exploited structure | Interval dependency treatment | Guarantee | Complexity | Reusable witness / proof object | Relation to `D_k/L_k/R_k/U_k` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Chen--Hashimoto 2003 / `PUBLISHER-ABSTRACT` | The abstract says “block decomposition of a Krawczyk-type interval operator”; the formula is **not verified**. | Saddle-point nonlinear equations; exact block layout **not verified**. | **Not verified.** | The abstract calls it a verification algorithm; theorem hypotheses and uniqueness scope are **not verified**. | “Fast” is qualitative in the accessible evidence; exact complexity is **not verified**. | **Not verified.** | It already blocks a generic “block Krawczyk for fast nonlinear verification” claim.  Exact recurrence overlap is unresolved. |
| Schwandt 1987/1989 / abstract or metadata only | Interval cyclic reduction; exact scalar/block recurrence is **not verified**. | Tridiagonal interval-coefficient systems, and a separately titled block-cyclic-reduction work. | The 1987 abstract verifies inclusion-preserving replacement of omitted computations; the representation and dependency analysis are **not verified**. | Inclusion preservation is supported only for the 1987 abstract's stated truncated method; exact premises are **not verified**. | **Not verified.** | No portable witness format was identified from accessible primary evidence. | Banded/block interval recursion and inclusion-preserving truncation are unsafe novelty phrases.  Equality with the one-way BE recurrence is not established. |
| Frommer--Hashemi 2012 / `FULL-TEXT/THEOREM` | Generic linear Krawczyk: `k(x_tilde,z)=-R(Ax_tilde-b)+(I-RA)z` (p. 4).  Let `S_A=(W_A A)IWA`, `S_B=IVB(BV_B)`, and `vec(D)=diag(Delta)`.  For `AX+XB=C`, equations (15)–(18) form `R_res=W_A(AX_tilde+X_tilde B-C)V_B`, `M=(D_A-S_A)Z`, `N=Z(D_B-S_B)`, and `U=(-R_res+M+N)./D`, which encloses the Krawczyk action preconditioned by `Delta^{-1}`. | Kronecker-sum system `P=I_n kron A+B^T kron I_m`; spectral diagonalization, or block diagonalization where `Delta` has sparse upper-triangular blocks (20)–(21). | Interval products enclose inverse eigenvector transforms.  `Delta^{-1}` is never formed: diagonal division or outward-rounded block back substitution is used.  Pages 10–11 explicitly show repeated right-hand-side occurrences and warn that interval dependency can grow exponentially with substitution length; bounded independent blocks are required. | Theorem 2 plus Proposition 1: `U subset int(Z)` proves nonsingularity and a unique Sylvester solution, transformed back into `X_tilde+IWA U IVB`. | Generic vectorized verification is reported as `O(m^3 n^3)`; Algorithm 1 is `O(m^3+n^3)` (Proposition 2).  With block sizes bounded by constant `b`, the back substitution is `O(nmb)` and the overall cubic bound remains. | Outward rounding; verified enclosures `IWA`, `IVB` of inverse transforms; epsilon inflation; strict `U subset int(Z)`.  The inspected paper specifies no portable independent-checker certificate. | Direct overlap: factorized Krawczyk, no explicit large inverse, structured inverse action by interval triangular solves, and an explicit dependency warning.  Non-overlap: one linear Sylvester/Kronecker-sum equation rather than nonlinear BE-MNA, no device stamps, no temporal interface quantifier, and no independent producer/checker protocol. |
| Current BlockStamp construction | `K=z_bar-CG+(I-C[JG])(X-z_bar)`, with checker profile `C=M^{-1}`.  For block-lower-bidiagonal `M`, `U_a=VSolve(D_a,R_a)` and `U_k=VSolve(D_k,R_k-L_kU_{k-1})`. | One-way BE time coupling plus device-local MNA stamps. | Conventional interval boxes and outward-rounded forward substitution.  No new dependency-preserving representation is currently defined; the recurrence can widen with slab length. | Strict slab inclusion invokes the established nonlinear Krawczyk theorem; per-block verified solves enclose the fixed exact inverse action. | For `p` dense `n`-blocks: conservative `O(p n^3)` factor verification plus `O(p n^2)` recurrence and `O(n^2)` streaming workspace, excluding output.  No advantage over verified sparse solvers follows from this bound. | Checker-reconstructed device semantics, per-block invertibility/solve evidence, input digest, tube, and strict-inclusion result. | The displayed recurrence is ordinary block forward substitution.  Device-local reconstruction and portable certificate organization are system differences; they do not presently constitute a new numerical recurrence. |

Frommer--Hashemi is the decisive formula-level overlap: it predates the broad idea of
factorizing a Krawczyk action, avoiding an explicit large inverse, applying the inverse
by outward-rounded triangular solution, and analyzing the associated dependency
failure.  Different matrix structure alone does not make those steps a new algorithm.

## 4. Broader theorem closure

1. Parameter-uniform Krawczyk/Hansen--Sengupta reasoning is established by the
   function-strip and parametric interval literature.  `S-param` is a necessary
   contract for slab composition, not a headline theorem contribution.
2. Verified sparse solves, approximate-inverse checks, and LU/factor error bounds are
   established verified-numerics components.  Producer factor hints are architecture,
   not novelty, and verified sparse kernels remain killer baselines.
3. Validated initial-set propagation and Lohner-style representations already address
   composition, correlation, and wrapping.  Certifying fixed BE roots is a different
   proof target, but that distinction alone is not a new structured solver.
4. Circuit interval root verification already exists for nonlinear DC equations.
   Repeating it along time points is not an algorithmic contribution.

## 5. Binary decision

Prior-art gate: REFRAME-SYSTEM

Prior-art reframe closure: COMPLETE

The current `D_k/L_k/R_k/U_k` recurrence must remain an implementation kernel and
baseline component, not the paper's algorithm headline.  The defensible research
opportunity is the restricted **Proof-Carrying SPICE system**: an untrusted transient
producer, independently reconstructed device/BE semantics, a portable fail-closed
certificate, parameterized slab composition, and selective recovery.  Each component
still requires comparison against its own prior art; this decision is not a claim that
the system combination is already publishably novel.

An algorithm-first framing may be reopened only after defining a non-equivalent
device-local dependency representation, reuse/witness mechanism, or optimization
objective with a theorem and component-matched evidence whose benefit is not explained
by ordinary sparse assembly or block substitution.  Missing Chen/Schwandt full texts
raise uncertainty and make this decision more conservative; they cannot be cited as
proof of either equivalence or non-overlap.  The project remains a Research Opportunity,
not a Paper Candidate.

## 6. Round 5 reframe closure

The action item `PRIOR_ART_REFRAME_SYSTEM` is closed by accepting, rather than arguing
around, the prior-art result above.  Closing the action item means that the contribution
boundary has been rewritten; it does **not** mean that algorithm novelty has passed.
The machine-readable state is therefore:

```text
prior-art task = CLOSED-BY-SYSTEM-REFRAME
algorithm novelty = ABANDONED-FOR-CURRENT-METHOD
system opportunity = OPEN / M2-DEPENDENT
Paper Candidate = FAIL-UNVERIFIED
```

### 6.1 Established foundations, not contributions

The following ingredients may be used and cited, but none may be presented as a new
method in this project:

- Krawczyk and interval-Newton existence/uniqueness tests;
- block forward substitution and exploitation of temporal block-banded structure;
- verified sparse solves and outward-rounded triangular solves;
- factorized or preconditioned verification and avoidance of an explicit full inverse;
- the generic producer--certificate--independent-checker architecture;
- parameter-uniform interval propagation, slab composition, and sampled-box predicate
  checking.

This boundary follows directly from Rump and the interval-analysis literature,
Frommer--Hashemi's formula-level overlap, Chen--Hashimoto's accessible abstract,
Schwandt's accessible interval banded/block-reduction records, Ogita/Rump verified
linear algebra, validated IVP work, and PCC/PCH/VIPR-style certifying systems.  The
unavailable Chen/Schwandt formulae remain an uncertainty, not evidence of non-overlap.

### 6.2 Claim register before M2

| Claim | Round 5 status | Exact defensible wording |
| --- | --- | --- |
| `S-fixed/S-param` | `ESTABLISHED-MATHEMATICS / IMPLEMENTATION-CANARY-SUPPORTED` | For the declared restricted fixed-step BE semantics, if the checker-side outward-rounded Krawczyk image is strictly contained in the declared tube, the stated local unique root conclusion follows under the checker TCB and assumptions A1--A7. |
| `C` | `ESTABLISHED-COROLLARY / EMPIRICAL-DEMONSTRATION-M2-DEPENDENT` | Uniformly accepted slabs compose only when every certified outgoing enclosure is contained in the next slab's incoming assumption; the conclusion concerns the specified discrete equations at declared sample points. |
| `I` | `ESTABLISHED-KERNEL / IMPLEMENTATION-CANARY-SUPPORTED` | Given checker-defined nonsingular blocks and the `VSolve` enclosure postcondition, the registered recurrence encloses the same exact real `M^{-1}r` action as dense materialization.  This is a standard block-solve instantiation, not a novelty claim. |
| `W` | `PLAUSIBLE-BUT-M2-DEPENDENT` | On the frozen workloads, joint-slab checking may improve certification rate or continuous certified prefix over matched pointwise B2 without a wider tube. |
| `D` | `UNSUPPORTED / ABANDONED-FOR-CURRENT-IMPLEMENTATION` | No direct device-locality claim is allowed: the current `temporal_device_blockstamp` path still traverses a globally assembled interval Jacobian. |
| `E` | `PLAUSIBLE-BUT-M2-DEPENDENT` | On the frozen nonlinear workloads, the circuit-structured checker may reduce a predeclared resource metric versus both matched B2 and dense slab without weakening certification, with generation and required fallback included for end-to-end claims. |
| `R` | `SUPPORTED-SAFETY-CONTRACT / ECONOMICS-M2-DEPENDENT` | A cached suffix is replayable only while each new outgoing enclosure is contained in the stored next incoming assumption; the first failed boundary invalidates the unchecked suffix. |
| `P` | `ESTABLISHED-COROLLARY / UNSUPPORTED-AS-PAPER-CONTRIBUTION` | A predicate verified over every accepted sample-point box holds for the certified discrete trajectory at those sample points; no inter-sample claim follows. |

The component ladder is not promoted to M2 evidence.  Its single-replicate result has
all configuration-level verdicts `UNKNOWN`; pooled B2 accepts more step slots and is
faster than the current temporal+streamed path, while the three slab methods have
identical verdict/rate/prefix/margin in every matched group.  These observations do not
prove `W` or `E`, and they reinforce abandonment of `D` for the current implementation.

### 6.3 Surviving paper-level propositions

The headline is narrowed to **Circuit-Structured, Independently Checkable
Certificates for Fixed-Discretization Nonlinear Transient MNA**.  `BlockStamp-Cert` may
remain an implementation name, not the name of a claimed new numerical recurrence.

| Proposition and exact wording | Closest prior art | Non-equivalence boundary | Evidence required before completion tense |
| --- | --- | --- | --- |
| **C1 -- restricted certifying-system contract.** “We specify and prototype a fail-closed certification contract for externally generated trajectories of a restricted fixed-step nonlinear BE-MNA model. Candidate states, tubes, and numerical hints are untrusted; acceptance is based on checker-side outward-rounded reconstruction of the declared discrete equations.” | DATE 2019/Nakaya circuit Krawczyk; Rump nonlinear verification; CAPD/VNODE trajectories; VWSIM circuit semantics; PCC/PCH/VIPR certifying architectures. | The proof target is an externally generated fixed-discretization transient-MNA local root, rather than DC all-root search, a continuous ODE flow, reachability, or a generic certificate.  This is a domain-specific trust boundary, not a new Krawczyk operator. | Auditable producer/checker semantic independence; complete input/semantics binding; corrupt-certificate tests; both nonlinear workloads; unfiltered replay; clean provenance.  Until then only “prototype/canary” is allowed. |
| **C2 -- circuit-specific certificate representation.** “The certificate interface binds the normalized circuit and BE semantics to the candidate/tube, ordering, scaling, midpoint operator, and verified-solve obligations, enabling replay without trusting producer convergence or factorization.” | VIPR/PCH/PCC and generic certifying algorithms; Frommer/Rump verified witnesses. | The object binds nonlinear transient-MNA device/history semantics and local-root obligations.  A bounded search finding no paper with the entire intersection is not a first-of-kind proof. | A serialized artifact containing method-specific factor/witness data; independent parsing/replay and tamper tests; byte accounting including those witnesses.  Current `certificate_bytes` contains only candidate+tube and cannot support this claim. |
| **C3 -- compositional fail-closed recovery protocol.** “Accepted uniform slab obligations compose through explicit outgoing-to-incoming containment, and recovery reuses cached suffix certificates only while that relation continues to hold; otherwise the suffix is invalidated.” | Validated initial-set/Lohner propagation and incremental certificate dependency checking. | The boundary object is specialized to a fixed-BE MNA result certificate; composition itself is established mathematics. | `S-param` implementation, multi-slab accepted traces, registered recovery cases, fault injection, fallback/recheck counts, and total recovery cost.  Whole-run strict fallback alone is not selective-recovery evidence. |
| **C4 -- verification economics.** “On the predeclared diode-RC and ring workloads, checking the restricted discrete-MNA certificate plus required fallback costs [measured effect] less than the matched strict verified comparator while preserving the declared certification strength.” | VIPR/PCH economics; verified sparse solvers and validated solvers as killer baselines. | Any remaining value is specific to nonlinear transient-MNA obligations under a matched end-to-end cost boundary, not to proof-carrying computation in general. | The complete frozen M2, five-process medians, clustered intervals, honest comparator scope, generation+check+fallback, RSS, complete witness bytes, primary matched hashes, and clean replay.  If stable net benefit is absent, the current system framing is not a Paper Candidate. |

The current `strict_mpfr_rerun` implementation must be described precisely as a
Decimal-160 reference-candidate construction followed by MPFR-256 directed B2
certificate checking.  It is a predeclared utility/fallback comparator, not evidence of
an independent full strict transient solver unless such a solver is separately
implemented.

### 6.4 Abandoned and unsupported statements

Abandoned statements include “novel BlockStamp numerical algorithm,” novelty of the
`D_k/L_k/R_k/U_k` recurrence, novelty of any foundation in Section 6.1, inherent
anti-wrapping/tightness/complexity benefits from BE block structure, and direct
device-local streaming in the current implementation.  Unsupported statements include
runtime, memory, certificate-size, acceptance, prefix, recovery-economics, portability,
or independent-implementation advantages until their listed evidence is present.

## 7. Post-M2 adaptive-method and killer-baseline closure

The complete frozen M2 initially passed Claim W against a pointwise B2 implementation
that propagated the full declared predecessor tube.  A stronger simple baseline instead
propagates each accepted Krawczyk image.  On all six registered 100-step instances this
contractive pointwise baseline lengthens the old B2 prefix, and it is never beaten by
fixed slabs of length 2, 4, 8, or 16.  A largest-first policy over
`{16, 8, 4, 2, 1}` also beats it on zero instances.  Step 009 and
`results/blockstamp/interface_contraction_canary.json` record the exact results.

Adaptive subdivision cannot supply the missing novelty.  Kearfott--Xing (1994)
already gives interval-verified continuation step control; Immler (2018) combines a
verified ODE solver with adaptive step size and set splitting; Duff--Lee (2024) gives
Krawczyk-certified homotopy tracking with adaptive step selection; and Lee (2025)
develops a priori step bounds and complexity for Krawczyk homotopy tracking.  Their
proof targets differ from fixed-BE MNA result certificates, but verified adaptive
step/slab selection is not a defensible stand-alone contribution.

The post-M2 claim register is consequently:

```text
Claim W = FAIL-CANARY / ITERATE
Claim D = STOP
Claim E = STOP
adaptive verified partition = PRIOR ART / NO CANARY GAIN
algorithm headline = STOP FOR CURRENT METHOD
Paper Candidate = FAIL-UNVERIFIED
```

Only a non-equivalent mathematical state/dependency representation or optimization
mechanism, separated from validated path-tracking and Lohner-style propagation and
beating contractive pointwise B2 in a new canary, can reopen the algorithm track.
