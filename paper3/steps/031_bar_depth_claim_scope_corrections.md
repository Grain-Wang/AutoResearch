# 031 BAR-Depth claim-scope corrections

## Status

`CLAIM_SCOPE_CORRECTED / HISTORICAL_MACHINE_ARTIFACTS_PRESERVED`.

This step records the wording migration required by Round 2. Historical JSON,
CSV, hashes, and review text remain byte-preserved; active idea and Steps
022--030 use only the corrected scope.

| Historical wording | Active wording | Evidence boundary |
| --- | --- | --- |
| `Boosting MDE 2021` | `Boosting-MDE edge-density selector adapted to frozen BAR actions` | Only the official selector score is adapted; the full Boosting-MDE pipeline was not evaluated. |
| `GO_PATCH_INFORMATION_NECESSARY` | `GO_PATCH_INFORMATION_BEYOND_TWO_FROZEN_CONTROLS` | The claim covers two control families at one preregistered parameter setting each. |
| shared latency GO wording | `PROVISIONAL / NOT_FORMAL` shared diagnostic | Shared measurements cannot complete the formal Pareto gate. |
| budget-adaptive allocation | selective regional refinement | Current action costs are equal; no heterogeneous-cost allocation is claimed. |
| metric/general depth implication | per-image scale-aligned relative-depth mechanism probe | The current DAV2-S/DIODE evaluation uses per-image GT scale alignment. |

The current point-score/threshold/Top-K router is additionally marked
`STOP_NOVELTY`; wording corrections do not revive W08 or establish an algorithm
claim.
