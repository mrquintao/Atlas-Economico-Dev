from fastapi import APIRouter, Response

from app.api.errors import ApiError
from app.api.v1.catalog import DbSession, build_indicator_out, national_geography
from app.models import Frequency
from app.repositories import catalog as catalog_repo
from app.schemas.catalog import GeographyOut
from app.schemas.dashboard import (
    Change12mOut,
    DashboardIndicatorOut,
    LatestValueOut,
    NationalDashboardOut,
)
from app.schemas.observations import AggregationOut
from app.services.dashboard import (
    NATIONAL_DASHBOARD_CODES,
    latest_summary,
    summary_frequency,
)
from app.services.observations import AGGREGATION_DESCRIPTIONS

router = APIRouter()


@router.get("/dashboard/national", tags=["dashboard"])
def get_national_dashboard(session: DbSession, response: Response) -> NationalDashboardOut:
    """Latest official value and 12-month change of each national dashboard indicator."""
    geo = national_geography(session)
    items: list[DashboardIndicatorOut] = []
    for code in NATIONAL_DASHBOARD_CODES:
        indicator = catalog_repo.get_indicator(session, code)
        if indicator is None:
            raise ApiError(500, "catalog_not_seeded", f"Indicador '{code}' não cadastrado.")
        indicator_out = build_indicator_out(session, indicator)
        original = Frequency(indicator.frequency)
        summary = latest_summary(
            session,
            indicator_id=indicator.id,
            geographic_unit_id=geo.id,
            original_frequency=original,
            first_stored_date=indicator_out.first_stored_date,
            last_stored_date=indicator_out.last_stored_date,
        )
        method = "none" if summary_frequency(original) == original else "last_value_of_period"
        items.append(
            DashboardIndicatorOut(
                indicator=indicator_out,
                status="available" if summary else "no_data",
                aggregation=AggregationOut(
                    method=method,  # type: ignore[arg-type]
                    description=AGGREGATION_DESCRIPTIONS[method],
                ),
                latest=None
                if summary is None
                else LatestValueOut(
                    date=summary.latest.reference_date,
                    value=summary.latest.value,
                    period_start=summary.latest.period_start,
                    period_end=summary.latest.period_end,
                ),
                change_12m=None
                if summary is None or summary.year_ago is None
                else Change12mOut(
                    value=summary.latest.value - summary.year_ago.value,
                    change_unit=indicator.change_unit,
                    reference_date=summary.year_ago.reference_date,
                    reference_value=summary.year_ago.value,
                ),
            )
        )
    response.headers["Cache-Control"] = "public, max-age=300"
    return NationalDashboardOut(geography=GeographyOut.model_validate(geo), indicators=items)
