from datetime import date, datetime

from sqlalchemy import func, select
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


def list_geographies(session: Session) -> list[GeographicUnit]:
    return list(session.scalars(select(GeographicUnit).order_by(GeographicUnit.ibge_code)))


def get_geography(session: Session, acronym_or_code: str) -> GeographicUnit | None:
    key = acronym_or_code.strip()
    return session.scalar(
        select(GeographicUnit).where(
            (func.upper(GeographicUnit.acronym) == key.upper()) | (GeographicUnit.ibge_code == key)
        )
    )


def last_successful_collection(session: Session, indicator_id: int) -> datetime | None:
    return session.scalar(
        select(func.max(IngestionRun.finished_at)).where(
            IngestionRun.indicator_id == indicator_id,
            IngestionRun.status == IngestionStatus.SUCCESS,
        )
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
