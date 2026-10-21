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


class StateRankingItemOut(BaseModel):
    position: int = Field(
        description="Posição na ordem pedida; valores iguais dividem a posição (1, 2, 2, 4)"
    )
    geography: GeographyOut
    value: float = Field(description="Valor publicado no período")


class StateRankingOut(BaseModel):
    """UFs ordered by one indicator at a single reference period; absences stay out (S8)."""

    indicator: IndicatorOut
    accumulation_window: str = Field(description="Janela de acumulação do valor publicado")
    metric_kind: Literal["relative", "absolute"] = Field(
        description="'relative': percentual da RCL publicado pela UF, comparável entre portes; "
        "'absolute': valor em R$, que reflete o tamanho de cada UF"
    )
    order: Literal["desc", "asc"] = Field(description="'desc': do maior para o menor")
    order_note: str = Field(description="Como a posição é definida (sem juízo de desempenho)")
    period: StateMapPeriodOut | None = Field(
        description="Período exibido, o mesmo para todas as UFs; nulo se não há dados"
    )
    default_rule: str = Field(description="Como o período padrão é escolhido")
    available_periods: list[StateMapPeriodOut] = Field(
        description="Períodos com ao menos uma UF com valor (entre as 27), do mais recente ao "
        "mais antigo"
    )
    selected_count: int = Field(description="Número de UFs selecionadas")
    ranked_count: int = Field(description="UFs selecionadas com valor no período")
    ranking: list[StateRankingItemOut] = Field(description="UFs com valor, na ordem pedida")
    missing: list[GeographyOut] = Field(
        description="UFs selecionadas sem valor no período, fora da classificação (nunca zero)"
    )
    missing_note: str | None = Field(description="Aviso sobre as UFs sem dado; nulo sem ausências")
    notes: list[str] = Field(description="Ressalvas de leitura e de comparabilidade")


class StateComparisonOut(BaseModel):
    """Series of one state indicator in a few UFs, each as published (S8)."""

    indicator: IndicatorOut
    accumulation_window: str = Field(description="Janela de acumulação do valor publicado")
    start_date: dt.date | None = Field(description="Filtro inicial pedido")
    end_date: dt.date | None = Field(description="Filtro final pedido")
    notes: list[str] = Field(description="Ressalvas de leitura e de comparabilidade")
    series: list[StateIndicatorSeriesOut] = Field(description="Uma série por UF, na ordem pedida")
