from datetime import date, datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    DataSource,
    GeographicUnit,
    Indicator,
    IngestionRun,
    IngestionStatus,
    Observation,
)


def list_indicators(session: Session) -> list[Indicator]:
    return list(
        session.scalars(
            select(Indicator).options(joinedload(Indicator.source)).order_by(Indicator.code)
        )
    )


def get_indicator(session: Session, code: str) -> Indicator | None:
    return session.scalar(
        select(Indicator).options(joinedload(Indicator.source)).where(Indicator.code == code)
    )


def list_sources(session: Session) -> list[DataSource]:
    return list(session.scalars(select(DataSource).order_by(DataSource.acronym)))


# Resolution order when a code or acronym exists at several levels ("1" is Brasil and the Norte
# region; "SE" is Sergipe and the Sudeste region): coarser national/state units come first.
LEVEL_ORDER = case(
    {"country": 0, "state": 1, "region": 2, "municipality": 3},
    value=GeographicUnit.geographic_level,
)


def list_geographies(session: Session, level: str | None = None) -> list[GeographicUnit]:
    query = select(GeographicUnit).options(joinedload(GeographicUnit.parent))
    if level is not None:
        query = query.where(GeographicUnit.geographic_level == level)
    # Codes have the same length within a level, so string order is numeric order.
    return list(session.scalars(query.order_by(LEVEL_ORDER, GeographicUnit.ibge_code)))


def get_geography(
    session: Session, acronym_or_code: str, level: str | None = None
) -> GeographicUnit | None:
    """Find a unit by acronym (case-insensitive) or IBGE code, optionally within one level.

    Without a level, an ambiguous key resolves by LEVEL_ORDER.
    """
    key = acronym_or_code.strip()
    query = select(GeographicUnit).where(
        (func.upper(GeographicUnit.acronym) == key.upper()) | (GeographicUnit.ibge_code == key)
    )
    if level is not None:
        query = query.where(GeographicUnit.geographic_level == level)
    return session.scalars(query.order_by(LEVEL_ORDER).limit(1)).first()


def last_successful_collection(session: Session, indicator_id: int) -> datetime | None:
    return session.scalar(
        select(func.max(IngestionRun.finished_at)).where(
            IngestionRun.indicator_id == indicator_id,
            IngestionRun.status == IngestionStatus.SUCCESS,
        )
    )


def latest_run(session: Session, indicator_id: int) -> IngestionRun | None:
    return session.scalar(
        select(IngestionRun)
        .where(IngestionRun.indicator_id == indicator_id)
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .limit(1)
    )


def observation_bounds(
    session: Session, indicator_id: int, geographic_unit_id: int
) -> tuple[date | None, date | None]:
    row = session.execute(
        select(func.min(Observation.reference_date), func.max(Observation.reference_date)).where(
            Observation.indicator_id == indicator_id,
            Observation.geographic_unit_id == geographic_unit_id,
        )
    ).one()
    return row[0], row[1]
