"""State endpoints (S5). Observation values are synthetic and inserted directly."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.states import STATE_DASHBOARD_CODES
from app.db.session import get_db
from app.ingestion.fiscal_catalog import (
    ACCUMULATION_WINDOWS,
    FISCAL_INDICATORS,
    YEAR_TO_DATE_CODES,
    YEAR_TO_DATE_WINDOW,
)
from app.main import app
from app.models import GeographicUnit, Indicator, Observation


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def add(db: Session, code: str, uf: str, rows: list[tuple[date, date, str]]) -> None:
    """Insert (period_start, period_end, value) rows; reference_date is the period start."""
    indicator = db.scalar(select(Indicator).where(Indicator.code == code))
    unit = db.scalar(
        select(GeographicUnit).where(
            GeographicUnit.acronym == uf, GeographicUnit.geographic_level == "state"
        )
    )
    assert indicator is not None and unit is not None
    now = datetime.now(UTC)
    for start, end, value in rows:
        db.add(
            Observation(
                indicator_id=indicator.id,
                geographic_unit_id=unit.id,
                reference_date=start,
                period_start=start,
                period_end=end,
                value=Decimal(value),
                collected_at=now,
                source_reference="test",
            )
        )
    db.flush()


def bimester(year: int, n: int, value: str) -> tuple[date, date, str]:
    start = date(year, 2 * n - 1, 1)
    end = date(year + 1, 1, 1) if n == 6 else date(year, 2 * n + 1, 1)
    return (start, date.fromordinal(end.toordinal() - 1), value)


def quadrimester(year: int, n: int, value: str) -> tuple[date, date, str]:
    ends = {1: date(year, 4, 30), 2: date(year, 8, 31), 3: date(year, 12, 31)}
    return (date(year, 4 * n - 3, 1), ends[n], value)


def by_code(body: dict) -> dict[str, dict]:
    return {item["indicator"]["code"]: item for item in body["indicators"]}


def test_display_order_covers_every_state_indicator() -> None:
    assert sorted(STATE_DASHBOARD_CODES) == sorted(FISCAL_INDICATORS)
    assert ACCUMULATION_WINDOWS.keys() == FISCAL_INDICATORS.keys()
    for code in FISCAL_INDICATORS:
        assert (ACCUMULATION_WINDOWS[code] == YEAR_TO_DATE_WINDOW) == (code in YEAR_TO_DATE_CODES)


# --- UF resolution ---


@pytest.mark.parametrize("path", ["indicators", "dashboard"])
@pytest.mark.parametrize("uf", ["XX", "BR", "1", "3", "3550308", "35x"])
def test_unknown_uf_or_other_level_is_404(client: TestClient, path: str, uf: str) -> None:
    # "BR" and "1" are Brasil, "3" is the Sudeste region, 3550308 a municipality code.
    response = client.get(f"/api/v1/states/{uf}/{path}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "state_not_found"


@pytest.mark.parametrize("uf", ["SP", "sp", " sp ", "35"])
def test_uf_by_acronym_any_case_or_ibge_code(client: TestClient, uf: str) -> None:
    body = client.get(f"/api/v1/states/{uf}/dashboard").json()
    assert body["geography"]["acronym"] == "SP"
    assert body["geography"]["geographic_level"] == "state"


@pytest.mark.parametrize("path", ["indicators", "dashboard"])
@pytest.mark.parametrize("uf", ["SE", "se", "28"])
def test_se_is_sergipe_not_the_sudeste_region(client: TestClient, path: str, uf: str) -> None:
    body = client.get(f"/api/v1/states/{uf}/{path}").json()
    assert body["geography"] == {
        "ibge_code": "28",
        "acronym": "SE",
        "name": "Sergipe",
        "geographic_level": "state",
    }


# --- /states/{uf}/indicators ---


def test_indicators_without_data_are_explicit_absences(client: TestClient) -> None:
    response = client.get("/api/v1/states/AC/indicators")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=300"
    body = response.json()
    assert body["notes"] == []
    assert [i["indicator"]["code"] for i in body["indicators"]] == list(STATE_DASHBOARD_CODES)
    for item in body["indicators"]:
        assert item["indicator"]["geographic_level"] == "state"
        assert item["geography"]["acronym"] == "AC"
        assert item["status"] == "no_data"
        assert item["count"] == 0 and item["observations"] == [] and item["stats"] is None
        assert item["indicator"]["first_stored_date"] is None
        assert item["accumulation_window"]


def test_indicators_series_belong_to_the_requested_uf_only(client: TestClient, db: Session) -> None:
    add(db, "STATE_RCL", "SP", [bimester(2025, 1, "100.5"), bimester(2025, 2, "101.25")])
    add(db, "STATE_RCL", "RJ", [bimester(2025, 1, "999")])
    body = client.get("/api/v1/states/SP/indicators").json()
    rcl = by_code(body)["STATE_RCL"]
    assert rcl["status"] == "available"
    assert rcl["unit"] == rcl["indicator"]["unit"]
    assert rcl["frequency"] == "bimonthly"
    assert rcl["aggregation"]["method"] == "none"
    assert [(o["date"], o["period_end"], o["value"]) for o in rcl["observations"]] == [
        ("2025-01-01", "2025-02-28", 100.5),
        ("2025-03-01", "2025-04-30", 101.25),
    ]
    assert rcl["indicator"]["first_stored_date"] == "2025-01-01"
    assert rcl["stats"]["change"] == pytest.approx(0.75)
    # Other indicators of SP have no stored value: absent, never zero.
    assert by_code(body)["STATE_DC"]["status"] == "no_data"


def test_indicators_date_filter_uses_period_end(client: TestClient, db: Session) -> None:
    add(db, "STATE_DC", "MG", [quadrimester(2025, n, str(n)) for n in (1, 2, 3)])
    body = client.get(
        "/api/v1/states/MG/indicators",
        params={"start_date": "2025-05-01", "end_date": "2025-12-31"},
    ).json()
    assert (body["start_date"], body["end_date"]) == ("2025-05-01", "2025-12-31")
    dc = by_code(body)["STATE_DC"]
    assert [o["period_end"] for o in dc["observations"]] == ["2025-08-31", "2025-12-31"]
    assert dc["start_date"] == "2025-05-01" and dc["end_date"] == "2025-12-31"

    # A range with no period: status stays "available" (the UF has data), but nothing is served.
    empty = client.get("/api/v1/states/MG/indicators", params={"start_date": "2030-01-01"}).json()
    dc = by_code(empty)["STATE_DC"]
    assert dc["status"] == "available" and dc["count"] == 0 and dc["stats"] is None


def test_indicators_year_to_date_flows_have_no_stats(client: TestClient, db: Session) -> None:
    add(db, "STATE_PRIMARY_RESULT", "BA", [bimester(2025, 1, "5"), bimester(2025, 6, "-3")])
    item = by_code(client.get("/api/v1/states/BA/indicators").json())["STATE_PRIMARY_RESULT"]
    assert item["count"] == 2 and item["stats"] is None
    assert item["accumulation_window"] == YEAR_TO_DATE_WINDOW


def test_indicators_invalid_range_and_unknown_parameter(client: TestClient) -> None:
    response = client.get(
        "/api/v1/states/SP/indicators",
        params={"start_date": "2025-02-01", "end_date": "2025-01-01"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_range"
    response = client.get("/api/v1/states/SP/indicators", params={"geography": "RJ"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_parameter"
    response = client.get("/api/v1/states/SP/indicators", params={"start_date": "2025-13-01"})
    assert response.status_code == 422


def test_df_carries_the_comparability_note(client: TestClient) -> None:
    for path in ("indicators", "dashboard"):
        notes = client.get(f"/api/v1/states/DF/{path}").json()["notes"]
        assert len(notes) == 1 and "Distrito Federal" in notes[0]


# --- /states/{uf}/dashboard ---


def test_dashboard_without_data(client: TestClient) -> None:
    response = client.get("/api/v1/states/RR/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert [i["indicator"]["code"] for i in body["indicators"]] == list(STATE_DASHBOARD_CODES)
    for item in body["indicators"]:
        assert item["status"] == "no_data"
        assert item["latest"] is None and item["change_12m"] is None
        assert item["change_note"] is None


def test_dashboard_compares_with_the_same_period_a_year_earlier(
    client: TestClient, db: Session
) -> None:
    add(
        db,
        "STATE_INVESTMENTS",
        "PE",
        [bimester(2024, 4, "700"), bimester(2024, 5, "900"), bimester(2025, 4, "1000.5")],
    )
    add(
        db,
        "STATE_DCL_RCL",
        "PE",
        [quadrimester(2024, 2, "40.25"), quadrimester(2025, 1, "41"), quadrimester(2025, 2, "39")],
    )
    items = by_code(client.get("/api/v1/states/PE/dashboard").json())

    investments = items["STATE_INVESTMENTS"]
    assert investments["latest"] == {
        "date": "2025-07-01",
        "value": 1000.5,
        "period_start": "2025-07-01",
        "period_end": "2025-08-31",
        "partial": False,
    }
    # Same bimester (4th) of 2024, not the latest 2024 value (5th bimester).
    assert investments["change_12m"]["reference_date"] == "2024-07-01"
    assert investments["change_12m"]["value"] == pytest.approx(300.5)
    assert investments["change_12m"]["change_unit"] == investments["indicator"]["change_unit"]
    assert "reais correntes, sem correção pela inflação" in investments["change_note"]
    assert investments["accumulation_window"] == YEAR_TO_DATE_WINDOW

    ratio = items["STATE_DCL_RCL"]
    assert ratio["latest"]["period_start"] == "2025-05-01"
    assert ratio["change_12m"] == {
        "value": pytest.approx(-1.25),
        "change_unit": "p.p.",
        "reference_date": "2024-05-01",
        "reference_value": 40.25,
    }
    assert "p.p." in ratio["change_note"]


def test_dashboard_without_the_year_earlier_period_has_no_change(
    client: TestClient, db: Session
) -> None:
    # 2024 has the 3rd bimester only; the latest is the 4th of 2025: no neighbour is used.
    add(db, "STATE_RCL", "CE", [bimester(2024, 3, "50"), bimester(2025, 4, "60")])
    rcl = by_code(client.get("/api/v1/states/CE/dashboard").json())["STATE_RCL"]
    assert rcl["status"] == "available"
    assert rcl["latest"]["value"] == 60
    assert rcl["change_12m"] is None
    assert rcl["change_note"] is None


def test_dashboard_never_serves_another_uf(client: TestClient, db: Session) -> None:
    add(db, "STATE_DC", "SP", [quadrimester(2025, 3, "382603718968.85")])
    assert by_code(client.get("/api/v1/states/RJ/dashboard").json())["STATE_DC"]["latest"] is None
    dc = by_code(client.get("/api/v1/states/SP/dashboard").json())["STATE_DC"]
    assert dc["latest"]["value"] == 382603718968.85
    assert dc["indicator"]["last_stored_date"] == "2025-09-01"


def test_openapi_documents_the_state_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/states/{uf}/indicators" in paths
    assert "/api/v1/states/{uf}/dashboard" in paths
