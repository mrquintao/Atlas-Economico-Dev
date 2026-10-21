"""Collection of several indicators in one execution (CLI ``ingest --all`` and the scheduler).

Each indicator is collected independently: a failure is logged, recorded in ``ingestion_runs``
by the ingestion itself and reported in the result, and the remaining indicators still run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.ingestion.series_ingestion import (
    IngestionError,
    IngestionSummary,
    SeriesClient,
    format_error,
    ingest_indicator,
)
from app.integrations.bcb.sgs import SGSClient
from app.integrations.ibge.sidra import SIDRAClient
from app.models import DataSource, Indicator, IngestionRun, IngestionStatus

logger = logging.getLogger(__name__)

# Source acronym -> connector able to collect its national series.
CONNECTORS: dict[str, type[SGSClient] | type[SIDRAClient]] = {
    "BCB": SGSClient,
    "IBGE": SIDRAClient,
}


# A run still "running" after this long was interrupted (e.g. the process was killed): one
# collection takes seconds to a few minutes even with every retry exhausted.
ORPHAN_RUN_AGE = timedelta(hours=1)


@dataclass
class BatchItem:
    indicator_code: str
    status: str
    run_id: int | None = None
    error: str | None = None
    summary: IngestionSummary | None = None


@dataclass
class BatchResult:
    items: list[BatchItem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(item.status == IngestionStatus.SUCCESS for item in self.items)

    @property
    def failed(self) -> list[str]:
        return [i.indicator_code for i in self.items if i.status != IngestionStatus.SUCCESS]


def select_indicators(session: Session, codes: Sequence[str] | None) -> list[Indicator]:
    """The requested indicators, or every series with a connector (ordered by code) when
    ``codes`` is None.

    Indicators derived from SICONFI annexes have no series connector: they are produced by
    ``derive-fiscal`` (ADR 0010), so the batch skips them and rejects an explicit request
    before any run is recorded.
    """
    query = (
        select(Indicator)
        .join(Indicator.source)
        .options(joinedload(Indicator.source))
        .order_by(Indicator.code)
    )
    if codes is None:
        return list(session.scalars(query.where(DataSource.acronym.in_(CONNECTORS))))
    found = {i.code: i for i in session.scalars(query.where(Indicator.code.in_(codes)))}
    unknown = [code for code in codes if code not in found]
    if unknown:
        raise IngestionError(f"Unknown indicator: {', '.join(unknown)}")
    derived = [code for code in codes if found[code].source.acronym not in CONNECTORS]
    if derived:
        raise IngestionError(
            f"No series connector for {', '.join(derived)}; derive it from the SICONFI "
            "annexes with `derive-fiscal`"
        )
    return [found[code] for code in codes]


def run_batch(
    session: Session,
    settings: Settings,
    codes: Sequence[str] | None = None,
    *,
    clients: Mapping[str, SeriesClient] | None = None,
    should_stop: Callable[[], bool] = lambda: False,
    **options: Any,
) -> BatchResult:
    """Collects each indicator in turn; ``options`` go to ``ingest_indicator`` (start, end...).

    ``clients`` maps a source acronym to a connector; missing ones are created from settings.
    ``should_stop`` is checked between indicators (graceful shutdown of the scheduler).
    """
    indicators = select_indicators(session, codes)
    close_orphan_runs(session)
    # Plain values: a failed ingestion rolls the session back and expires the ORM objects.
    targets = [(i.code, i.id, i.source.acronym) for i in indicators]
    result = BatchResult()
    logger.info("batch_started", extra={"indicators": [code for code, _, _ in targets]})
    with ExitStack() as stack:
        open_clients: dict[str, SeriesClient] = dict(clients or {})
        for code, _, source in targets:
            if should_stop():
                logger.warning("batch_interrupted", extra={"pending": code})
                break
            item = BatchItem(code, IngestionStatus.FAILED)
            try:
                if source not in open_clients:
                    # select_indicators only returns indicators of sources with a connector.
                    open_clients[source] = stack.enter_context(CONNECTORS[source](settings))
                summary = ingest_indicator(
                    session, open_clients[source], code, source_acronym=source, **options
                )
                item.status, item.run_id, item.summary = summary.status, summary.run_id, summary
            except Exception as exc:
                # ingest_indicator records its own failures in ingestion_runs; keep going.
                session.rollback()
                item.run_id = item.run_id or getattr(exc, "ingestion_run_id", None)
                item.error = format_error(exc)
                logger.error(
                    "batch_indicator_failed", extra={"indicator": code, "error": item.error}
                )
            result.items.append(item)
    logger.info(
        "batch_finished",
        extra={"ok": result.ok, "failed": result.failed, "total": len(result.items)},
    )
    return result


def close_orphan_runs(session: Session, now: datetime | None = None) -> int:
    """Marks as failed the runs left "running" by an interrupted process, so the status shown
    to users does not claim a collection in progress forever."""
    cutoff = (now or datetime.now(UTC)) - ORPHAN_RUN_AGE
    result = session.execute(
        update(IngestionRun)
        .where(IngestionRun.status == IngestionStatus.RUNNING, IngestionRun.started_at < cutoff)
        .values(
            status=IngestionStatus.FAILED,
            finished_at=None,
            error_message="Interrupted: the collection process stopped before finishing",
        )
        .returning(IngestionRun.id)
    )
    closed = [row[0] for row in result]
    session.commit()
    if closed:
        logger.warning("orphan_runs_closed", extra={"run_ids": closed})
    return len(closed)
