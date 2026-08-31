# Step 004: Theorem Prior-Art Closure

## Question and method

Round 1 required a theorem-level audit of parameterized Krawczyk tests, validated
initial-set propagation, block implicit certification, and verified factor witnesses.
We rechecked the ten closest full texts already archived in this repository and
extended citation/search chains through Krawczyk/Neumaier, parametric solution-set
enclosures, and Rump/Ogita's 2024 factor-verification work. Formal Round 3 then added three
high-threat structured-numerics families: Chen--Hashimoto block Krawczyk, Schwandt
interval cyclic reduction, and Frommer--Hashemi factorized Krawczyk.

The evidence labels used in the new formal Round 3 rows below are binding.
`FULL-TEXT/THEOREM` means the cited theorem or proof object was inspected.
`PUBLISHER-ABSTRACT` and `INSTITUTIONAL-METADATA` support only the words explicitly
recorded in those sources; they do **not** establish theorem premises, formula
equivalence, or non-overlap with BlockStamp. Missing a same-named algorithm is not
novelty evidence.

## Proof-object and evidence-level matrix

| Work (local text where available) | Located result/proof object | Overlap with S-param or factor checking | Consequence |
| --- | --- | --- | --- |
| Krawczyk & Neumaier, *An Improved Interval Newton Operator* (1986) | Existence/uniqueness and solution-set enclosure by interval operators | Standard nonlinear inclusion foundation | S-fixed is not novel. |
| Krawczyk, *Optimal Enclosure of a Generalized Zero Set of a Function Strip* (2005) | Fixed intervals enclosing generalized zero/fixed-point sets | Function-strip parameter families are close to uniform S-param | Do not claim parameter quantification itself. |
| Kolev, *Sensitivity Analysis Using a Fixed Point Interval Iteration* (2008), Thm. 1–2 | Parametric existence tests using Hansen--Sengupta and Krawczyk operators | Directly targets existence for every allowed parameter | S-param is a contract needed for composition, not the algorithmic novelty. |
| Chen & Hashimoto, [*Verification methods for nonlinear equations with saddle point functions*](https://doi.org/10.1016/S0377-0427(03)00570-3), *Journal of Computational and Applied Mathematics* 159(1), 13–24 (2003). DOI: `10.1016/S0377-0427(03)00570-3` | `PUBLISHER-ABSTRACT + INSTITUTIONAL-METADATA`; the official abstract describes a fast verification algorithm based on a block decomposition of a Krawczyk-type interval operator. Target full text/theorem not inspected. | Direct method-description overlap with block Krawczyk for nonlinear equations | Generic “block-decomposed Krawczyk” or “fast structured nonlinear verification” is prior art. The available evidence does not resolve BE-MNA/device-stamp/time-recurrence overlap. |
| Rump, `rump2010_verification_methods.md`, §§10–13 | Verified linear and nonlinear systems under floating-point error | Untrusted approximate inverses are already admissible when final inclusion is verified | Producer hints are architecture, not novelty. |
| Ogita & Oishi, `ogita2013_fast_verified_sparse_systems.md`, Thm. 3.1 and Algorithms 1–2 | Componentwise verified sparse-system bounds without an explicit inverse | Direct killer baseline for implicit sparse operator actions | Must compare against verified sparse kernels. |
| Rump & Ogita, *Verified Error Bounds for Matrix Decompositions* (2024), main verification theorems | Existence and entrywise error bounds for LU/QR/etc. factors | Directly covers rigorous factor verification, though not nonlinear MNA slabs | A small ordinary `A-LU` residual is insufficient. |
| Schwandt, [*A truncated cyclic reduction algorithm for interval arithmetic tridiagonal systems of equations*](https://doi.org/10.1080/00207168708803564), *International Journal of Computer Mathematics* 21(2), 161–184 (1987). DOI: `10.1080/00207168708803564` | `PUBLISHER-ABSTRACT + INSTITUTIONAL-METADATA`; the abstract says omitted reduction/solution computations are replaced by inexpensive intervals while preserving inclusion. Target full text/theorem not inspected. | Interval tridiagonal recursion and inclusion-preserving truncation | Neither banded interval recurrence nor reliable truncation is novel. Exact relation to nonlinear BlockStamp obligations remains unverified. |
| Schwandt, [*Cyclic Reduction for Tridiagonal Systems of Equations with Interval Coefficients on Vector Computers*](https://doi.org/10.1137/0726039), *SIAM Journal on Numerical Analysis* 26(3), 661–680 (1989). DOI: `10.1137/0726039` | `PUBLISHER-ABSTRACT + INSTITUTIONAL-METADATA`; the SIAM abstract describes interval-arithmetic cyclic-reduction algorithms and reports vectorization/numerical experiments. Target theorem not inspected. | Interval tridiagonal structured solve | “Interval cyclic reduction” is prior art; no theorem-level evidence here decides the BlockStamp recurrence. |
| Schwandt, [*Truncated interval arithmetic block cyclic reduction*](https://doi.org/10.1016/0168-9274(89)90047-0), *Applied Numerical Mathematics* 5(6), 495–527 (1989). DOI: `10.1016/0168-9274(89)90047-0` | `PUBLISHER-ABSTRACT + INSTITUTIONAL-METADATA`; the publisher abstract describes interval block cyclic reduction for block-tridiagonal systems and inexpensive replacement intervals preserving inclusion. Target full text/theorem not inspected. | Strong direct threat to interval block-banded recursion and truncated verified evaluation | Block structure plus inclusion-preserving reduction cannot be claimed. Circuit stamps, nonlinear slab composition, portable proof objects, and the exact recurrence still require formula-level comparison. |
| Frommer & Hashemi, [*Verified error bounds for solutions of Sylvester matrix equations*](https://doi.org/10.1016/j.laa.2010.12.002), *Linear Algebra and its Applications* 436(2), 405–420 (2012). DOI: `10.1016/j.laa.2010.12.002` | `PUBLISHER-ABSTRACT + INSTITUTIONAL-METADATA`; the abstract describes a Krawczyk variant with factorized preconditioner, cubic dense complexity under diagonalizability, and block diagonalization otherwise. Wuppertal lists preprint BUW-SC 2010/3, but its PDF timed out in this audit; no target theorem was inspected. | Strong direct threat to factorized Krawczyk actions that avoid an explicit large inverse/operator | Factorization and structure-based complexity reduction cannot be novelty. Sylvester/Kronecker versus block-lower-bidiagonal BE-MNA non-equivalence is not yet theorem-verified. |
| Nedialkov et al., validated IVP literature summarized in `kapela2021_capd_dynsys.md`, §§2–5 | Unique-flow enclosures propagated from interval initial sets | Continuous-time analogue of quantified interfaces and composition | Time-slab propagation is not novel. |
| Kapela et al., `kapela2021_capd_dynsys.md`, Algorithms 1–2 | Lohner/doubleton set propagation and C0/C1 enclosures | Explicitly addresses wrapping and correlations across steps | Axis-aligned interface boxes require a killer comparison or a narrower claim. |
| Akhter et al., `akhter2019_finding_all_dc_operating_points.md`, §II | Circuit-specific interval/Krawczyk root exclusion and uniqueness | Device interval semantics plus circuit nonlinear roots | Repeating this per BE point is not sufficient novelty. |
| Chaudhry et al., `chaudhry2025_adjoint_dae_error.md`, Thms. 3.1 and 4.1 | DAE adjoint representations of discretization/QoI error | Different guarantee: error representation rather than outward-rounded local-root proof | Keep continuous-time/discretization error outside Claim S. |

## Closure decision

1. **S-param is substantially covered as general interval methodology.**  The uniform
   inclusion argument in Step 003 is necessary for sound composition but cannot be a
   headline theorem contribution.
2. **Verified LU/factor witnesses are substantially covered.**  The research must use
   them as a trusted subroutine or strong baseline, not present factor residual checking
   as new.
3. **Validated initial-set propagation already handles composition and wrapping.**  The
   distinction in proof target (fixed BE roots versus continuous flow) is real, but not
   by itself enough for a strong paper.
4. **Generic structural acceleration is also substantially covered at the
   method-description level.** Chen--Hashimoto covers block-decomposed Krawczyk;
   Schwandt covers interval tridiagonal/block-tridiagonal cyclic reduction and
   inclusion-preserving truncation; Frommer--Hashemi covers factorized Krawczyk and
   structure-based complexity reduction. None of these phrases is a safe contribution.
5. **The remaining falsifiable novelty opportunity is narrower:** an outward-rounded
   implicit evaluation of the slab Krawczyk operator that jointly exploits MNA device
   stamps and block lower-bidiagonal time structure, with a new recurrence/bound and a
   component-matched advantage over verified sparse pointwise checking.

No inspected source was confirmed to provide that exact circuit/time structured checker,
but the three new high-threat families have not yet received target-full-text/theorem-level
comparison. Consequently, absence of confirmation is **not** evidence that their formulas
exclude BlockStamp. Until that audit, a valid recurrence theorem, and the B2-strong
experiment all exist, novelty remains **`ITERATE / POTENTIAL-UNVERIFIED`** and this work is
not a Paper Candidate.
