from datetime import date
from decimal import Decimal

from app.repositories.observations import ObservationRow
from app.services.observations import compute_stats


def row(day: int, value: str) -> ObservationRow:
    d = date(2024, 1, day)
    return ObservationRow(d, Decimal(value), d, d)


def test_empty_series_has_no_stats() -> None:
    assert compute_stats([]) is None


def test_change_is_absolute_difference() -> None:
    stats = compute_stats([row(1, "10.00"), row(2, "12.00")])
    assert stats is not None
    assert stats.change == Decimal("2.00")  # +2 p.p., not +20 %


def test_min_max_ties_resolve_to_earliest_date() -> None:
    stats = compute_stats([row(1, "5"), row(2, "7"), row(3, "5"), row(4, "7")])
    assert stats is not None
    assert (stats.min.reference_date.day, stats.max.reference_date.day) == (1, 2)
