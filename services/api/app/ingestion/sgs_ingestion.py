"""Ingestion of BCB/SGS series into ``observations``.

Guarantees:
- Idempotent: re-running with the same data inserts and updates nothing.
- Incremental: by default only re-fetches from (last stored date - overlap) onwards, so recent
  revisions by the source are still detected.
- Revisions: a changed value updates the observation and records an ``observation_revisions`` row.
- Atomic: observations are written in a single transaction; on failure nothing is changed and
  the run is recorded as failed.
- Never stores dates after the collection date in Brasília time (SGS 432 pre-publishes the
  current target until the next Copom meeting; those days are not yet observations).
- Stored dates that the source no longer returns are kept and reported, never deleted silently.
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.clock import brazil_today
from app.integrations.bcb.sgs import SGSClient, SGSPoint
from app.models import (
    Frequency,
    GeographicUnit,
    Indicator,
    IngestionRun,
    IngestionStatus,
    Observation,
    ObservationRevision,
)

logger = logging.getLogger(__name__)

# How far before the last stored observation incremental runs re-fetch, so that recent
# revisions by the source are detected. ``None`` means "always re-fetch the full history":
# monthly fiscal ratios inherit IBGE GDP revisions that can reach years back, and the whole
# series is a single small request (~240 points).
INCREMENTAL_OVERLAP: dict[Frequency, timedelta | None] = {
    Frequency.DAILY: timedelta(days=90),
    Frequency.MONTHLY: None,
}
_INSERT_CHUNK = 1000
NATIONAL_IBGE_CODE = "1"


class IngestionError(Exception):
    pass


@dataclass
class IngestionSummary:
    run_id: int
    indicator_code: str
    status: str
    start: date
    end: date
    received: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_future: int = 0
    skipped_null: int = 0
    missing_from_source: list[str] = field(default_factory=list)
    windows: list[dict[str, Any]] = field(default_factory=list)


def _resolve_range(
    session: Session,
    indicator: Indicator,
    geo: GeographicUnit,
    *,
    start: date | None,
    end: date | None,
    full: bool,
    today: date,
) -> tuple[date, date]:
    effective_end = min(end or today, today)
    if start is not None:
        effective_start = start
    else:
        first_available = indicator.first_available_date or date(1900, 1, 1)
        last_stored = None
        if not full:
            last_stored = session.scalar(
                select(func.max(Observation.reference_date)).where(
                    Observation.indicator_id == indicator.id,
                    Observation.geographic_unit_id == geo.id,
                )
            )
        frequency = Frequency(indicator.frequency)
        if frequency not in INCREMENTAL_OVERLAP:
            raise IngestionError(f"No incremental policy for {frequency} series")
        overlap = INCREMENTAL_OVERLAP[frequency]
        if last_stored is None or overlap is None:
            effective_start = first_available
        else:
            effective_start = max(first_available, last_stored - overlap)
    if effective_start > effective_end:
        raise IngestionError(f"Empty range: {effective_start} > {effective_end}")
    return effective_start, effective_end


def ingest_sgs_indicator(
    session: Session,
    client: SGSClient,
    indicator_code: str,
    *,
    start: date | None = None,
    end: date | None = None,
    full: bool = False,
    today: date | None = None,
) -> IngestionSummary:
    today = today or brazil_today()
    indicator = session.scalar(select(Indicator).where(Indicator.code == indicator_code))
    if indicator is None:
        raise IngestionError(f"Unknown indicator: {indicator_code}")
    if indicator.source.acronym != "BCB":
        raise IngestionError(f"{indicator_code} is not an SGS (BCB) series")
    geo = session.scalar(
        select(GeographicUnit).where(GeographicUnit.ibge_code == NATIONAL_IBGE_CODE)
    )
    if geo is None:
        raise IngestionError("National geographic unit (IBGE code 1) is not seeded")

    range_start, range_end = _resolve_range(
        session, indicator, geo, start=start, end=end, full=full, today=today
    )

    # The run record is committed up-front so that failures remain auditable.
    run = IngestionRun(
        source_id=indicator.source_id,
        indicator_id=indicator.id,
        status=IngestionStatus.RUNNING,
        records_received=0,
        records_inserted=0,
        records_updated=0,
        records_unchanged=0,
        metadata_json={"start": range_start.isoformat(), "end": range_end.isoformat()},
    )
    session.add(run)
    session.commit()
    collected_at = datetime.now(UTC)
    summary = IngestionSummary(run.id, indicator_code, run.status, range_start, range_end)
    log_ctx = {"run_id": run.id, "indicator": indicator_code}
    logger.info("ingestion_started", extra={**log_ctx, "start": range_start, "end": range_end})

    try:
        results = client.fetch_series(
            indicator.source_series_code,
            range_start,
            range_end,
            daily=indicator.frequency == Frequency.DAILY,
        )
        points: list[SGSPoint] = []
        for result in results:
            summary.skipped_null += result.skipped_null_values
            summary.windows.append(
                {
                    "start": result.start.isoformat(),
                    "end": result.end.isoformat(),
                    "url": result.url,
                    "records": len(result.points),
                    "payload_sha256": result.payload_sha256,
                }
            )
            for point in result.points:
                if point.reference_date > today:
                    summary.skipped_future += 1
                else:
                    points.append(point)
        summary.received = len(points)
        _upsert(session, run, indicator, geo, points, collected_at, summary)

        run.status = IngestionStatus.SUCCESS
        summary.status = run.status
        _finish(run, summary)
        session.commit()
    except Exception as exc:
        logger.exception("ingestion_failed", extra=log_ctx)
        summary.status = IngestionStatus.FAILED
        # Recording the failure touches the database again (the rollback expires `run`, so it
        # is reloaded). If that fails too (e.g. database down), the original error still wins.
        try:
            session.rollback()
            run.status = IngestionStatus.FAILED
            run.error_message = f"{type(exc).__name__}: {exc}"[:2000]
            _finish(run, summary)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("ingestion_failure_not_recorded", extra=log_ctx)
        raise

    logger.info(
        "ingestion_finished",
        extra={
            **log_ctx,
            "received": summary.received,
            "inserted": summary.inserted,
            "updated": summary.updated,
            "unchanged": summary.unchanged,
            "skipped_future": summary.skipped_future,
        },
    )
    return summary


def period_end(reference_date: date, frequency: Frequency) -> date:
    """Last day of the period an SGS observation refers to.

    SGS dates daily values by the day itself and monthly values by the 1st of the month.
    """
    if frequency == Frequency.DAILY:
        return reference_date
    if frequency == Frequency.MONTHLY:
        if reference_date.day != 1:
            raise IngestionError(f"Monthly SGS date not on the 1st: {reference_date}")
        last_day = calendar.monthrange(reference_date.year, reference_date.month)[1]
        return reference_date.replace(day=last_day)
    raise IngestionError(f"Unsupported frequency for SGS ingestion: {frequency}")


def _upsert(
    session: Session,
    run: IngestionRun,
    indicator: Indicator,
    geo: GeographicUnit,
    points: list[SGSPoint],
    collected_at: datetime,
    summary: IngestionSummary,
) -> None:
    frequency = Frequency(indicator.frequency)
    existing: dict[date, tuple[int, Decimal]] = {
        row.reference_date: (row.id, row.value)
        for row in session.execute(
            select(Observation.id, Observation.reference_date, Observation.value).where(
                Observation.indicator_id == indicator.id,
                Observation.geographic_unit_id == geo.id,
                Observation.reference_date.between(summary.start, summary.end),
            )
        )
    }
    returned = {point.reference_date for point in points}
    missing = sorted(d for d in existing if d not in returned)
    if missing:
        # Stored values are kept (never deleted silently); the gap is reported for review.
        summary.missing_from_source = [d.isoformat() for d in missing[:100]]
        logger.warning(
            "stored_dates_missing_from_source",
            extra={
                "indicator": indicator.code,
                "count": len(missing),
                "first": missing[0],
                "last": missing[-1],
            },
        )
    source_reference = f"bcdata.sgs.{indicator.source_series_code}"
    new_rows: list[dict[str, Any]] = []
    for point in points:
        current = existing.get(point.reference_date)
        if current is None:
            new_rows.append(
                {
                    "indicator_id": indicator.id,
                    "geographic_unit_id": geo.id,
                    "reference_date": point.reference_date,
                    "period_start": point.reference_date,
                    "period_end": period_end(point.reference_date, frequency),
                    "value": point.value,
                    "collected_at": collected_at,
                    "source_reference": source_reference,
                }
            )
        elif current[1] != point.value:
            observation_id, previous = current
            session.add(
                ObservationRevision(
                    observation_id=observation_id,
                    previous_value=previous,
                    new_value=point.value,
                    ingestion_run_id=run.id,
                )
            )
            observation = session.get_one(Observation, observation_id)
            observation.value = point.value
            observation.collected_at = collected_at
            summary.updated += 1
        else:
            summary.unchanged += 1

    for offset in range(0, len(new_rows), _INSERT_CHUNK):
        chunk = new_rows[offset : offset + _INSERT_CHUNK]
        statement = (
            pg_insert(Observation)
            .values(chunk)
            .on_conflict_do_nothing(
                constraint="uq_observations_indicator_id_geographic_unit_id_reference_date"
            )
            .returning(Observation.id)
        )
        # rowcount is unreliable for multi-row INSERT; count the returned ids instead.
        summary.inserted += len(session.execute(statement).all())
    session.flush()


def _finish(run: IngestionRun, summary: IngestionSummary) -> None:
    run.finished_at = datetime.now(UTC)
    run.records_received = summary.received
    run.records_inserted = summary.inserted
    run.records_updated = summary.updated
    run.records_unchanged = summary.unchanged
    run.metadata_json = {
        **(run.metadata_json or {}),
        "windows": summary.windows,
        "skipped_future_dates": summary.skipped_future,
        "skipped_null_values": summary.skipped_null,
        "missing_from_source": summary.missing_from_source,
    }
