from datetime import date, datetime

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
