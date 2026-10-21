"""Incremental collection of SICONFI report annexes (RREO/RGF) of the states (S3).

For each state and exercise the delivery statement (``extrato_entregas``, one request) tells
which periods were delivered and when they were last delivered or rectified. A period is only
requested when it was never stored or the statement shows a newer delivery than the stored one
(``refresh`` forces it). Rows are stored exactly as published; a rectification updates, adds or
removes rows and every change is recorded in the run (``metadata_json.revisions``). Each report
is committed on its own, so a failure keeps the reports already collected and the run is
recorded as failed with the outcomes so far.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.series_ingestion import IngestionError, format_error
from app.integrations.tesouro.siconfi import (
    PERIODS_PER_YEAR,
    Delivery,
    ReportRequest,
    ReportResult,
    SiconfiClient,
    latest_delivery,
    plain_decimal,
)
from app.models import (
    DataSource,
    FiscalReport,
    FiscalReportRow,
    GeographicLevel,
    GeographicUnit,
    IngestionRun,
    IngestionStatus,
)

logger = logging.getLogger(__name__)

SOURCE_ACRONYM = "SICONFI"
DATASET = "siconfi_reports"
DEFAULT_PERIODICITY = {"RREO": "B", "RGF": "Q"}
# Revisions listed in full in the run metadata; beyond this only the count is kept.
MAX_LISTED_REVISIONS = 1000


@dataclass
class ReportOutcome:
    state: str
    exercise: int
    period: int
    # inserted | updated | unchanged | up_to_date | not_delivered | not_available
    status: str
    rows: int = 0
    delivered_at: str | None = None


@dataclass
class SiconfiSummary:
    run_id: int
    report_type: str
    annex: str
    requests: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_deleted: int = 0
    rows_unchanged: int = 0
    reports: list[ReportOutcome] = field(default_factory=list)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    revision_count: int = 0

    def record_revision(self, revision: dict[str, Any]) -> None:
        self.revision_count += 1
        if len(self.revisions) < MAX_LISTED_REVISIONS:
            self.revisions.append(revision)


def ingest_siconfi_reports(
    session: Session,
    settings: Settings,
    client: SiconfiClient | None = None,
    *,
    report_type: str,
    annex: str,
    states: list[str],
    exercises: list[int],
    periods: list[int] | None = None,
    periodicity: str | None = None,
    power: str | None = None,
    sphere: str = "E",
    refresh: bool = False,
) -> SiconfiSummary:
    """Collect one annex of a report for the given states, exercises and periods.

    Invalid requests (unknown state, period or annex) raise ``IngestionError`` or
    ``SiconfiError`` before any run exists; failures afterwards are recorded as a failed run and
    re-raised.
    """
    periodicity = periodicity or DEFAULT_PERIODICITY.get(report_type, "")
    if report_type == "RGF" and power is None:
        power = "E"
    wanted_periods = periods or list(range(1, PERIODS_PER_YEAR.get(periodicity, 0) + 1))
    # Validates report type, annex, periodicity, periods, sphere and power up front.
    for period in wanted_periods:
        ReportRequest(report_type, 2000, period, annex, "35", sphere, power, periodicity)
    units = _states(session, states)
    source = session.scalar(select(DataSource).where(DataSource.acronym == SOURCE_ACRONYM))
    if source is None:
        raise IngestionError(f"Data source {SOURCE_ACRONYM} is not seeded")

    plan = {
        "dataset": DATASET,
        "report_type": report_type,
        "annex": annex,
        "states": [u.acronym for u in units],
        "exercises": exercises,
        "periods": wanted_periods,
        "periodicity": periodicity,
        "sphere": sphere,
        "power": power,
        "refresh": refresh,
    }
    run = IngestionRun(
        source_id=source.id,
        indicator_id=None,
        started_at=datetime.now(UTC),
        status=IngestionStatus.RUNNING,
        metadata_json=plan,
    )
    session.add(run)
    session.commit()
    run_id = run.id
    summary = SiconfiSummary(run_id, report_type, annex)
    owns_client = client is None
    client = client or SiconfiClient(settings)
    try:
        for unit in units:
            for exercise in exercises:
                deliveries = client.fetch_deliveries(unit.ibge_code, exercise)
                for period in wanted_periods:
                    request = ReportRequest(
                        report_type, exercise, period, annex, unit.ibge_code, sphere, power,
                        periodicity,
                    )  # fmt: skip
                    outcome = _collect(session, client, unit, request, deliveries, refresh, summary)
                    summary.reports.append(outcome)
                    session.commit()
        summary.requests = client.requests_made
        _finish(session, run_id, summary, IngestionStatus.SUCCESS)
        session.commit()
    except Exception as exc:
        session.rollback()
        summary.requests = client.requests_made
        _finish(session, run_id, summary, IngestionStatus.FAILED, exc)
        session.commit()
        logger.error("siconfi_ingestion_failed", extra={"run_id": run_id, "error": str(exc)})
        raise
    finally:
        if owns_client:
            client.close()
    logger.info(
        "siconfi_ingestion_succeeded",
        extra={
            "run_id": run_id,
            "inserted": summary.rows_inserted,
            "updated": summary.rows_updated,
        },
    )
    return summary


def _states(session: Session, acronyms: list[str]) -> list[GeographicUnit]:
    # IBGE acronyms are unique only per level (SE = Sergipe and Sudeste): always filter by level.
    found = {
        unit.acronym: unit
        for unit in session.scalars(
            select(GeographicUnit).where(GeographicUnit.geographic_level == GeographicLevel.STATE)
        )
    }
    wanted = [a.upper() for a in acronyms]
    unknown = sorted(set(wanted) - set(found))
    if unknown or not wanted:
        raise IngestionError(f"Unknown or missing state acronyms: {unknown}")
    return [found[a] for a in dict.fromkeys(wanted)]


def _collect(
    session: Session,
    client: SiconfiClient,
    unit: GeographicUnit,
    request: ReportRequest,
    deliveries: list[Delivery],
    refresh: bool,
    summary: SiconfiSummary,
) -> ReportOutcome:
    outcome = ReportOutcome(unit.acronym, request.exercise, request.period, "not_delivered")
    delivered_at = latest_delivery(
        deliveries, request.report_type, request.period, request.periodicity
    )
    if delivered_at is None:
        return outcome
    outcome.delivered_at = delivered_at.isoformat()
    stored = session.scalar(
        select(FiscalReport).where(
            FiscalReport.geographic_unit_id == unit.id,
            FiscalReport.report_type == request.report_type,
            FiscalReport.exercise == request.exercise,
            FiscalReport.periodicity == request.periodicity,
            FiscalReport.period == request.period,
            FiscalReport.annex == request.annex,
            FiscalReport.sphere == request.sphere,
            FiscalReport.power.is_(None)
            if request.power is None
            else FiscalReport.power == request.power,
        )
    )
    if (
        not refresh
        and stored is not None
        and stored.delivered_at is not None
        and delivered_at <= stored.delivered_at
    ):
        outcome.status, outcome.rows = "up_to_date", stored.row_count
        return outcome
    result = client.fetch_report(request)
    if not result.rows:
        # Delivered but not (yet) in the data lake: keep what is stored and try again next time.
        logger.warning("siconfi_report_not_available", extra={"url": result.url})
        outcome.status = "not_available"
        return outcome
    outcome.rows = len(result.rows)
    now = datetime.now(UTC)
    if stored is None:
        report = FiscalReport(
            geographic_unit_id=unit.id,
            report_type=request.report_type,
            exercise=request.exercise,
            periodicity=request.periodicity,
            period=request.period,
            annex=request.annex,
            sphere=request.sphere,
            power=request.power,
            **_report_fields(result, delivered_at, now),
        )
        report.rows = [
            FiscalReportRow(
                label=r.label,
                column=r.column,
                account_code=r.account_code,
                account=r.account,
                value=r.value,
            )
            for r in result.rows
        ]
        session.add(report)
        summary.rows_inserted += len(result.rows)
        outcome.status = "inserted"
        return outcome
    changed = stored.content_hash != result.content_hash
    if changed:
        _apply_revision(stored, result, summary, unit.acronym)
    else:
        summary.rows_unchanged += len(result.rows)
    for key, value in _report_fields(result, delivered_at, now).items():
        setattr(stored, key, value)
    outcome.status = "updated" if changed else "unchanged"
    return outcome


def _report_fields(result: ReportResult, delivered_at: datetime, now: datetime) -> dict[str, Any]:
    return {
        "institution": result.institution,
        "population": result.population,
        "row_count": len(result.rows),
        "content_hash": result.content_hash,
        "delivered_at": delivered_at,
        "source_url": result.url,
        "collected_at": now,
    }


def _apply_revision(
    stored: FiscalReport, result: ReportResult, summary: SiconfiSummary, state: str
) -> None:
    """Bring the stored rows to the published content, recording every change."""
    current = {(r.label, r.column, r.account_code, r.account): r for r in stored.rows}
    published = {r.key: r for r in result.rows}
    base = {
        "state": state,
        "exercise": stored.exercise,
        "period": stored.period,
        "previous_hash": stored.content_hash,
    }

    def record(key: tuple[str, ...], previous: Decimal | None, new: Decimal | None) -> None:
        summary.record_revision(
            {
                **base,
                "row": dict(zip(("label", "column", "account_code", "account"), key, strict=True)),
                "previous": None if previous is None else plain_decimal(previous),
                "new": None if new is None else plain_decimal(new),
            }
        )

    for key, row in published.items():
        existing = current.get(key)
        if existing is None:
            stored.rows.append(
                FiscalReportRow(
                    label=row.label,
                    column=row.column,
                    account_code=row.account_code,
                    account=row.account,
                    value=row.value,
                )
            )
            summary.rows_inserted += 1
            record(key, None, row.value)
        elif existing.value != row.value:
            record(key, existing.value, row.value)
            existing.value = row.value
            summary.rows_updated += 1
        else:
            summary.rows_unchanged += 1
    for key, existing in current.items():
        if key not in published:
            record(key, existing.value, None)
            stored.rows.remove(existing)
            summary.rows_deleted += 1


def _finish(
    session: Session,
    run_id: int,
    summary: SiconfiSummary,
    status: IngestionStatus,
    error: BaseException | None = None,
) -> None:
    run = session.get_one(IngestionRun, run_id)
    run.status = status
    run.finished_at = datetime.now(UTC)
    run.records_received = sum(o.rows for o in summary.reports if o.status != "up_to_date")
    run.records_inserted = summary.rows_inserted
    run.records_updated = summary.rows_updated + summary.rows_deleted
    run.records_unchanged = summary.rows_unchanged
    if error is not None:
        run.error_message = format_error(error)
    run.metadata_json = {
        **(run.metadata_json or {}),
        "requests": summary.requests,
        "rows_deleted": summary.rows_deleted,
        "reports": [asdict(o) for o in summary.reports],
        "revision_count": summary.revision_count,
        "revisions": summary.revisions,
    }
