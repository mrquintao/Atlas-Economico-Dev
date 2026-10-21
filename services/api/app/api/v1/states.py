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
    StateComparisonOut,
    StateDashboardIndicatorOut,
    StateDashboardOut,
    StateIndicatorSeriesOut,
    StateIndicatorsOut,
    StateMapOut,
    StateMapPeriodOut,
    StateMapValueOut,
    StateRankingItemOut,
    StateRankingOut,
)
from app.services.ranking import RankingOrder, rank_values

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
    "tamanho de cada UF; para comparar UFs de portes diferentes, prefira as métricas relativas "
    "(DCL/RCL e despesa com pessoal do Executivo/RCL)."
)
MAP_YEAR_TO_DATE_NOTE = (
    "Acumulado de janeiro até o bimestre selecionado. Todas as UFs estão no mesmo bimestre; não "
    "compare bimestres diferentes."
)
PERSONNEL_CODES = frozenset({"STATE_PERSONNEL_EXEC", "STATE_PERSONNEL_EXEC_RCL"})
MAP_PERSONNEL_Q3_NOTE = (
    "No 3º quadrimestre, a despesa com pessoal inclui os restos a pagar não processados inscritos."
)

# Ranking and comparison texts validated by the economist (S8).
RELATIVE_CODES = frozenset({"STATE_DCL_RCL", "STATE_PERSONNEL_EXEC_RCL"})
RANKING_ORDER_NOTES: dict[RankingOrder, str] = {
    "desc": "Posição pela ordem dos valores, do maior para o menor, entre as UFs selecionadas "
    "com valor no período. A posição não indica desempenho melhor ou pior.",
    "asc": "Posição pela ordem dos valores, do menor para o maior, entre as UFs selecionadas "
    "com valor no período. A posição não indica desempenho melhor ou pior.",
}
RANKING_TIES_NOTE = (
    "Valores iguais ocupam a mesma posição; a posição seguinte pula as posições ocupadas "
    "(ex.: 1, 2, 2, 4)."
)
RANKING_ABSOLUTE_NOTE = (
    "Valores absolutos, em reais correntes, sem correção pela inflação. A ordem reflete "
    "sobretudo o tamanho de cada UF. Para comparar UFs de portes diferentes, prefira as "
    "métricas relativas: DCL/RCL e despesa com pessoal do Executivo/RCL."
)
RELATIVE_NOTE = (
    "Métrica relativa: percentual publicado pela própria UF no Relatório de Gestão Fiscal, sem "
    "recálculo pelo Atlas. Dividir pela receita corrente líquida permite comparar UFs de "
    "tamanhos diferentes."
)
DENOMINATOR_NOTES = {
    "STATE_DCL_RCL": "O denominador é a RCL ajustada para endividamento definida na LRF, que pode "
    "diferir levemente da RCL exibida no Atlas. DCL/RCL começa em 2020, quando essa RCL ajustada "
    "passou a ser o denominador.",
    "STATE_PERSONNEL_EXEC_RCL": "O denominador é a RCL ajustada para o cálculo dos limites da "
    "despesa com pessoal (LRF), que pode diferir levemente da RCL exibida no Atlas.",
}
SIGNED_NOTE = (
    "Valores negativos são possíveis: DCL negativa indica haveres financeiros maiores que a "
    "dívida; resultado negativo indica déficit."
)
# Only the absence of a stored value is known: the report may not have been delivered to the
# SICONFI or may not have been collected yet (qa-auditor, S8).
MISSING_NOTE = (
    "Sem dado no período: {ufs}. Não há valor armazenado para essas UFs neste período (o "
    "relatório pode não ter sido entregue ao SICONFI ou ainda não ter sido coletado); elas ficam "
    "fora da classificação. Ausência de dado não equivale a zero."
)
MISSING_NOTE_ONE = (
    "Sem dado no período: {ufs}. Não há valor armazenado para essa UF neste período (o "
    "relatório pode não ter sido entregue ao SICONFI ou ainda não ter sido coletado); ela fica "
    "fora da classificação. Ausência de dado não equivale a zero."
)
COMPARISON_NOTE = (
    "Cada linha mostra a série da UF como publicada; períodos sem dado aparecem como interrupção."
)
COMPARISON_YEAR_TO_DATE_NOTE = (
    "Valores acumulados no ano recomeçam em janeiro, por isso a linha é interrompida a cada ano."
)
COMPARISON_PERSONNEL_NOTE = (
    "No 3º quadrimestre de cada ano, a despesa com pessoal inclui os restos a pagar não "
    "processados inscritos."
)
COMPARISON_BRL_NOTE = (
    "Valores em reais correntes, sem correção pela inflação; refletem também o tamanho de cada UF."
)
MIN_RANKING_UFS = 2
MAX_COMPARISON_UFS = 6

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
    indicator = get_state_indicator_or_404(session, code)
    code = indicator.code
    periods = observations_repo.fetch_period_coverage(session, indicator.id)
    period = select_period(periods, reference_date, code)
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


def get_state_indicator_or_404(session: Session, code: str) -> Indicator:
    code = code.strip().upper()
    if code not in STATE_DASHBOARD_CODES:
        raise ApiError(404, "indicator_not_found", f"Indicador estadual '{code}' não encontrado.")
    return get_seeded_indicator(session, code)


def select_period(
    periods: list[PeriodCoverage], reference_date: date | None, code: str
) -> PeriodCoverage | None:
    """The requested period (404 if no UF has it) or, without a request, the default one."""
    if reference_date is None:
        return default_map_period(periods)
    period = next((p for p in periods if p.reference_date == reference_date), None)
    if period is None:
        raise ApiError(
            404,
            "period_not_found",
            f"Nenhuma UF tem valor de '{code}' no período {reference_date.isoformat()}.",
        )
    return period


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


CodePath = Annotated[str, Path(description="Código do indicador estadual (ex.: STATE_DCL_RCL)")]


def parse_selection(
    session: Session, ufs: str | None, minimum: int, maximum: int
) -> list[GeographicUnit]:
    """UFs of a comma-separated list (acronyms or IBGE codes), in the given order.

    Without a list, the 27 UFs by acronym. Unknown or repeated UFs are rejected, never ignored.
    """
    if ufs is None:
        selection = sorted(
            catalog_repo.list_geographies(session, GeographicLevel.STATE), key=lambda g: g.acronym
        )
    else:
        selection = []
        for key in (part.strip() for part in ufs.split(",")):
            geo = catalog_repo.get_geography(session, key, GeographicLevel.STATE) if key else None
            if geo is None:
                raise ApiError(422, "invalid_selection", f"UF '{key}' não encontrada.")
            if any(g.id == geo.id for g in selection):
                raise ApiError(422, "invalid_selection", f"UF '{geo.acronym}' repetida.")
            selection.append(geo)
    if not minimum <= len(selection) <= maximum:
        raise ApiError(
            422,
            "invalid_selection",
            f"Selecione de {minimum} a {maximum} UFs (recebidas: {len(selection)}).",
        )
    return selection


@router.get("/states/ranking/{code}", tags=["states"], responses=STATE_RESPONSES)
def get_state_ranking(
    code: CodePath,
    session: DbSession,
    response: Response,
    reference_date: Annotated[
        date | None,
        Query(description="Período (YYYY-MM-DD) entre os `available_periods`; padrão: ver regra"),
    ] = None,
    ufs: Annotated[
        str | None,
        Query(description="UFs separadas por vírgula (ex.: SP,MG,RJ); padrão: as 27"),
    ] = None,
    order: Annotated[
        RankingOrder, Query(description="'desc' (do maior para o menor) ou 'asc'")
    ] = "desc",
) -> StateRankingOut:
    """Selected UFs ordered by one state indicator at a single reference period.

    The period follows the map's rule (same period for every UF, default chosen over the 27
    UFs). UFs without a published value for it are listed in ``missing``, never ranked.
    """
    indicator = get_state_indicator_or_404(session, code)
    code = indicator.code
    selection = parse_selection(session, ufs, MIN_RANKING_UFS, 27)
    periods = observations_repo.fetch_period_coverage(session, indicator.id)
    period = select_period(periods, reference_date, code)
    values = (
        observations_repo.fetch_state_cross_section(session, indicator.id, period.reference_date)
        if period
        else {}
    )
    by_acronym = {geo.acronym: geo for geo in selection}
    ranked = rank_values(
        {geo.acronym: values[geo.id] for geo in selection if geo.id in values}, order
    )
    missing = sorted((geo for geo in selection if geo.id not in values), key=lambda g: g.acronym)
    response.headers["Cache-Control"] = "public, max-age=300"
    return StateRankingOut(
        indicator=build_indicator_out(session, indicator),
        accumulation_window=ACCUMULATION_WINDOWS[code],
        metric_kind="relative" if code in RELATIVE_CODES else "absolute",
        order=order,
        order_note=RANKING_ORDER_NOTES[order],
        period=_period_out(period) if period else None,
        default_rule=MAP_DEFAULT_RULE,
        available_periods=[_period_out(p) for p in periods],
        selected_count=len(selection),
        ranked_count=len(ranked),
        ranking=[
            StateRankingItemOut(
                position=item.position,
                geography=GeographyOut.model_validate(by_acronym[item.acronym]),
                value=float(item.value),
            )
            for item in ranked
        ],
        missing=[GeographyOut.model_validate(geo) for geo in missing],
        missing_note=(MISSING_NOTE_ONE if len(missing) == 1 else MISSING_NOTE).format(
            ufs=", ".join(g.acronym for g in missing)
        )
        if missing and period
        else None,
        notes=ranking_notes(indicator, period, selection),
    )


def ranking_notes(
    indicator: Indicator, period: PeriodCoverage | None, selection: list[GeographicUnit]
) -> list[str]:
    code = indicator.code
    notes = [RANKING_TIES_NOTE]
    if code in RELATIVE_CODES:
        notes += [RELATIVE_NOTE, DENOMINATOR_NOTES[code]]
    else:
        notes.append(RANKING_ABSOLUTE_NOTE)
    if code in YEAR_TO_DATE_CODES:
        notes.append(MAP_YEAR_TO_DATE_NOTE)
    if code in SIGNED_CODES:
        notes.append(SIGNED_NOTE)
    if code in PERSONNEL_CODES and period is not None and period.period_end.month == 12:
        notes.append(MAP_PERSONNEL_Q3_NOTE)
    if any(geo.acronym == "DF" for geo in selection):
        notes.append(DF_NOTE)
    return notes


@router.get("/states/compare/{code}", tags=["states"], responses=STATE_RESPONSES)
def get_state_comparison(
    code: CodePath,
    session: DbSession,
    response: Response,
    ufs: Annotated[
        str,
        Query(description=f"De 1 a {MAX_COMPARISON_UFS} UFs separadas por vírgula (ex.: SP,MG)"),
    ],
    start_date: Annotated[date | None, Query(description="Data inicial (YYYY-MM-DD)")] = None,
    end_date: Annotated[date | None, Query(description="Data final (YYYY-MM-DD)")] = None,
) -> StateComparisonOut:
    """One state indicator in a few UFs, each series as published and in its own periods."""
    if start_date and end_date and start_date > end_date:
        raise ApiError(422, "invalid_range", "start_date deve ser anterior ou igual a end_date.")
    indicator = get_state_indicator_or_404(session, code)
    code = indicator.code
    selection = parse_selection(session, ufs, 1, MAX_COMPARISON_UFS)
    series: list[StateIndicatorSeriesOut] = []
    for geo in selection:
        item = series_response(session, indicator, geo, start_date, end_date)
        series.append(
            StateIndicatorSeriesOut(
                **dict(item),
                status="available" if item.indicator.last_stored_date else "no_data",
                accumulation_window=ACCUMULATION_WINDOWS[code],
            )
        )
    response.headers["Cache-Control"] = "public, max-age=300"
    return StateComparisonOut(
        indicator=build_indicator_out(session, indicator),
        accumulation_window=ACCUMULATION_WINDOWS[code],
        start_date=start_date,
        end_date=end_date,
        notes=comparison_notes(indicator, selection),
        series=series,
    )


def comparison_notes(indicator: Indicator, selection: list[GeographicUnit]) -> list[str]:
    code = indicator.code
    notes = [COMPARISON_NOTE]
    if code in YEAR_TO_DATE_CODES:
        notes.append(COMPARISON_YEAR_TO_DATE_NOTE)
    notes.append(COMPARISON_BRL_NOTE if indicator.unit == BRL_UNIT else DENOMINATOR_NOTES[code])
    if code in SIGNED_CODES:
        notes.append(SIGNED_NOTE)
    if code in PERSONNEL_CODES:
        notes.append(COMPARISON_PERSONNEL_NOTE)
    if any(geo.acronym == "DF" for geo in selection):
        notes.append(DF_NOTE)
    return notes
