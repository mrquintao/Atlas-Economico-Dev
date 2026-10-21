from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.models import GeographicUnit, Indicator
from app.repositories import catalog as repo
from app.schemas.catalog import GeographyOut, IndicatorOut, SourceOut
from app.schemas.observations import ErrorResponse

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
NOT_FOUND = {404: {"model": ErrorResponse}}


def national_geography(session: Session) -> GeographicUnit:
    geo = repo.get_geography(session, "BR")
    if geo is None:
        raise ApiError(500, "catalog_not_seeded", "Unidade geográfica nacional não cadastrada.")
    return geo


def build_indicator_out(session: Session, indicator: Indicator) -> IndicatorOut:
    geo = national_geography(session)
    first, last = repo.observation_bounds(session, indicator.id, geo.id)
    return IndicatorOut(
        code=indicator.code,
        name=indicator.name,
        short_name=indicator.short_name,
        description=indicator.description,
        unit=indicator.unit,
        change_unit=indicator.change_unit,
        frequency=indicator.frequency,
        geographic_level=indicator.geographic_level,
        methodology=indicator.methodology,
        methodology_version=indicator.methodology_version,
        first_available_date=indicator.first_available_date,
        source=SourceOut.model_validate(indicator.source),
        source_series_code=indicator.source_series_code,
        source_url=indicator.source_url,
        first_stored_date=first,
        last_stored_date=last,
        last_collected_at=repo.last_successful_collection(session, indicator.id),
    )


def get_indicator_or_404(session: Session, code: str) -> Indicator:
    indicator = repo.get_indicator(session, code.upper())
    if indicator is None:
        raise ApiError(404, "indicator_not_found", f"Indicador '{code}' não encontrado.")
    return indicator


@router.get("/health", tags=["system"])
def health(session: DbSession) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        raise ApiError(503, "database_unavailable", "Banco de dados indisponível.") from exc
    return {"status": "ok", "database": "ok"}


@router.get("/sources", tags=["catalog"])
def list_sources(session: DbSession) -> list[SourceOut]:
    return [SourceOut.model_validate(s) for s in repo.list_sources(session)]


@router.get("/geographies", tags=["catalog"])
def list_geographies(session: DbSession) -> list[GeographyOut]:
    return [GeographyOut.model_validate(g) for g in repo.list_geographies(session)]


@router.get("/indicators", tags=["catalog"])
def list_indicators(session: DbSession) -> list[IndicatorOut]:
    return [build_indicator_out(session, i) for i in repo.list_indicators(session)]


@router.get("/indicators/{code}", tags=["catalog"], responses=NOT_FOUND)
def get_indicator(code: str, session: DbSession) -> IndicatorOut:
    return build_indicator_out(session, get_indicator_or_404(session, code))
