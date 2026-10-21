"""State fiscal indicators derived from SICONFI annexes (S4).

The regression samples come from OFFICIAL annexes (tests/fixtures/siconfi_official_2025.json,
collected from the SICONFI API on 2026-10-21, values exactly as published) and the expected
values below were confirmed by the economist against the API. Tests that alter values, add
duplicates or move reports to other exercises do so on copies and say so; such data is synthetic.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ingestion import cli
from app.ingestion.batch import select_indicators
from app.ingestion.fiscal_catalog import FISCAL_INDICATORS, required_annexes
from app.ingestion.fiscal_indicators import (
    derive_fiscal_indicator,
    period_bounds,
)
from app.ingestion.series_ingestion import IngestionError
from app.main import app
from app.models import (
    FiscalReport,
    FiscalReportRow,
    GeographicLevel,
    GeographicUnit,
    Indicator,
    IngestionRun,
    Observation,
    ObservationRevision,
)
from tests.conftest import load_fixture

OFFICIAL = json.loads(load_fixture("siconfi_official_2025.json"))
DELIVERED_AT = datetime(2026, 1, 30, 12, 0, tzinfo=UTC)  # synthetic delivery date

# Official values (2025, RREO 6th bimester / RGF 3rd four-month period of the Executive).
EXPECTED_2025: dict[str, dict[str, str]] = {
    "STATE_RCL": {
        "SP": "266221395322.55",
        "MG": "111739462561.63",
        "RJ": "100556162133.43",
        "RS": "65232845641.12",
        "BA": "68995621759.51",
        "DF": "39201192140.12",
    },
    "STATE_DC": {
        "SP": "382603718968.85",
        "MG": "213515242948.53",
        "RJ": "237303359171.9",
        "RS": "134105266266.76",
        "BA": "34741201081.59",
        "DF": "9386032883.67",
    },
    "STATE_DCL": {
        "SP": "330471301118.9",
        "MG": "187101497500.28",
        "RJ": "218405063161.58",
        "RS": "113377582604.03",
        "BA": "24569330296.45",
        "DF": "6221218399.07",
    },
    "STATE_DCL_RCL": {
        "SP": "124.23",
        "MG": "167.46",
        "RJ": "217.25",
        "RS": "174.03",
        "BA": "35.67",
        "DF": "15.91",
    },
    "STATE_PERSONNEL_EXEC": {
        "SP": "109727119797.17",
        "MG": "53869167715.23",
        "RJ": "45958926684.55",
        "RS": "28739368022.57",
        "BA": "27772068635.09",
        "DF": "16175614683.65",
    },
    "STATE_PERSONNEL_EXEC_RCL": {
        "SP": "41.29",
        "MG": "48.22",
        "RJ": "45.74",
        "RS": "44.16",
        "BA": "40.36",
        "DF": "41.46",
    },
    "STATE_PRIMARY_RESULT": {
        "SP": "8486487348.83",
        "MG": "4765083530.93",
        "RJ": "793967578.97",
        "RS": "-1989477217.56",
        "BA": "-1450985435.85",
        "DF": "-821469255.49",
    },
    "STATE_NOMINAL_RESULT": {
        "SP": "-23923863520.54",
        "MG": "-10581335263.83",
        "RJ": "-20562297949.86",
        "RS": "-3163203504.66",
        "BA": "-1862245134.01",
        "DF": "-808841030.57",
    },
    "STATE_INVESTMENTS": {
        "SP": "11829883529",
        "MG": "6563089695.22",
        "RJ": "5409391134.07",
        "RS": "2341594679.44",
        "BA": "7369038232.51",
        "DF": "1833483393.14",
    },
}


# ---- unit tests (no database) ----


@pytest.mark.parametrize(
    ("periodicity", "period", "expected"),
    [
        ("B", 1, (date(2024, 1, 1), date(2024, 2, 29))),  # leap year
        ("B", 6, (date(2025, 11, 1), date(2025, 12, 31))),
        ("Q", 1, (date(2025, 1, 1), date(2025, 4, 30))),
        ("Q", 3, (date(2025, 9, 1), date(2025, 12, 31))),
    ],
)
def test_period_bounds(periodicity: str, period: int, expected: tuple[date, date]) -> None:
    year = expected[0].year
    assert period_bounds(year, periodicity, period) == expected


@pytest.mark.parametrize(("periodicity", "period"), [("B", 7), ("Q", 4), ("Q", 0), ("S", 1)])
def test_period_bounds_rejects_invalid_periods(periodicity: str, period: int) -> None:
    with pytest.raises((IngestionError, KeyError)):
        period_bounds(2025, periodicity, period)


def test_rgf_column_follows_the_period() -> None:
    selector = FISCAL_INDICATORS["STATE_DCL"].selectors[0]
    assert [selector.column_for(p) for p in (1, 2, 3)] == [
        "Até o 1º Quadrimestre",
        "Até o 2º Quadrimestre",
        "Até o 3º Quadrimestre",
    ]
    rcl = FISCAL_INDICATORS["STATE_RCL"].selectors[0]
    assert rcl.column_for(4) == "TOTAL (ÚLTIMOS 12 MESES)"


def test_required_annexes_respect_the_first_exercise() -> None:
    definitions = FISCAL_INDICATORS.values()
    before_2023 = required_annexes(definitions, [2019])
    assert ("RREO", "RREO-Anexo 06", None) not in before_2023
    assert sorted(required_annexes(definitions, [2025])) == [
        ("RGF", "RGF-Anexo 01", "E"),
        ("RGF", "RGF-Anexo 02", "E"),
        ("RREO", "RREO-Anexo 01", None),
        ("RREO", "RREO-Anexo 03", None),
        ("RREO", "RREO-Anexo 06", None),
    ]
    assert required_annexes(definitions, [2015]) == []


def test_cli_rejects_collection_without_years(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["derive-fiscal", "--collect"])
    assert "--collect requires --year" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        cli.main(["derive-fiscal", "--refresh"])
    with pytest.raises(SystemExit):
        cli.main(["derive-fiscal", "--indicator", "SELIC_TARGET"])


# ---- database tests ----


def _states(db: Session) -> dict[str, GeographicUnit]:
    return {
        u.acronym: u
        for u in db.scalars(
            select(GeographicUnit).where(GeographicUnit.geographic_level == GeographicLevel.STATE)
        )
    }


def _store(db: Session, report: dict[str, Any], **overrides: Any) -> FiscalReport:
    data = {**report, **overrides}
    unit = _states(db)[data["state"]]
    stored = FiscalReport(
        geographic_unit_id=unit.id,
        report_type=data["report_type"],
        exercise=data["exercise"],
        periodicity="B" if data["report_type"] == "RREO" else "Q",
        period=data["period"],
        annex=data["annex"],
        sphere="E",
        power=data["power"],
        row_count=data["source_rows"],
        content_hash="official-sample",
        delivered_at=DELIVERED_AT,
        source_url=f"https://apidatalake.tesouro.gov.br/ords/siconfi/tt/{data['annex']}",
        collected_at=datetime(2026, 10, 21, tzinfo=UTC),
        rows=[
            FiscalReportRow(
                label=r["label"],
                column=r["column"],
                account_code=r["account_code"],
                account=r["account"],
                value=Decimal(r["value"]),
            )
            for r in data["rows"]
        ],
    )
    db.add(stored)
    db.flush()
    return stored


@pytest.fixture
def official(db: Session) -> list[FiscalReport]:
    return [_store(db, report) for report in OFFICIAL["reports"]]


def _values(db: Session, code: str) -> dict[tuple[str, date], Observation]:
    rows = db.execute(
        select(GeographicUnit.acronym, Observation)
        .join(Observation, Observation.geographic_unit_id == GeographicUnit.id)
        .join(Indicator, Indicator.id == Observation.indicator_id)
        .where(Indicator.code == code)
    ).all()
    return {(acronym, obs.reference_date): obs for acronym, obs in rows}


def test_catalog_matches_the_definitions(db: Session) -> None:
    seeded = {
        i.code: i
        for i in db.scalars(
            select(Indicator).join(Indicator.source).where(Indicator.code.like("STATE_%"))
        )
    }
    assert set(seeded) == set(FISCAL_INDICATORS)
    for code, definition in FISCAL_INDICATORS.items():
        indicator = seeded[code]
        assert indicator.source.acronym == "SICONFI"
        assert indicator.geographic_level == "state"
        periodicity = {s.periodicity for s in definition.selectors}
        assert indicator.frequency == {"B": "bimonthly", "Q": "four_monthly"}[periodicity.pop()]
        first = min(s.first_exercise for s in definition.selectors)
        assert indicator.first_available_date == date(first, 1, 1)
        assert definition.selectors[0].account_code in indicator.methodology
        # Ratios are percentages compared in p.p.; amounts are nominal reais.
        expected_change = "p.p." if indicator.unit.startswith("%") else "R$ correntes"
        assert indicator.change_unit == expected_change


def test_official_samples_are_derived_exactly(db: Session, official: list[FiscalReport]) -> None:
    for code, definition in FISCAL_INDICATORS.items():
        summary = derive_fiscal_indicator(db, definition)
        assert summary.status == "success", code
        assert summary.ambiguous == 0 and summary.row_missing == 0, code
        expected = EXPECTED_2025[code]
        assert summary.inserted == len(expected), code
        values = _values(db, code)
        periodicity = definition.selectors[0].periodicity
        period = 6 if periodicity == "B" else 3
        start, end = period_bounds(2025, periodicity, period)
        for state, value in expected.items():
            observation = values[(state, start)]
            assert observation.value == Decimal(value), (code, state)
            assert observation.period_start == start and observation.period_end == end
            assert observation.published_at == DELIVERED_AT
            meta = observation.metadata_json or {}
            assert meta["account_code"] == definition.selectors[0].account_code
            assert meta["column"] == definition.selectors[0].column_for(period)


def test_derivation_is_idempotent(db: Session, official: list[FiscalReport]) -> None:
    definition = FISCAL_INDICATORS["STATE_DCL"]
    derive_fiscal_indicator(db, definition)
    count = db.scalar(select(func.count()).select_from(Observation))
    again = derive_fiscal_indicator(db, definition)
    assert (again.inserted, again.updated, again.unchanged) == (0, 0, 6)
    assert db.scalar(select(func.count()).select_from(Observation)) == count
    run = db.get_one(IngestionRun, again.run_id)
    assert run.status == "success" and run.records_unchanged == 6
    assert run.metadata_json is not None and run.metadata_json["outcomes"] == []


def test_rectified_value_is_revised(db: Session, official: list[FiscalReport]) -> None:
    definition = FISCAL_INDICATORS["STATE_DCL"]
    derive_fiscal_indicator(db, definition)
    # Synthetic rectification of the official SP value.
    row = db.scalar(
        select(FiscalReportRow)
        .join(FiscalReport)
        .join(GeographicUnit)
        .where(
            GeographicUnit.acronym == "SP",
            GeographicUnit.geographic_level == GeographicLevel.STATE,
            FiscalReport.annex == "RGF-Anexo 02",
            FiscalReportRow.account_code == "DividaConsolidadaLiquida",
            FiscalReportRow.column == "Até o 3º Quadrimestre",
        )
    )
    assert row is not None
    row.value = Decimal("330471301119.90")
    db.flush()
    summary = derive_fiscal_indicator(db, definition)
    assert (summary.updated, summary.unchanged) == (1, 5)
    observation = _values(db, "STATE_DCL")[("SP", date(2025, 9, 1))]
    assert observation.value == Decimal("330471301119.90")
    revision = db.scalar(
        select(ObservationRevision).where(ObservationRevision.observation_id == observation.id)
    )
    assert revision is not None
    assert revision.previous_value == Decimal("330471301118.9")
    assert revision.ingestion_run_id == summary.run_id


def test_missing_row_is_a_gap_never_zero(db: Session, official: list[FiscalReport]) -> None:
    definition = FISCAL_INDICATORS["STATE_INVESTMENTS"]
    derive_fiscal_indicator(db, definition, states=["SP", "MG"])
    # Synthetic: the RJ annex loses the row; SP's row disappears after being derived.
    for state in ("RJ", "SP"):
        for row in list(_rows(db, state, "RREO-Anexo 01", "Investimentos")):
            db.delete(row)
    db.flush()
    summary = derive_fiscal_indicator(db, definition, states=["SP", "MG", "RJ"])
    assert summary.status == "success"
    assert summary.row_missing == 2 and summary.unchanged == 1
    values = _values(db, "STATE_INVESTMENTS")
    assert ("RJ", date(2025, 11, 1)) not in values
    # A stored value is kept (never deleted silently) and reported in the run.
    assert values[("SP", date(2025, 11, 1))].value == Decimal("11829883529")
    run = db.get_one(IngestionRun, summary.run_id)
    assert run.metadata_json is not None
    missing = [o for o in run.metadata_json["outcomes"] if o["status"] == "row_missing"]
    assert {o["state"] for o in missing} == {"RJ", "SP"}


def _rows(db: Session, state: str, annex: str, account_code: str) -> list[FiscalReportRow]:
    return list(
        db.scalars(
            select(FiscalReportRow)
            .join(FiscalReport)
            .join(GeographicUnit)
            .where(
                GeographicUnit.acronym == state,
                GeographicUnit.geographic_level == GeographicLevel.STATE,
                FiscalReport.annex == annex,
                FiscalReportRow.account_code == account_code,
            )
        )
    )


def test_ambiguous_rows_fail_without_storing(db: Session, official: list[FiscalReport]) -> None:
    definition = FISCAL_INDICATORS["STATE_RCL"]
    # Synthetic: a second RCL row with the same column under another rotulo.
    report = _rows(db, "BA", "RREO-Anexo 03", "RREO3ReceitaCorrenteLiquida")[0].report
    report.rows.append(
        FiscalReportRow(
            label="Outro",
            column="TOTAL (ÚLTIMOS 12 MESES)",
            account_code="RREO3ReceitaCorrenteLiquida",
            account="RECEITA CORRENTE LÍQUIDA (sintética)",
            value=Decimal("1"),
        )
    )
    db.flush()
    with pytest.raises(IngestionError, match="more than one row"):
        derive_fiscal_indicator(db, definition)
    assert _values(db, "STATE_RCL") == {}
    run = db.scalar(select(IngestionRun).order_by(IngestionRun.id.desc()).limit(1))
    assert run is not None and run.status == "failed"
    assert run.metadata_json is not None
    ambiguous = [o for o in run.metadata_json["outcomes"] if o["status"] == "ambiguous"]
    assert [o["state"] for o in ambiguous] == ["BA"]


def test_exercises_outside_the_definition_are_not_derived(db: Session) -> None:
    # Synthetic copies of official 2025 annexes relabelled as 2022 and 2019.
    rreo6 = next(r for r in OFFICIAL["reports"] if r["annex"] == "RREO-Anexo 06")
    rgf2 = next(r for r in OFFICIAL["reports"] if r["annex"] == "RGF-Anexo 02")
    _store(db, rreo6, exercise=2022)
    _store(db, rgf2, exercise=2019)
    primary = derive_fiscal_indicator(db, FISCAL_INDICATORS["STATE_PRIMARY_RESULT"])
    ratio = derive_fiscal_indicator(db, FISCAL_INDICATORS["STATE_DCL_RCL"])
    dcl = derive_fiscal_indicator(db, FISCAL_INDICATORS["STATE_DCL"])
    assert primary.inserted == 0 and ratio.inserted == 0
    assert dcl.inserted == 1  # the DCL series starts in 2018


def test_filters_by_state_and_exercise(db: Session, official: list[FiscalReport]) -> None:
    definition = FISCAL_INDICATORS["STATE_DC"]
    assert derive_fiscal_indicator(db, definition, exercises=[2024]).inserted == 0
    summary = derive_fiscal_indicator(db, definition, states=["sp", "DF"], exercises=[2025])
    assert summary.inserted == 2
    assert {state for state, _ in _values(db, "STATE_DC")} == {"SP", "DF"}
    with pytest.raises(IngestionError, match="Unknown or missing state"):
        derive_fiscal_indicator(db, definition, states=["XX"])


def test_batch_never_collects_derived_indicators(db: Session) -> None:
    assert all(not i.code.startswith("STATE_") for i in select_indicators(db, None))
    with pytest.raises(IngestionError, match="derive-fiscal"):
        select_indicators(db, ["STATE_RCL"])


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_serves_state_observations(
    db: Session, official: list[FiscalReport], client: TestClient
) -> None:
    derive_fiscal_indicator(db, FISCAL_INDICATORS["STATE_DCL_RCL"])
    response = client.get("/api/v1/indicators/STATE_DCL_RCL/observations?geography=ES")
    assert response.status_code == 200
    assert response.json()["observations"] == []  # ES was not collected: a gap, never zero
    response = client.get("/api/v1/indicators/STATE_DCL_RCL/observations?geography=RJ")
    assert response.status_code == 200
    body = response.json()
    assert body["indicator"]["frequency"] == "four_monthly"
    assert body["indicator"]["geographic_level"] == "state"
    assert [(p["date"], p["value"], p["period_end"]) for p in body["observations"]] == [
        ("2025-09-01", 217.25, "2025-12-31")
    ]
    # National geography is refused for a state indicator.
    assert client.get("/api/v1/indicators/STATE_DCL_RCL/observations").status_code == 422
    catalog = {i["code"]: i for i in client.get("/api/v1/indicators").json()}
    assert catalog["STATE_DCL_RCL"]["first_stored_date"] == "2025-09-01"
    assert catalog["STATE_DCL_RCL"]["last_collected_at"] is not None
    assert catalog["STATE_RCL"]["first_stored_date"] is None
