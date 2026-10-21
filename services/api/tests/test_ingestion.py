"""Ingestion tests against PostgreSQL with mocked SGS responses (synthetic values)."""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.series_ingestion import IngestionError, ingest_sgs_indicator
from app.integrations.bcb.sgs import (
    SGSClient,
    SGSUnavailableError,
    format_sgs_date,
    parse_sgs_date,
)
from app.models import IngestionRun, Observation, ObservationRevision
from tests.conftest import sgs_json

TODAY = date(2024, 1, 10)


class FakeSGS:
    """Serves synthetic daily values from a dict, honouring the requested window."""

    def __init__(self, values: dict[date, str | None]) -> None:
        self.values = values
        self.requests: list[tuple[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        start = request.url.params["dataInicial"]
        end = request.url.params["dataFinal"]
        self.requests.append((start, end))
        lo, hi = parse_sgs_date(start), parse_sgs_date(end)
        points = [(format_sgs_date(d), v) for d, v in sorted(self.values.items()) if lo <= d <= hi]
        return sgs_json(points)


def client_for(settings: Settings, fake) -> SGSClient:
    return SGSClient(settings, transport=httpx.MockTransport(fake), sleep=lambda _: None)


def daily(start: date, days: int, value: str) -> dict[date, str | None]:
    return {start + timedelta(days=i): value for i in range(days)}


def count_obs(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Observation)) or 0


@pytest.fixture
def ingest(db: Session, settings: Settings):
    def run(fake, **kwargs):
        kwargs.setdefault("today", TODAY)
        return ingest_sgs_indicator(db, client_for(settings, fake), "SELIC_TARGET", **kwargs)

    return run


def test_inserts_observations_and_logs_run(db: Session, ingest) -> None:
    fake = FakeSGS(daily(date(2024, 1, 1), 10, "11.75"))
    summary = ingest(fake, start=date(2024, 1, 1))

    assert (summary.status, summary.received, summary.inserted) == ("success", 10, 10)
    assert count_obs(db) == 10
    obs = db.scalar(select(Observation).where(Observation.reference_date == date(2024, 1, 5)))
    assert obs is not None
    assert obs.value == Decimal("11.75")
    assert obs.source_reference == "bcdata.sgs.432"
    assert obs.period_start == obs.period_end == date(2024, 1, 5)

    run = db.get_one(IngestionRun, summary.run_id)
    assert run.status == "success"
    assert run.records_inserted == 10
    assert run.finished_at is not None
    assert run.metadata_json["windows"][0]["payload_sha256"]


def test_rerun_is_idempotent(db: Session, ingest) -> None:
    fake = FakeSGS(daily(date(2024, 1, 1), 10, "11.75"))
    ingest(fake, start=date(2024, 1, 1))
    second = ingest(fake, start=date(2024, 1, 1))

    assert (second.inserted, second.updated, second.unchanged) == (0, 0, 10)
    assert count_obs(db) == 10
    assert db.scalar(select(func.count()).select_from(ObservationRevision)) == 0


def test_detects_and_records_revisions(db: Session, ingest) -> None:
    values = daily(date(2024, 1, 1), 5, "11.75")
    ingest(FakeSGS(values), start=date(2024, 1, 1))
    values[date(2024, 1, 3)] = "12.25"
    summary = ingest(FakeSGS(values), start=date(2024, 1, 1))

    assert (summary.inserted, summary.updated, summary.unchanged) == (0, 1, 4)
    revision = db.scalar(select(ObservationRevision))
    assert revision is not None
    assert (revision.previous_value, revision.new_value) == (Decimal("11.75"), Decimal("12.25"))
    assert revision.ingestion_run_id == summary.run_id


def test_never_stores_dates_after_collection_date(db: Session, ingest) -> None:
    # SGS 432 pre-publishes the target until the next Copom meeting.
    fake = FakeSGS(daily(date(2024, 1, 8), 10, "11.75"))
    summary = ingest(fake, start=date(2024, 1, 8), end=date(2024, 1, 31))

    assert fake.requests[-1][1] == format_sgs_date(TODAY)  # dataFinal clamped to today
    assert summary.inserted == 3
    assert db.scalar(select(func.max(Observation.reference_date))) == TODAY


def test_skips_null_values_instead_of_storing_zero(db: Session, ingest) -> None:
    values = daily(date(2024, 1, 1), 3, "11.75")
    values[date(2024, 1, 2)] = ""
    summary = ingest(FakeSGS(values), start=date(2024, 1, 1))

    assert summary.inserted == 2
    assert summary.skipped_null == 1
    stored = db.scalars(select(Observation.reference_date).order_by(Observation.reference_date))
    assert list(stored) == [date(2024, 1, 1), date(2024, 1, 3)]


def test_incremental_run_starts_before_last_stored_date(db: Session, ingest) -> None:
    ingest(FakeSGS(daily(date(2023, 1, 1), 365, "13.75")), start=date(2023, 1, 1))
    fake = FakeSGS(daily(date(2023, 1, 1), 375, "13.75"))
    summary = ingest(fake)  # no start: incremental

    assert summary.start == date(2023, 12, 31) - timedelta(days=90)
    assert summary.inserted == 10
    assert count_obs(db) == 375


def test_full_run_starts_at_first_available_date(db: Session, ingest) -> None:
    summary = ingest(FakeSGS({}), full=True)
    assert summary.start == date(1999, 3, 5)
    assert summary.inserted == 0


def test_failure_keeps_previous_data_and_records_failed_run(
    db: Session, ingest, settings: Settings
) -> None:
    ingest(FakeSGS(daily(date(2024, 1, 1), 5, "11.75")), start=date(2024, 1, 1))

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    with pytest.raises(SGSUnavailableError):
        ingest(broken, start=date(2024, 1, 1))

    assert count_obs(db) == 5
    failed = db.scalar(select(IngestionRun).order_by(IngestionRun.id.desc()))
    assert failed is not None
    assert failed.status == "failed"
    assert "ConnectError" in (failed.error_message or "")
    assert failed.finished_at is not None


def test_partial_failure_is_atomic(db: Session, ingest, settings: Settings) -> None:
    """If a later window fails, earlier windows of the same run are not persisted."""
    good = FakeSGS(daily(date(2022, 1, 1), 800, "9.25"))

    def flaky(request: httpx.Request) -> httpx.Response:
        if request.url.params["dataInicial"] == "01/01/2022":
            return good(request)
        return httpx.Response(503)

    with pytest.raises(SGSUnavailableError):
        ingest_sgs_indicator(
            db,
            client_for(settings.model_copy(update={"bcb_daily_window_years": 1}), flaky),
            "SELIC_TARGET",
            start=date(2022, 1, 1),
            today=date(2024, 3, 1),
        )
    assert count_obs(db) == 0


def test_unknown_indicator(db: Session, ingest) -> None:
    with pytest.raises(IngestionError):
        ingest_sgs_indicator(db, client_for(Settings(), FakeSGS({})), "NOPE")


def test_reports_stored_dates_missing_from_source(db: Session, ingest) -> None:
    ingest(FakeSGS(daily(date(2024, 1, 1), 5, "11.75")), start=date(2024, 1, 1))
    values = daily(date(2024, 1, 1), 5, "11.75")
    del values[date(2024, 1, 5)]
    summary = ingest(FakeSGS(values), start=date(2024, 1, 1))

    assert summary.status == "success"
    assert summary.missing_from_source == ["2024-01-05"]
    assert count_obs(db) == 5  # kept, not silently deleted
    run = db.get_one(IngestionRun, summary.run_id)
    assert run.metadata_json["missing_from_source"] == ["2024-01-05"]


def test_empty_response_for_stored_range_is_a_failure(db: Session, ingest) -> None:
    # An outage answering "no data" must not count as a successful collection.
    ingest(FakeSGS(daily(date(2024, 1, 1), 3, "11.75")), start=date(2024, 1, 1))
    with pytest.raises(IngestionError, match=r"no records .* 3 stored observations") as info:
        ingest(FakeSGS({}), start=date(2024, 1, 1))
    assert count_obs(db) == 3  # stored data kept
    runs = db.scalars(select(IngestionRun).order_by(IngestionRun.id)).all()
    assert [r.status for r in runs] == ["success", "failed"]
    assert info.value.ingestion_run_id == runs[1].id  # type: ignore[attr-defined]


def test_empty_response_without_stored_data_is_not_a_failure(db: Session, ingest) -> None:
    summary = ingest(FakeSGS({}), start=date(2024, 1, 1))
    assert summary.status == "success"
    assert summary.received == 0


def test_default_collection_date_uses_brasilia_time(
    db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.ingestion.series_ingestion as module

    monkeypatch.setattr(module, "brazil_today", lambda: date(2024, 1, 5))
    fake = FakeSGS(daily(date(2024, 1, 1), 10, "11.75"))
    summary = ingest_sgs_indicator(
        db, client_for(settings, fake), "SELIC_TARGET", start=date(2024, 1, 1)
    )
    assert summary.end == date(2024, 1, 5)
    assert summary.inserted == 5


def test_original_error_survives_failure_to_record_the_run(
    db: Session, ingest, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.ingestion.series_ingestion as module

    def database_down(*_: object) -> None:
        raise RuntimeError("database down")

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    monkeypatch.setattr(module, "_finish", database_down)
    with pytest.raises(SGSUnavailableError):
        ingest(broken, start=date(2024, 1, 1))


# --- Monthly series (DBGG_GDP, SGS 13762). Synthetic values. ---


def monthly(values: dict[tuple[int, int], str]) -> dict[date, str | None]:
    return {date(y, m, 1): v for (y, m), v in values.items()}


@pytest.fixture
def ingest_dbgg(db: Session, settings: Settings):
    def run(fake, **kwargs):
        kwargs.setdefault("today", date(2024, 10, 21))
        return ingest_sgs_indicator(db, client_for(settings, fake), "DBGG_GDP", **kwargs)

    return run


def test_monthly_observation_covers_the_whole_month(db: Session, ingest_dbgg) -> None:
    fake = FakeSGS(monthly({(2024, 1): "74.47", (2024, 2): "74.81"}))
    summary = ingest_dbgg(fake, full=True)

    assert summary.inserted == 2
    feb = db.scalar(select(Observation).where(Observation.reference_date == date(2024, 2, 1)))
    assert feb is not None
    assert (feb.period_start, feb.period_end) == (date(2024, 2, 1), date(2024, 2, 29))
    assert feb.value == Decimal("74.81")
    assert feb.source_reference == "bcdata.sgs.13762"


def test_monthly_series_is_requested_in_a_single_window(db: Session, ingest_dbgg) -> None:
    fake = FakeSGS(monthly({(2006, 12): "55.48", (2024, 8): "77.36"}))
    ingest_dbgg(fake, full=True)
    assert fake.requests == [("01/12/2006", "21/10/2024")]


def test_monthly_incremental_run_refetches_full_history(db: Session, ingest_dbgg) -> None:
    """GDP revisions can change the ratio years back, so every run re-reads everything."""
    values = monthly({(2006, 12): "55.48", (2015, 12): "65.50", (2024, 8): "77.36"})
    ingest_dbgg(FakeSGS(values))
    values[date(2015, 12, 1)] = "65.61"  # e.g. GDP revised by IBGE
    summary = ingest_dbgg(FakeSGS(values))  # no start/full: incremental

    assert summary.start == date(2006, 12, 1)
    assert (summary.inserted, summary.updated, summary.unchanged) == (0, 1, 2)
    revision = db.scalar(select(ObservationRevision))
    assert revision is not None
    assert (revision.previous_value, revision.new_value) == (Decimal("65.50"), Decimal("65.61"))


def test_monthly_date_not_on_first_day_is_rejected(db: Session, ingest_dbgg) -> None:
    fake = FakeSGS({date(2024, 1, 15): "74.47"})
    with pytest.raises(IngestionError, match="not on the 1st"):
        ingest_dbgg(fake, full=True)
    assert count_obs(db) == 0


def test_frequency_without_incremental_policy_fails_clearly(
    db: Session, ingest_dbgg, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.ingestion.series_ingestion as module

    monkeypatch.setattr(module, "INCREMENTAL_OVERLAP", {})
    with pytest.raises(IngestionError, match="No incremental policy"):
        ingest_dbgg(FakeSGS({}))
