# Step 001: Proof-Carrying SPICE Literature and Novelty Gate

## Decision

`GO_TO_MINIMAL_PROBLEM_PROBE`, not `PAPER_CANDIDATE`.

## Completed

- Verified the DATE 2019 and Nakaya 2009 DC interval seeds.
- Searched circuit interval verification, validated ODE/DAE integration, AMS formal
  verification, proof-carrying computation, verified sparse linear algebra, and
  Verilog-A compilation.
- Audited 29 high-relevance works and identified eight highest-threat clusters.
- Downloaded 14 legitimate public PDFs and converted them to page-anchored Markdown.
- Recorded source URLs, SHA-256 checksums, evidence levels, and unavailable full text.

## Scientific facts added

1. Krawczyk on transistor circuit equations and automated CMOS DC interval
   verification are established prior art.
2. Validated ODE solvers already prove unique solutions and propagate enclosures for
   interval initial states/parameters; generic time-slab composition is not enough.
3. Producer/certificate/consumer checking is established in proof-carrying hardware
   and certifying optimization.
4. Fast verified sparse linear-system algorithms exist, but general sparse matrices,
   fill-in, and witness checking remain active constraints.
5. Verilog-A code and derivative generation exist; no verified interval third
   semantics was found in the inspected OpenVAF/ADMS literature.
6. No inspected work simultaneously provides producer-agnostic independently
   checkable certificates for transistor-level nonlinear transient discrete MNA.

## Strongest objection

The proposal may be only DATE 2019 applied per time step, with standard validated-ODE
interval propagation and a conventional proof-carrying wrapper.

## Next gate-changing action

Implement only the smallest BE diode/MOS slab probe needed to compare pointwise,
dense-slab, and block-structured certification. Do not build a general Verilog-A
compiler or run large experiments before the claimed structural advantage appears.
