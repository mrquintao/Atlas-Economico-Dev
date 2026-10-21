"""IBGE mesh connector tests (no network: httpx.MockTransport).

`ibge_malhas_uf_2022_minima_sample.json` is a real, reduced IBGE response (see fixtures/README.md);
every other geometry here is synthetic.
"""

import json
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.integrations.ibge.malhas import (
    MalhasClient,
    MalhasError,
    MalhasPayloadError,
    MalhasUnavailableError,
    geometry_hash,
    parse_boundaries_payload,
    parse_geometry,
)
from tests.conftest import load_fixture

SAMPLE = "ibge_malhas_uf_2022_minima_sample.json"
# Synthetic square inside Brazil.
SQUARE = [[[-48.0, -16.0], [-47.0, -16.0], [-47.0, -15.0], [-48.0, -15.0], [-48.0, -16.0]]]


def feature(code: Any, geometry: Any = None) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": geometry or {"type": "Polygon", "coordinates": SQUARE},
        "properties": {"codarea": code},
    }


def collection(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


def geojson_response(payload: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status, content=json.dumps(payload), headers={"content-type": "application/vnd.geo+json"}
    )


def client_for(settings: Settings, handler, sleep=lambda _: None) -> MalhasClient:
    return MalhasClient(settings, transport=httpx.MockTransport(handler), sleep=sleep)


# --- parsing ---


def test_parses_real_sample() -> None:
    boundaries = parse_boundaries_payload(json.loads(load_fixture(SAMPLE)))
    assert [b.ibge_code for b in boundaries] == ["16", "28", "53"]
    kinds = {b.ibge_code: b.geometry["type"] for b in boundaries}
    assert kinds == {"16": "MultiPolygon", "28": "Polygon", "53": "Polygon"}
    # The IBGE `minima` mesh already has at most 4 decimals: quantisation leaves it unchanged.
    features = json.loads(load_fixture(SAMPLE))["features"]
    original = {f["properties"]["codarea"]: f["geometry"] for f in features}
    for boundary in boundaries:
        assert boundary.geometry == original[boundary.ibge_code]
        assert boundary.geometry_hash == geometry_hash(original[boundary.ibge_code])


def test_quantises_coordinates_to_4_decimals() -> None:
    ring = [[-48.123456, -16.0], [-47.0, -16.0], [-47.0, -15.000049], [-48.123456, -16.0]]
    geometry = parse_geometry({"type": "Polygon", "coordinates": [ring]}, "test")
    assert geometry["coordinates"][0][0] == [-48.1235, -16.0]
    assert geometry["coordinates"][0][2] == [-47.0, -15.0]


def test_geometry_hash_ignores_key_order() -> None:
    a = {"type": "Polygon", "coordinates": SQUARE}
    b = {"coordinates": SQUARE, "type": "Polygon"}
    assert geometry_hash(a) == geometry_hash(b)
    assert geometry_hash(a) != geometry_hash({"type": "MultiPolygon", "coordinates": [SQUARE]})


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "FeatureCollection"),
        ({"type": "Feature"}, "FeatureCollection"),
        (collection(), "without features"),
        ({"type": "FeatureCollection", "features": [{"type": "Point"}]}, "Unexpected item"),
        (collection(feature(53)), "Invalid codarea"),
        (collection(feature("DF")), "Invalid codarea"),
        (collection({"type": "Feature", "geometry": None, "properties": None}), "codarea"),
        (collection(feature("53"), feature("53")), "Duplicate codarea"),
        (collection(feature("53", {"type": "Point", "coordinates": [-47, -15]})), "Unsupported"),
        (collection(feature("53", {"type": "Polygon", "coordinates": []})), "without rings"),
        (
            collection(feature("53", {"type": "Polygon", "coordinates": [SQUARE[0][:3]]})),
            "fewer than 4",
        ),
        (
            collection(feature("53", {"type": "Polygon", "coordinates": [SQUARE[0][:4]]})),
            "not closed",
        ),
        (
            collection(
                feature("53", {"type": "Polygon", "coordinates": [[[0.0, 0.0]] * 4]}),
            ),
            "outside Brazil",
        ),
        (
            collection(
                feature("53", {"type": "Polygon", "coordinates": [[[-47.0, True]] * 4]}),
            ),
            "Invalid position",
        ),
        (
            collection(
                feature("53", {"type": "Polygon", "coordinates": [[[-47.0, -15.0, 1.0]] * 4]}),
            ),
            "Invalid position",
        ),
        (collection(feature("53", {"type": "MultiPolygon", "coordinates": []})), "MultiPolygon"),
    ],
)
def test_rejects_invalid_payloads(payload: Any, message: str) -> None:
    with pytest.raises(MalhasPayloadError, match=message):
        parse_boundaries_payload(payload)


def test_rejects_non_finite_coordinates() -> None:
    ring = [[-47.0, -15.0], [float("nan"), -15.0], [-47.0, -16.0], [-47.0, -15.0]]
    with pytest.raises(MalhasPayloadError, match="Non-finite"):
        parse_geometry({"type": "Polygon", "coordinates": [ring]}, "test")


# --- HTTP client ---


def test_requests_state_mesh_with_edition_and_quality(settings: Settings) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, content=load_fixture(SAMPLE))

    with client_for(settings, handler) as client:
        result = client.fetch_state_boundaries(2022)
    assert len(seen) == 1
    assert seen[0].url.path == "/api/v3/malhas/paises/BR"
    assert dict(seen[0].url.params) == {
        "formato": "application/vnd.geo+json",
        "intrarregiao": "UF",
        "qualidade": "minima",
        "periodo": "2022",
    }
    assert result.url == str(seen[0].url)
    assert (result.mesh_year, result.quality) == (2022, "minima")
    assert [b.ibge_code for b in result.boundaries] == ["16", "28", "53"]
    assert len(result.content_hash) == 64


def test_rejects_unknown_quality(settings: Settings) -> None:
    client = client_for(settings, lambda _: httpx.Response(200))
    with client, pytest.raises(MalhasError, match="quality"):
        client.fetch_state_boundaries(2022, "alta")


def test_retries_server_errors_and_non_json_then_succeeds(settings: Settings) -> None:
    responses = iter(
        [
            httpx.Response(500, content=b'{"statusCode":500}'),
            httpx.Response(200, content=b"<html>manutencao</html>"),
            geojson_response(collection(feature("53"))),
        ]
    )
    delays: list[float] = []
    with client_for(settings, lambda _: next(responses), sleep=delays.append) as client:
        result = client.fetch_state_boundaries(2022)
    assert [b.ibge_code for b in result.boundaries] == ["53"]
    assert delays == [0.01, 0.02]  # exponential backoff


def test_gives_up_after_max_attempts(settings: Settings) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls % 2:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(503)

    client = client_for(settings, handler)
    with client, pytest.raises(MalhasUnavailableError, match="after 4 attempts"):
        client.fetch_state_boundaries(2023)
    assert calls == settings.http_max_retries + 1


def test_permanent_errors_are_not_retried(settings: Settings) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    with client_for(settings, handler) as client, pytest.raises(MalhasError, match="HTTP 404"):
        client.fetch_state_boundaries(2022)
    assert calls == 1


def test_invalid_payload_is_not_retried(settings: Settings) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return geojson_response(collection(feature("53"), feature("53")))

    with client_for(settings, handler) as client, pytest.raises(MalhasPayloadError):
        client.fetch_state_boundaries(2022)
    assert calls == 1


def test_throttles_consecutive_requests() -> None:
    settings = Settings(ibge_min_request_interval_seconds=0.5, http_backoff_base_seconds=0)
    responses = iter([httpx.Response(503), geojson_response(collection(feature("53")))])
    delays: list[float] = []
    with client_for(settings, lambda _: next(responses), sleep=delays.append) as client:
        client.fetch_state_boundaries(2022)
    # No wait before the first request; ~0.5 s before the second (backoff itself is 0 here).
    throttle = [d for d in delays if d > 0]
    assert len(throttle) == 1 and 0.4 < throttle[0] <= 0.5
