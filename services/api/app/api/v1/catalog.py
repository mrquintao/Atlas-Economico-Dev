import hashlib
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.config import get_settings
from app.db.session import get_db
from app.ingestion.batch import DERIVED_SOURCES
from app.integrations.ibge.malhas import COORDINATE_DECIMALS, MALHAS_DOCUMENTATION_URL
from app.models import GeographicBoundary, GeographicLevel, GeographicUnit, Indicator, IngestionRun
from app.repositories import catalog as repo
from app.schemas.catalog import (
    BoundariesMetadataOut,
    BoundariesOut,
    BoundaryFeatureOut,
    BoundaryPropertiesOut,
    GeographyListItem,
    GeographyOut,
    IndicatorOut,
    IngestionRunOut,
    SourceOut,
)
from app.schemas.observations import ErrorResponse

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
NOT_FOUND = {404: {"model": ErrorResponse}}


def national_geography(session: Session) -> GeographicUnit:
    geo = repo.get_geography(session, "BR", GeographicLevel.COUNTRY)
    if geo is None:
        raise ApiError(500, "catalog_not_seeded", "Unidade geográfica nacional não cadastrada.")
    return geo


def build_indicator_out(
    session: Session, indicator: Indicator, geo: GeographicUnit | None = None
) -> IndicatorOut:
    if geo is None and indicator.geographic_level != GeographicLevel.COUNTRY:
        # Catalog view of a subnational indicator: the stored range across all its units.
        unit_id = None
    else:
        unit_id = (geo or national_geography(session)).id
    first, last = repo.observation_bounds(session, indicator.id, unit_id)
    if indicator.source.acronym in DERIVED_SOURCES:
        # Derived indicators: a run reads stored annexes; the collection date is the annexes'.
        last_collected = repo.last_observation_collection(session, indicator.id, unit_id)
    else:
        last_collected = repo.last_successful_collection(session, indicator.id)
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
        last_collected_at=last_collected,
        last_run=_run_out(repo.latest_run(session, indicator.id)),
    )


def _run_out(run: IngestionRun | None) -> IngestionRunOut | None:
    if run is None:
        return None
    return IngestionRunOut(
        status=run.status,  # type: ignore[arg-type]
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_type=run.error_message.split(":", 1)[0] if run.error_message else None,
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
def list_geographies(
    session: DbSession,
    level: Annotated[
        GeographicLevel | None, Query(description="Filtra por nível (country, region, state)")
    ] = None,
) -> list[GeographyListItem]:
    return [
        GeographyListItem(
            **GeographyOut.model_validate(g).model_dump(),
            parent=GeographyOut.model_validate(g.parent) if g.parent else None,
        )
        for g in repo.list_geographies(session, level)
    ]


BOUNDARY_QUALITY = "minima"
BOUNDARIES_SIMPLIFICATION = (
    "Malha generalizada pelo próprio IBGE (qualidade=minima), sem simplificação adicional; "
    f"coordenadas quantizadas em {COORDINATE_DECIMALS} casas decimais (cerca de 11 m)."
)
# Meshes change at most once a year; clients and proxies may reuse a response for a day and
# revalidate it cheaply with If-None-Match.
BOUNDARIES_CACHE_CONTROL = "public, max-age=86400"


class GeoJSONResponse(JSONResponse):
    """GeoJSON media type; a JSONResponse subclass so OpenAPI documents the response schema."""

    media_type = "application/geo+json"

    def render(self, content: Any) -> bytes:
        # Bodies arrive already serialised by the route (``model_dump_json``).
        return content.encode() if isinstance(content, str) else super().render(content)


def boundaries_etag(boundaries: list[GeographicBoundary]) -> str:
    """Weak validator over what the features say (edition, codes, names, geometries).

    ``collected_at`` is left out on purpose: re-collecting an identical mesh keeps caches valid.
    Weak because the same representation is served with and without gzip.
    """
    digest = hashlib.sha256()
    for b in boundaries:
        unit = b.geographic_unit
        parts = (b.mesh_year, b.quality, unit.ibge_code, unit.acronym, unit.name, b.geometry_hash)
        digest.update("|".join(map(str, parts)).encode() + b"\n")
    return f'W/"{digest.hexdigest()[:32]}"'


def etag_matches(if_none_match: str, etag: str) -> bool:
    """Weak comparison (RFC 9110 §13.1.2): ``W/`` prefixes are ignored; ``*`` matches any."""
    opaque = etag.removeprefix("W/")
    tokens = [t.strip() for t in if_none_match.split(",") if t.strip()]
    return any(t == "*" or t.removeprefix("W/") == opaque for t in tokens)


@router.get(
    "/geographies/states/boundaries",
    tags=["catalog"],
    response_model=BoundariesOut,
    response_class=GeoJSONResponse,
    responses={
        304: {"description": "Não modificado (ETag igual ao `If-None-Match`)"},
        404: {"model": ErrorResponse},
    },
)
def get_state_boundaries(
    session: DbSession,
    request: Request,
    mesh_year: Annotated[
        int | None,
        Query(
            ge=2000,
            le=2100,
            description="Edição da malha do IBGE; padrão: a mais recente armazenada",
        ),
    ] = None,
) -> Response:
    """Official IBGE boundaries of the 27 UFs as a GeoJSON FeatureCollection."""
    level = GeographicLevel.STATE
    year = mesh_year or repo.latest_mesh_year(session, level, BOUNDARY_QUALITY)
    boundaries = repo.list_boundaries(session, level, year, BOUNDARY_QUALITY) if year else []
    if not boundaries:
        raise ApiError(
            404,
            "boundaries_not_found",
            "Malha das UFs não coletada" + (f" para a edição {mesh_year}." if mesh_year else "."),
        )
    etag = boundaries_etag(boundaries)
    headers = {"ETag": etag, "Cache-Control": BOUNDARIES_CACHE_CONTROL}
    if etag_matches(request.headers.get("if-none-match", ""), etag):
        # The GZip middleware sets Vary on 200s (body > 1 KB) but not on this empty 304.
        return Response(status_code=304, headers={**headers, "Vary": "Accept-Encoding"})
    settings = get_settings()
    body = BoundariesOut(
        metadata=BoundariesMetadataOut(
            source=SourceOut(
                acronym="IBGE",
                name="API de malhas geográficas do IBGE (v3)",
                organization="Instituto Brasileiro de Geografia e Estatística",
                base_url=settings.ibge_malhas_base_url,
                documentation_url=MALHAS_DOCUMENTATION_URL,
            ),
            source_url=boundaries[0].source_url,
            mesh_year=boundaries[0].mesh_year,
            quality=BOUNDARY_QUALITY,
            coordinate_decimals=COORDINATE_DECIMALS,
            simplification=BOUNDARIES_SIMPLIFICATION,
            collected_at=max(b.collected_at for b in boundaries),
        ),
        features=[
            BoundaryFeatureOut(
                id=b.geographic_unit.ibge_code,
                properties=BoundaryPropertiesOut(
                    ibge_code=b.geographic_unit.ibge_code,
                    acronym=b.geographic_unit.acronym,
                    name=b.geographic_unit.name,
                ),
                geometry=b.geometry,
            )
            for b in boundaries
        ],
    ).model_dump_json()
    return GeoJSONResponse(body, headers=headers)


@router.get("/indicators", tags=["catalog"])
def list_indicators(session: DbSession) -> list[IndicatorOut]:
    return [build_indicator_out(session, i) for i in repo.list_indicators(session)]


@router.get("/indicators/{code}", tags=["catalog"], responses=NOT_FOUND)
def get_indicator(code: str, session: DbSession) -> IndicatorOut:
    return build_indicator_out(session, get_indicator_or_404(session, code))
