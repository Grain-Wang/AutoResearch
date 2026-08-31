# Step 008: Next-Round M0/M1/M2 Gate

## 1. Decision and purpose

Current machine decision from `results/blockstamp/next_round_gate.json`:

```text
M0 = PASS-CANARY
M1 = ITERATE (Claim I implementation canary passed; novelty unresolved)
M2 = NOT-STARTED
PAPER_CANDIDATE = FAIL-UNVERIFIED
```

This document freezes the smallest evidence sequence that can change the BlockStamp
paper decision and records the first execution against it.  It consolidates Review
Rounds 2--5.  A generated path is evidence only for its declared canary scope; passing
a numerical artifact does not establish a theorem, novelty, efficiency, or Paper
Candidate status.

The order is mandatory:

```text
M0 soundness chain -> M1 operator object -> M2 matched nonlinear probe
```

M0 or M1 failure prevents M2 performance claims.  Work outside this chain must not be
used to compensate for a failed core gate.

## 2. Common evidence contract

Every JSON artifact must contain:

- `schema_version`, `generated_at_utc`, `git_commit`, and `dirty_worktree`;
- `command`, `python_version`, `platform`, and a structured dependency/backend version;
- `config_sha256`, `input_sha256`, `source_files_sha256`, and all random seeds;
- `status` in `PASS`, `ITERATE`, `STOP`, or `UNSUPPORTED`;
- `attempted_cases`, `supported_cases`, `unsupported_cases`, and `failure_codes`;
- `first_failure`, which is `null` on no observed failure and otherwise contains a
  replayable case identifier, input/configuration, expected relation, and observed
  value.

CSV artifacts must have an adjacent `<stem>.manifest.json` containing the same
provenance fields, the CSV SHA-256, row count, required column list, allowed
method/verdict values, and the command that generated the CSV.  Artifacts may not be
hand-edited.  All failed,
rejected, unsupported, timeout, and warm-up-excluded configurations remain in the raw
output with a machine-readable reason.

The only checker verdicts are `ACCEPT`, `UNKNOWN`, and `UNSUPPORTED`.  An oracle fact
such as `root_in_tube=false` must be stored separately and may not be written as a
checker `REJECT_NO_ROOT` verdict without an implemented no-root theorem.

## 3. M0: soundness-chain gate

### 3.1 Formal operator condition

The first checker operator is frozen as follows:

1. `M` is the checker-reconstructed binary64 point midpoint Jacobian after the declared
   checker-validated permutation and scaling.
2. `M` has block lower-bidiagonal form with diagonal blocks `D_k` and subdiagonal blocks
   `L_k`.
3. `C` denotes the exact real inverse action `M^{-1}`; it is evaluated by
   outward-rounded verified block solves, never by trusting a producer inverse.
4. Every diagonal-block solve must prove that all elimination/triangular pivots exclude
   zero.  An inconclusive or singular block returns `UNSUPPORTED` or `UNKNOWN`, never
   `ACCEPT`.
5. The `C = 0`, `F(x) = x + 2`, `X = [-1, 1]` counterexample and singular-block cases
   must be executable regressions rejected by the checker premises.

The corrected S-fixed/S-param statements may cite standard Krawczyk theory, but the
standard theorem is not a novelty claim.

### 3.2 Rigorous arithmetic artifact

Reserved path: `paper2/results/blockstamp/rigorous_backend_summary.json`.

In addition to the common fields, it must contain:

- `backend.name`, `backend.version`, `backend.library`, `backend.precision_bits`;
- `rounding_modes.lower = RNDD` and `rounding_modes.upper = RNDU`;
- one entry for each of `add`, `sub`, `mul`, `div`, `exp`, `expm1`, `log`, and `sqrt`;
- per operation: `random_cases`, `edge_cases`, `supported_cases`, `unsupported_cases`,
  `containment_violations`, `oracle_precision_bits`, and `edge_families`;
- edge families covering subnormal values, the finite overflow frontier, near-zero
  denominators, cancellation, domain boundaries, and hard-to-round special-function
  inputs where applicable.

Acceptance requires at least 50,000 seeded random cases per operation in addition to
the fixed edge corpus, an independent higher-precision oracle, zero containment
violations for all supported inputs, and structured fail-closed output for unsupported
domains/ranges.  A summary produced by a manually maintained JSON file is invalid.

**Observed canary.**  The artifact reports `PASS`: 400,056 attempted cases, consisting
of 50,000 random cases and 7 edge cases for each of eight operations; 400,044 cases
were supported, 12 edge/domain cases returned structured unsupported results, and 0
containment violations were observed.  Its own `claim_scope` is a directed-rounding
implementation audit, not a formal proof of MPFR or the complete checker TCB.

### 3.3 BE MNA artifact

Reserved path: `paper2/results/blockstamp/mna_canary.json`.

Required fields include:

- `semantics_sha256`, `state_layout_sha256`, `topology_sha256`, `step_method`,
  `step_size`, and `steps`;
- separate `rc` and `diode_rc` sections with `oracle`, `oracle_precision_bits`,
  `root_contained_steps`, `root_excluded_steps`, `max_point_residual`,
  `jacobian_sample_count`, `jacobian_containment_violations`, and
  `checker_false_accepts`;
- `negative_cases` covering wrong BE history, node/branch mapping, permutation,
  root-excluding tubes, singular `C`, malformed inputs, and unsupported device/domain
  boxes, each with `oracle_root_in_tube`, `checker_verdict`, and `failure_code`.

Acceptance requires at least 100 consecutive BE steps for both RC and diode-RC,
containment of every supported analytic/multiprecision root in its declared valid tube,
zero Jacobian containment violations, and zero confirmed false accepts.  A shared
point/interval evaluator is not an independent oracle.

**Observed canary.**  The artifact reports `PASS`: RC and diode-RC each completed 100
steps with 100 `ACCEPT` verdicts and every registered root contained.  Across both
circuits, 1,800 Jacobian samples had 0 containment violations.  The 17 registered
negative cases had 0 confirmed false accepts.  Artifact totals are 217 attempted, 212
supported, and 5 structured unsupported cases.  The scope remains restricted BE MNA
with a dense pointwise checker, not B2-strong.

### 3.4 M0 decision

M0 is `PASS-CANARY` only when Sections 3.1--3.3 pass at the registered implementation
scope.  Any confirmed false accept,
arithmetic containment failure, accepted singular operator, accepted branch-crossing
box, or accepted incorrect BE history triggers `STOP-S`.  After a root-cause repair,
all M0 cases must be replayed before the stop can be cleared; performance results
generated under the failed chain are invalid.

**Current M0 decision:** `PASS-CANARY`.  This is machine implementation evidence under
the recorded source/configuration hashes and conditional mathematical contract; it is
not an unconditional soundness theorem.  The current artifacts record
`dirty_worktree=true`, so clean independent replay remains required.

## 4. M1: BlockStamp operator gate

### 4.1 Frozen recurrence

For remainder blocks `R_k`, the only first-round operator is:

```text
U_0 = VSolve(D_0, R_0)
U_k = VSolve(D_k, R_k - L_k U_{k-1}), k = 1, ..., s-1
```

`VSolve(D, V)` must enclose the exact real solve for every point matrix `D` and interval
right-hand side `V` that it reports as supported.  The proof obligation is that the
flattened recursive result contains every exact real value in `M^{-1}R`; it is not a
claim that block forward substitution is new or inherently less wrapping.

### 4.2 Operator artifact

Reserved path: `paper2/results/blockstamp/operator_canary.json`.

Required fields include:

- `recurrence_version`, `backend_sha256`, `generator_version`, `generator_seed`, and
  `dense_oracle`;
- one `grid` record for every Cartesian pair
  `block_dimension in {1,2,4,8}` and `slab_length in {2,4,8}`;
- per grid record: `attempted_cases`, `supported_cases`, `unsupported_cases`,
  `containment_violations`, `verified_pivots`, `max_enclosure_inflation`,
  `median_enclosure_inflation`, and replayable `failure_case_ids`;
- a `singular_cases` section with attempted count, verdict distribution, and false
  supported count;
- an explicit definition of `enclosure_inflation` and the treatment of zero-width
  oracle intervals.

Acceptance requires at least 200 nonsingular seeded instances for every required grid
cell, MPFR or equivalent independent dense action as the oracle, zero containment
violations, and zero singular/inconclusive cases reported as successful solves.
Unsupported cases do not count toward the 200 accepted nonsingular instances.

**Observed canary.**  The artifact reports `PASS`: all 12 Cartesian grid cells contain
200 supported nonsingular instances, for 2,400 total, with 0 recursive or dense-action
containment violations.  Two cases per cell, 24 total, use nonzero-width interval
right-hand sides and are checked against the exact Fraction coordinate hull of the
materialized dense dyadic-rational action.  One additional singular system returned
`UNSUPPORTED` and was not counted toward the 2,400.  The largest absolute enclosure
inflation over the exact hull was 0.1321725812626729; this scale-dependent diagnostic
does not pass Claim W or compare against B2.

### 4.3 Novelty closure and M1 decision

Before an algorithm novelty statement is allowed, the theorem matrix must compare the
frozen proof object against Chen--Hashimoto block-Krawczyk, Schwandt interval cyclic
reduction, Frommer--Hashemi factorized Krawczyk, and the closest verified sparse solve.
It must record the exact operator, structural assumptions, theorem guarantee,
complexity, and the remaining device/time-specific difference.

Passing the numerical artifact establishes `CLAIM-I: IMPLEMENTATION-CANARY-PASS`; it
does not establish novelty or efficiency.  M1 remains `ITERATE` if containment passes
but the literature comparison or device-aware remainder mechanism is unresolved.  If
the frozen recurrence is directly covered by prior art and no non-equivalent
device/time representation remains, stop the algorithm-headline claim.  Continue only
as a restricted certificate-system opportunity if M2 later demonstrates end-to-end
value over strict rerun.

**Current M1 decision:** `ITERATE`.  Claim I is
`IMPLEMENTATION-CANARY-PASS`, efficiency is `UNVERIFIED`, and novelty is `UNRESOLVED`.
The operator canary therefore permits continued mechanism work but cannot support an
algorithm contribution statement.

## 5. M2: matched nonlinear and killer-baseline gate

M2 starts only after M0 passes, the M1 operator canary has zero containment violations,
and a component-matched B2-strong/fairness path is ready.  The first two numerical
conditions now pass at canary level; B2-strong is not ready, so M2 remains
`NOT-STARTED`.

### 5.1 Frozen workload and run grid

- Workloads: `diode_rc` and `nmos_ring_3stage`.
- Instances: at least three predeclared conditioning/load/initial-state settings per
  workload.
- Time steps: `{100, 300, 1000}`.
- Slab lengths: `{1, 2, 4, 8, 16}` where applicable.
- Timing: five independent processes per matched timing configuration; one warm-up is
  recorded but excluded before observing timings.
- Methods: `strict_mpfr_rerun`, `dense_slab_generic`,
  `device_local_pointwise_b2`, `temporal_only`, and
  `temporal_device_blockstamp`.

B2-strong must use a verified-sparse linear kernel where applicable.  It is the primary
killer for slab necessity.  Dense slab is the operator-strength/cost comparator;
strict MPFR rerun is the end-to-end utility comparator; temporal-only versus
temporal+device isolates Claim D.

### 5.2 B2 fairness artifact

Reserved path: `paper2/results/blockstamp/b2_fairness.json`.

It must contain hashes for the input, producer trace, candidate centers, tubes,
arithmetic backend, device semantics, MNA semantics, scaling, ordering, midpoint
operator/factor, thread count, hardware, and build/runtime environment for every
matched method.  Required fields include `all_required_hashes_present`,
`all_shared_hashes_match`, `allowed_method_differences`, `easy_case_accepts`,
`known_bad_cases`, and `confirmed_false_accepts`.

M2 is invalid if a shared hash is absent or differs without a predeclared method reason,
or if the baseline and proposed method use different tube initialization, precision,
semantics, scaling, ordering, factor quality, threads, or hardware.

**Observed B2 status.**  `b2_fairness.json` reports `ITERATE / B2-CANARY-ONLY`: the
dense pointwise path accepted 200 registered easy cases, and 17 known-bad cases had 0
confirmed false accepts.  However, `all_required_hashes_present=false`, shared-method
matching is not yet decidable, and `strong_baseline_status` is
`UNIMPLEMENTED-VERIFIED-SPARSE`.  Missing items are the verified-sparse kernel, a
component-matched BlockStamp circuit path, and timing/RSS/certificate-byte ladder.

### 5.3 Component and minimal-probe artifacts

Reserved paths:

- `paper2/results/blockstamp/component_ladder.csv` plus manifest;
- `paper2/results/blockstamp/minimal_probe.csv` plus manifest.

Every result row must contain:

```text
run_id, circuit_id, instance_id, producer_id, producer_precision,
producer_tolerance, step_size, steps, slab_length, replicate, method,
input_sha256, producer_trace_sha256, candidate_sha256, tube_sha256,
backend_sha256, semantics_sha256, scaling_sha256, ordering_sha256,
factor_sha256, threads, hardware_id, checker_verdict, failure_code,
oracle_root_in_tube, confirmed_false_accept, certification_rate,
certified_prefix_steps, tube_max_relative_width, tube_growth_rate,
inclusion_margin_min, assembly_seconds, verified_solve_seconds,
operator_propagation_seconds, certificate_generation_seconds,
check_seconds, fallback_seconds, end_to_end_seconds, peak_rss_bytes,
certificate_bytes, raw_trajectory_bytes
```

The component ladder must contain all four certification methods
`dense_slab_generic`, `device_local_pointwise_b2`, `temporal_only`, and
`temporal_device_blockstamp` for each matched input.  The minimal probe additionally
contains `strict_mpfr_rerun`.  No success-only filtering is permitted.

**Current artifact status:** neither `component_ladder.csv` nor `minimal_probe.csv`
exists; no Claim W/D/E or nonlinear transient performance result is available.

### 5.4 Stable-signal definition

Comparisons use matched configurations and circuit-instance clustered bootstrap 95%
confidence intervals.  Time uses the five-process median per configuration.  A
resource advantage is `stable` only if, for the same primary metric among
`check_seconds`, `peak_rss_bytes`, or `certificate_bytes`:

1. the baseline-to-BlockStamp ratio is greater than one in at least two predeclared
   instances of **each** workload at both slab lengths 8 and 16;
2. the clustered 95% confidence-interval lower bound of the aggregate ratio is greater
   than one; and
3. those matched configurations do not have lower certification rate or a shorter
   certified prefix under BlockStamp.

All ratios and confidence intervals are reported even when this rule fails.  The rule
is a frozen canary decision, not a universal practical-significance threshold.

Claim W has a separate mechanism rule: relative to matched B2, slab certification must
show a strictly longer certified prefix or higher certification rate in at least two
instances of each workload for a nontrivial slab length, without a larger maximum tube
width on those same instances.  A runtime gain alone does not pass Claim W.

Claim D passes only if temporal+device beats temporal-only under the stable-signal rule
for at least one registered resource metric, or passes the Claim-W mechanism rule on
the same matched inputs.

### 5.5 M2 stop rules

- **STOP-S:** any confirmed false accept or broken M0 containment premise.  Invalidate
  all dependent M1/M2 results.
- **STOP-W:** B2 has no worse certification rate, prefix, or tube growth and no higher
  cost across both nonlinear workloads.  Remove slab anti-wrapping/acceptance claims;
  do not treat a single failed prototype as proof that all non-equivalent dependency
  representations are impossible.
- **STOP-E:** at slab lengths 8 and 16, none of check time, peak RSS, or certificate
  bytes satisfies the stable-signal definition against both the matched B2/verified-
  sparse path and dense slab.  Do not seek larger circuits merely to hide this failure.
- **STOP-D:** temporal+device does not satisfy either stable-signal rule against
  temporal-only.  Remove device-locality as an algorithmic contribution and report it,
  at most, as an implementation choice.

If W, E, and D all stop, stop the BlockStamp algorithm headline.  A restricted
pointwise certificate system may remain only if its complete generation, checking,
and fallback cost has a stable advantage over independent strict rerun.  If that also
fails, archive the current opportunity rather than expanding engineering scope.

If natural tight/default double producers rarely yield an incorrect trajectory, this
does not falsify the certificate object.  It does require reframing the motivation to
untrusted, approximate, low-precision, or accelerated producers; no claim that mature
SPICE commonly returns wrong answers is then allowed.

## 6. Promotion rule

M2 may emit `PRE_PAPER_CANDIDATE` only when all of the following hold:

1. M0 passes and all known bad cases have zero confirmed false accepts;
2. M1 contains the independent dense action for every required supported case;
3. the B2 fairness manifest has complete matching hashes;
4. at least one of Claim W or Claim E passes under its frozen rule, with Claim D reported
   independently rather than inferred;
5. both nonlinear workloads have complete, unfiltered, replayable outputs;
6. every performance statement includes certificate generation, checking, and required
   fallback cost; and
7. the recurrence-specific prior-art comparison leaves a defensible algorithmic
   difference.

This is not the full Paper Candidate gate.  Promotion to `PAPER_CANDIDATE` additionally
requires independent replay in a clean output directory, a stable result under the
strongest verified baselines, evidence that gains are not caused by implementation
differences, and a complete core-component ablation.  Until those facts exist, the
repository status remains `Research Opportunity / Paper Candidate FAIL-UNVERIFIED`.

## 7. Current decision and reproduction

The generated gate artifact reports:

- `Research Opportunity: PASS`;
- `M0: PASS-CANARY`;
- `M1: ITERATE`, with `Claim I: IMPLEMENTATION-CANARY-PASS`, novelty unresolved, and
  efficiency unverified;
- `M2: NOT-STARTED`;
- `Paper Candidate: FAIL-UNVERIFIED`.

Run the recorded commands from `paper2/` under Python 3.12 with MPFR available:

```bash
python3 -m experiments.generate_numerical_defects --output results/blockstamp/numerical_defect_cases.csv --seed 17
python3 -m experiments.run_rigorous_backend --samples 50000 --seed 20260831
python3 -m experiments.run_mna_canary --steps 100 --step-size 1e-05
python3 -m experiments.run_operator_canary --cases-per-grid 200 --dense-canary-cases 2 --seed 20260831
python3 -m experiments.run_next_round_gate
```

The gate runner consumes the generated canary artifacts; it must be rerun after any
source, configuration, or artifact change.  Clean-output replay is still required
because the current artifacts record a dirty worktree.
