"""Incremental SICONFI ingestion (S3) against PostgreSQL.

Every report and delivery here is SYNTHETIC (values and dates invented for the tests); HTTP is
served by httpx.MockTransport emulating the SICONFI endpoints.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion import cli
from app.ingestion.series_ingestion import IngestionError
from app.ingestion.siconfi import ReportOutcome, SiconfiSummary, ingest_siconfi_reports
from app.integrations.tesouro.siconfi import SiconfiClient, SiconfiError, SiconfiPayloadError
from app.models import FiscalReport, FiscalReportRow, GeographicUnit, IngestionRun

CODES = {"SP": "35", "RJ": "33"}
DELIVERABLE = {
    "RREO": "Relatório Resumido de Execução Orçamentária",
    "RGF": "Relatório de Gestão Fiscal",
}


@dataclass
class FakeSiconfi:
    """Synthetic SICONFI: deliveries[(code, deliverable, period)] = date; reports[(path, code,
    period)] = {coluna: valor}."""

    deliveries: dict[tuple[str, str, int], str] = field(default_factory=dict)
    reports: dict[tuple[str, str, int], dict[str, Any]] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    broken: set[tuple[str, str, int]] = field(default_factory=set)

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, params = request.url.path.rsplit("/", 1)[-1], request.url.params
        self.calls.append(path)
        code = params["id_ente"]
        if path == "extrato_entregas":
            year = int(params["an_referencia"])
            items = [
                {
                    "exercicio": year,
                    "cod_ibge": int(c),
                    "instituicao": "Governo (sintético)",
                    "entregavel": deliverable,
                    "periodo": period,
                    "periodicidade": "B" if deliverable == DELIVERABLE["RREO"] else "Q",
                    "status_relatorio": "HO",
                    "data_status": date,
                }
                for (c, deliverable, period), date in self.deliveries.items()
                if c == code
            ]
            return self._page(items)
        period = int(params["nr_periodo"])
        key = (path, code, period)
        values = self.reports.get(key, {})
        items = [
            {
                "exercicio": int(params["an_exercicio"]),
                "periodo": period,
                "periodicidade": "B" if path == "rreo" else "Q",
                "instituicao": "Governo (sintético)",
                "cod_ibge": int(code),
                "populacao": 1000,
                "anexo": params["no_anexo"],
                "esfera": "E",
                **({"demonstrativo": "RREO"} if path == "rreo" else {"co_poder": "E"}),
                "rotulo": "Padrão",
                "coluna": column,
                "cod_conta": "ContaSintetica",
                "conta": "CONTA SINTÉTICA",
                "valor": "INVALID" if key in self.broken else value,
            }
            for column, value in values.items()
        ]
        return self._page(items)

    @staticmethod
    def _page(items: list[Any]) -> httpx.Response:
        body = json.dumps({"items": items, "hasMore": False, "offset": 0}, default=str)
        return httpx.Response(200, content=body.replace('"@', "").replace('@"', ""))

    def client(self, settings: Settings) -> SiconfiClient:
        return SiconfiClient(
            settings, transport=httpx.MockTransport(self.handler), sleep=lambda _: None
        )


def num(text: str) -> str:
    """Emit a JSON number from text (the fake strips the @ markers), keeping exact decimals."""
    return f"@{text}@"


@pytest.fixture
def fake() -> Iterator[FakeSiconfi]:
    server = FakeSiconfi()
    for uf in ("SP", "RJ"):
        for period in (1, 2):
            server.deliveries[(CODES[uf], DELIVERABLE["RREO"], period)] = "2024-03-30T10:00:00Z"
            server.reports[("rreo", CODES[uf], period)] = {
                "C1": num("1000.10"),
                "C2": num(f"{period}2345678901.23"),
            }
    yield server


def run(db: Session, settings: Settings, fake: FakeSiconfi, **kwargs: Any):
    options: dict[str, Any] = {
        "report_type": "RREO",
        "annex": "RREO-Anexo 03",
        "states": ["SP", "RJ"],
        "exercises": [2024],
        **kwargs,
    }
    return ingest_siconfi_reports(db, settings, fake.client(settings), **options)


def stored_values(db: Session, uf: str, period: int, annex: str = "RREO-Anexo 03") -> dict:
    rows = db.execute(
        select(FiscalReportRow.column, FiscalReportRow.value)
        .join(FiscalReport)
        .join(GeographicUnit)
        .where(
            GeographicUnit.acronym == uf,
            GeographicUnit.geographic_level == "state",
            FiscalReport.period == period,
            FiscalReport.annex == annex,
        )
    )
    return {column: value for column, value in rows}


def report_of(db: Session, uf: str, period: int) -> FiscalReport:
    return db.scalars(
        select(FiscalReport)
        .join(GeographicUnit)
        .where(
            GeographicUnit.acronym == uf,
            GeographicUnit.geographic_level == "state",
            FiscalReport.period == period,
        )
    ).one()


def statuses(summary) -> list[tuple[str, int, str]]:
    return [(o.state, o.period, o.status) for o in summary.reports]


def test_first_collection_stores_delivered_periods_exactly(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    summary = run(db, settings, fake)
    assert statuses(summary)[:3] == [
        ("SP", 1, "inserted"),
        ("SP", 2, "inserted"),
        ("SP", 3, "not_delivered"),
    ]
    assert summary.rows_inserted == 8
    assert stored_values(db, "RJ", 2) == {
        "C1": Decimal("1000.10"),
        "C2": Decimal("22345678901.23"),
    }
    report = report_of(db, "SP", 1)
    assert report.power is None and report.periodicity == "B" and report.row_count == 2
    assert report.delivered_at is not None and report.delivered_at.year == 2024
    assert "no_anexo=RREO-Anexo+03" in report.source_url
    run_row = db.get_one(IngestionRun, summary.run_id)
    assert run_row.status == "success"
    assert run_row.records_inserted == 8
    assert run_row.metadata_json is not None
    assert run_row.metadata_json["dataset"] == "siconfi_reports"
    # 1 statement per state-year + 1 request per delivered period; 4 future periods not asked.
    assert fake.calls.count("extrato_entregas") == 2 and fake.calls.count("rreo") == 4


def test_rerun_without_new_delivery_requests_only_the_statement(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    run(db, settings, fake)
    fake.calls.clear()
    summary = run(db, settings, fake)
    assert {o.status for o in summary.reports if o.period <= 2} == {"up_to_date"}
    assert fake.calls == ["extrato_entregas", "extrato_entregas"]
    assert summary.rows_inserted == summary.rows_updated == 0
    assert db.scalar(select(func.count()).select_from(FiscalReport)) == 4
    assert db.scalar(select(func.count()).select_from(FiscalReportRow)) == 8


def test_rectification_updates_rows_and_records_revisions(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    run(db, settings, fake)
    old_hash = report_of(db, "SP", 2).content_hash
    fake.deliveries[("35", DELIVERABLE["RREO"], 2)] = "2025-01-15T10:00:00Z"
    fake.reports[("rreo", "35", 2)] = {"C1": num("1000.11"), "C3": num("5")}
    summary = run(db, settings, fake, states=["SP"])
    assert statuses(summary)[:2] == [("SP", 1, "up_to_date"), ("SP", 2, "updated")]
    assert stored_values(db, "SP", 2) == {"C1": Decimal("1000.11"), "C3": Decimal("5")}
    assert (summary.rows_updated, summary.rows_inserted, summary.rows_deleted) == (1, 1, 1)
    revisions = {r["row"]["column"]: (r["previous"], r["new"]) for r in summary.revisions}
    assert revisions == {
        "C1": ("1000.1", "1000.11"),
        "C3": (None, "5"),
        "C2": ("22345678901.23", None),
    }
    assert all(r["previous_hash"] == old_hash for r in summary.revisions)
    run_row = db.get_one(IngestionRun, summary.run_id)
    assert run_row.metadata_json is not None and run_row.metadata_json["revision_count"] == 3
    report = report_of(db, "SP", 2)
    assert report.delivered_at is not None
    assert report.delivered_at.year == 2025 and report.row_count == 2


def test_refresh_collects_again_and_keeps_unchanged_rows(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    run(db, settings, fake)
    summary = run(db, settings, fake, refresh=True, periods=[1])
    assert statuses(summary) == [("SP", 1, "unchanged"), ("RJ", 1, "unchanged")]
    assert summary.rows_unchanged == 4 and summary.revisions == []


def test_delivered_but_not_in_the_data_lake_is_retried_later(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    fake.deliveries[("35", DELIVERABLE["RREO"], 3)] = "2024-07-30T10:00:00Z"
    summary = run(db, settings, fake, states=["SP"], periods=[3])
    assert statuses(summary) == [("SP", 3, "not_available")]
    assert db.scalar(select(func.count()).select_from(FiscalReport)) == 0
    fake.reports[("rreo", "35", 3)] = {"C1": num("7")}
    summary = run(db, settings, fake, states=["SP"], periods=[3])
    assert statuses(summary) == [("SP", 3, "inserted")]


def test_failure_keeps_committed_reports_and_records_failed_run(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    fake.broken.add(("rreo", "33", 1))
    with pytest.raises(SiconfiPayloadError):
        run(db, settings, fake)
    assert set(stored_values(db, "SP", 2)) == {"C1", "C2"}  # SP was committed before RJ failed
    assert stored_values(db, "RJ", 1) == {}
    failed = db.scalars(select(IngestionRun).order_by(IngestionRun.id.desc())).first()
    assert failed is not None and failed.status == "failed"
    assert failed.error_message is not None and "Non-numeric valor" in failed.error_message
    assert failed.metadata_json is not None
    assert [r["state"] for r in failed.metadata_json["reports"]] == ["SP"] * 6


def test_rgf_stores_power_and_does_not_mix_with_rreo(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    fake.deliveries[("35", DELIVERABLE["RGF"], 1)] = "2024-05-30T10:00:00Z"
    fake.reports[("rgf", "35", 1)] = {"DC": num("300000000000.01")}
    summary = run(
        db, settings, fake, report_type="RGF", annex="RGF-Anexo 02", states=["SP"], periods=[1]
    )
    assert statuses(summary) == [("SP", 1, "inserted")]
    report = db.scalars(select(FiscalReport).where(FiscalReport.report_type == "RGF")).one()
    assert (report.power, report.periodicity) == ("E", "Q")
    assert stored_values(db, "SP", 1, "RGF-Anexo 02") == {"DC": Decimal("300000000000.01")}
    run(db, settings, fake, report_type="RGF", annex="RGF-Anexo 02", states=["SP"], periods=[1])
    assert db.scalar(select(func.count()).select_from(FiscalReport)) == 1


def test_rreo_reports_with_null_power_are_unique(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    run(db, settings, fake, states=["SP"], periods=[1])
    run(db, settings, fake, states=["SP"], periods=[1], refresh=True)
    assert db.scalar(select(func.count()).select_from(FiscalReport)) == 1


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"states": ["XX"]}, IngestionError),
        ({"states": ["SE", "XX"]}, IngestionError),
        ({"states": []}, IngestionError),
        ({"periods": [7]}, SiconfiError),
        ({"annex": "RGF-Anexo 02"}, SiconfiError),
        ({"annex": "RREO-Anexo 3"}, SiconfiError),  # the API would answer [] for every period
    ],
)
def test_invalid_requests_fail_before_any_run(
    db: Session, settings: Settings, fake: FakeSiconfi, kwargs: dict[str, Any], error: type
) -> None:
    before = db.scalar(select(func.count()).select_from(IngestionRun))
    with pytest.raises(error):
        run(db, settings, fake, **kwargs)
    assert db.scalar(select(func.count()).select_from(IngestionRun)) == before
    assert fake.calls == []


def test_state_acronym_is_resolved_at_state_level(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    fake.deliveries[("28", DELIVERABLE["RREO"], 1)] = "2024-03-30T10:00:00Z"
    fake.reports[("rreo", "28", 1)] = {"C1": num("1")}
    summary = run(db, settings, fake, states=["se"], periods=[1])  # Sergipe, not Sudeste
    assert statuses(summary) == [("SE", 1, "inserted")]


@pytest.mark.parametrize(
    "argv",
    [
        ["--report", "RREO", "--annex", "RREO-Anexo 03", "--state", "SP", "--year", "2014"],
        ["--report", "RREO", "--annex", "RREO-Anexo 03", "--state", "SP", "--year", "2999"],
        ["--report", "RREO", "--annex", "x", "--state", "SP", "--year", "2024", "--power", "E"],
        ["--report", "DCA", "--annex", "x", "--state", "SP", "--year", "2024"],
    ],
)
def test_cli_rejects_invalid_arguments(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["ingest-siconfi", *argv])
    assert exc.value.code == 2


def test_rectification_not_yet_in_the_data_lake_is_requested_again(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    """The statement lists a new delivery before the data lake serves the new content."""
    run(db, settings, fake, states=["SP"], periods=[2])
    recent = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fake.deliveries[("35", DELIVERABLE["RREO"], 2)] = recent
    summary = run(db, settings, fake, states=["SP"], periods=[2])
    assert statuses(summary) == [("SP", 2, "awaiting_source")]
    assert report_of(db, "SP", 2).delivered_at.year == 2024  # type: ignore[union-attr]
    fake.reports[("rreo", "35", 2)] = {"C1": num("999"), "C2": num("22345678901.23")}
    summary = run(db, settings, fake, states=["SP"], periods=[2])
    assert statuses(summary) == [("SP", 2, "updated")]
    assert stored_values(db, "SP", 2)["C1"] == Decimal("999")
    summary = run(db, settings, fake, states=["SP"], periods=[2])
    assert statuses(summary) == [("SP", 2, "up_to_date")]


def test_unchanged_content_is_accepted_after_the_grace_period(
    db: Session, settings: Settings, fake: FakeSiconfi
) -> None:
    run(db, settings, fake, states=["SP"], periods=[2])
    old = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fake.deliveries[("35", DELIVERABLE["RREO"], 2)] = old  # rectification of another annex
    summary = run(db, settings, fake, states=["SP"], periods=[2])
    assert statuses(summary) == [("SP", 2, "unchanged")]
    summary = run(db, settings, fake, states=["SP"], periods=[2])
    assert statuses(summary) == [("SP", 2, "up_to_date")]


def test_failed_commit_is_not_counted_as_stored(
    db: Session, settings: Settings, fake: FakeSiconfi, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit, calls = db.commit, {"n": 0}

    def flaky_commit() -> None:
        calls["n"] += 1
        if calls["n"] == 3:  # 1 = run created, 2 = SP period 1, 3 = SP period 2
            raise RuntimeError("simulated commit failure")
        commit()

    monkeypatch.setattr(db, "commit", flaky_commit)
    with pytest.raises(RuntimeError):
        run(db, settings, fake, states=["SP"], periods=[1, 2])
    failed = db.scalars(select(IngestionRun).order_by(IngestionRun.id.desc())).first()
    assert failed is not None and failed.status == "failed"
    assert failed.records_inserted == 2  # only period 1 was stored
    assert failed.metadata_json is not None
    assert [r["period"] for r in failed.metadata_json["reports"]] == [1]
    assert stored_values(db, "SP", 2) == {}


def test_interruption_is_recorded_as_failed_run(
    db: Session, settings: Settings, fake: FakeSiconfi, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupt(*_: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(SiconfiClient, "fetch_report", interrupt)
    with pytest.raises(KeyboardInterrupt):
        run(db, settings, fake, states=["SP"], periods=[1])
    last = db.scalars(select(IngestionRun).order_by(IngestionRun.id.desc())).first()
    assert last is not None and last.status == "failed"


def test_cli_fails_when_every_delivered_period_is_empty(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = SiconfiSummary(1, "RREO", "RREO-Anexo 03")
    summary.reports = [
        ReportOutcome("SP", 2024, 1, "not_available"),
        ReportOutcome("SP", 2024, 2, "not_delivered"),
    ]
    monkeypatch.setattr(cli, "ingest_siconfi_reports", lambda *a, **k: summary)
    monkeypatch.setattr(cli, "get_session_factory", lambda: lambda: nullcontext(None))
    argv = ["ingest-siconfi", "--report", "RREO", "--annex", "RREO-Anexo 03"]
    assert cli.main([*argv, "--state", "SP", "--year", "2024"]) == cli.EXIT_FAILED
    assert "check the annex name" in capsys.readouterr().err
    summary.reports[0].status = "inserted"
    assert cli.main([*argv, "--state", "SP", "--year", "2024"]) == cli.EXIT_OK
