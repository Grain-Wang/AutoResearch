# 029 BAR-Depth formal latency v2

## Status

`DIRECT_ACCURACY_V2_COMPLETE / ACCURACY_ONLY_ORACLE_MARGIN_SURVIVES /
QUEUE_ACTIVE / LATENCY_SESSION_1_ATTEMPT_1_CONTAMINATED_RUNNING /
RETRY_THEN_SESSION_2_PENDING / NOT_FORMAL / NOT_PAPER_CANDIDATE`.

Round 2 invalidated the old W07 formal queue before it acquired a GPU. That
task was gracefully drained at `PENDING/attempt=0`; no GPU job or external
process was terminated. The v1 shared run remains diagnostic-only.

## Frozen v2 evidence contract

The accuracy grid in
[`direct_resolution_v2.json`](../configs/bar_depth/direct_resolution_v2.json)
contains all 28 DAV2-S input sizes from 518 through 2030 in steps of 56. The
v2 runner emits a 200-image row for every size and records a reproducible CUDA
OOM as an outcome instead of deleting that candidate. Candidate range closure
requires either two consecutive sizes whose p50 and p95 both exceed regional
K=3, or a contiguous OOM suffix through the hard maximum.

The timing contract in
[`matched_latency_v2.json`](../configs/bar_depth/matched_latency_v2.json)
requires two independent exclusive A800 sessions. In each session every method
receives 20 warm-ups and 20 cross-scan images times 10 repetitions, yielding
200 raw timing rows per method and 400 after the sessions are combined. The
runner records p50/p90/p95, named stages, peak allocated GPU memory,
images/second, and one-second GPU PID/clock/power/pstate telemetry. Any monitor
failure or foreign compute PID invalidates that session.

The joint analyzer resamples timing units and scan-accuracy clusters, rebuilds
the feasible set, and reselects the most accurate feasible direct candidate in
every bootstrap replicate. It accepts the formal gate only if all of the
following hold:

1. both session artifacts pass row-count, stage-sum, and exclusivity checks;
2. every non-OOM method has session p50 relative difference at most 5% and p95
   relative difference at most 10%;
3. accuracy and timing agree on the OOM set;
4. the frozen candidate range is closed;
5. the oracle-minus-replicate-best direct margin and its joint-bootstrap lower
   bound are positive.

## Completed accuracy-only stage

The exclusive direct-resolution task completed on its first attempt. Its frozen
matrix contains 5,600 rows: 200 images at each of 28 input sizes. All candidates
from 518 through 2030 returned `OK`; none was OOM. The raw matrix and provenance
are committed as
[`direct_resolution_raw_v2.csv`](../results/bar_depth/direct_resolution_raw_v2.csv)
and
[`direct_resolution_raw_provenance_v2.json`](../results/bar_depth/direct_resolution_raw_provenance_v2.json).

The reproducible accuracy-only analyzer deliberately takes the maximum over
**all** non-OOM whole-image sizes in every scan-bootstrap replicate, without
using latency to narrow the candidate family. The point winner is the 518 base
resolution with 0.00% improvement. Every larger resolution has a negative point
estimate; the least negative is 574 at -0.4214%. Regional fixed K=3 is 6.6236%
and regional oracle K=3 is 9.6600%.

Oracle minus the replicate-wise all-size direct envelope is 9.6600 percentage
points at the point estimate, with paired 10,000-replicate 95% interval
`[1.4235, 11.9335]` percentage points. Because the all-size family is a superset
of any future latency-feasible family, this is a conservative accuracy-only
result. It supports
`PROVISIONAL_ACCURACY_ONLY_GO_ORACLE_MARGIN_OVER_ALL_DIRECT_SIZES`, but it does
not close the range in latency or complete the Pareto gate. Machine outputs are
[`direct_resolution_accuracy_analysis_v2.csv`](../results/bar_depth/direct_resolution_accuracy_analysis_v2.csv)
and
[`direct_resolution_accuracy_analysis_v2.json`](../results/bar_depth/direct_resolution_accuracy_analysis_v2.json).

## Current execution boundary

The fail-closed four-task queue remains active under user-level tmux. It waits
for four consecutive 30-second exclusive-idle samples, uses at most one GPU,
and will not terminate or preempt another process. At the latest check,
accuracy was `PASSED/attempt=1`; latency session 1 was
`RUNNING/attempt=1`; session 2 and CPU analysis remained `PENDING/attempt=0`.

Session 1 acquired a clean allocation, but live one-second monitoring observed
foreign compute processes entering the assigned GPU after launch. Consequently
the current attempt is contaminated and is not admissible as exclusive timing
evidence. The runner is fail-closed: after the attempt exits it must return an
invalid-session status, and the scheduler has one retry configured. The retry
will again wait for the full exclusive-idle window. No foreign process will be
terminated. Session 2 cannot start until a valid session 1 passes.

Therefore this step still does not report a formal Pareto result. The only
timing reanalysis currently available is the shared v1 diagnostic under the v2
joint bootstrap:
`PROVISIONAL_NOT_FORMAL_GO_REGIONAL_ORACLE_PARETO_FORMAL_V2`. Its oracle margin
over the replicate-wise best feasible direct candidate is 9.66 percentage
points with joint 95% interval `[4.21, 12.38]` percentage points. All tested
518--1022 candidates remain feasible, so that run also confirms that the old
direct range was not closed.
