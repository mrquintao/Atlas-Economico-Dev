"""Connector for the IBGE geographic mesh API (official boundaries, GeoJSON).

Endpoint used (documented at https://servicodados.ibge.gov.br/api/docs/malhas?versao=3):

    GET {base_url}/paises/BR?formato=application/vnd.geo+json&intrarregiao=UF
        &qualidade={quality}&periodo={mesh_year}

The response is a GeoJSON ``FeatureCollection`` with one feature per federative unit, each
carrying only ``properties.codarea`` (the UF's IBGE code, e.g. ``"53"``) and a ``Polygon`` or
``MultiPolygon`` geometry in longitude/latitude (WGS 84 order).

Observed behaviour this connector relies on (verified 2026-10-21):
- ``periodo`` selects the mesh edition; 2022 is the latest one served (also the default when the
  parameter is omitted); 2023 and later answer HTTP 500, so a missing edition is a server error,
  not a 404.
- ``qualidade=minima`` is the IBGE's own generalised (simplified) mesh: 27 features, ~98 KB,
  coordinates with at most 4 decimal places (~11 m). ``intermediaria`` is ~250 KB and
  ``maxima`` ~1 MB.
- Responses carry ``Cache-Control: max-age=604800`` (meshes change at most yearly).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MALHAS_DOCUMENTATION_URL = "https://servicodados.ibge.gov.br/api/docs/malhas?versao=3"
QUALITIES = ("minima", "intermediaria", "maxima")
# Explicit quantisation of the stored coordinates (no-op on the IBGE `minima` mesh, which
# already has at most 4 decimals): 1e-4 degree is ~11 m, far below what a national map shows.
COORDINATE_DECIMALS = 4
# Generous bounding box of Brazil including its oceanic islands (Trindade at -29.3 longitude).
_LON_RANGE = (-75.0, -28.0)
_LAT_RANGE = (-34.5, 6.0)


class MalhasError(Exception):
    """Base error for IBGE mesh integration failures."""


class MalhasPayloadError(MalhasError):
    """The response did not match the expected structure."""


class MalhasUnavailableError(MalhasError):
    """The service could not be reached or kept failing after retries."""


@dataclass(frozen=True)
class AreaBoundary:
    """Boundary of one area as served by the IBGE (geometry already quantised)."""

    ibge_code: str
    geometry: dict[str, Any]
    geometry_hash: str


@dataclass(frozen=True)
class BoundariesResult:
    url: str
    mesh_year: int
    quality: str
    boundaries: list[AreaBoundary]
    content_hash: str


def geometry_hash(geometry: dict[str, Any]) -> str:
    """SHA-256 of the canonical JSON of a geometry (key order and spacing independent)."""
    canonical = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _quantise_position(position: Any, where: str) -> list[float]:
    if (
        not isinstance(position, list)
        or len(position) != 2
        or not all(isinstance(c, int | float) and not isinstance(c, bool) for c in position)
    ):
        raise MalhasPayloadError(f"Invalid position in {where}: {position!r}")
    lon, lat = (float(c) for c in position)
    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise MalhasPayloadError(f"Non-finite position in {where}: {position!r}")
    if not (_LON_RANGE[0] <= lon <= _LON_RANGE[1] and _LAT_RANGE[0] <= lat <= _LAT_RANGE[1]):
        raise MalhasPayloadError(f"Position outside Brazil in {where}: {position!r}")
    return [round(lon, COORDINATE_DECIMALS), round(lat, COORDINATE_DECIMALS)]


def _parse_polygon(rings: Any, where: str) -> list[list[list[float]]]:
    if not isinstance(rings, list) or not rings:
        raise MalhasPayloadError(f"Polygon without rings in {where}")
    parsed: list[list[list[float]]] = []
    for ring in rings:
        if not isinstance(ring, list) or len(ring) < 4:
            raise MalhasPayloadError(f"Ring with fewer than 4 positions in {where}")
        positions = [_quantise_position(p, where) for p in ring]
        if positions[0] != positions[-1]:
            raise MalhasPayloadError(f"Ring not closed in {where}")
        parsed.append(positions)
    return parsed


def parse_geometry(geometry: Any, where: str) -> dict[str, Any]:
    """Validate a Polygon/MultiPolygon and return it with quantised coordinates."""
    if not isinstance(geometry, dict):
        raise MalhasPayloadError(f"Missing geometry in {where}")
    kind, coordinates = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        return {"type": "Polygon", "coordinates": _parse_polygon(coordinates, where)}
    if kind == "MultiPolygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise MalhasPayloadError(f"MultiPolygon without polygons in {where}")
        polygons = [_parse_polygon(polygon, where) for polygon in coordinates]
        return {"type": "MultiPolygon", "coordinates": polygons}
    raise MalhasPayloadError(f"Unsupported geometry type {kind!r} in {where}")


def parse_boundaries_payload(payload: Any) -> list[AreaBoundary]:
    """Validate an IBGE mesh FeatureCollection and return one boundary per area code.

    Raises ``MalhasPayloadError`` on structural problems, invalid geometries, missing or
    duplicate area codes.
    """
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise MalhasPayloadError("Expected a GeoJSON FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise MalhasPayloadError("FeatureCollection without features")
    boundaries: dict[str, AreaBoundary] = {}
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise MalhasPayloadError(f"Unexpected item at position {index}")
        properties = feature.get("properties")
        code = properties.get("codarea") if isinstance(properties, dict) else None
        if not isinstance(code, str) or not code.isdigit():
            raise MalhasPayloadError(f"Invalid codarea at position {index}: {code!r}")
        if code in boundaries:
            raise MalhasPayloadError(f"Duplicate codarea in payload: {code}")
        geometry = parse_geometry(feature.get("geometry"), f"codarea {code}")
        boundaries[code] = AreaBoundary(code, geometry, geometry_hash(geometry))
    return sorted(boundaries.values(), key=lambda b: b.ibge_code)


class MalhasClient:
    """HTTP client for the IBGE mesh API with timeouts, retry with backoff and rate limiting."""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or get_settings()
        self._sleep = sleep
        self._last_request_at: float | None = None
        self._client = httpx.Client(
            base_url=self.settings.ibge_malhas_base_url,
            timeout=httpx.Timeout(self.settings.http_timeout_seconds),
            headers={
                "User-Agent": self.settings.http_user_agent,
                "Accept": "application/vnd.geo+json, application/json",
            },
            transport=transport,
        )

    def __enter__(self) -> MalhasClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        interval = self.settings.ibge_min_request_interval_seconds
        if self._last_request_at is not None and interval > 0:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < interval:
                self._sleep(interval - elapsed)
        self._last_request_at = time.monotonic()

    def fetch_state_boundaries(self, mesh_year: int, quality: str = "minima") -> BoundariesResult:
        """Boundaries of the 27 federative units in the given mesh edition."""
        if quality not in QUALITIES:
            raise MalhasError(f"Unknown mesh quality {quality!r}; expected one of {QUALITIES}")
        params = {
            "formato": "application/vnd.geo+json",
            "intrarregiao": "UF",
            "qualidade": quality,
            "periodo": str(mesh_year),
        }
        max_attempts = self.settings.http_max_retries + 1
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            self._throttle()
            try:
                response = self._client.get("/paises/BR", params=params)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                result = self._interpret(response, mesh_year, quality)
                if result is not None:
                    return result
                last_error = f"HTTP {response.status_code}"
            if attempt < max_attempts:
                delay = self.settings.http_backoff_base_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "malhas_request_retry",
                    extra={"mesh_year": mesh_year, "attempt": attempt, "delay_s": delay},
                )
                self._sleep(delay)
        raise MalhasUnavailableError(
            f"IBGE state mesh {mesh_year} ({quality}) failed after {max_attempts} attempts: "
            f"{last_error}"
        )

    def _interpret(
        self, response: httpx.Response, mesh_year: int, quality: str
    ) -> BoundariesResult | None:
        """Return a result, raise for permanent errors, or ``None`` to retry."""
        url = str(response.request.url)
        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError:
                return None  # 200 with a non-JSON body (e.g. maintenance page): retry
            return BoundariesResult(
                url=url,
                mesh_year=mesh_year,
                quality=quality,
                boundaries=parse_boundaries_payload(payload),
                content_hash=hashlib.sha256(response.content).hexdigest(),
            )
        if response.status_code in _RETRYABLE_STATUS:
            return None
        raise MalhasError(f"Unexpected HTTP {response.status_code} from {url}")
