"""Derivation of state fiscal indicators from the raw SICONFI annexes (S4).

Each indicator is ONE published row of one annex, identified by report, annex, power, account
code (``cod_conta``) and column, never by position (ADR 0010). Nothing is computed from several
rows: ratios are the ones published in the annexes. The derivation reads only the raw layer
(``fiscal_reports``/``fiscal_report_rows``), so it can be repeated at will without touching the
SICONFI API; collecting the annexes is ``ingest_siconfi_reports``.

For every (indicator, state, exercise, period) the outcome is one of:

* ``inserted`` / ``updated`` / ``unchanged`` — the row exists and was stored as an observation
  (a changed value is recorded in ``observation_revisions``);
* ``row_missing`` — the annex was collected but has no such row: the observation is absent
  (never zero) and a stored one is kept and reported, as for the national series;
* ``ambiguous`` — more than one row matches: nothing is stored and the run fails, because the
  mapping no longer identifies the value (the annex structure changed).

Periods whose annex was never collected are simply absent: there is nothing to derive.
"""

from __future__ import annotations

import calendar
import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.ingestion.series_ingestion import IngestionError, format_error
from app.models import (
    FiscalReport,
    FiscalReportRow,
    GeographicLevel,
    GeographicUnit,
    Indicator,
    IngestionRun,
    IngestionStatus,
    Observation,
    ObservationRevision,
)

logger = logging.getLogger(__name__)

DATASET = "siconfi_derivation"
SOURCE_ACRONYM = "SICONFI"
SPHERE = "E"
# Months covered by each period: bimester (RREO) and four-month period (RGF).
MONTHS_PER_PERIOD = {"B": 2, "Q": 4}
PERIODICITY = {"RREO": "B", "RGF": "Q"}
MAX_LISTED_OUTCOMES = 2000


@dataclass(frozen=True)
class RowSelector:
    """Where an indicator is published, valid for exercises ``first_exercise..last_exercise``.

    ``column`` may contain ``{period}`` (e.g. ``"Até o {period}º Quadrimestre"``). ``label``
    (the ``rotulo``) disambiguates annexes that repeat an account code in several tables.
    """

    report_type: str
    annex: str
    power: str | None
    account_code: str
    column: str
    first_exercise: int
    last_exercise: int | None = None
    label: str | None = None

    @property
    def periodicity(self) -> str:
        return PERIODICITY[self.report_type]

    def covers(self, exercise: int) -> bool:
        return exercise >= self.first_exercise and (
            self.last_exercise is None or exercise <= self.last_exercise
        )

    def column_for(self, period: int) -> str:
        return self.column.format(period=period)


@dataclass(frozen=True)
class FiscalIndicator:
    code: str
    selectors: tuple[RowSelector, ...]

    def selector_for(self, exercise: int) -> RowSelector | None:
        return next((s for s in self.selectors if s.covers(exercise)), None)


@dataclass
class DerivationOutcome:
    state: str
    exercise: int
    period: int
    # inserted | updated | unchanged | row_missing | ambiguous
    status: str
    value: str | None = None


@dataclass
class DerivationSummary:
    indicator_code: str
    run_id: int
    status: str = IngestionStatus.RUNNING
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    row_missing: int = 0
    ambiguous: int = 0
    outcomes: list[DerivationOutcome] = field(default_factory=list)

    def record(self, outcome: DerivationOutcome) -> None:
        setattr(self, outcome.status, getattr(self, outcome.status) + 1)
        if len(self.outcomes) < MAX_LISTED_OUTCOMES:
            self.outcomes.append(outcome)


def period_bounds(exercise: int, periodicity: str, period: int) -> tuple[date, date]:
    """First and last day of a bimester or four-month period (the reference period, ADR 0005)."""
    months = MONTHS_PER_PERIOD[periodicity]
    if not 1 <= period <= 12 // months:
        raise IngestionError(f"Invalid period {period} for periodicity {periodicity}")
    first_month = (period - 1) * months + 1
    last_month = first_month + months - 1
    last_day = calendar.monthrange(exercise, last_month)[1]
    return date(exercise, first_month, 1), date(exercise, last_month, last_day)


def derive_fiscal_indicator(
    session: Session,
    definition: FiscalIndicator,
    *,
    states: Sequence[str] | None = None,
    exercises: Sequence[int] | None = None,
) -> DerivationSummary:
    """Derive one indicator for the given states (default: all) and exercises (default: all
    collected). Failures are recorded as a failed run and re-raised."""
    indicator = session.scalar(
        select(Indicator)
        .options(joinedload(Indicator.source))
        .where(Indicator.code == definition.code)
    )
    if indicator is None:
        raise IngestionError(f"Unknown indicator: {definition.code}")
    if indicator.source.acronym != SOURCE_ACRONYM:
        raise IngestionError(f"{definition.code} is not a SICONFI indicator")
    if indicator.geographic_level != GeographicLevel.STATE:
        raise IngestionError(f"{definition.code} is not a state indicator")
    units = _states(session, states)
    run = IngestionRun(
        source_id=indicator.source_id,
        indicator_id=indicator.id,
        started_at=datetime.now(UTC),
        status=IngestionStatus.RUNNING,
        metadata_json={
            "dataset": DATASET,
            "states": None if states is None else [u.acronym for u in units],
            "exercises": None if exercises is None else sorted(set(exercises)),
            "selectors": [asdict(s) for s in definition.selectors],
        },
    )
    session.add(run)
    session.commit()
    summary = DerivationSummary(definition.code, run.id)
    try:
        for selector in definition.selectors:
            _derive_selector(session, indicator, run, selector, units, exercises, summary)
        if summary.ambiguous:
            raise IngestionError(
                f"{summary.ambiguous} period(s) match more than one row; the annex structure "
                "changed and the mapping must be reviewed"
            )
        summary.status = IngestionStatus.SUCCESS
        _finish(session, run.id, summary)
        session.commit()
    except BaseException as exc:  # also Ctrl+C: never leave the run as "running"
        session.rollback()
        summary.status = IngestionStatus.FAILED
        _finish(session, run.id, summary, exc)
        session.commit()
        logger.error(
            "fiscal_derivation_failed",
            extra={"indicator": definition.code, "run_id": run.id, "error": str(exc)},
        )
        raise
    logger.info(
        "fiscal_derivation_succeeded",
        extra={
            "indicator": definition.code,
            "run_id": run.id,
            "inserted": summary.inserted,
            "updated": summary.updated,
            "row_missing": summary.row_missing,
        },
    )
    return summary


def _states(session: Session, acronyms: Sequence[str] | None) -> list[GeographicUnit]:
    # IBGE acronyms are unique only per level (SE = Sergipe and Sudeste): always filter by level.
    found = {
        unit.acronym: unit
        for unit in session.scalars(
            select(GeographicUnit)
            .where(GeographicUnit.geographic_level == GeographicLevel.STATE)
            .order_by(GeographicUnit.ibge_code)
        )
    }
    if acronyms is None:
        return list(found.values())
    wanted = [a.upper() for a in acronyms]
    unknown = sorted(set(wanted) - set(found))
    if unknown or not wanted:
        raise IngestionError(f"Unknown or missing state acronyms: {unknown}")
    return [found[a] for a in dict.fromkeys(wanted)]


def _derive_selector(
    session: Session,
    indicator: Indicator,
    run: IngestionRun,
    selector: RowSelector,
    units: list[GeographicUnit],
    exercises: Sequence[int] | None,
    summary: DerivationSummary,
) -> None:
    by_id = {u.id: u for u in units}
    query = select(FiscalReport).where(
        FiscalReport.report_type == selector.report_type,
        FiscalReport.annex == selector.annex,
        FiscalReport.periodicity == selector.periodicity,
        FiscalReport.sphere == SPHERE,
        FiscalReport.power.is_(None)
        if selector.power is None
        else FiscalReport.power == selector.power,
        FiscalReport.geographic_unit_id.in_(by_id),
        FiscalReport.exercise >= selector.first_exercise,
    )
    if selector.last_exercise is not None:
        query = query.where(FiscalReport.exercise <= selector.last_exercise)
    if exercises is not None:
        query = query.where(FiscalReport.exercise.in_(list(exercises)))
    reports = session.scalars(
        query.order_by(FiscalReport.geographic_unit_id, FiscalReport.exercise, FiscalReport.period)
    ).all()
    for report in reports:
        unit = by_id[report.geographic_unit_id]
        column = selector.column_for(report.period)
        row_query = select(FiscalReportRow).where(
            FiscalReportRow.report_id == report.id,
            FiscalReportRow.account_code == selector.account_code,
            FiscalReportRow.column == column,
        )
        if selector.label is not None:
            row_query = row_query.where(FiscalReportRow.label == selector.label)
        rows = session.scalars(row_query).all()
        outcome = DerivationOutcome(unit.acronym, report.exercise, report.period, "row_missing")
        if len(rows) > 1:
            outcome.status = "ambiguous"
        elif rows:
            row = rows[0]
            outcome.value = str(row.value)
            outcome.status = _upsert(session, indicator, run, unit, report, row, selector)
        summary.record(outcome)
    session.flush()


def _upsert(
    session: Session,
    indicator: Indicator,
    run: IngestionRun,
    unit: GeographicUnit,
    report: FiscalReport,
    row: FiscalReportRow,
    selector: RowSelector,
) -> str:
    start, end = period_bounds(report.exercise, report.periodicity, report.period)
    fields: dict[str, Any] = {
        "period_start": start,
        "period_end": end,
        "published_at": report.delivered_at,
        "collected_at": report.collected_at,
        "source_reference": (
            f"SICONFI {report.report_type} {report.annex} {report.exercise}/"
            f"{report.periodicity}{report.period}"
        )[:255],
        "metadata_json": {
            "fiscal_report_id": report.id,
            "fiscal_report_row_id": row.id,
            "report_type": report.report_type,
            "annex": report.annex,
            "power": report.power,
            "label": row.label,
            "account_code": row.account_code,
            "account": row.account,
            "column": row.column,
            "source_url": report.source_url,
        },
    }
    observation = session.scalar(
        select(Observation).where(
            Observation.indicator_id == indicator.id,
            Observation.geographic_unit_id == unit.id,
            Observation.reference_date == start,
        )
    )
    if observation is None:
        session.add(
            Observation(
                indicator_id=indicator.id,
                geographic_unit_id=unit.id,
                reference_date=start,
                value=row.value,
                **fields,
            )
        )
        return "inserted"
    changed = observation.value != row.value
    if changed:
        session.add(
            ObservationRevision(
                observation_id=observation.id,
                previous_value=observation.value,
                new_value=row.value,
                ingestion_run_id=run.id,
            )
        )
        observation.value = row.value
    for key, value in fields.items():
        setattr(observation, key, value)
    return "updated" if changed else "unchanged"


def _finish(
    session: Session,
    run_id: int,
    summary: DerivationSummary,
    error: BaseException | None = None,
) -> None:
    run = session.get_one(IngestionRun, run_id)
    run.status = summary.status
    run.finished_at = datetime.now(UTC)
    if error is None:
        run.records_received = summary.inserted + summary.updated + summary.unchanged
        run.records_inserted = summary.inserted
        run.records_updated = summary.updated
        run.records_unchanged = summary.unchanged
    else:
        # Nothing of a failed derivation was committed.
        run.error_message = format_error(error)
    run.metadata_json = {
        **(run.metadata_json or {}),
        "row_missing": summary.row_missing,
        "ambiguous": summary.ambiguous,
        "outcomes": [
            asdict(o) for o in summary.outcomes if error is not None or o.status != "unchanged"
        ],
    }
