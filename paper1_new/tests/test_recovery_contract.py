import pytest

from experiments.interval_backend import Interval
from experiments.recovery import SlabRecord, first_invalid_suffix


def _records() -> list[SlabRecord]:
    return [
        SlabRecord(Interval(0.0, 1.0), Interval(0.2, 0.8), "a"),
        SlabRecord(Interval(0.0, 1.0), Interval(0.3, 0.7), "b"),
        SlabRecord(Interval(0.2, 0.8), Interval(0.4, 0.6), "c"),
    ]


@pytest.mark.parametrize(
    "outgoing", [Interval(0.3, 0.7), Interval(0.0, 1.0), Interval(0.1, 0.9)]
)
def test_subset_equal_and_enlarged_inside_assumption_reuse(outgoing: Interval) -> None:
    assert first_invalid_suffix(_records(), 0, outgoing) is None


@pytest.mark.parametrize("outgoing", [Interval(0.9, 1.1), Interval(2.0, 3.0)])
def test_overlap_and_disjoint_invalidate(outgoing: Interval) -> None:
    assert first_invalid_suffix(_records(), 0, outgoing) == 1


def test_later_cached_boundary_failure_invalidates_earliest_suffix() -> None:
    records = _records()
    records[2] = SlabRecord(Interval(0.4, 0.6), Interval(0.4, 0.6), "c")
    assert first_invalid_suffix(records, 0, Interval(0.3, 0.7)) == 2


def test_final_slab_has_no_suffix() -> None:
    assert first_invalid_suffix(_records(), 2, Interval(10.0, 11.0)) is None
