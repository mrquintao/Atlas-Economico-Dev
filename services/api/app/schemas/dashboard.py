import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import GeographyOut, IndicatorOut
from app.schemas.observations import AggregationOut


class LatestValueOut(BaseModel):
    date: dt.date = Field(description="Data de referência do último valor oficial")
    value: float
    period_start: dt.date
    period_end: dt.date


class Change12mOut(BaseModel):
    """Absolute difference versus the same month one year earlier, in `change_unit`."""

    value: float = Field(description="Último valor menos o valor de 12 meses antes")
    change_unit: str
    reference_date: dt.date = Field(description="Data de referência do valor comparado")
    reference_value: float


class DashboardIndicatorOut(BaseModel):
    indicator: IndicatorOut
    status: Literal["available", "no_data"] = Field(
        description="'available' ou 'no_data' (sem valores armazenados)"
    )
    aggregation: AggregationOut = Field(
        description="Como a série foi lida para obter o último valor e a comparação em 12 meses"
    )
    latest: LatestValueOut | None
    change_12m: Change12mOut | None = Field(
        description="Ausente quando não há valor no mesmo mês do ano anterior (nunca zero)"
    )


class NationalDashboardOut(BaseModel):
    geography: GeographyOut
    indicators: list[DashboardIndicatorOut]
