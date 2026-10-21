from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from app.api.errors import ApiError
from app.api.v1.catalog import DbSession, build_indicator_out, get_indicator_or_404
from app.ingestion.fiscal_catalog import YEAR_TO_DATE_CODES
from app.models import Frequency
from app.repositories import catalog as catalog_repo
from app.repositories.observations import ObservationRow
from app.schemas.catalog import GeographyOut
from app.schemas.observations import (
    AggregationOut,
    ErrorResponse,
    ObservationOut,
    ObservationsResponse,
    PointOut,
    SeriesStatsOut,
)
from app.services.observations import (
    AGGREGATION_DESCRIPTIONS,
    FrequencyNotSupportedError,
    compute_stats,
    load_series,
)

router = APIRouter()


@router.get(
    "/indicators/{code}/observations",
    tags=["observations"],
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def get_observations(
    code: str,
    session: DbSession,
    response: Response,
    start_date: Annotated[date | None, Query(description="Data inicial (YYYY-MM-DD)")] = None,
    end_date: Annotated[date | None, Query(description="Data final (YYYY-MM-DD)")] = None,
    geography: Annotated[
        str, Query(description="Sigla ou código IBGE da unidade geográfica")
    ] = "BR",
    frequency: Annotated[
        Literal["original", "daily", "monthly"],
        Query(description="'original' preserva a frequência da fonte"),
    ] = "original",
) -> ObservationsResponse:
    if start_date and end_date and start_date > end_date:
        raise ApiError(422, "invalid_range", "start_date deve ser anterior ou igual a end_date.")

    indicator = get_indicator_or_404(session, code)
    # Prefer a unit at the indicator's own level ("SE" is a state and a region; "1" is Brasil and
    # a region); any other match only feeds the geography_not_available error below.
    geo = catalog_repo.get_geography(
        session, geography, indicator.geographic_level
    ) or catalog_repo.get_geography(session, geography)
    if geo is None:
        raise ApiError(
            404, "geography_not_found", f"Unidade geográfica '{geography}' não encontrada."
        )
    if geo.geographic_level != indicator.geographic_level:
        # Never serve a national series as if it were a state (or other level) indicator.
        raise ApiError(
            422,
            "geography_not_available",
            f"O indicador {indicator.code} é publicado apenas no nível "
            f"'{indicator.geographic_level}', não para '{geo.acronym}'.",
        )

    original = Frequency(indicator.frequency)
    target = original if frequency == "original" else Frequency(frequency)
    first_stored, last_stored = catalog_repo.observation_bounds(session, indicator.id, geo.id)
    try:
        series = load_series(
            session,
            indicator_id=indicator.id,
            geographic_unit_id=geo.id,
            original_frequency=original,
            target_frequency=target,
            start=start_date,
            end=end_date,
            first_stored_date=first_stored,
            last_stored_date=last_stored,
        )
    except FrequencyNotSupportedError as exc:
        raise ApiError(422, "frequency_not_supported", str(exc)) from exc

    # Year-to-date flows restart every January: a change or extreme across periods would compare
    # non-comparable values (e.g. a 1st bimester with a 6th), so no statistics are served.
    stats = None if indicator.code in YEAR_TO_DATE_CODES else compute_stats(series.rows)
    response.headers["Cache-Control"] = "public, max-age=300"
    return ObservationsResponse(
        indicator=build_indicator_out(session, indicator, geo),
        geography=GeographyOut.model_validate(geo),
        unit=indicator.unit,
        original_frequency=original,
        frequency=target,
        aggregation=AggregationOut(
            method=series.aggregation,  # type: ignore[arg-type]
            description=AGGREGATION_DESCRIPTIONS[series.aggregation],
        ),
        # Effective range covered by the returned reference periods, clipped to the request:
        # from the first period's start to the last period's end (or, for a partial last
        # period, its last available date).
        start_date=effective_start(series.rows, start_date),
        end_date=effective_end(series.rows, series.partial_flags, end_date),
        count=len(series.rows),
        stats=None
        if stats is None
        else SeriesStatsOut(
            first=PointOut(date=stats.first.reference_date, value=stats.first.value),
            last=PointOut(date=stats.last.reference_date, value=stats.last.value),
            change=stats.change,
            change_unit=indicator.change_unit,
            min=PointOut(date=stats.min.reference_date, value=stats.min.value),
            max=PointOut(date=stats.max.reference_date, value=stats.max.value),
        ),
        observations=[
            ObservationOut(
                date=row.reference_date,
                value=row.value,
                period_start=row.period_start,
                period_end=row.period_end,
                partial=partial,
            )
            for row, partial in zip(series.rows, series.partial_flags, strict=True)
        ],
    )


def effective_start(rows: list[ObservationRow], requested: date | None) -> date | None:
    if not rows:
        return requested
    first = rows[0].period_start
    return max(first, requested) if requested else first


def effective_end(
    rows: list[ObservationRow], partial: list[bool], requested: date | None
) -> date | None:
    if not rows:
        return requested
    last = rows[-1].reference_date if partial[-1] else rows[-1].period_end
    return min(last, requested) if requested else last
