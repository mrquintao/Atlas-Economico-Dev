import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import GeographyOut, IndicatorOut

AggregationMethod = Literal["none", "last_value_of_period"]


class AggregationOut(BaseModel):
    method: AggregationMethod
    description: str


class ObservationOut(BaseModel):
    date: dt.date = Field(description="Data de referência do valor oficial (ISO 8601)")
    value: float
    period_start: dt.date
    period_end: dt.date
    partial: bool = Field(
        default=False,
        description="Período ainda não encerrado (ex.: mês corrente na visão mensal)",
    )


class PointOut(BaseModel):
    date: dt.date
    value: float


class SeriesStatsOut(BaseModel):
    """Statistics over the returned range. Changes are absolute differences in `change_unit`."""

    first: PointOut
    last: PointOut
    change: float
    change_unit: str
    min: PointOut
    max: PointOut


class ObservationsResponse(BaseModel):
    indicator: IndicatorOut
    geography: GeographyOut
    unit: str
    original_frequency: str
    frequency: str
    aggregation: AggregationOut
    start_date: dt.date | None = Field(description="Início efetivo do intervalo consultado")
    end_date: dt.date | None = Field(description="Fim efetivo do intervalo consultado")
    count: int
    stats: SeriesStatsOut | None
    observations: list[ObservationOut]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
