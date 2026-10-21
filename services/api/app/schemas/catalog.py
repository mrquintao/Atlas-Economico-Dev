from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
