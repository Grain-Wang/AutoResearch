# RO-1: Circuit-Structured Proof-Carrying Transient MNA

## Status

- Stage: Research Opportunity
- Opportunity gate: PASS
- Paper Candidate gate: FAIL / UNVERIFIED
- Algorithm headline: STOP for current BlockStamp recurrence
- Literature cutoff: 2026-09-04

## Baseline defect

A conventional transient SPICE success flag and small residual do not independently
prove that the declared discrete nonlinear MNA equation has a locally unique root
near the returned state. Existing validated ODE integration provides rigorous
continuous-flow enclosures, and existing circuit interval work verifies DC operating
points, but the current audit did not find their conjunction with an arbitrary
external trajectory, portable certificate, and independent checker.

## Algorithmic hypothesis

For a fixed Backward Euler discretization, divide the candidate trajectory into
slabs. Treat the incoming state interval as a universally quantified parameter.
Let an untrusted producer provide trajectory centers, tube radii, permutations, and
sparse factor/preconditioner hints. An independent checker reconstructs device-local
interval stamps and verifies a block-structured Krawczyk inclusion using reliable
outward rounding. Accepted slab endpoints become the next interface interval;
rejected slabs are split or recomputed.

The novelty cannot be Krawczyk, interval arithmetic, time stepping, or the generic
producer/checker pattern. A paper-worthy successor must introduce a non-equivalent
dependency representation, witness-reuse decision, or optimization mechanism. It must
beat a pointwise Krawczyk baseline that propagates its own accepted interface image;
ordinary block forward substitution, device-stamp traversal, or adaptive slab splitting
is insufficient.

## Post-M2 diagnosis

The complete frozen M2 reports `W=PASS` only against a pointwise baseline that feeds the
full producer tube forward; `D=STOP` and `E=STOP`. A six-instance strengthened canary
propagates the accepted pointwise Krawczyk image and improves the old pointwise prefix in
6/6 instances. It dominates or ties every fixed slab length, while largest-first
adaptive slabs improve 0/6 instances. Adaptive verified step selection is also covered
by interval continuation, certified Krawczyk homotopy tracking, and validated ODE prior
art. See `steps/009_m2_result_gate.md`.

## Falsifiable probe

- Models: R/C/diode and Level-1 MOS only.
- Circuits: at least two of ring oscillator, SRAM cell, and op-amp transient.
- Scale: 10--100 nodes and 100--1000 fixed BE steps.
- Comparators: pointwise Krawczyk, dense slab Krawczyk, high-precision strict rerun,
  and a verified sparse-linear kernel.
- Outcomes: acceptance rate, tube growth, checker/runtime ratio, certificate bytes,
  local fallback fraction, and failure slices by conditioning and slab length.

## Stop conditions

The current BlockStamp algorithm path meets its stop condition: block checking has no
advantage over contractive pointwise B2, Claim D/E failed, and the recurrence is standard
verified block substitution. The restricted certificate-system problem remains real,
but it may not advance to Paper Candidate without a new algorithmic mechanism and a new
low-cost gate.

## Evidence

See `paper2/research/proof_carrying_spice_literature.md` and the source PDFs under
`paper2/reference_papers_origin/`.
