"""National dashboard endpoint tests. Observation values are synthetic and inserted directly."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import GeographicUnit, Indicator, Observation

URL = "/api/v1/dashboard/national"


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def add(db: Session, code: str, rows: list[tuple[date, date, date, str]]) -> None:
    """Insert (reference_date, period_start, period_end, value) rows for an indicator."""
    indicator = db.scalar(select(Indicator).where(Indicator.code == code))
    brazil = db.scalar(select(GeographicUnit).where(GeographicUnit.acronym == "BR"))
    assert indicator is not None and brazil is not None
    now = datetime.now(UTC)
    for reference, start, end, value in rows:
        db.add(
            Observation(
                indicator_id=indicator.id,
                geographic_unit_id=brazil.id,
                reference_date=reference,
                period_start=start,
                period_end=end,
                value=Decimal(value),
                collected_at=now,
                source_reference="test",
            )
        )
    db.flush()


def daily(day: date, value: str) -> tuple[date, date, date, str]:
    return (day, day, day, value)


def monthly(year: int, month: int, last_day: int, value: str) -> tuple[date, date, date, str]:
    return (date(year, month, 1), date(year, month, 1), date(year, month, last_day), value)


def by_code(body: dict) -> dict[str, dict]:
    return {item["indicator"]["code"]: item for item in body["indicators"]}


def test_lists_the_three_indicators_in_order_without_zeros(client: TestClient) -> None:
    response = client.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert body["geography"]["acronym"] == "BR"
    assert [i["indicator"]["code"] for i in body["indicators"]] == [
        "SELIC_TARGET",
        "DBGG_GDP",
        "IPCA_12M",
    ]
    for item in body["indicators"]:
        # No stored data: explicit absence, never a zero value.
        assert item["status"] == "no_data"
        assert item["latest"] is None
        assert item["change_12m"] is None
        assert item["indicator"]["source_url"].startswith("https://")


def test_daily_series_compares_last_value_of_same_month_a_year_earlier(
    client: TestClient, db: Session
) -> None:
    add(
        db,
        "SELIC_TARGET",
        [
            daily(date(2025, 10, 1), "14.25"),
            daily(date(2025, 10, 31), "15.00"),  # last value of Oct/2025
            daily(date(2025, 11, 3), "15.00"),
            daily(date(2026, 10, 1), "14.00"),
            daily(date(2026, 10, 21), "13.75"),
        ],
    )
    item = by_code(client.get(URL).json())["SELIC_TARGET"]
    assert item["status"] == "available"
    assert item["aggregation"]["method"] == "last_value_of_period"
    assert item["latest"] == {
        "date": "2026-10-21",
        "value": 13.75,
        "period_start": "2026-10-01",
        "period_end": "2026-10-31",
    }
    assert item["change_12m"] == {
        "value": -1.25,
        "change_unit": "p.p.",
        "reference_date": "2025-10-31",
        "reference_value": 15.0,
    }


def test_monthly_series_compares_same_month_a_year_earlier(client: TestClient, db: Session) -> None:
    add(
        db,
        "DBGG_GDP",
        [
            monthly(2023, 3, 31, "72.90"),
            monthly(2024, 2, 29, "74.81"),
            monthly(2024, 3, 31, "75.02"),
        ],
    )
    item = by_code(client.get(URL).json())["DBGG_GDP"]
    assert item["aggregation"]["method"] == "none"
    assert item["latest"]["date"] == "2024-03-01"
    assert item["latest"]["value"] == 75.02
    assert item["change_12m"]["reference_date"] == "2023-03-01"
    assert item["change_12m"]["value"] == pytest.approx(2.12)
    assert item["change_12m"]["change_unit"] == "p.p."


def test_missing_year_ago_month_omits_change_instead_of_interpolating(
    client: TestClient, db: Session
) -> None:
    # Feb/2023 and Apr/2023 exist, but Mar/2023 does not: no neighbour is used.
    add(
        db,
        "IPCA_12M",
        [monthly(2023, 2, 28, "5.60"), monthly(2023, 4, 30, "4.18"), monthly(2024, 3, 31, "3.93")],
    )
    item = by_code(client.get(URL).json())["IPCA_12M"]
    assert item["status"] == "available"
    assert item["latest"]["value"] == 3.93
    assert item["change_12m"] is None


def test_change_matches_observations_endpoint(client: TestClient, db: Session) -> None:
    add(db, "SELIC_TARGET", [daily(date(2024, 1, 31), "11.75"), daily(date(2025, 1, 15), "12.25")])
    item = by_code(client.get(URL).json())["SELIC_TARGET"]
    monthly_view = client.get(
        "/api/v1/indicators/SELIC_TARGET/observations", params={"frequency": "monthly"}
    ).json()
    assert item["change_12m"]["value"] == monthly_view["stats"]["change"] == 0.5


def test_cache_header_and_openapi(client: TestClient) -> None:
    response = client.get(URL)
    assert response.headers["cache-control"] == "public, max-age=300"
    assert URL in client.get("/openapi.json").json()["paths"]


def test_rejects_unknown_query_parameters(client: TestClient) -> None:
    response = client.get(URL, params={"geography": "SP"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_parameter"
