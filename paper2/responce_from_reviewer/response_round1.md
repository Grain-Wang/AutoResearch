# Response to Review Round 1

We agree with the central diagnosis: the previous repository contained a strong
protocol but no theorem-backed implementation or experimental evidence.  We therefore
did not expand to SRAM, Verilog-A, modern compact models, or a second producer.

## Implemented in this round

1. **Soundness quantifiers.** `steps/003_formal_soundness_contract.md` now separates
   S-fixed from S-param, states the uniform residual/Jacobian enclosure needed for every
   incoming interface value, lists seven executable assumptions, and gives proof
   skeletons and explicit local/discrete non-claims.
2. **Recovery dependency propagation.** `steps/006_selective_recovery_contract.md` and
   `experiments/recovery.py` permit suffix reuse only when the newly certified outgoing
   interval is contained in the cached next-slab assumption.  Six scenario classes are
   tested; overlap or disjointness invalidates the suffix.
3. **Arithmetic TCB canary.** `experiments/interval_backend.py` implements auditable
   binary64 interval arithmetic through exact Decimal images and directed final
   conversion, including `exp`, `log`, `sqrt`, hex serialization, and structured
   unsupported-domain results.  Randomized exact-oracle tests exercise 10,000 points
   per binary operation and per special function with zero observed containment
   violations.  This is implementation evidence, not a substitute for the theorem.
4. **Device branch semantics.** Checker-side diode and restricted Level-1 NMOS stamps
   independently enclose values and derivatives.  Tests cover 1,000 diode boxes and
   1,000 boxes in each MOS region.  Boxes crossing cutoff/triode/saturation boundaries
   return unsupported instead of selecting the center branch.
5. **Non-corruption motivation canary.** A 24-case passive MNA conductance sweep shows a
   natural conditioning mechanism where a residual threshold accepts while the exact
   forward error is one volt and the declared tube excludes the analytic root.  We
   label this `PASS-CANARY / REAL-WORKLOAD-UNVERIFIED`; it does not establish prevalence
   in production SPICE.
6. **Prior-art closure.** `steps/004_theorem_prior_art_closure.md` records ten
   theorem-level neighbors.  It concludes that parameterized Krawczyk, initial-set
   composition, and factor verification are established methodology.  The only
   remaining candidate novelty is the circuit/time structured implicit operator bound.

## Claims deliberately not made

- Claim S is not yet established for BlockStamp because the block-recursive operator
  and factor-enclosure chain are not implemented.
- Claim E/R has no performance support.
- Fault injection is not statistical evidence for soundness.
- The passive canary is not industrial-severity evidence.
- The work remains a Research Opportunity, not a Paper Candidate.

## Next gate

The next atomic task is B2-strong plus an explicit small-matrix BlockStamp recurrence,
sharing the same tube, scaling, stamps, ordering, factor witness, precision, and thread
settings.  We will then run the frozen diode/ring-oscillator slab grid.  If the component
ladder cannot isolate a structural acceptance, wrapping, memory, or runtime advantage,
we will stop the efficiency/Paper-Candidate claim rather than expand engineering scope.
