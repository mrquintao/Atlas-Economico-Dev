from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.core.config import Settings
from app.integrations.bcb.sgs import SGSClient, SGSError, SGSPayloadError, SGSUnavailableError
from tests.conftest import load_fixture, sgs_json


def make_client(settings: Settings, handler) -> tuple[SGSClient, list[float]]:
    sleeps: list[float] = []
    client = SGSClient(settings, transport=httpx.MockTransport(handler), sleep=sleeps.append)
    return client, sleeps


def html_400() -> httpx.Response:
    return httpx.Response(
        400, content=load_fixture("sgs_html_error.html"), headers={"content-type": "text/html"}
    )


def test_fetch_window_sends_documented_parameters(settings: Settings) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return sgs_json([("01/01/2024", "11.75")])

    client, _ = make_client(settings, handler)
    result = client.fetch_window("432", date(2024, 1, 1), date(2024, 1, 31))

    assert seen[0].url.path == "/dados/serie/bcdata.sgs.432/dados"
    assert dict(seen[0].url.params) == {
        "formato": "json",
        "dataInicial": "01/01/2024",
        "dataFinal": "31/01/2024",
    }
    assert result.points[0].value == Decimal("11.75")
    assert result.payload_sha256 and len(result.payload_sha256) == 64


def test_retries_transient_html_error_with_exponential_backoff(settings: Settings) -> None:
    responses = [html_400(), html_400(), sgs_json([("01/01/2024", "11.75")])]
    client, sleeps = make_client(settings, lambda _: responses.pop(0))
    result = client.fetch_window("432", date(2024, 1, 1), date(2024, 1, 1))
    assert len(result.points) == 1
    assert sleeps == [0.01, 0.02]


def test_retries_timeouts_then_gives_up(settings: Settings) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out", request=request)

    client, sleeps = make_client(settings, handler)
    with pytest.raises(SGSUnavailableError, match="4 attempts"):
        client.fetch_window("432", date(2024, 1, 1), date(2024, 1, 1))
    assert calls == settings.http_max_retries + 1
    assert sleeps == [0.01, 0.02, 0.04]


@pytest.mark.parametrize("status", [500, 502, 503, 429])
def test_retries_server_errors(settings: Settings, status: int) -> None:
    responses = [httpx.Response(status), sgs_json([("01/01/2024", "1")])]
    client, _ = make_client(settings, lambda _: responses.pop(0))
    assert len(client.fetch_window("432", date(2024, 1, 1), date(2024, 1, 1)).points) == 1


def test_404_json_means_no_data(settings: Settings) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"erro": {"statusCode": 404, "detail": "Value(s) not found"}},
        )

    client, sleeps = make_client(settings, handler)
    result = client.fetch_window("432", date(2030, 1, 1), date(2030, 1, 10))
    assert result.points == []
    assert sleeps == []


def test_406_json_window_too_large_is_not_retried(settings: Settings) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            406, json={"error": "O sistema aceita uma janela de consulta de, no máximo, 10 anos"}
        )

    client, _ = make_client(settings, handler)
    with pytest.raises(SGSPayloadError, match="rejected"):
        client.fetch_window("432", date(2000, 1, 1), date(2024, 12, 31))
    assert calls == 1


def test_unexpected_status_raises(settings: Settings) -> None:
    client, _ = make_client(settings, lambda _: httpx.Response(403))
    with pytest.raises(SGSError, match="403"):
        client.fetch_window("432", date(2024, 1, 1), date(2024, 1, 1))


def test_rejects_dates_outside_requested_window(settings: Settings) -> None:
    client, _ = make_client(settings, lambda _: sgs_json([("05/01/2024", "1")]))
    with pytest.raises(SGSPayloadError, match="outside"):
        client.fetch_window("432", date(2024, 1, 1), date(2024, 1, 2))


def test_malformed_json_raises(settings: Settings) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"[{", headers={"content-type": "application/json"})

    client, _ = make_client(settings, handler)
    with pytest.raises(SGSPayloadError, match="Malformed"):
        client.fetch_window("432", date(2024, 1, 1), date(2024, 1, 1))


def test_fetch_series_splits_daily_series_into_windows(settings: Settings) -> None:
    requested: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append((request.url.params["dataInicial"], request.url.params["dataFinal"]))
        return sgs_json([])

    client, _ = make_client(settings.model_copy(update={"bcb_daily_window_years": 1}), handler)
    client.fetch_series("432", date(2022, 6, 1), date(2024, 12, 31))
    assert requested == [
        ("01/06/2022", "31/05/2023"),
        ("01/06/2023", "31/05/2024"),
        ("01/06/2024", "31/12/2024"),
    ]


def test_persistent_html_400_hints_at_wrong_series_code(settings: Settings) -> None:
    client, _ = make_client(settings, lambda _: html_400())
    with pytest.raises(SGSUnavailableError, match="check that the series code exists"):
        client.fetch_window("99999999", date(2024, 1, 1), date(2024, 1, 1))
