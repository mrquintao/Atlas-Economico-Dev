from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Date, cast, func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.models import GeographicLevel, GeographicUnit, Observation

_ONE_DAY = timedelta(days=1)
_FOUR_DAYS = timedelta(days=4)


@dataclass(frozen=True, slots=True)
class ObservationRow:
    reference_date: date
    value: Decimal
    period_start: date
    period_end: date


def _filters(indicator_id: int, geographic_unit_id: int, start: date | None, end: date | None):
    """An observation matches when its reference period **ends** within ``[start, end]``.

    Daily series: the period is the day itself, so this is a plain date filter. Monthly series
    (dated on the 1st by the SGS): a range from 20/10/2021 to 15/03/2022 includes Oct/2021
    (ended 31/10) and excludes Mar/2022 (not ended by 15/03), so no value refers to a moment
    after the requested end. Uses ix_observations_indicator_geo_period_end (ADR 0005).
    """
    clauses = [
        Observation.indicator_id == indicator_id,
        Observation.geographic_unit_id == geographic_unit_id,
    ]
    if start is not None:
        clauses.append(Observation.period_end >= start)
    if end is not None:
        clauses.append(Observation.period_end <= end)
    return clauses


def fetch_observations(
    session: Session,
    indicator_id: int,
    geographic_unit_id: int,
    start: date | None,
    end: date | None,
) -> list[ObservationRow]:
    statement = (
        select(
            Observation.reference_date,
            Observation.value,
            Observation.period_start,
            Observation.period_end,
        )
        .where(*_filters(indicator_id, geographic_unit_id, start, end))
        .order_by(Observation.reference_date)
    )
    return [ObservationRow(*row) for row in session.execute(statement)]


def fetch_last_value_per_month(
    session: Session,
    indicator_id: int,
    geographic_unit_id: int,
    start: date | None,
    end: date | None,
) -> list[ObservationRow]:
    """Last available observation of each calendar month (no averaging, no interpolation)."""
    month = cast(func.date_trunc("month", Observation.reference_date), Date).label("month")
    statement = (
        select(month, Observation.reference_date, Observation.value)
        .where(*_filters(indicator_id, geographic_unit_id, start, end))
        .ext(distinct_on(month))
        .order_by(month, Observation.reference_date.desc())
    )
    rows: list[ObservationRow] = []
    for month_start, reference_date, value in session.execute(statement):
        next_month = (month_start.replace(day=28) + _FOUR_DAYS).replace(day=1)
        rows.append(ObservationRow(reference_date, value, month_start, next_month - _ONE_DAY))
    return rows


@dataclass(frozen=True, slots=True)
class PeriodCoverage:
    reference_date: date
    period_start: date
    period_end: date
    units: int


def _state_units():
    return select(GeographicUnit.id).where(GeographicUnit.geographic_level == GeographicLevel.STATE)


def fetch_period_coverage(session: Session, indicator_id: int) -> list[PeriodCoverage]:
    """Reference periods with a stored value in some UF and how many UFs have one, most
    recent first. Only state-level units count (coverage is at most 27)."""
    statement = (
        select(
            Observation.reference_date,
            func.min(Observation.period_start),
            func.max(Observation.period_end),
            func.count(),
        )
        .where(
            Observation.indicator_id == indicator_id,
            Observation.geographic_unit_id.in_(_state_units()),
        )
        .group_by(Observation.reference_date)
        .order_by(Observation.reference_date.desc())
    )
    return [PeriodCoverage(*row) for row in session.execute(statement)]


def fetch_state_cross_section(
    session: Session, indicator_id: int, reference_date: date
) -> dict[int, Decimal]:
    """Value of every UF at one reference date, keyed by geographic unit id."""
    statement = select(Observation.geographic_unit_id, Observation.value).where(
        Observation.indicator_id == indicator_id,
        Observation.reference_date == reference_date,
        Observation.geographic_unit_id.in_(_state_units()),
    )
    return {unit_id: value for unit_id, value in session.execute(statement)}
