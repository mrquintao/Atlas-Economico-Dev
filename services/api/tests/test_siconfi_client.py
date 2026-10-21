"""SICONFI connector (S3): parsing, pagination, retries, validation and the rate limiter.

The ``siconfi_*_sample.json`` fixtures are REAL excerpts of the official API (see
tests/fixtures/README.md); every other payload here is SYNTHETIC. HTTP is httpx.MockTransport.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.tesouro import siconfi
from app.integrations.tesouro.siconfi import (
    RateLimiter,
    ReportRequest,
    ReportRow,
    SiconfiClient,
    SiconfiError,
    SiconfiPayloadError,
    SiconfiUnavailableError,
    latest_delivery,
    rows_hash,
)
from tests.conftest import load_fixture

RGF_SP = ReportRequest("RGF", 2024, 3, "RGF-Anexo 02", "35", "E", "E", "Q")
RREO_SP = ReportRequest("RREO", 2024, 6, "RREO-Anexo 03", "35")


class FakeClock:
    """Monotonic clock that only moves when the code under test sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def page(items: list[Any], has_more: bool = False, offset: int = 0) -> httpx.Response:
    body = {"items": items, "hasMore": has_more, "limit": 5000, "offset": offset}
    return httpx.Response(200, content=json.dumps(body))


def make_client(
    settings: Settings, handler: Callable[[httpx.Request], httpx.Response], clock: FakeClock
) -> SiconfiClient:
    return SiconfiClient(
        settings, transport=httpx.MockTransport(handler), sleep=clock.sleep, clock=clock
    )


def rgf_item(**overrides: Any) -> dict[str, Any]:
    """A synthetic RGF row matching RGF_SP."""
    item = {
        "exercicio": 2024,
        "periodo": 3,
        "periodicidade": "Q",
        "instituicao": "Governo (sintético)",
        "cod_ibge": 35,
        "co_poder": "E",
        "populacao": 1000,
        "anexo": "RGF-Anexo 02",
        "esfera": "E",
        "rotulo": "Padrão",
        "coluna": "C1",
        "cod_conta": "Conta",
        "conta": "CONTA SINTÉTICA",
        "valor": 1.5,
    }
    return {**item, **overrides}


def test_parses_real_rgf_excerpt_with_exact_decimals(settings: Settings) -> None:
    body = load_fixture("siconfi_rgf_anexo02_sp_2024_q3_sample.json")
    client = make_client(settings, lambda _: httpx.Response(200, content=body), FakeClock())
    result = client.fetch_report(RGF_SP)
    assert len(result.rows) == 6
    assert result.institution == "Governo do Estado de São Paulo"
    assert result.population == 46024937
    first = result.rows[0]
    assert first.key == (
        "Padrão",
        "SALDO DO EXERCÍCIO ANTERIOR",
        "DividaConsolidada",
        "DÍVIDA CONSOLIDADA - DC (I)",
    )
    assert first.value == Decimal("347336600618.37")
    assert str(first.value) == "347336600618.37"  # parsed from the JSON text, never via float
    assert result.pages == 1
    assert "no_anexo=RGF-Anexo+02" in result.url and "co_poder=E" in result.url


def test_parses_real_rreo_excerpt(settings: Settings) -> None:
    body = load_fixture("siconfi_rreo_anexo03_sp_2024_b6_sample.json")
    client = make_client(settings, lambda _: httpx.Response(200, content=body), FakeClock())
    result = client.fetch_report(RREO_SP)
    assert [r.value for r in result.rows][:2] == [
        Decimal("38251989923.43"),
        Decimal("29617962827.16"),
    ]
    assert "co_poder" not in result.url and "in_periodicidade" not in result.url


def test_values_with_many_digits_stay_exact(settings: Settings) -> None:
    item = json.dumps(rgf_item()).replace('"valor": 1.5', '"valor": 9007199254740993.99')
    body = '{"items": [' + item + '], "hasMore": false}'
    client = make_client(settings, lambda _: httpx.Response(200, content=body), FakeClock())
    assert client.fetch_report(RGF_SP).rows[0].value == Decimal("9007199254740993.99")


def test_follows_pagination_until_has_more_is_false(settings: Settings) -> None:
    rows = [rgf_item(coluna=f"C{i}", valor=i) for i in range(7)]
    offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        chunk = rows[offset : offset + 3]  # the server pages by 3 regardless of `limit`
        return page(chunk, has_more=offset + 3 < len(rows), offset=offset)

    result = make_client(settings, handler, FakeClock()).fetch_report(RGF_SP)
    assert offsets == [0, 3, 6]
    assert result.pages == 3
    assert [r.value for r in result.rows] == [Decimal(i) for i in range(7)]


def test_rejects_page_that_does_not_advance(settings: Settings) -> None:
    client = make_client(settings, lambda _: page([], has_more=True), FakeClock())
    with pytest.raises(SiconfiPayloadError, match="empty page"):
        client.fetch_report(RGF_SP)


def test_rejects_pagination_that_never_ends(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(siconfi, "MAX_PAGES", 3)

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        return page([rgf_item(coluna=f"C{offset}")], has_more=True, offset=offset)

    with pytest.raises(SiconfiPayloadError, match="did not end"):
        make_client(settings, handler, FakeClock()).fetch_report(RGF_SP)


def test_rejects_page_with_unexpected_offset(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return page([rgf_item(coluna=request.url.params["offset"])], has_more=True, offset=0)

    with pytest.raises(SiconfiPayloadError, match="offset"):
        make_client(settings, handler, FakeClock()).fetch_report(RGF_SP)


def test_retries_429_5xx_and_non_json_with_backoff(settings: Settings) -> None:
    responses = iter(
        [
            httpx.Response(429),
            httpx.Response(503),
            httpx.Response(200, content=b"<html>manutencao</html>"),
            page([rgf_item()]),
        ]
    )
    clock = FakeClock()
    client = make_client(settings, lambda _: next(responses), clock)
    assert len(client.fetch_report(RGF_SP).rows) == 1
    assert client.requests_made == 4
    # Backoff: 0.01, 0.02, 0.04 s (settings fixture), topped up to the 1.1 s rate limit.
    assert [round(s, 2) for s in clock.sleeps] == [0.01, 1.09, 0.02, 1.08, 0.04, 1.06]


def test_retries_transport_errors(settings: Settings) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("connection refused", request=request)
        return page([rgf_item()])

    assert len(make_client(settings, handler, FakeClock()).fetch_report(RGF_SP).rows) == 1


def test_gives_up_after_max_retries(settings: Settings) -> None:
    client = make_client(settings, lambda _: httpx.Response(502), FakeClock())
    with pytest.raises(SiconfiUnavailableError, match="4 attempts: HTTP 502"):
        client.fetch_report(RGF_SP)
    assert client.requests_made == settings.http_max_retries + 1


def test_permanent_http_error_is_not_retried(settings: Settings) -> None:
    client = make_client(settings, lambda _: httpx.Response(404), FakeClock())
    with pytest.raises(SiconfiError, match="Unexpected HTTP 404"):
        client.fetch_report(RGF_SP)
    assert client.requests_made == 1


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"cod_ibge": 33}, "cod_ibge"),
        ({"anexo": "RGF-Anexo 01"}, "anexo"),
        ({"periodo": 2}, "periodo"),
        ({"co_poder": "L"}, "co_poder"),
        ({"esfera": "M"}, "esfera"),
        ({"valor": "1,5"}, "Non-numeric"),
        ({"valor": None}, "Non-numeric"),
        ({"valor": True}, "Non-numeric"),
        ({"conta": None}, "conta"),
    ],
)
def test_rejects_invalid_rows(settings: Settings, override: dict[str, Any], message: str) -> None:
    client = make_client(settings, lambda _: page([rgf_item(**override)]), FakeClock())
    with pytest.raises(SiconfiPayloadError, match=message):
        client.fetch_report(RGF_SP)


@pytest.mark.parametrize("body", ['{"hasMore": false}', '{"items": [], "hasMore": "no"}', "[]"])
def test_rejects_malformed_pages(settings: Settings, body: str) -> None:
    client = make_client(settings, lambda _: httpx.Response(200, content=body), FakeClock())
    with pytest.raises(SiconfiError):
        client.fetch_report(RGF_SP)


def test_rejects_duplicate_rows(settings: Settings) -> None:
    client = make_client(settings, lambda _: page([rgf_item(), rgf_item(valor=2)]), FakeClock())
    with pytest.raises(SiconfiPayloadError, match="Duplicate row"):
        client.fetch_report(RGF_SP)


def test_empty_result_is_not_an_error(settings: Settings) -> None:
    result = make_client(settings, lambda _: page([]), FakeClock()).fetch_report(RGF_SP)
    assert result.rows == []


def test_rate_limiter_spaces_requests_by_at_least_one_second(settings: Settings) -> None:
    """Deterministic proof of the ≤ 1 request/s limit, retries and pagination included."""
    clock = FakeClock()
    request_times: list[float] = []
    responses = iter([httpx.Response(503), page([rgf_item()], has_more=True), page([], offset=1)])

    def handler(request: httpx.Request) -> httpx.Response:
        request_times.append(clock())
        return next(responses)

    client = make_client(settings, handler, clock)
    client.fetch_report(RGF_SP)
    responses = iter([page([rgf_item()])])  # a second report: the limiter state carries over
    client.fetch_report(RGF_SP)
    gaps = [b - a for a, b in pairwise(request_times)]
    assert len(request_times) == 4
    assert all(gap >= 1.0 for gap in gaps), gaps
    assert min(gaps) == pytest.approx(settings.siconfi_min_request_interval_seconds)


def test_rate_limiter_does_not_sleep_when_requests_are_already_spaced() -> None:
    clock = FakeClock()
    limiter = RateLimiter(1.0, clock=clock, sleep=clock.sleep)
    limiter.wait()
    clock.now += 5
    limiter.wait()
    assert clock.sleeps == []


def test_minimum_interval_cannot_be_configured_below_the_official_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(siconfi_min_request_interval_seconds=0.5)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"report_type": "DCA", "annex": "DCA-Anexo I"},
        {"period": 7},
        {"annex": "RGF-Anexo 02"},
        {"power": "E"},
        {"periodicity": "Q"},
        {"entity_code": "SP"},
        {"sphere": "D"},  # DF is queried with sphere E; "D" is not a co_esfera value
    ],
)
def test_report_request_validation(kwargs: dict[str, Any]) -> None:
    base: dict[str, Any] = {
        "report_type": "RREO",
        "exercise": 2024,
        "period": 1,
        "annex": "RREO-Anexo 03",
        "entity_code": "35",
    }
    with pytest.raises(SiconfiError):
        ReportRequest(**{**base, **kwargs})


def test_semiannual_rgf_is_not_supported() -> None:
    # "S" is the simplified RGF of small municipalities ("RGF Simplificado"), out of scope.
    with pytest.raises(SiconfiError, match="Periodicity"):
        ReportRequest("RGF", 2024, 1, "RGF-Anexo 02", "35", "E", "E", "S")


def test_rgf_requires_power() -> None:
    with pytest.raises(SiconfiError, match="power"):
        ReportRequest("RGF", 2024, 1, "RGF-Anexo 02", "35", "E", None, "Q")


def test_deliveries_from_real_excerpt(settings: Settings) -> None:
    body = load_fixture("siconfi_extrato_sp_2024_sample.json")
    client = make_client(settings, lambda _: httpx.Response(200, content=body), FakeClock())
    deliveries = client.fetch_deliveries("35", 2024)
    assert len(deliveries) == 19
    # RREO: delivered only by the executive; the 6th bimester was rectified (RE) in 2025-04.
    assert latest_delivery(deliveries, "RREO", 6, "B") == datetime(
        2025, 4, 30, 22, 31, 7, tzinfo=UTC
    )
    # RGF: latest across every body (the executive rectified after the court of justice).
    assert latest_delivery(deliveries, "RGF", 3, "Q") == datetime(
        2025, 5, 28, 21, 6, 35, tzinfo=UTC
    )
    assert latest_delivery(deliveries, "RGF", 3, "S") is None
    assert latest_delivery(deliveries, "RREO", 6, "Q") is None


def test_deliveries_of_another_entity_are_rejected(settings: Settings) -> None:
    body = load_fixture("siconfi_extrato_sp_2024_sample.json")
    client = make_client(settings, lambda _: httpx.Response(200, content=body), FakeClock())
    with pytest.raises(SiconfiPayloadError, match="another entity"):
        client.fetch_deliveries("33", 2024)


def test_rows_hash_ignores_order_but_not_values() -> None:
    a = ReportRow("r", "c1", "k", "conta", Decimal("1.50"))
    b = ReportRow("r", "c2", "k", "conta", Decimal("2"))
    assert rows_hash([a, b]) == rows_hash([b, a])
    assert rows_hash([a, b]) != rows_hash([a, ReportRow("r", "c2", "k", "conta", Decimal("3"))])
    # Same numbers written differently (trailing zeros, stored NUMERIC scale) hash the same.
    same = [
        ReportRow("r", "c1", "k", "conta", Decimal("1.5")),
        ReportRow("r", "c2", "k", "conta", Decimal("2.00000000")),
    ]
    assert rows_hash(same) == rows_hash([a, b])
