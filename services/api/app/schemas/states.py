import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import GeographyOut, IndicatorOut
from app.schemas.dashboard import DashboardIndicatorOut
from app.schemas.observations import ObservationsResponse

NOTES_DESCRIPTION = "Ressalvas de comparabilidade da UF (ex.: Distrito Federal)"


class StateIndicatorSeriesOut(ObservationsResponse):
    """One state indicator in the UF: catalog metadata, availability and the filtered series."""

    status: Literal["available", "no_data"] = Field(
        description="'available' ou 'no_data' (nenhum valor armazenado para a UF)"
    )
    accumulation_window: str = Field(description="Janela de acumulação do valor publicado")


class StateIndicatorsOut(BaseModel):
    geography: GeographyOut
    start_date: dt.date | None = Field(description="Filtro inicial pedido")
    end_date: dt.date | None = Field(description="Filtro final pedido")
    notes: list[str] = Field(description=NOTES_DESCRIPTION)
    indicators: list[StateIndicatorSeriesOut]


class StateDashboardIndicatorOut(DashboardIndicatorOut):
    accumulation_window: str = Field(description="Janela de acumulação do valor publicado")
    change_note: str | None = Field(
        description="Base e unidade da comparação com o ano anterior (nula sem comparação)"
    )


class StateDashboardOut(BaseModel):
    geography: GeographyOut
    notes: list[str] = Field(description=NOTES_DESCRIPTION)
    indicators: list[StateDashboardIndicatorOut]


class StateMapValueOut(BaseModel):
    geography: GeographyOut
    status: Literal["available", "no_data"] = Field(
        description="'no_data': a UF não tem valor publicado neste período (nunca é zero)"
    )
    value: float | None = Field(description="Valor publicado no período; nulo sem dado")


class StateMapPeriodOut(BaseModel):
    reference_date: dt.date
    period_start: dt.date
    period_end: dt.date
    coverage: int = Field(description="Número de UFs com valor publicado no período")


class StateMapOut(BaseModel):
    """One indicator in the 27 UFs at a single reference period (cross-section for the map)."""

    indicator: IndicatorOut
    accumulation_window: str = Field(description="Janela de acumulação do valor publicado")
    scale: Literal["sequential", "diverging"] = Field(
        description="'diverging' (centrada em zero) para indicadores que podem ser negativos; "
        "propriedade do catálogo, não dos valores do período"
    )
    period: StateMapPeriodOut | None = Field(
        description="Período exibido, o mesmo para todas as UFs; nulo se não há dados"
    )
    default_rule: str = Field(description="Como o período padrão é escolhido")
    available_periods: list[StateMapPeriodOut] = Field(
        description="Períodos com ao menos uma UF com valor, do mais recente ao mais antigo"
    )
    notes: list[str] = Field(description="Ressalvas de comparabilidade entre UFs")
    states: list[StateMapValueOut] = Field(description="As 27 UFs, em ordem de sigla")
