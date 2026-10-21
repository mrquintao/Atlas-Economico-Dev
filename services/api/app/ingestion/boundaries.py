"""Collection of the official IBGE state boundaries (S2).

The 27 features of the mesh must match the 27 seeded states 1:1 by IBGE code; otherwise nothing
is written and the run is recorded as failed. Re-collecting the same edition is idempotent: a
geometry is only rewritten when its hash changed, and the changed codes are recorded in the run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.series_ingestion import IngestionError, format_error
from app.integrations.ibge.malhas import MalhasClient
from app.models import (
    DataSource,
    GeographicBoundary,
    GeographicLevel,
    GeographicUnit,
    IngestionRun,
    IngestionStatus,
)

logger = logging.getLogger(__name__)

SOURCE_ACRONYM = "IBGE"
DATASET = "state_boundaries"


@dataclass
class BoundariesSummary:
    run_id: int
    mesh_year: int
    quality: str
    received: int
    inserted: int
    updated: int
    unchanged: int
    updated_codes: list[str] = field(default_factory=list)


def ingest_state_boundaries(
    session: Session,
    settings: Settings,
    client: MalhasClient | None = None,
    *,
    mesh_year: int | None = None,
    quality: str = "minima",
) -> BoundariesSummary:
    """Collect the state mesh and store it.

    Every failure after the run is created (source, payload, code matching, database) is recorded
    as a failed run and re-raised; a missing IBGE data source raises before any run exists.
    """
    year = mesh_year if mesh_year is not None else settings.ibge_mesh_year
    source = session.scalar(select(DataSource).where(DataSource.acronym == SOURCE_ACRONYM))
    if source is None:
        raise IngestionError(f"Data source {SOURCE_ACRONYM} is not seeded")
    run = IngestionRun(
        source_id=source.id,
        indicator_id=None,
        started_at=datetime.now(UTC),
        status=IngestionStatus.RUNNING,
        metadata_json={"dataset": DATASET, "mesh_year": year, "quality": quality},
    )
    session.add(run)
    session.commit()
    run_id = run.id
    try:
        owns_client = client is None
        client = client or MalhasClient(settings)
        try:
            result = client.fetch_state_boundaries(year, quality)
        finally:
            if owns_client:
                client.close()
        states = {
            unit.ibge_code: unit
            for unit in session.scalars(
                select(GeographicUnit).where(
                    GeographicUnit.geographic_level == GeographicLevel.STATE
                )
            )
        }
        received, expected = {b.ibge_code for b in result.boundaries}, set(states)
        if received != expected:
            raise IngestionError(
                "Mesh codes do not match the seeded states: "
                f"missing {sorted(expected - received)}, unknown {sorted(received - expected)}"
            )
        existing = {
            b.geographic_unit_id: b
            for b in session.scalars(
                select(GeographicBoundary).where(
                    GeographicBoundary.mesh_year == year, GeographicBoundary.quality == quality
                )
            )
        }
        now = datetime.now(UTC)
        summary = BoundariesSummary(run_id, year, quality, len(result.boundaries), 0, 0, 0)
        for boundary in result.boundaries:
            unit = states[boundary.ibge_code]
            stored = existing.get(unit.id)
            if stored is None:
                session.add(
                    GeographicBoundary(
                        geographic_unit_id=unit.id,
                        mesh_year=year,
                        quality=quality,
                        geometry=boundary.geometry,
                        geometry_hash=boundary.geometry_hash,
                        source_url=result.url,
                        collected_at=now,
                    )
                )
                summary.inserted += 1
                continue
            stored.collected_at = now
            stored.source_url = result.url
            if stored.geometry_hash == boundary.geometry_hash:
                summary.unchanged += 1
            else:
                stored.geometry = boundary.geometry
                stored.geometry_hash = boundary.geometry_hash
                summary.updated += 1
                summary.updated_codes.append(boundary.ibge_code)
        run = session.get_one(IngestionRun, run_id)
        run.status = IngestionStatus.SUCCESS
        run.finished_at = datetime.now(UTC)
        run.records_received = summary.received
        run.records_inserted = summary.inserted
        run.records_updated = summary.updated
        run.records_unchanged = summary.unchanged
        run.metadata_json = {
            **(run.metadata_json or {}),
            "source_url": result.url,
            "content_hash": result.content_hash,
            "updated_codes": summary.updated_codes,
        }
        session.commit()
    except Exception as exc:
        session.rollback()
        run = session.get_one(IngestionRun, run_id)
        run.status = IngestionStatus.FAILED
        run.finished_at = datetime.now(UTC)
        run.error_message = format_error(exc)
        session.commit()
        logger.error("boundaries_ingestion_failed", extra={"run_id": run_id, "error": str(exc)})
        raise
    logger.info(
        "boundaries_ingestion_succeeded",
        extra={"run_id": run_id, "inserted": summary.inserted, "updated": summary.updated},
    )
    return summary
