"""Connector for the IBGE SIDRA aggregate-data API.

Endpoint used (documented at https://apisidra.ibge.gov.br/):

    GET {base_url}/values/t/{table}/n1/all/v/{variable}/p/{first}-{last}/f/c

``n1/all`` is the national level and ``f/c`` returns codes only. The response is a JSON array
whose first item is a header (column names) followed by one item per observation, e.g.
``{"NC": "1", "MC": "2", "V": "4.58", "D1C": "1", "D2C": "2265", "D3C": "202609"}`` where
``MC`` is the unit code, ``V`` the value, ``D2C`` the variable and ``D3C`` the month (YYYYMM).

Observed behaviour this connector relies on (verified 2026-10-21, table 1737):
- Values that do not exist are the literal strings ``...`` (not applicable, e.g. a 12-month
  accumulation before 12 months of data exist), ``..`` and ``-`` (nil) or ``X`` (confidential);
  all are treated as missing, never as zero.
- Unit code ``2`` is ``%`` and ``30`` is the index number; the unit is validated so that a
  wrong variable is never ingested silently.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.integrations.bcb.sgs import SGSPoint, SGSWindowResult

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MISSING_MARKERS = {"", "...", "..", "-", "x", "null"}
UNIT_PERCENT = "2"


class SIDRAError(Exception):
    """Base error for SIDRA integration failures."""


class SIDRAPayloadError(SIDRAError):
    """The response did not match the expected structure."""


class SIDRAUnavailableError(SIDRAError):
    """The service could not be reached or kept failing after retries."""


def parse_sidra_month(raw: str) -> date:
    """``"202609"`` -> ``date(2026, 9, 1)`` (monthly values are dated on the 1st)."""
    text = str(raw).strip()
    if len(text) != 6 or not text.isdigit() or not 1 <= int(text[4:]) <= 12:
        raise SIDRAPayloadError(f"Invalid SIDRA month code: {raw!r}")
    return date(int(text[:4]), int(text[4:]), 1)


def parse_sidra_value(raw: Any) -> Decimal | None:
    """Parse a SIDRA value. Returns ``None`` for missing markers (never 0)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text.lower() in _MISSING_MARKERS:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise SIDRAPayloadError(f"Invalid SIDRA value: {raw!r}") from exc
    if not value.is_finite():
        raise SIDRAPayloadError(f"Non-finite SIDRA value: {raw!r}")
    return value


def parse_sidra_payload(
    payload: Any, *, variable: str, unit_code: str
) -> tuple[list[SGSPoint], int]:
    """Validate and convert a SIDRA JSON payload (codes format).

    Returns the points sorted by date and the number of missing values skipped. Raises
    ``SIDRAPayloadError`` on structural problems, a variable or unit other than expected, or
    duplicate months.
    """
    if not isinstance(payload, list) or not payload:
        raise SIDRAPayloadError("Expected a non-empty JSON array")
    header, rows = payload[0], payload[1:]
    # Codes format, national level, monthly periods: anything else (e.g. a quarterly table
    # whose AAAA0N codes look like months) is rejected.
    if (
        not isinstance(header, dict)
        or header.get("V") != "Valor"
        or header.get("D3C") != "Mês (Código)"
        or header.get("D1C") != "Brasil (Código)"
    ):
        raise SIDRAPayloadError(f"Unexpected header row: {header!r}")
    points: dict[date, SGSPoint] = {}
    seen: set[date] = set()
    skipped = 0
    for index, item in enumerate(rows, start=1):
        if not isinstance(item, dict) or not {"V", "D2C", "D3C", "MC"} <= item.keys():
            raise SIDRAPayloadError(f"Unexpected item at position {index}: {item!r}")
        if item["D2C"] != variable:
            raise SIDRAPayloadError(f"Variable {item['D2C']!r} returned, expected {variable!r}")
        if item.get("D1C") != "1":
            raise SIDRAPayloadError(f"Territory {item.get('D1C')!r} returned, expected Brasil (1)")
        reference_date = parse_sidra_month(item["D3C"])
        if reference_date in seen:
            raise SIDRAPayloadError(f"Duplicate month in payload: {item['D3C']}")
        seen.add(reference_date)
        value = parse_sidra_value(item["V"])
        if value is None:
            # Missing rows come with an empty unit code ("MC": ""), so this check comes first.
            skipped += 1
            continue
        if item["MC"] != unit_code:
            raise SIDRAPayloadError(
                f"Unit code {item['MC']!r} for {item['D3C']}, expected {unit_code!r}"
            )
        points[reference_date] = SGSPoint(reference_date, value)
    return sorted(points.values(), key=lambda p: p.reference_date), skipped


def split_series_code(series_code: str) -> tuple[str, str]:
    """``"1737/2265"`` -> ``("1737", "2265")`` (table / variable)."""
    table, _, variable = series_code.partition("/")
    if not table.isdigit() or not variable.isdigit():
        raise SIDRAError(f"SIDRA series code must be 'table/variable', got {series_code!r}")
    return table, variable


class SIDRAClient:
    """HTTP client for SIDRA with timeouts, retry with exponential backoff and rate limiting.

    Exposes ``fetch_series`` with the same shape as ``SGSClient`` so ingestion can use either.
    """

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
            base_url=self.settings.ibge_sidra_base_url,
            timeout=httpx.Timeout(self.settings.http_timeout_seconds),
            headers={"User-Agent": self.settings.http_user_agent, "Accept": "application/json"},
            transport=transport,
        )

    def __enter__(self) -> SIDRAClient:
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

    def fetch_window(self, series_code: str, start: date, end: date) -> SGSWindowResult:
        table, variable = split_series_code(series_code)
        period = f"{start:%Y%m}-{end:%Y%m}"
        path = f"/values/t/{table}/n1/all/v/{variable}/p/{period}/f/c"
        max_attempts = self.settings.http_max_retries + 1
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            self._throttle()
            try:
                response = self._client.get(path)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                result = self._interpret(response, variable, start, end)
                if result is not None:
                    return result
                last_error = f"HTTP {response.status_code}"
            if attempt < max_attempts:
                delay = self.settings.http_backoff_base_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "sidra_request_retry",
                    extra={"series": series_code, "attempt": attempt, "delay_s": delay},
                )
                self._sleep(delay)
        raise SIDRAUnavailableError(
            f"SIDRA series {series_code} window {start}..{end} failed after "
            f"{max_attempts} attempts: {last_error}"
        )

    def _interpret(
        self, response: httpx.Response, variable: str, start: date, end: date
    ) -> SGSWindowResult | None:
        """Return a result, raise for permanent errors, or ``None`` to retry."""
        url = str(response.request.url)
        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError:
                return None  # 200 with a non-JSON body (e.g. maintenance page): retry
            points, skipped = parse_sidra_payload(
                payload, variable=variable, unit_code=UNIT_PERCENT
            )
            for point in points:
                if not start <= point.reference_date <= end:
                    raise SIDRAPayloadError(
                        f"Month {point.reference_date:%Y-%m} outside requested {start}..{end}"
                    )
            return SGSWindowResult(
                start, end, url, points, skipped, hashlib.sha256(response.content).hexdigest()
            )
        if response.status_code in _RETRYABLE_STATUS:
            return None
        if response.status_code == 400:
            raise SIDRAPayloadError(f"SIDRA rejected request {url}: {response.text[:300]}")
        raise SIDRAError(f"Unexpected HTTP {response.status_code} from {url}")

    def fetch_series(
        self, series_code: str, start: date, end: date, *, daily: bool = False
    ) -> list[SGSWindowResult]:
        """Fetch ``[start, end]`` (monthly series; one request covers the whole history)."""
        if daily:
            raise SIDRAError("Daily series are not supported by the SIDRA connector")
        return [self.fetch_window(series_code, start, end)]
