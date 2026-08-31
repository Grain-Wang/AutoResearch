# Historical Stage Assessment Before the CCF-B Review

This note preserves the useful technical conclusions that were previously stored as `review_round3.md`, but it is **not part of the formal reviewer-round sequence**.

## Why this note exists

The old Round-3 file was created without a preceding research-response increment and mixed a historical paper1/CoVoL transition sentence into the paper2 reviewer chain. Its technical content was useful, but its placement polluted reviewer numbering and future Codex context. The formal reviewer sequence is now kept under `paper2/responce_from_reviewer/`; this file is only a research-history note.

## Preserved technical conclusions

1. **Research status**: BlockStamp-Cert remains a Research Opportunity; the minimal problem probe and Paper Candidate Gate are not yet passed.
2. **Novelty is narrower than generic block Krawczyk**: Krawczyk/interval Newton, parameterized root enclosure, initial-set propagation, verified factor witnesses, proof-carrying producer/checker patterns, and DC circuit interval verification are prior methodology.
3. **High-threat neighboring methods**: block-decomposed Krawczyk-type verification, interval cyclic-reduction/banded verified solves, and factorized-preconditioner verified computation mean that “block Krawczyk” or “implicit factorized solve” alone cannot be the headline novelty.
4. **The only defensible algorithmic opportunity** is the joint use of transient-MNA temporal dependence and device-local stamp structure in a rigorous implicit operator evaluation, with component-matched evidence that the combination changes runtime, memory, certificate size, or certification behavior.
5. **Soundness blocker**: the preconditioning operator used in the Krawczyk condition must be defined as a checker-verifiable nonsingular real operator. The old contract did not explicitly exclude `C=0`; therefore the final theorem must close this assumption.
6. **Recommended first operator definition**: use a checker-side midpoint block-lower-bidiagonal Jacobian `M`, define the proof operator through the exact real inverse action of `M`, and evaluate that action with outward-rounded verified block solves.
7. **Minimal recurrence under study**:

   \[
   U_a = \operatorname{VSolve}(D_a,R_a),\qquad
   U_k = \operatorname{VSolve}(D_k,R_k-L_kU_{k-1}).
   \]

   The implementation must show that the recursive interval result contains the corresponding dense real operator action. The recurrence itself may still be standard block forward substitution; paper value depends on the circuit-specific combination and measurable advantage.
8. **Arithmetic TCB**: the Decimal-based backend is only a canary. Transcendental functions and division need a genuinely directed-rounded backend before any strict soundness claim.
9. **Minimum transient-MNA path**: RC analytic canary → diode-RC nonlinear BE root → 3-stage ring oscillator → only then larger analog modules.
10. **Strong baseline ladder**: pointwise verified Krawczyk → dense slab → temporal-only recurrence → temporal+device BlockStamp. All variants must share arithmetic, device semantics, tube, scaling, ordering, factor hints, precision, and timing environment.

## Stop/reframe conditions retained

- Stop the efficiency claim if the recurrence has no stable runtime/memory/certificate advantage over component-matched baselines.
- Stop the slab headline if pointwise certification is already cheap and does not suffer meaningful interface propagation loss.
- Stop the soundness claim on any confirmed false accept, invalid directed enclosure, or theorem counterexample accepted by the checker.
- Reframe as a restricted independent-checker/system paper if the numerical recurrence is standard but the complete checker still has clear end-to-end value.

## Provenance

The original stage-assessment file entered the branch in commit `5dc8f8f082ce7b0da2e53481559abe682a6c52cc`. This note keeps the scientifically useful conclusions while removing the historical cross-project wording and reviewer-round ambiguity.
