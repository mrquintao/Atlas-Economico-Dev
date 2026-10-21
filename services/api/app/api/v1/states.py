"""State (UF) endpoints over the SICONFI-derived indicators (S5)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.v1.catalog import DbSession, build_indicator_out
from app.api.v1.dashboard import get_seeded_indicator, summarize_indicator
from app.api.v1.observations import series_response
from app.ingestion.fiscal_catalog import ACCUMULATION_WINDOWS, SIGNED_CODES, YEAR_TO_DATE_CODES
from app.models import GeographicLevel, GeographicUnit, Indicator
from app.repositories import catalog as catalog_repo
from app.repositories import observations as observations_repo
from app.repositories.observations import PeriodCoverage
from app.schemas.catalog import GeographyOut
from app.schemas.observations import ErrorResponse
from app.schemas.states import (
    StateDashboardIndicatorOut,
    StateDashboardOut,
    StateIndicatorSeriesOut,
    StateIndicatorsOut,
    StateMapOut,
    StateMapPeriodOut,
    StateMapValueOut,
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

# Map texts validated by the economist (S6).
MAP_MIN_COVERAGE = 14
MAP_DEFAULT_RULE = (
    f"Período padrão: o mais recente com valor publicado por pelo menos {MAP_MIN_COVERAGE} das 27 "
    "UFs (ou, se nenhum atingir esse número, o mais recente com algum valor)."
)
BRL_UNIT = "R$ correntes"
MAP_ABSOLUTE_NOTE = (
    "Valores absolutos, em reais correntes, sem correção pela inflação. Refletem também o "
    "tamanho de cada UF; métricas relativas virão em entrega futura."
)
MAP_YEAR_TO_DATE_NOTE = (
    "Acumulado de janeiro até o bimestre selecionado. Todas as UFs estão no mesmo bimestre; não "
    "compare bimestres diferentes."
)
PERSONNEL_CODES = frozenset({"STATE_PERSONNEL_EXEC", "STATE_PERSONNEL_EXEC_RCL"})
MAP_PERSONNEL_Q3_NOTE = (
    "No 3º quadrimestre, a despesa com pessoal inclui os restos a pagar não processados inscritos."
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


@router.get("/states/map/{code}", tags=["states"], responses=STATE_RESPONSES)
def get_state_map(
    code: Annotated[str, Path(description="Código do indicador estadual (ex.: STATE_DCL_RCL)")],
    session: DbSession,
    response: Response,
    reference_date: Annotated[
        date | None,
        Query(description="Período (YYYY-MM-DD) entre os `available_periods`; padrão: ver regra"),
    ] = None,
) -> StateMapOut:
    """One state indicator in the 27 UFs at a single reference period, for the choropleth map.

    Every UF is read at the same period (never the latest value of each UF); a UF without a
    published value for it is ``no_data`` with a null value.
    """
    code = code.strip().upper()
    if code not in STATE_DASHBOARD_CODES:
        raise ApiError(404, "indicator_not_found", f"Indicador estadual '{code}' não encontrado.")
    indicator = get_seeded_indicator(session, code)
    periods = observations_repo.fetch_period_coverage(session, indicator.id)
    if reference_date is None:
        period = default_map_period(periods)
    else:
        period = next((p for p in periods if p.reference_date == reference_date), None)
        if period is None:
            raise ApiError(
                404,
                "period_not_found",
                f"Nenhuma UF tem valor de '{code}' no período {reference_date.isoformat()}.",
            )
    values = (
        observations_repo.fetch_state_cross_section(session, indicator.id, period.reference_date)
        if period
        else {}
    )
    states = sorted(
        catalog_repo.list_geographies(session, GeographicLevel.STATE), key=lambda g: g.acronym
    )
    response.headers["Cache-Control"] = "public, max-age=300"
    return StateMapOut(
        indicator=build_indicator_out(session, indicator),
        accumulation_window=ACCUMULATION_WINDOWS[code],
        scale="diverging" if code in SIGNED_CODES else "sequential",
        period=_period_out(period) if period else None,
        default_rule=MAP_DEFAULT_RULE,
        available_periods=[_period_out(p) for p in periods],
        notes=map_notes(indicator, period),
        states=[
            StateMapValueOut(
                geography=GeographyOut.model_validate(geo),
                status="available" if geo.id in values else "no_data",
                value=float(values[geo.id]) if geo.id in values else None,
            )
            for geo in states
        ],
    )


def default_map_period(periods: list[PeriodCoverage]) -> PeriodCoverage | None:
    """Most recent period with at least MAP_MIN_COVERAGE UFs, else the most recent one.

    Reports of a period arrive over weeks: a map of its first three UFs would mislead.
    """
    covered = next((p for p in periods if p.units >= MAP_MIN_COVERAGE), None)
    return covered or (periods[0] if periods else None)


def map_notes(indicator: Indicator, period: PeriodCoverage | None) -> list[str]:
    notes: list[str] = []
    if indicator.code in YEAR_TO_DATE_CODES:
        notes.append(MAP_YEAR_TO_DATE_NOTE)
    if indicator.unit == BRL_UNIT:
        notes.append(MAP_ABSOLUTE_NOTE)
    if indicator.code in PERSONNEL_CODES and period is not None and period.period_end.month == 12:
        notes.append(MAP_PERSONNEL_Q3_NOTE)
    notes.append(DF_NOTE)
    return notes


def _period_out(period: PeriodCoverage) -> StateMapPeriodOut:
    return StateMapPeriodOut(
        reference_date=period.reference_date,
        period_start=period.period_start,
        period_end=period.period_end,
        coverage=period.units,
    )
