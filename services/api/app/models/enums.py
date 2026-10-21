from enum import StrEnum


class Frequency(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"  # RREO bimester
    QUARTERLY = "quarterly"
    FOUR_MONTHLY = "four_monthly"  # RGF four-month period
    ANNUAL = "annual"


class GeographicLevel(StrEnum):
    COUNTRY = "country"
    REGION = "region"
    STATE = "state"
    MUNICIPALITY = "municipality"


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
