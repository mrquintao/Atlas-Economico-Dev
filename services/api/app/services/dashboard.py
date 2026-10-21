"""National dashboard summary: latest official value and 12-month change of each indicator."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import Frequency
from app.repositories.observations import ObservationRow
from app.services.observations import load_series

# Indicators of the national dashboard, in display order (PROJECT_SPEC §13 C).
NATIONAL_DASHBOARD_CODES = ("SELIC_TARGET", "DBGG_GDP", "IPCA_12M")


@dataclass(frozen=True, slots=True)
class LatestSummary:
    latest: ObservationRow
    # Same calendar month one year earlier; None when that month has no stored value.
    year_ago: ObservationRow | None


def summary_frequency(original: Frequency) -> Frequency:
    """Daily series are compared month to month (last value of each month); others as stored."""
    return Frequency.MONTHLY if original == Frequency.DAILY else original


def latest_summary(
    session: Session,
    *,
    indicator_id: int,
    geographic_unit_id: int,
    original_frequency: Frequency,
    first_stored_date: date | None,
    last_stored_date: date | None,
) -> LatestSummary | None:
    """Latest value and the value of the same month one year earlier.

    Mirrors the dashboard card: on the monthly view (last value of each month for daily
    series), the latest point is compared with the point whose period starts 12 months
    earlier. A missing month yields no comparison (never zero, never interpolated).
    """
    if last_stored_date is None:
        return None
    year_ago_start = _shift_year(last_stored_date.replace(day=1), -1)
    series = load_series(
        session,
        indicator_id=indicator_id,
        geographic_unit_id=geographic_unit_id,
        original_frequency=original_frequency,
        target_frequency=summary_frequency(original_frequency),
        start=year_ago_start,
        end=None,
        first_stored_date=first_stored_date,
        last_stored_date=last_stored_date,
    )
    if not series.rows:
        return None
    latest = series.rows[-1]
    target = _shift_year(latest.period_start, -1)
    year_ago = next((row for row in series.rows if row.period_start == target), None)
    return LatestSummary(latest, year_ago)


def _shift_year(day: date, years: int) -> date:
    # Period starts are the 1st of a month, so there is no 29 February to handle; keep the
    # clamp anyway for any other date.
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)
