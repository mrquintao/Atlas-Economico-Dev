"""Connector for the Banco Central do Brasil time-series API (SGS / BCData).

Endpoint used (documented at https://dadosabertos.bcb.gov.br/):

    GET {base_url}/bcdata.sgs.{series}/dados
        ?formato=json&dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa

Response: JSON array of ``{"data": "dd/mm/aaaa", "valor": "<decimal with dot>"}``.

Observed behaviour this connector relies on (verified 2026-10-21):
- Daily series reject windows longer than 10 years (HTTP 406 with a JSON error message), so
  requests are split into windows of at most ``MAX_DAILY_WINDOW_YEARS``.
- A window with no data returns HTTP 404 with ``{"erro": {...}}``; it is treated as empty.
- The gateway intermittently answers HTTP 400 with an HTML error page; this is retried.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

MAX_DAILY_WINDOW_YEARS = 10
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class SGSError(Exception):
    """Base error for SGS integration failures."""


class SGSPayloadError(SGSError):
    """The response did not match the expected structure."""


class SGSUnavailableError(SGSError):
    """The service could not be reached or kept failing after retries."""


@dataclass(frozen=True, slots=True)
class SGSPoint:
    reference_date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class SGSWindowResult:
    start: date
    end: date
    url: str
    points: list[SGSPoint]
    skipped_null_values: int
    payload_sha256: str | None


def format_sgs_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def parse_sgs_date(raw: str) -> date:
    try:
        return datetime.strptime(raw.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError) as exc:
        raise SGSPayloadError(f"Invalid SGS date: {raw!r}") from exc


def parse_sgs_value(raw: Any) -> Decimal | None:
    """Parse an SGS value. Returns ``None`` for missing values (never 0)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "" or text.lower() in {"null", "-"}:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise SGSPayloadError(f"Invalid SGS value: {raw!r}") from exc
    if not value.is_finite():
        raise SGSPayloadError(f"Non-finite SGS value: {raw!r}")
    return value


def parse_sgs_payload(payload: Any) -> tuple[list[SGSPoint], int]:
    """Validate and convert an SGS JSON payload.

    Returns the parsed points sorted by date and the number of entries skipped because the
    value was missing. Raises ``SGSPayloadError`` on any structural problem or duplicate date.
    """
    if not isinstance(payload, list):
        raise SGSPayloadError(f"Expected a JSON array, got {type(payload).__name__}")
    points: dict[date, SGSPoint] = {}
    skipped = 0
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or "data" not in item or "valor" not in item:
            raise SGSPayloadError(f"Unexpected item at position {index}: {item!r}")
        reference_date = parse_sgs_date(item["data"])
        value = parse_sgs_value(item["valor"])
        if value is None:
            skipped += 1
            continue
        if reference_date in points:
            raise SGSPayloadError(f"Duplicate date in payload: {reference_date.isoformat()}")
        points[reference_date] = SGSPoint(reference_date, value)
    return sorted(points.values(), key=lambda p: p.reference_date), skipped


def _add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:  # 29 February
        return value.replace(year=value.year + years, day=28)


def split_into_windows(start: date, end: date, max_years: int) -> Iterator[tuple[date, date]]:
    """Split ``[start, end]`` into consecutive inclusive windows spanning < ``max_years``."""
    if start > end:
        raise ValueError("start must be <= end")
    cursor = start
    while cursor <= end:
        window_end = min(_add_years(cursor, max_years) - timedelta(days=1), end)
        yield cursor, window_end
        cursor = window_end + timedelta(days=1)


class SGSClient:
    """HTTP client for SGS with timeouts, retry with exponential backoff and rate limiting."""

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
            base_url=self.settings.bcb_sgs_base_url,
            timeout=httpx.Timeout(self.settings.http_timeout_seconds),
            headers={"User-Agent": self.settings.http_user_agent, "Accept": "application/json"},
            transport=transport,
        )

    def __enter__(self) -> SGSClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        interval = self.settings.bcb_min_request_interval_seconds
        if self._last_request_at is not None and interval > 0:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < interval:
                self._sleep(interval - elapsed)
        self._last_request_at = time.monotonic()

    def fetch_window(self, series_code: str, start: date, end: date) -> SGSWindowResult:
        path = f"/bcdata.sgs.{series_code}/dados"
        params = {
            "formato": "json",
            "dataInicial": format_sgs_date(start),
            "dataFinal": format_sgs_date(end),
        }
        max_attempts = self.settings.http_max_retries + 1
        last_error: str = ""
        for attempt in range(1, max_attempts + 1):
            self._throttle()
            try:
                response = self._client.get(path, params=params)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                outcome = self._interpret(response, start, end)
                if outcome is not None:
                    return outcome
                last_error = (
                    f"HTTP {response.status_code} ({_content_type(response) or 'no content-type'})"
                )
            if attempt < max_attempts:
                delay = self.settings.http_backoff_base_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "sgs_request_retry",
                    extra={
                        "series": series_code,
                        "attempt": attempt,
                        "delay_s": delay,
                        "error": last_error,
                        "window": f"{start}/{end}",
                    },
                )
                self._sleep(delay)
        hint = ""
        if "HTTP 400" in last_error:
            # The gateway answers an unknown series code with the same HTML 400 page it uses
            # for transient failures, so persistent 400s may mean a wrong catalog code.
            hint = " (persistent HTML 400: check that the series code exists in SGS)"
        raise SGSUnavailableError(
            f"SGS series {series_code} window {start}..{end} failed after "
            f"{max_attempts} attempts: {last_error}{hint}"
        )

    def _interpret(
        self, response: httpx.Response, start: date, end: date
    ) -> SGSWindowResult | None:
        """Return a result, raise for permanent errors, or ``None`` to retry."""
        url = str(response.request.url)
        is_json = "json" in _content_type(response)
        if response.status_code == 200 and is_json:
            try:
                payload = response.json()
            except ValueError as exc:
                raise SGSPayloadError(f"Malformed JSON from {url}") from exc
            points, skipped = parse_sgs_payload(payload)
            for point in points:
                if not start <= point.reference_date <= end:
                    raise SGSPayloadError(
                        f"Date {point.reference_date} outside requested window {start}..{end}"
                    )
            return SGSWindowResult(
                start, end, url, points, skipped, hashlib.sha256(response.content).hexdigest()
            )
        if response.status_code == 404 and is_json:
            if _is_empty_window(response):
                # SGS answers 404 + {"erro": {... "Value(s) not found"}} for a window without data.
                return SGSWindowResult(start, end, url, [], 0, None)
            # Any other 404 (e.g. the gateway's {"error": "endpoint not found!"} for a wrong
            # base URL) is a failure, never "no data": it would make an outage look like success.
            raise SGSError(f"SGS endpoint not found (HTTP 404) at {url}: {response.text[:200]}")
        if response.status_code in (400, 406) and is_json:
            raise SGSPayloadError(f"SGS rejected request {url}: {response.text[:300]}")
        if response.status_code == 400 or response.status_code in _RETRYABLE_STATUS:
            return None  # HTML 400 from the gateway is transient; 5xx/429 too.
        if response.status_code == 200:
            return None  # 200 with a non-JSON body (e.g. maintenance page)
        raise SGSError(f"Unexpected HTTP {response.status_code} from {url}")

    def fetch_series(
        self, series_code: str, start: date, end: date, *, daily: bool = True
    ) -> list[SGSWindowResult]:
        """Fetch ``[start, end]`` respecting the 10-year limit for daily series."""
        if daily:
            years = min(self.settings.bcb_daily_window_years, MAX_DAILY_WINDOW_YEARS)
            windows = list(split_into_windows(start, end, years))
        else:
            windows = [(start, end)]
        return [self.fetch_window(series_code, w_start, w_end) for w_start, w_end in windows]


def _is_empty_window(response: httpx.Response) -> bool:
    try:
        payload = response.json()
    except ValueError:
        return False
    error = payload.get("erro") if isinstance(payload, dict) else None
    return isinstance(error, dict) and "not found" in str(error.get("detail", "")).lower()


def _content_type(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").lower()
