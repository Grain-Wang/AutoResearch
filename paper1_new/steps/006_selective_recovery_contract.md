# Step 006: Selective Recovery Contract

## Safety rule

Each accepted slab record stores `(incoming_assumption, outgoing_enclosure,
certificate_digest)`.  After slab `j` is recomputed, a cached certificate for slab
`j+1` may be replayed only when the new outgoing enclosure is a subset of the cached
incoming assumption.  Overlap is insufficient.  At the first containment failure,
that slab and the entire unchecked suffix become invalid and must be checked again.

## State machine

```text
VALID_PREFIX -> RECOMPUTE(j)
RECOMPUTE(j) --fail--> UNKNOWN(j), invalidate suffix j..
RECOMPUTE(j) --accept O_new--> TEST_BOUNDARY(j+1)
TEST_BOUNDARY --O_new subset Y_cached--> REPLAY(j+1)
TEST_BOUNDARY --otherwise--> INVALIDATE_SUFFIX(j+1), RECHECK(j+1..)
REPLAY(k) --cached ACCEPT and boundary holds--> TEST_BOUNDARY(k+1)
REPLAY(k) --failure--> INVALIDATE_SUFFIX(k), RECHECK(k..)
```

## Required executable scenarios

1. A strictly smaller new outgoing box permits replay.
2. An equal box permits replay.
3. A partially overlapping box invalidates the suffix.
4. A disjoint box invalidates the suffix.
5. An enlarged box is replayable only if it still lies inside the cached assumption.
6. Consecutive failures restart checking at the earliest invalid boundary.

Selective recovery is therefore not “recompute only the failed slab.”  Its valid
claim is “reuse the maximal certified suffix prefix whose stored incoming assumptions
still contain every newly established boundary enclosure.”  Any runtime benefit is an
experimental hypothesis until end-to-end fallback cost is measured.
