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


# --- /states/map/{code} ---

ALL_UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()  # noqa: SIM905


def test_map_lists_the_27_ufs_with_absences_as_null(client: TestClient, db: Session) -> None:
    add(db, "STATE_DCL_RCL", "SP", [quadrimester(2025, 1, "160.5")])
    add(db, "STATE_DCL_RCL", "MG", [quadrimester(2025, 1, "-3.25")])
    response = client.get("/api/v1/states/map/STATE_DCL_RCL")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=300"
    body = response.json()
    assert body["indicator"]["code"] == "STATE_DCL_RCL"
    assert body["scale"] == "diverging"
    assert body["period"] == {
        "reference_date": "2025-01-01",
        "period_start": "2025-01-01",
        "period_end": "2025-04-30",
        "coverage": 2,
    }
    states = {s["geography"]["acronym"]: s for s in body["states"]}
    assert [s["geography"]["acronym"] for s in body["states"]] == ALL_UFS
    assert all(s["geography"]["geographic_level"] == "state" for s in body["states"])
    assert states["SP"] == {**states["SP"], "status": "available", "value": 160.5}
    assert states["MG"]["value"] == -3.25
    # An absence is never zero.
    assert states["AC"]["status"] == "no_data" and states["AC"]["value"] is None
    assert sum(s["status"] == "available" for s in body["states"]) == 2


def test_map_reads_every_uf_at_the_same_period(client: TestClient, db: Session) -> None:
    # SP already published Q2; MG only Q1. The map never mixes the latest value of each UF.
    add(db, "STATE_DCL_RCL", "SP", [quadrimester(2025, 1, "150"), quadrimester(2025, 2, "155")])
    add(db, "STATE_DCL_RCL", "MG", [quadrimester(2025, 1, "180")])
    body = client.get("/api/v1/states/map/STATE_DCL_RCL").json()
    assert body["period"]["reference_date"] == "2025-05-01"
    states = {s["geography"]["acronym"]: s for s in body["states"]}
    assert states["SP"]["value"] == 155
    assert states["MG"]["status"] == "no_data"
    assert [p["reference_date"] for p in body["available_periods"]] == [
        "2025-05-01",
        "2025-01-01",
    ]
    assert [p["coverage"] for p in body["available_periods"]] == [1, 2]

    chosen = client.get("/api/v1/states/map/STATE_DCL_RCL?reference_date=2025-01-01").json()
    values = {s["geography"]["acronym"]: s["value"] for s in chosen["states"]}
    assert values["SP"] == 150 and values["MG"] == 180


def test_map_default_period_needs_14_ufs(client: TestClient, db: Session) -> None:
    # Q1 published by 14 UFs, Q2 by only 3 so far: the default is Q1.
    for uf in ALL_UFS[:14]:
        add(db, "STATE_PERSONNEL_EXEC_RCL", uf, [quadrimester(2025, 1, "45")])
    for uf in ALL_UFS[:3]:
        add(db, "STATE_PERSONNEL_EXEC_RCL", uf, [quadrimester(2025, 2, "46")])
    body = client.get("/api/v1/states/map/STATE_PERSONNEL_EXEC_RCL").json()
    assert body["period"]["reference_date"] == "2025-01-01"
    assert body["period"]["coverage"] == 14
    assert "14 das 27" in body["default_rule"]
    assert body["scale"] == "sequential"
    # The less covered period stays selectable.
    later = client.get(
        "/api/v1/states/map/STATE_PERSONNEL_EXEC_RCL?reference_date=2025-05-01"
    ).json()
    assert later["period"]["coverage"] == 3


def test_map_default_falls_back_to_latest_period(client: TestClient, db: Session) -> None:
    add(db, "STATE_RCL", "SP", [bimester(2025, 1, "1"), bimester(2025, 2, "2")])
    body = client.get("/api/v1/states/map/STATE_RCL").json()
    assert body["period"]["reference_date"] == "2025-03-01"


def test_map_without_data(client: TestClient) -> None:
    body = client.get("/api/v1/states/map/STATE_DC").json()
    assert body["period"] is None
    assert body["available_periods"] == []
    assert len(body["states"]) == 27
    assert all(s["status"] == "no_data" and s["value"] is None for s in body["states"])


@pytest.mark.parametrize("code", ["SELIC_TARGET", "XX", "IPCA_12M"])
def test_map_only_serves_state_indicators(client: TestClient, code: str) -> None:
    response = client.get(f"/api/v1/states/map/{code}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "indicator_not_found"


def test_map_code_is_case_insensitive(client: TestClient) -> None:
    assert client.get("/api/v1/states/map/state_dcl").json()["indicator"]["code"] == "STATE_DCL"


def test_map_unknown_period_is_404(client: TestClient, db: Session) -> None:
    add(db, "STATE_DCL", "SP", [quadrimester(2025, 1, "1")])
    response = client.get("/api/v1/states/map/STATE_DCL?reference_date=2025-02-01")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "period_not_found"
    invalid = client.get("/api/v1/states/map/STATE_DCL?reference_date=2025-13-01")
    assert invalid.status_code == 422


def test_map_scale_comes_from_the_catalog(client: TestClient, db: Session) -> None:
    # All values positive in the period, still diverging: the indicator can be negative.
    add(db, "STATE_PRIMARY_RESULT", "SP", [bimester(2025, 1, "10")])
    expected = {
        "STATE_PRIMARY_RESULT": "diverging",
        "STATE_NOMINAL_RESULT": "diverging",
        "STATE_DCL": "diverging",
        "STATE_DCL_RCL": "diverging",
        "STATE_RCL": "sequential",
        "STATE_DC": "sequential",
        "STATE_PERSONNEL_EXEC": "sequential",
        "STATE_PERSONNEL_EXEC_RCL": "sequential",
        "STATE_INVESTMENTS": "sequential",
    }
    assert expected.keys() == set(STATE_DASHBOARD_CODES)
    for code, scale in expected.items():
        assert client.get(f"/api/v1/states/map/{code}").json()["scale"] == scale


def test_map_notes(client: TestClient, db: Session) -> None:
    add(db, "STATE_PERSONNEL_EXEC", "SP", [quadrimester(2025, 2, "1"), quadrimester(2025, 3, "2")])

    def notes(code: str, query: str = "") -> list[str]:
        return client.get(f"/api/v1/states/map/{code}{query}").json()["notes"]

    q3 = notes("STATE_PERSONNEL_EXEC")
    assert any("restos a pagar" in n for n in q3)
    assert any("Valores absolutos" in n for n in q3)
    assert q3[-1].startswith("O Distrito Federal")
    q2 = notes("STATE_PERSONNEL_EXEC", "?reference_date=2025-05-01")
    assert not any("restos a pagar" in n for n in q2)
    ratio = notes("STATE_DCL_RCL")
    assert not any("Valores absolutos" in n for n in ratio)
    assert len(ratio) == 1
    assert any("Acumulado de janeiro" in n for n in notes("STATE_INVESTMENTS"))
    assert not any("Acumulado de janeiro" in n for n in notes("STATE_RCL"))


def test_map_counts_only_state_level_units(client: TestClient, db: Session) -> None:
    add(db, "STATE_DCL", "SP", [quadrimester(2025, 1, "1")])
    # A stray row of another level (Brasil) must not count as a UF nor appear in the map.
    indicator = db.scalar(select(Indicator).where(Indicator.code == "STATE_DCL"))
    brazil = db.scalar(
        select(GeographicUnit).where(
            GeographicUnit.acronym == "BR", GeographicUnit.geographic_level == "country"
        )
    )
    assert indicator is not None and brazil is not None
    db.add(
        Observation(
            indicator_id=indicator.id,
            geographic_unit_id=brazil.id,
            reference_date=date(2025, 1, 1),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 4, 30),
            value=Decimal("99"),
            collected_at=datetime.now(UTC),
            source_reference="test",
        )
    )
    db.flush()
    body = client.get("/api/v1/states/map/STATE_DCL").json()
    assert body["period"]["coverage"] == 1
    assert len(body["states"]) == 27


# --- /states/ranking/{code} (S8) ---


def ranking(client: TestClient, code: str, query: str = "") -> dict:
    response = client.get(f"/api/v1/states/ranking/{code}{query}")
    assert response.status_code == 200, response.text
    return response.json()


def positions(body: dict) -> list[tuple[int, str, float]]:
    return [(r["position"], r["geography"]["acronym"], r["value"]) for r in body["ranking"]]


def test_ranking_orders_selected_ufs_and_leaves_absences_out(
    client: TestClient, db: Session
) -> None:
    add(db, "STATE_DCL_RCL", "SP", [quadrimester(2025, 1, "124.23")])
    add(db, "STATE_DCL_RCL", "MG", [quadrimester(2025, 1, "167.46")])
    add(db, "STATE_DCL_RCL", "ES", [quadrimester(2025, 1, "-14.5")])
    body = ranking(client, "STATE_DCL_RCL")
    assert body["metric_kind"] == "relative"
    assert body["order"] == "desc"
    assert "do maior para o menor" in body["order_note"]
    assert "não indica desempenho" in body["order_note"]
    assert body["period"]["reference_date"] == "2025-01-01"
    assert positions(body) == [(1, "MG", 167.46), (2, "SP", 124.23), (3, "ES", -14.5)]
    # The 24 other UFs: out of the ranking, never zero, with a notice.
    assert body["selected_count"] == 27 and body["ranked_count"] == 3
    assert len(body["missing"]) == 24
    assert body["missing"][0]["acronym"] == "AC"
    assert body["missing_note"].startswith("Sem dado no período: AC, AL, AM")
    assert "não equivale a zero" in body["missing_note"]

    ascending = ranking(client, "STATE_DCL_RCL", "?order=asc&ufs=SP,MG,ES,BA")
    assert positions(ascending) == [(1, "ES", -14.5), (2, "SP", 124.23), (3, "MG", 167.46)]
    assert "do menor para o maior" in ascending["order_note"]
    assert [g["acronym"] for g in ascending["missing"]] == ["BA"]
    assert ascending["missing_note"].startswith("Sem dado no período: BA. Essa UF não publicou")


def test_ranking_ties_share_a_position(client: TestClient, db: Session) -> None:
    # Equal published decimals tie (1, 2, 2, 4), ordered by acronym within the tie.
    for uf, value in [("SP", "41.29"), ("RJ", "45.74"), ("BA", "45.74"), ("AM", "38.28")]:
        add(db, "STATE_PERSONNEL_EXEC_RCL", uf, [quadrimester(2025, 1, value)])
    body = ranking(client, "STATE_PERSONNEL_EXEC_RCL", "?ufs=SP,RJ,BA,AM")
    assert positions(body) == [
        (1, "BA", 45.74),
        (1, "RJ", 45.74),
        (3, "SP", 41.29),
        (4, "AM", 38.28),
    ]
    assert body["missing"] == [] and body["missing_note"] is None
    assert any("1, 2, 2, 4" in n for n in body["notes"])


def test_ranking_uses_one_period_for_every_uf(client: TestClient, db: Session) -> None:
    # MG has not published Q2: it is missing in Q2, never ranked with its Q1 value.
    add(db, "STATE_DCL", "SP", [quadrimester(2025, 1, "10"), quadrimester(2025, 2, "11")])
    add(db, "STATE_DCL", "MG", [quadrimester(2025, 1, "20")])
    latest = ranking(client, "STATE_DCL", "?ufs=SP,MG")
    assert latest["period"]["reference_date"] == "2025-05-01"
    assert positions(latest) == [(1, "SP", 11)]
    assert [g["acronym"] for g in latest["missing"]] == ["MG"]
    earlier = ranking(client, "STATE_DCL", "?ufs=SP,MG&reference_date=2025-01-01")
    assert positions(earlier) == [(1, "MG", 20), (2, "SP", 10)]
    missing_period = client.get("/api/v1/states/ranking/STATE_DCL?reference_date=2024-01-01")
    assert missing_period.status_code == 404
    assert missing_period.json()["error"]["code"] == "period_not_found"


def test_ranking_default_period_is_chosen_over_the_27_ufs(client: TestClient, db: Session) -> None:
    for uf in ALL_UFS[:14]:
        add(db, "STATE_DCL_RCL", uf, [quadrimester(2025, 1, "50")])
    add(db, "STATE_DCL_RCL", "SP", [quadrimester(2025, 2, "60")])
    # Even when only SP and AC are selected, the default is the well-covered Q1.
    body = ranking(client, "STATE_DCL_RCL", "?ufs=SP,AC")
    assert body["period"]["reference_date"] == "2025-01-01"
    assert body["default_rule"].startswith("Período padrão")


def test_ranking_notes(client: TestClient, db: Session) -> None:
    add(db, "STATE_PERSONNEL_EXEC", "SP", [quadrimester(2025, 3, "2")])
    add(db, "STATE_PERSONNEL_EXEC", "MG", [quadrimester(2025, 3, "1")])
    absolute = ranking(client, "STATE_PERSONNEL_EXEC", "?ufs=SP,MG")
    assert absolute["metric_kind"] == "absolute"
    assert any("reflete sobretudo o tamanho" in n for n in absolute["notes"])
    assert any("restos a pagar" in n for n in absolute["notes"])
    # DF note only when the DF is selected.
    assert not any(n.startswith("O Distrito Federal") for n in absolute["notes"])
    with_df = ranking(client, "STATE_PERSONNEL_EXEC", "?ufs=SP,DF")
    assert with_df["notes"][-1].startswith("O Distrito Federal")

    ratio = ranking(client, "STATE_DCL_RCL")["notes"]
    assert any(n.startswith("Métrica relativa") for n in ratio)
    assert any("RCL ajustada" in n for n in ratio)
    assert any("Valores negativos são possíveis" in n for n in ratio)
    assert not any("reflete sobretudo" in n for n in ratio)
    assert any("Acumulado de janeiro" in n for n in ranking(client, "STATE_INVESTMENTS")["notes"])


def test_ranking_without_data(client: TestClient) -> None:
    body = ranking(client, "STATE_DC", "?ufs=SP,MG")
    assert body["period"] is None
    assert body["ranking"] == []
    assert [g["acronym"] for g in body["missing"]] == ["MG", "SP"]
    assert body["missing_note"] is None


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("?ufs=SP", "de 2 a 27"),
        ("?ufs=SP,XX", "'XX'"),
        ("?ufs=SP,sp", "repetida"),
        ("?ufs=SP,35", "repetida"),
        ("?ufs=SP,,MG", "''"),
        ("?ufs=SP,BR", "'BR'"),
    ],
)
def test_ranking_rejects_invalid_selections(client: TestClient, query: str, message: str) -> None:
    response = client.get(f"/api/v1/states/ranking/STATE_DCL_RCL{query}")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_selection"
    assert message in error["message"]


def test_ranking_accepts_ibge_codes_and_rejects_bad_params(client: TestClient) -> None:
    body = ranking(client, "state_dcl_rcl", "?ufs=35,mg")
    assert body["indicator"]["code"] == "STATE_DCL_RCL"
    assert body["selected_count"] == 2
    assert client.get("/api/v1/states/ranking/STATE_DCL?order=up").status_code == 422
    assert client.get("/api/v1/states/ranking/SELIC_TARGET").status_code == 404


# --- /states/compare/{code} (S8) ---


def test_comparison_returns_each_uf_series_as_published(client: TestClient, db: Session) -> None:
    add(db, "STATE_RCL", "SP", [bimester(2025, 1, "100"), bimester(2025, 2, "110")])
    add(db, "STATE_RCL", "MG", [bimester(2025, 2, "50")])
    response = client.get("/api/v1/states/compare/STATE_RCL?ufs=MG,SP,AC")
    assert response.status_code == 200
    body = response.json()
    assert body["indicator"]["code"] == "STATE_RCL"
    series = body["series"]
    assert [s["geography"]["acronym"] for s in series] == ["MG", "SP", "AC"]
    assert [o["value"] for o in series[1]["observations"]] == [100, 110]
    assert [o["date"] for o in series[0]["observations"]] == ["2025-03-01"]
    # A UF without data is an explicit absence, not a series of zeros.
    assert series[2]["status"] == "no_data" and series[2]["observations"] == []
    assert any("tamanho de cada UF" in n for n in body["notes"])
    filtered = client.get("/api/v1/states/compare/STATE_RCL?ufs=SP&start_date=2025-03-01").json()
    assert [o["value"] for o in filtered["series"][0]["observations"]] == [110]


def test_comparison_notes_and_limits(client: TestClient) -> None:
    def notes(code: str, ufs: str) -> list[str]:
        return client.get(f"/api/v1/states/compare/{code}?ufs={ufs}").json()["notes"]

    primary = notes("STATE_PRIMARY_RESULT", "SP,DF")
    assert any("recomeçam em janeiro" in n for n in primary)
    assert any("déficit" in n for n in primary)
    assert primary[-1].startswith("O Distrito Federal")
    personnel = notes("STATE_PERSONNEL_EXEC_RCL", "SP")
    assert any("RCL ajustada" in n for n in personnel)
    assert any("restos a pagar" in n for n in personnel)
    assert not any("recomeçam" in n for n in personnel)

    too_many = client.get("/api/v1/states/compare/STATE_RCL?ufs=SP,MG,RJ,RS,BA,PR,SC")
    assert too_many.status_code == 422
    assert client.get("/api/v1/states/compare/STATE_RCL").status_code == 422
    bad_range = client.get(
        "/api/v1/states/compare/STATE_RCL?ufs=SP&start_date=2025-02-01&end_date=2025-01-01"
    )
    assert bad_range.json()["error"]["code"] == "invalid_range"
