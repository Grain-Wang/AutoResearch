"""Dependency-safe selective slab recovery."""

from __future__ import annotations

from dataclasses import dataclass

from experiments.interval_backend import Interval


@dataclass(frozen=True, slots=True)
class SlabRecord:
    incoming: Interval
    outgoing: Interval
    certificate_digest: str


def first_invalid_suffix(
    records: list[SlabRecord], changed_index: int, new_outgoing: Interval
) -> int | None:
    """Return the first slab that must be rechecked after a changed outgoing box."""
    if changed_index < 0 or changed_index >= len(records):
        raise IndexError("changed slab index is outside the certificate sequence")
    next_index = changed_index + 1
    if next_index >= len(records):
        return None
    if not new_outgoing.subset_of(records[next_index].incoming):
        return next_index
    outgoing = records[next_index].outgoing
    for index in range(next_index + 1, len(records)):
        if not outgoing.subset_of(records[index].incoming):
            return index
        outgoing = records[index].outgoing
    return None
