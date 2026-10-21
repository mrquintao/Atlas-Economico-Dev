"""State (UF) endpoints over the SICONFI-derived indicators (S5)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.catalog import DbSession
from app.api.v1.dashboard import get_seeded_indicator, summarize_indicator
from app.api.v1.observations import series_response
from app.ingestion.fiscal_catalog import ACCUMULATION_WINDOWS
from app.models import GeographicLevel, GeographicUnit
from app.repositories import catalog as catalog_repo
from app.schemas.catalog import GeographyOut
from app.schemas.observations import ErrorResponse
from app.schemas.states import (
    StateDashboardIndicatorOut,
    StateDashboardOut,
    StateIndicatorSeriesOut,
    StateIndicatorsOut,
)

router = APIRouter()

# Display order validated by the economist: revenue, expenditure, results, debt.
STATE_DASHBOARD_CODES = (
    "STATE_RCL",
    "STATE_PERSONNEL_EXEC",
    "STATE_PERSONNEL_EXEC_RCL",
    "STATE_INVESTMENTS",
    "STATE_PRIMARY_RESULT",
    "STATE_NOMINAL_RESULT",
    "STATE_DC",
    "STATE_DCL",
    "STATE_DCL_RCL",
)

DF_NOTE = (
    "O Distrito Federal acumula competências estaduais e municipais (IPTU, ISS e cota-parte do "
    "FPM entram na sua RCL) e não tem Judiciário nem Ministério Público próprios. Por isso, seus "
    "valores não são diretamente comparáveis aos dos estados."
)
CHANGE_NOTE_BRL = (
    "Diferença em relação ao mesmo período do ano anterior, em reais correntes, sem correção "
    "pela inflação."
)
CHANGE_NOTE_PP = (
    "Diferença em pontos percentuais (p.p.) em relação ao mesmo período do ano anterior."
)

UfPath = Annotated[str, Path(description="Sigla (ex.: SP) ou código IBGE (ex.: 35) da UF")]
STATE_RESPONSES = {404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}


def get_state_or_404(session: Session, uf: str) -> GeographicUnit:
    # Only the state level: "BR", region codes and municipalities are not UFs ("SE" is Sergipe).
    geo = catalog_repo.get_geography(session, uf, GeographicLevel.STATE)
    if geo is None:
        raise ApiError(404, "state_not_found", f"UF '{uf}' não encontrada.")
    return geo


def state_notes(geo: GeographicUnit) -> list[str]:
    return [DF_NOTE] if geo.acronym == "DF" else []


@router.get("/states/{uf}/indicators", tags=["states"], responses=STATE_RESPONSES)
def get_state_indicators(
    uf: UfPath,
    session: DbSession,
    response: Response,
    start_date: Annotated[date | None, Query(description="Data inicial (YYYY-MM-DD)")] = None,
    end_date: Annotated[date | None, Query(description="Data final (YYYY-MM-DD)")] = None,
) -> StateIndicatorsOut:
    """Every state indicator for the UF: metadata, availability and series as published."""
    if start_date and end_date and start_date > end_date:
        raise ApiError(422, "invalid_range", "start_date deve ser anterior ou igual a end_date.")
    geo = get_state_or_404(session, uf)
    items: list[StateIndicatorSeriesOut] = []
    for code in STATE_DASHBOARD_CODES:
        series = series_response(
            session, get_seeded_indicator(session, code), geo, start_date, end_date
        )
        items.append(
            StateIndicatorSeriesOut(
                **dict(series),
                status="available" if series.indicator.last_stored_date else "no_data",
                accumulation_window=ACCUMULATION_WINDOWS[code],
            )
        )
    response.headers["Cache-Control"] = "public, max-age=300"
    return StateIndicatorsOut(
        geography=GeographyOut.model_validate(geo),
        start_date=start_date,
        end_date=end_date,
        notes=state_notes(geo),
        indicators=items,
    )


@router.get("/states/{uf}/dashboard", tags=["states"], responses=STATE_RESPONSES)
def get_state_dashboard(uf: UfPath, session: DbSession, response: Response) -> StateDashboardOut:
    """Latest published value of each state indicator and its change versus the same period
    one year earlier (no percentage change: results and DCL change sign)."""
    geo = get_state_or_404(session, uf)
    items: list[StateDashboardIndicatorOut] = []
    for code in STATE_DASHBOARD_CODES:
        indicator = get_seeded_indicator(session, code)
        summary = summarize_indicator(session, indicator, geo)
        items.append(
            StateDashboardIndicatorOut(
                **dict(summary),
                accumulation_window=ACCUMULATION_WINDOWS[code],
                change_note=None
                if summary.change_12m is None
                else CHANGE_NOTE_PP
                if indicator.change_unit == "p.p."
                else CHANGE_NOTE_BRL,
            )
        )
    response.headers["Cache-Control"] = "public, max-age=300"
    return StateDashboardOut(
        geography=GeographyOut.model_validate(geo), notes=state_notes(geo), indicators=items
    )
