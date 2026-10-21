"""API tests against PostgreSQL. Observation values are synthetic and inserted directly."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import GeographicUnit, Indicator, IngestionRun, Observation


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def selic(db: Session) -> Indicator:
    indicator = db.scalar(select(Indicator).where(Indicator.code == "SELIC_TARGET"))
    assert indicator is not None
    return indicator


@pytest.fixture
def seeded(db: Session, selic: Indicator) -> None:
    """Synthetic daily series 2024-01-25..2024-03-10: 11.75 until 31/01, then 11.25."""
    brazil = db.scalar(select(GeographicUnit).where(GeographicUnit.acronym == "BR"))
    assert brazil is not None
    now = datetime.now(UTC)
    start = date(2024, 1, 25)
    for offset in range((date(2024, 3, 10) - start).days + 1):
        day = start + timedelta(days=offset)
        db.add(
            Observation(
                indicator_id=selic.id,
                geographic_unit_id=brazil.id,
                reference_date=day,
                period_start=day,
                period_end=day,
                value=Decimal("11.75") if day <= date(2024, 1, 31) else Decimal("11.25"),
                collected_at=now,
                source_reference="test",
            )
        )
    db.add(
        IngestionRun(
            source_id=selic.source_id,
            indicator_id=selic.id,
            status="success",
            finished_at=now,
            records_received=0,
            records_inserted=0,
            records_updated=0,
            records_unchanged=0,
        )
    )
    db.flush()


URL = "/api/v1/indicators/SELIC_TARGET/observations"


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}


def test_openapi_is_available(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "/api/v1/indicators/{code}/observations" in spec["paths"]


def test_lists_catalog(client: TestClient) -> None:
    codes = [i["code"] for i in client.get("/api/v1/indicators").json()]
    assert "SELIC_TARGET" in codes
    assert client.get("/api/v1/sources").json()[0]["acronym"] == "BCB"
    assert client.get("/api/v1/geographies").json()[0]["acronym"] == "BR"


def test_indicator_metadata(client: TestClient, seeded: None) -> None:
    body = client.get("/api/v1/indicators/selic_target").json()
    assert body["code"] == "SELIC_TARGET"
    assert body["source_series_code"] == "432"
    assert body["unit"] == "% a.a."
    assert body["change_unit"] == "p.p."
    assert body["source_url"].startswith("https://dadosabertos.bcb.gov.br/")
    assert body["last_stored_date"] == "2024-03-10"
    assert body["last_collected_at"] is not None


def test_unknown_indicator_returns_consistent_error(client: TestClient) -> None:
    response = client.get("/api/v1/indicators/NOPE")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "indicator_not_found"


def test_filters_by_date_range_inclusive(client: TestClient, seeded: None) -> None:
    body = client.get(URL, params={"start_date": "2024-01-30", "end_date": "2024-02-02"}).json()
    assert body["count"] == 4
    assert [o["date"] for o in body["observations"]] == [
        "2024-01-30",
        "2024-01-31",
        "2024-02-01",
        "2024-02-02",
    ]
    assert body["aggregation"]["method"] == "none"
    assert body["frequency"] == body["original_frequency"] == "daily"
    assert body["unit"] == "% a.a."


def test_stats_report_change_in_percentage_points(client: TestClient, seeded: None) -> None:
    stats = client.get(URL, params={"start_date": "2024-01-30", "end_date": "2024-02-02"}).json()[
        "stats"
    ]
    assert stats["first"] == {"date": "2024-01-30", "value": 11.75}
    assert stats["last"] == {"date": "2024-02-02", "value": 11.25}
    assert stats["change"] == pytest.approx(-0.5)
    assert stats["change_unit"] == "p.p."
    assert stats["min"]["date"] == "2024-02-01"
    assert stats["max"]["date"] == "2024-01-30"


def test_monthly_uses_last_value_of_each_month(client: TestClient, seeded: None) -> None:
    body = client.get(URL, params={"frequency": "monthly"}).json()
    assert body["aggregation"]["method"] == "last_value_of_period"
    assert "último valor" in body["aggregation"]["description"]
    assert [(o["date"], o["value"], o["partial"]) for o in body["observations"]] == [
        ("2024-01-31", 11.75, True),  # data only starts on 25/01
        ("2024-02-29", 11.25, False),
        ("2024-03-10", 11.25, True),  # month still running at the last stored date
    ]
    assert body["observations"][1]["period_start"] == "2024-02-01"
    assert body["observations"][1]["period_end"] == "2024-02-29"
    assert body["start_date"] == "2024-01-01"


def test_monthly_marks_month_cut_by_end_date_as_partial(client: TestClient, seeded: None) -> None:
    body = client.get(URL, params={"frequency": "monthly", "end_date": "2024-02-15"}).json()
    assert body["observations"][-1] == {
        "date": "2024-02-15",
        "value": 11.25,
        "period_start": "2024-02-01",
        "period_end": "2024-02-29",
        "partial": True,
    }


def test_empty_range_returns_no_values_not_zeros(client: TestClient, seeded: None) -> None:
    body = client.get(URL, params={"start_date": "2010-01-01", "end_date": "2010-12-31"}).json()
    assert body["count"] == 0
    assert body["observations"] == []
    assert body["stats"] is None


def test_rejects_inverted_range(client: TestClient) -> None:
    response = client.get(URL, params={"start_date": "2024-02-01", "end_date": "2024-01-01"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_range"


@pytest.mark.parametrize(
    "params",
    [{"start_date": "01/01/2024"}, {"end_date": "2024-13-01"}, {"frequency": "weekly"}],
)
def test_rejects_invalid_parameters(client: TestClient, params: dict[str, str]) -> None:
    response = client.get(URL, params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_national_series_is_not_served_for_a_state(client: TestClient, db: Session) -> None:
    brazil = db.scalar(select(GeographicUnit).where(GeographicUnit.acronym == "BR"))
    assert brazil is not None
    db.add(
        GeographicUnit(
            ibge_code="31",
            acronym="MG",
            name="Minas Gerais",
            geographic_level="state",
            parent_id=brazil.id,
        )
    )
    db.flush()
    response = client.get(URL, params={"geography": "MG"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "geography_not_available"


def test_unknown_geography(client: TestClient) -> None:
    response = client.get(URL, params={"geography": "XX"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "geography_not_found"


def test_cors_allows_configured_frontend(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    blocked = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in blocked.headers


def test_monthly_marks_month_cut_by_start_date_as_partial(client: TestClient, seeded: None) -> None:
    body = client.get(URL, params={"frequency": "monthly", "start_date": "2024-02-15"}).json()
    assert body["start_date"] == "2024-02-15"  # never earlier than requested
    assert body["observations"][0]["period_start"] == "2024-02-01"
    assert body["observations"][0]["partial"] is True


def test_monthly_marks_first_stored_month_as_partial(client: TestClient, seeded: None) -> None:
    # Synthetic data starts on 25/01, so January is not fully covered.
    body = client.get(URL, params={"frequency": "monthly"}).json()
    assert body["observations"][0]["partial"] is True
    assert body["observations"][1]["partial"] is False


@pytest.fixture
def dbgg_seeded(db: Session) -> None:
    """Synthetic monthly series Jan..Mar 2024 for DBGG_GDP."""
    indicator = db.scalar(select(Indicator).where(Indicator.code == "DBGG_GDP"))
    brazil = db.scalar(select(GeographicUnit).where(GeographicUnit.acronym == "BR"))
    assert indicator is not None and brazil is not None
    now = datetime.now(UTC)
    for month, value, end in [(1, "74.47", 31), (2, "74.81", 29), (3, "75.02", 31)]:
        db.add(
            Observation(
                indicator_id=indicator.id,
                geographic_unit_id=brazil.id,
                reference_date=date(2024, month, 1),
                period_start=date(2024, month, 1),
                period_end=date(2024, month, end),
                value=Decimal(value),
                collected_at=now,
                source_reference="test",
            )
        )
    db.flush()


DBGG_URL = "/api/v1/indicators/DBGG_GDP/observations"


def test_dbgg_metadata(client: TestClient) -> None:
    body = client.get("/api/v1/indicators/DBGG_GDP").json()
    assert body["source_series_code"] == "13762"
    assert body["unit"] == "% do PIB"
    assert body["change_unit"] == "p.p."
    assert body["frequency"] == "monthly"
    assert body["first_available_date"] == "2006-12-01"
    assert "SGS 4537" in body["methodology"]  # warns against mixing methodologies


def test_monthly_series_is_served_without_aggregation(
    client: TestClient, dbgg_seeded: None
) -> None:
    for frequency in ("original", "monthly"):
        body = client.get(DBGG_URL, params={"frequency": frequency}).json()
        assert body["aggregation"]["method"] == "none"
        assert body["frequency"] == "monthly"
        assert [(o["date"], o["period_end"], o["partial"]) for o in body["observations"]] == [
            ("2024-01-01", "2024-01-31", False),
            ("2024-02-01", "2024-02-29", False),
            ("2024-03-01", "2024-03-31", False),
        ]
        assert body["stats"]["change"] == pytest.approx(0.55)
        assert body["stats"]["change_unit"] == "p.p."


def test_monthly_series_cannot_be_converted_to_daily(client: TestClient) -> None:
    response = client.get(DBGG_URL, params={"frequency": "daily"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "frequency_not_supported"


def test_catalog_lists_both_indicators(client: TestClient) -> None:
    codes = [i["code"] for i in client.get("/api/v1/indicators").json()]
    assert codes == ["DBGG_GDP", "SELIC_TARGET"]


# --- Unknown query parameters (issue #3) ---


@pytest.mark.parametrize(
    ("url", "params"),
    [
        (URL, {"start": "2030-01-01"}),  # typo of start_date: used to return the whole series
        (URL, {"start_date": "2024-01-01", "foo": "1"}),
        ("/api/v1/indicators", {"page": "2"}),
        ("/api/v1/health", {"verbose": "true"}),
    ],
)
def test_unknown_query_parameters_are_rejected(
    client: TestClient, url: str, params: dict[str, str]
) -> None:
    response = client.get(url, params=params)
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "unknown_parameter"
    known = {"start_date", "end_date", "geography", "frequency"}
    assert body["details"]["unknown"] == sorted(set(params) - known)


def test_known_query_parameters_still_accepted(client: TestClient, seeded: None) -> None:
    params = {"start_date": "2024-02-01", "end_date": "2024-02-02", "geography": "BR",
              "frequency": "original"}
    assert client.get(URL, params=params).status_code == 200


def test_docs_and_openapi_unaffected(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


# --- Monthly series are filtered by reference-period overlap (issue #3) ---


def test_monthly_series_includes_month_overlapping_start(
    client: TestClient, dbgg_seeded: None
) -> None:
    # Jan/2024 covers 01–31/01: a range starting on 15/01 overlaps it.
    body = client.get(DBGG_URL, params={"start_date": "2024-01-15"}).json()
    assert [o["date"] for o in body["observations"]] == ["2024-01-01", "2024-02-01", "2024-03-01"]
    assert body["start_date"] == "2024-01-15"  # effective start never earlier than requested


def test_monthly_series_includes_month_overlapping_end(
    client: TestClient, dbgg_seeded: None
) -> None:
    body = client.get(DBGG_URL, params={"end_date": "2024-02-15"}).json()
    assert [o["date"] for o in body["observations"]] == ["2024-01-01", "2024-02-01"]


def test_monthly_series_excludes_months_outside_range(
    client: TestClient, dbgg_seeded: None
) -> None:
    body = client.get(DBGG_URL, params={"start_date": "2024-02-01", "end_date": "2024-02-29"}).json()
    assert [o["date"] for o in body["observations"]] == ["2024-02-01"]


def test_daily_series_filtering_is_unchanged(client: TestClient, seeded: None) -> None:
    body = client.get(URL, params={"start_date": "2024-02-15", "end_date": "2024-02-16"}).json()
    assert [o["date"] for o in body["observations"]] == ["2024-02-15", "2024-02-16"]
