"""Batch collection (``ingest --all``, scheduler) against PostgreSQL with fake connectors.

Values are synthetic. Connectors are replaced by in-memory fakes; nothing touches the network.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion import cli
from app.ingestion.batch import close_orphan_runs, run_batch, select_indicators
from app.ingestion.series_ingestion import IngestionError
from app.integrations.bcb.sgs import SGSPoint, SGSUnavailableError, SGSWindowResult
from app.models import DataSource, Indicator, IngestionRun

TODAY = date(2024, 3, 10)
CATALOG = ["DBGG_GDP", "IPCA_12M", "SELIC_TARGET"]


class FakeClient:
    """Answers every series with one synthetic point on the 1st of TODAY's month."""

    def __init__(self, fail_series: set[str] | None = None) -> None:
        self.fail_series = fail_series or set()
        self.requested: list[str] = []

    def fetch_series(
        self, series_code: str, start: date, end: date, *, daily: bool = False
    ) -> list[SGSWindowResult]:
        self.requested.append(series_code)
        if series_code in self.fail_series:
            raise SGSUnavailableError(f"synthetic outage for {series_code}")
        point = SGSPoint(TODAY.replace(day=1), Decimal("10.5"))
        return [SGSWindowResult(start, end, "fake://", [point], 0, None)]


def runs_by_code(db: Session) -> dict[str, list[IngestionRun]]:
    rows = db.execute(
        select(Indicator.code, IngestionRun)
        .join(IngestionRun, IngestionRun.indicator_id == Indicator.id)
        .order_by(IngestionRun.id)
    ).all()
    result: dict[str, list[IngestionRun]] = {}
    for code, run in rows:
        result.setdefault(code, []).append(run)
    return result


def test_all_selects_the_whole_catalog_in_code_order(db: Session) -> None:
    assert [i.code for i in select_indicators(db, None)] == CATALOG


def test_unknown_code_is_rejected_before_any_collection(db: Session) -> None:
    with pytest.raises(IngestionError, match="Unknown indicator: NOPE"):
        select_indicators(db, ["SELIC_TARGET", "NOPE"])
    assert runs_by_code(db) == {}


def test_collects_every_indicator_with_its_source_connector(
    db: Session, settings: Settings
) -> None:
    bcb, ibge = FakeClient(), FakeClient()
    result = run_batch(db, settings, clients={"BCB": bcb, "IBGE": ibge}, today=TODAY)
    assert result.ok
    assert [(i.indicator_code, i.status) for i in result.items] == [
        (code, "success") for code in CATALOG
    ]
    assert sorted(bcb.requested) == ["13762", "432"]
    assert ibge.requested == ["1737/2265"]
    assert all(item.summary and item.summary.inserted == 1 for item in result.items)


def test_failure_of_one_indicator_does_not_stop_the_others(db: Session, settings: Settings) -> None:
    bcb = FakeClient(fail_series={"13762"})  # DBGG_GDP fails, and it is collected first
    result = run_batch(db, settings, clients={"BCB": bcb, "IBGE": FakeClient()}, today=TODAY)
    assert not result.ok
    assert result.failed == ["DBGG_GDP"]
    statuses = {i.indicator_code: i.status for i in result.items}
    assert statuses == {"DBGG_GDP": "failed", "IPCA_12M": "success", "SELIC_TARGET": "success"}
    failed = result.items[0]
    assert failed.error is not None and "synthetic outage" in failed.error
    assert failed.run_id is not None  # the failed run is identified in the report

    runs = runs_by_code(db)
    assert [r.status for r in runs["DBGG_GDP"]] == ["failed"]
    assert "synthetic outage" in (runs["DBGG_GDP"][0].error_message or "")
    assert runs["DBGG_GDP"][0].finished_at is not None
    assert [r.status for r in runs["SELIC_TARGET"]] == ["success"]


def test_failure_before_the_request_is_recorded_as_a_run(db: Session, settings: Settings) -> None:
    # End date before the first available date: rejected before any data is requested.
    result = run_batch(
        db,
        settings,
        ["SELIC_TARGET"],
        clients={"BCB": FakeClient()},
        start=date(2024, 3, 5),
        end=date(2024, 3, 1),
        today=TODAY,
    )
    assert result.failed == ["SELIC_TARGET"]
    run = runs_by_code(db)["SELIC_TARGET"][0]
    assert run.status == "failed"
    assert run.error_message is not None and run.error_message.startswith("IngestionError:")
    assert result.items[0].error is not None


def test_source_without_connector_fails_and_is_recorded(db: Session, settings: Settings) -> None:
    other = DataSource(acronym="XYZ", name="Synthetic", organization="Test", base_url="x")
    db.add(other)
    db.flush()
    selic = db.scalar(select(Indicator).where(Indicator.code == "SELIC_TARGET"))
    assert selic is not None
    selic.source_id = other.id
    db.flush()
    db.expire_all()

    result = run_batch(db, settings, ["SELIC_TARGET", "IPCA_12M"], clients={"IBGE": FakeClient()})
    assert result.failed == ["SELIC_TARGET"]
    assert result.items[0].error == "IngestionError: No connector for source XYZ"
    assert result.items[0].run_id is not None
    assert runs_by_code(db)["SELIC_TARGET"][0].status == "failed"
    assert result.items[1].status == "success"


def test_derived_indicators_are_skipped_or_rejected(db: Session, settings: Settings) -> None:
    # The whole catalog (`ingest --all`, the scheduler) leaves the SICONFI indicators out.
    assert [i.code for i in select_indicators(db, None)] == ["DBGG_GDP", "IPCA_12M", "SELIC_TARGET"]
    with pytest.raises(IngestionError, match="use `derive-fiscal`"):
        run_batch(db, settings, ["SELIC_TARGET", "STATE_DCL"])
    assert runs_by_code(db) == {}


def test_stop_request_skips_the_remaining_indicators(db: Session, settings: Settings) -> None:
    bcb = FakeClient()
    result = run_batch(
        db,
        settings,
        clients={"BCB": bcb, "IBGE": FakeClient()},
        should_stop=lambda: len(bcb.requested) > 0,  # stop after the first indicator
        today=TODAY,
    )
    done = [i.indicator_code for i in result.items]
    assert done == ["DBGG_GDP"]
    assert "IPCA_12M" not in runs_by_code(db)


def test_orphan_running_runs_are_closed(db: Session, settings: Settings) -> None:
    selic = db.scalar(select(Indicator).where(Indicator.code == "SELIC_TARGET"))
    assert selic is not None
    now = datetime.now(UTC)
    for started in (now - timedelta(hours=3), now - timedelta(minutes=5)):
        db.add(
            IngestionRun(
                source_id=selic.source_id,
                indicator_id=selic.id,
                status="running",
                started_at=started,
                records_received=0,
                records_inserted=0,
                records_updated=0,
                records_unchanged=0,
            )
        )
    db.flush()
    assert close_orphan_runs(db, now) == 1
    runs = runs_by_code(db)["SELIC_TARGET"]
    assert [r.status for r in runs] == ["failed", "running"]  # a recent run may be live
    assert (runs[0].error_message or "").startswith("Interrupted")


@pytest.fixture
def cli_env(db: Session, monkeypatch: pytest.MonkeyPatch, settings: Settings):
    """Runs the CLI on the test session with fake connectors."""

    class SessionContext:
        def __enter__(self) -> Session:
            return db

        def __exit__(self, *_: object) -> None:
            return None

    clients = {"BCB": FakeClient(), "IBGE": FakeClient()}
    real_run_batch = cli.run_batch

    def fake_run_batch(session, settings_, codes, **options):
        return real_run_batch(session, settings_, codes, clients=clients, today=TODAY, **options)

    monkeypatch.setattr(cli, "get_session_factory", lambda: SessionContext)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "configure_logging", lambda *_: None)
    monkeypatch.setattr(cli, "run_batch", fake_run_batch)
    return clients


def test_cli_all_exits_zero_when_everything_succeeds(cli_env, capsys) -> None:
    assert cli.main(["ingest", "--all"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [(r["indicator"], r["status"]) for r in report] == [(c, "success") for c in CATALOG]


def test_cli_exits_non_zero_when_any_collection_fails(cli_env, capsys) -> None:
    cli_env["IBGE"].fail_series.add("1737/2265")
    assert cli.main(["ingest", "--all"]) == 1
    report = {r["indicator"]: r for r in json.loads(capsys.readouterr().out)}
    assert report["IPCA_12M"]["status"] == "failed"
    assert "synthetic outage" in report["IPCA_12M"]["error"]
    assert report["SELIC_TARGET"]["status"] == "success"


def test_cli_single_indicator(cli_env, capsys) -> None:
    assert cli.main(["ingest", "SELIC_TARGET"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert [r["indicator"] for r in report] == ["SELIC_TARGET"]
    assert report[0]["summary"]["inserted"] == 1


def test_cli_unknown_indicator_exits_non_zero(cli_env, capsys) -> None:
    assert cli.main(["ingest", "NOPE"]) == 1
    assert "Unknown indicator: NOPE" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [["--start", "2024-03-05", "--end", "2024-03-01"], ["--start", "2999-01-01"]],
)
def test_cli_rejects_invalid_ranges_without_recording_runs(
    cli_env, db: Session, args: list[str]
) -> None:
    with pytest.raises(SystemExit):
        cli.main(["ingest", "--all", *args])
    assert runs_by_code(db) == {}


def test_cli_requires_exactly_one_target() -> None:
    with pytest.raises(SystemExit):
        cli.main(["ingest"])
    with pytest.raises(SystemExit):
        cli.main(["ingest", "SELIC_TARGET", "--all"])
