# RO-1: Circuit-Structured Proof-Carrying Transient MNA

## Status

- Stage: Research Opportunity
- Opportunity gate: PASS
- Paper Candidate gate: FAIL / UNVERIFIED
- Literature cutoff: 2026-08-25

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
producer/checker pattern. A paper-worthy algorithm must exploit device locality and
the block lower-banded temporal Jacobian to reduce certificate size or checking cost
relative to pointwise Krawczyk and strict reruns.

## Falsifiable probe

- Models: R/C/diode and Level-1 MOS only.
- Circuits: at least two of ring oscillator, SRAM cell, and op-amp transient.
- Scale: 10--100 nodes and 100--1000 fixed BE steps.
- Comparators: pointwise Krawczyk, dense slab Krawczyk, high-precision strict rerun,
  and a verified sparse-linear kernel.
- Outcomes: acceptance rate, tube growth, checker/runtime ratio, certificate bytes,
  local fallback fraction, and failure slices by conditioning and slab length.

## Stop conditions

STOP or reformulate if the claimed baseline defect cannot be reproduced; interface
wrapping generally explodes before useful trajectory lengths; block checking has no
advantage over pointwise/strict baselines; or the checker must duplicate essentially
the entire trusted simulation cost.

## Evidence

See `paper2/research/proof_carrying_spice_literature.md` and the source PDFs under
`paper2/reference_papers_origin/`.
