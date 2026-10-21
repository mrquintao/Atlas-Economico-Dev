import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import GeographyOut
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
    change_note: str = Field(description="Base e unidade da comparação com o ano anterior")


class StateDashboardOut(BaseModel):
    geography: GeographyOut
    notes: list[str] = Field(description=NOTES_DESCRIPTION)
    indicators: list[StateDashboardIndicatorOut]
