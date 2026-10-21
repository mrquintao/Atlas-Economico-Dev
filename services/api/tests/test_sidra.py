"""SIDRA connector and IPCA_12M ingestion tests. Values are synthetic (not official data)."""

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.series_ingestion import (
    IngestionError,
    ingest_sgs_indicator,
    ingest_sidra_indicator,
)
from app.integrations.ibge.sidra import (
    SIDRAClient,
    SIDRAError,
    SIDRAPayloadError,
    SIDRAUnavailableError,
    parse_sidra_month,
    parse_sidra_payload,
    parse_sidra_value,
    split_series_code,
)
from app.models import Observation, ObservationRevision

HEADER = {
    "NC": "Nível Territorial (Código)",
    "MC": "Unidade de Medida (Código)",
    "V": "Valor",
    "D1C": "Brasil (Código)",
    "D2C": "Variável (Código)",
    "D3C": "Mês (Código)",
}


def row(month: str, value: str, unit: str = "2", variable: str = "2265") -> dict[str, str]:
    return {"NC": "1", "MC": unit, "V": value, "D1C": "1", "D2C": variable, "D3C": month}


def sidra_response(rows: list[dict[str, str]], status: int = 200) -> httpx.Response:
    return httpx.Response(
        status, content=json.dumps([HEADER, *rows]), headers={"content-type": "application/json"}
    )


def client_for(settings: Settings, handler) -> SIDRAClient:
    return SIDRAClient(settings, transport=httpx.MockTransport(handler), sleep=lambda _: None)


# --- parsing ---


def test_parse_month() -> None:
    assert parse_sidra_month("202609") == date(2026, 9, 1)
    for bad in ("2026", "202613", "20260a", "202600"):
        with pytest.raises(SIDRAPayloadError):
            parse_sidra_month(bad)


@pytest.mark.parametrize("raw", ["...", "..", "-", "X", "x", "", None])
def test_missing_markers_are_none_never_zero(raw) -> None:
    assert parse_sidra_value(raw) is None


def test_parse_value() -> None:
    assert parse_sidra_value("4.58") == Decimal("4.58")
    assert parse_sidra_value("-0.10") == Decimal("-0.10")
    for bad in ("abc", "NaN", "Infinity"):
        with pytest.raises(SIDRAPayloadError):
            parse_sidra_value(bad)


def test_payload_skips_missing_and_sorts() -> None:
    payload = [HEADER, row("202002", "3.2"), row("198012", "..."), row("202001", "3.1")]
    points, skipped = parse_sidra_payload(payload, variable="2265", unit_code="2")
    assert skipped == 1
    assert [(p.reference_date, p.value) for p in points] == [
        (date(2020, 1, 1), Decimal("3.1")),
        (date(2020, 2, 1), Decimal("3.2")),
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"erro": "x"},
        [],
        [{"foo": 1}],
        [HEADER, {"V": "1"}],
        [HEADER, row("202001", "1"), row("202001", "2")],  # duplicate month
        [HEADER, row("202001", "1", variable="63")],  # wrong variable
        [HEADER, row("202001", "1", unit="30")],  # wrong unit (index number)
    ],
)
def test_payload_rejects_invalid(payload) -> None:
    with pytest.raises(SIDRAPayloadError):
        parse_sidra_payload(payload, variable="2265", unit_code="2")


def test_series_code() -> None:
    assert split_series_code("1737/2265") == ("1737", "2265")
    with pytest.raises(SIDRAError):
        split_series_code("2265")


# --- connector ---


def test_request_url_and_result(settings: Settings) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return sidra_response([row("202001", "3.1")])

    (result,) = client_for(settings, handler).fetch_series(
        "1737/2265", date(2020, 1, 1), date(2020, 3, 1)
    )
    assert seen[0].url.path == "/values/t/1737/n1/all/v/2265/p/202001-202003/f/c"
    assert [p.value for p in result.points] == [Decimal("3.1")]
    assert result.payload_sha256


def test_retries_transient_errors(settings: Settings) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        if calls["n"] == 2:
            return httpx.Response(200, text="<html>maintenance</html>")
        return sidra_response([row("202001", "3.1")])

    (result,) = client_for(settings, handler).fetch_series(
        "1737/2265", date(2020, 1, 1), date(2020, 1, 1)
    )
    assert calls["n"] == 3 and len(result.points) == 1


def test_gives_up_after_retries(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(SIDRAUnavailableError):
        client_for(settings, handler).fetch_series("1737/2265", date(2020, 1, 1), date(2020, 1, 1))


def test_bad_request_and_unexpected_status_are_not_retried(settings: Settings) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, text="Parâmetro inválido")

    with pytest.raises(SIDRAPayloadError):
        client_for(settings, handler).fetch_series("1737/2265", date(2020, 1, 1), date(2020, 1, 1))
    assert calls["n"] == 1
    with pytest.raises(SIDRAError):
        client_for(settings, lambda r: httpx.Response(404)).fetch_series(
            "1737/2265", date(2020, 1, 1), date(2020, 1, 1)
        )


def test_month_outside_window_is_rejected(settings: Settings) -> None:
    with pytest.raises(SIDRAPayloadError):
        client_for(settings, lambda r: sidra_response([row("201901", "1")])).fetch_series(
            "1737/2265", date(2020, 1, 1), date(2020, 3, 1)
        )


def test_daily_not_supported(settings: Settings) -> None:
    with pytest.raises(SIDRAError):
        client_for(settings, lambda r: sidra_response([])).fetch_series(
            "1737/2265", date(2020, 1, 1), date(2020, 3, 1), daily=True
        )


# --- ingestion (PostgreSQL) ---


class FakeSIDRA:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def __call__(self, request: httpx.Request) -> httpx.Response:
        first, last = request.url.path.split("/p/")[1].split("/")[0].split("-")
        return sidra_response(
            [row(m, v) for m, v in sorted(self.values.items()) if first <= m <= last]
        )


@pytest.fixture
def ingest_ipca(db: Session, settings: Settings):
    def run(fake, **kwargs):
        kwargs.setdefault("today", date(2024, 10, 21))
        return ingest_sidra_indicator(db, client_for(settings, fake), "IPCA_12M", **kwargs)

    return run


def test_ingest_idempotent_with_gaps_and_revisions(db: Session, ingest_ipca) -> None:
    values = {"198012": "...", "198101": "100.5", "198102": "101.0", "198103": "-"}
    first = ingest_ipca(FakeSIDRA(values))
    assert (first.received, first.inserted, first.skipped_null) == (2, 2, 2)

    obs = db.scalars(select(Observation).order_by(Observation.reference_date)).all()
    assert [o.reference_date for o in obs] == [date(1981, 1, 1), date(1981, 2, 1)]
    # period_start/period_end are the reference month, not the 12-month window (ADR 0005).
    assert (obs[0].period_start, obs[0].period_end) == (date(1981, 1, 1), date(1981, 1, 31))
    assert obs[0].source_reference == "sidra.t1737.v2265"

    again = ingest_ipca(FakeSIDRA(values))
    assert (again.inserted, again.updated, again.unchanged) == (0, 0, 2)

    values["198101"] = "100.6"
    revised = ingest_ipca(FakeSIDRA(values))
    assert (revised.inserted, revised.updated) == (0, 1)
    revision = db.scalars(select(ObservationRevision)).one()
    assert (revision.previous_value, revision.new_value) == (Decimal("100.50"), Decimal("100.60"))


def test_range_capped_at_today(db: Session, ingest_ipca) -> None:
    summary = ingest_ipca(FakeSIDRA({"202410": "4.0", "202411": "4.1"}), start=date(2024, 10, 1))
    assert summary.end == date(2024, 10, 21)
    assert summary.inserted == 1
    with pytest.raises(IngestionError):  # nothing to collect after today
        ingest_ipca(FakeSIDRA({}), start=date(2024, 11, 1))


def test_source_mismatch_is_rejected(db: Session, settings: Settings) -> None:
    with pytest.raises(IngestionError):
        ingest_sgs_indicator(db, client_for(settings, FakeSIDRA({})), "IPCA_12M")
    with pytest.raises(IngestionError):
        ingest_sidra_indicator(db, client_for(settings, FakeSIDRA({})), "SELIC_TARGET")
