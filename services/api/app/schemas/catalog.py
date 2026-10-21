from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    acronym: str
    name: str
    organization: str
    base_url: str
    documentation_url: str | None


class GeographyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ibge_code: str
    acronym: str
    name: str
    geographic_level: str


class GeographyListItem(GeographyOut):
    """A unit with its parent in the hierarchy (country → region → state)."""

    parent: GeographyOut | None


class IngestionRunOut(BaseModel):
    """Latest collection attempt of an indicator, whatever its outcome."""

    status: Literal["running", "success", "failed"]
    started_at: datetime
    finished_at: datetime | None
    # Only the exception type is public; the full message stays in ingestion_runs and the logs.
    error_type: str | None


class IndicatorOut(BaseModel):
    code: str
    name: str
    short_name: str
    description: str
    unit: str
    change_unit: str
    frequency: str
    geographic_level: str
    methodology: str
    methodology_version: str | None
    first_available_date: date | None
    source: SourceOut
    source_series_code: str
    source_url: str
    # Derived from stored data / ingestion log
    first_stored_date: date | None
    last_stored_date: date | None
    last_collected_at: datetime | None
    last_run: IngestionRunOut | None


class BoundaryPropertiesOut(BaseModel):
    ibge_code: str
    acronym: str
    name: str


class BoundaryFeatureOut(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str = Field(description="Código IBGE da unidade")
    properties: BoundaryPropertiesOut
    geometry: dict[str, Any] = Field(description="Polygon ou MultiPolygon (longitude, latitude)")


class BoundariesMetadataOut(BaseModel):
    source: SourceOut
    source_url: str = Field(description="Consulta oficial à API de malhas do IBGE")
    mesh_year: int = Field(description="Edição da malha (parâmetro `periodo` do IBGE)")
    quality: str = Field(description="Nível de generalização da malha do IBGE")
    coordinate_decimals: int
    simplification: str
    collected_at: datetime


class BoundariesOut(BaseModel):
    """GeoJSON FeatureCollection of official IBGE boundaries, with provenance metadata."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    metadata: BoundariesMetadataOut
    features: list[BoundaryFeatureOut]
