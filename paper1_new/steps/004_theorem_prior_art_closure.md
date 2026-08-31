# Step 004: Theorem Prior-Art Closure

## Question and method

Round 1 required a theorem-level audit of parameterized Krawczyk tests, validated
initial-set propagation, block implicit certification, and verified factor witnesses.
We rechecked the ten closest full texts already archived in this repository and
extended citation/search chains through Krawczyk/Neumaier, parametric solution-set
enclosures, and Rump/Ogita's 2024 factor-verification work.  The table records proof
objects, not title-keyword matches.  Missing a same-named algorithm is not novelty
evidence.

## Theorem-level matrix

| Work (local text where available) | Located result/proof object | Overlap with S-param or factor checking | Consequence |
| --- | --- | --- | --- |
| Krawczyk & Neumaier, *An Improved Interval Newton Operator* (1986) | Existence/uniqueness and solution-set enclosure by interval operators | Standard nonlinear inclusion foundation | S-fixed is not novel. |
| Krawczyk, *Optimal Enclosure of a Generalized Zero Set of a Function Strip* (2005) | Fixed intervals enclosing generalized zero/fixed-point sets | Function-strip parameter families are close to uniform S-param | Do not claim parameter quantification itself. |
| Kolev, *Sensitivity Analysis Using a Fixed Point Interval Iteration* (2008), Thm. 1–2 | Parametric existence tests using Hansen--Sengupta and Krawczyk operators | Directly targets existence for every allowed parameter | S-param is a contract needed for composition, not the algorithmic novelty. |
| Rump, `rump2010_verification_methods.md`, §§10–13 | Verified linear and nonlinear systems under floating-point error | Untrusted approximate inverses are already admissible when final inclusion is verified | Producer hints are architecture, not novelty. |
| Ogita & Oishi, `ogita2013_fast_verified_sparse_systems.md`, Thm. 3.1 and Algorithms 1–2 | Componentwise verified sparse-system bounds without an explicit inverse | Direct killer baseline for implicit sparse operator actions | Must compare against verified sparse kernels. |
| Rump & Ogita, *Verified Error Bounds for Matrix Decompositions* (2024), main verification theorems | Existence and entrywise error bounds for LU/QR/etc. factors | Directly covers rigorous factor verification, though not nonlinear MNA slabs | A small ordinary `A-LU` residual is insufficient. |
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
4. **The remaining falsifiable novelty opportunity is narrower:** an outward-rounded
   implicit evaluation of the slab Krawczyk operator that jointly exploits MNA device
   stamps and block lower-bidiagonal time structure, with a new recurrence/bound and a
   component-matched advantage over verified sparse pointwise checking.

No inspected work was confirmed to provide that exact circuit/time structured checker,
but this remains a bounded negative search conclusion.  Until the recurrence theorem
and B2-strong experiment exist, novelty remains `POTENTIAL / UNVERIFIED`.
