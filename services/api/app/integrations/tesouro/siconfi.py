"""Connector for the SICONFI open-data API (Tesouro Nacional): RREO and RGF reports.

Endpoints used (documented at https://apidatalake.tesouro.gov.br/docs/siconfi/):

    GET {base_url}/rreo?an_exercicio=&nr_periodo=&co_tipo_demonstrativo=RREO&no_anexo=
        &co_esfera=&id_ente=
    GET {base_url}/rgf?an_exercicio=&in_periodicidade=&nr_periodo=&co_tipo_demonstrativo=RGF
        &no_anexo=&co_esfera=&co_poder=&id_ente=
    GET {base_url}/extrato_entregas?id_ente=&an_referencia=

Every response is an Oracle REST Data Services page:
``{"items": [...], "hasMore": bool, "limit": int, "offset": int, "count": int, "links": [...]}``.

Observed behaviour this connector relies on (verified 2026-10-21):
- The default page size is 5000 rows; ``offset``/``limit`` query parameters page through larger
  results and ``hasMore`` tells whether another page exists. One annex of one state usually fits
  in a single page (largest seen: RREO-Anexo 02 of RJ, 2024, 2021 rows).
- Missing or unknown filters do not fail: the API answers 200 with ``items: []``. An empty
  result therefore means "not available in the data lake", never an error.
- Report rows carry ``rotulo``, ``coluna``, ``cod_conta``, ``conta`` and ``valor`` (a JSON
  number with up to 2 decimals); in the reports checked, (rotulo, coluna, cod_conta, conta)
  identifies a row. ``valor`` is parsed straight from the JSON text into ``Decimal``.
- ``extrato_entregas`` lists every delivery of the entity (all powers and bodies) with the
  latest ``data_status`` (UTC) per deliverable and period; a rectification (``RE``) moves it.
- The documented limit is 1 request per second; the client never goes faster (see
  ``RateLimiter``) and retries 429/5xx with exponential backoff.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

SICONFI_DOCUMENTATION_URL = "https://apidatalake.tesouro.gov.br/docs/siconfi/"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
PAGE_SIZE = 5000
# A single annex of one entity has at most a few thousand rows; anything beyond this many pages
# means the pagination is not advancing.
MAX_PAGES = 50

# Deliverable names as listed by `extrato_entregas`.
DELIVERABLES = {
    "RREO": "Relatório Resumido de Execução Orçamentária",
    "RGF": "Relatório de Gestão Fiscal",
}
# Periodicity code -> number of periods in a year.
PERIODS_PER_YEAR = {"B": 6, "Q": 3, "S": 2}
# The semiannual RGF ("S") is the simplified report (co_tipo_demonstrativo "RGF Simplificado") of
# municipalities under 50k inhabitants (LRF art. 63); not supported while municipalities are out
# of scope.
REPORT_PERIODICITIES = {"RREO": ("B",), "RGF": ("Q",)}
# co_esfera accepted by /rreo and /rgf (siconfi.yaml): M = municipalities, E = states and DF,
# U = Union, C = consortia ("D" = DF exists only in the /entes schema).
SPHERES = ("E", "M", "U", "C")
# co_poder (RGF only): E = Executive, L = Legislative, J = Judiciary, M = Public Prosecution,
# D = Public Defender's Office.
POWERS = ("E", "L", "J", "M", "D")


class SiconfiError(Exception):
    """Base error for SICONFI integration failures."""


class SiconfiPayloadError(SiconfiError):
    """The response did not match the expected structure or request."""


class SiconfiUnavailableError(SiconfiError):
    """The service could not be reached or kept failing after retries."""


class RateLimiter:
    """Guarantees at least ``min_interval`` seconds between the starts of two requests.

    ``clock`` and ``sleep`` are injectable so tests can check the spacing deterministically.
    """

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self.min_interval - (self._clock() - self._last)
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()


@dataclass(frozen=True)
class ReportRequest:
    """One annex of one report of one entity for one period."""

    report_type: str  # "RREO" or "RGF"
    exercise: int
    period: int
    annex: str  # e.g. "RREO-Anexo 03", "RGF-Anexo 02"
    entity_code: str  # IBGE code of the entity (2 digits for states)
    sphere: str = "E"
    power: str | None = None  # RGF only (E, L, J, M, D)
    periodicity: str = "B"  # RREO: B; RGF: Q

    def __post_init__(self) -> None:
        if self.report_type not in REPORT_PERIODICITIES:
            raise SiconfiError(f"Unknown report type {self.report_type!r}")
        if self.periodicity not in REPORT_PERIODICITIES[self.report_type]:
            raise SiconfiError(f"Periodicity {self.periodicity!r} invalid for {self.report_type}")
        if not 1 <= self.period <= PERIODS_PER_YEAR[self.periodicity]:
            raise SiconfiError(f"Period {self.period} invalid for periodicity {self.periodicity}")
        if not re.fullmatch(rf"{self.report_type}-Anexo \d{{2}}( - .+)?", self.annex):
            raise SiconfiError(
                f"Annex {self.annex!r} is not a {self.report_type} annex name "
                f'(e.g. "{self.report_type}-Anexo 02", "RREO-Anexo 10 - RPPS")'
            )
        if self.sphere not in SPHERES:
            raise SiconfiError(f"Unknown sphere {self.sphere!r}")
        if self.report_type == "RGF" and self.power not in POWERS:
            raise SiconfiError(f"RGF requires a power in {POWERS}, got {self.power!r}")
        if self.report_type == "RREO" and self.power is not None:
            raise SiconfiError("RREO is consolidated for the entity and takes no power")
        if not self.entity_code.isdigit():
            raise SiconfiError(f"Invalid entity code {self.entity_code!r}")

    def params(self) -> dict[str, str]:
        params = {
            "an_exercicio": str(self.exercise),
            "nr_periodo": str(self.period),
            "co_tipo_demonstrativo": self.report_type,
            "no_anexo": self.annex,
            "co_esfera": self.sphere,
            "id_ente": self.entity_code,
        }
        if self.report_type == "RGF":
            params["in_periodicidade"] = self.periodicity
            params["co_poder"] = self.power or ""
        return params


@dataclass(frozen=True)
class ReportRow:
    label: str  # rotulo
    column: str  # coluna
    account_code: str  # cod_conta
    account: str  # conta
    value: Decimal

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.label, self.column, self.account_code, self.account)


@dataclass(frozen=True)
class ReportResult:
    request: ReportRequest
    url: str
    institution: str | None
    population: int | None
    rows: list[ReportRow]
    content_hash: str  # SHA-256 of the canonical rows (order and pagination independent)
    pages: int


@dataclass(frozen=True)
class Delivery:
    deliverable: str
    institution: str
    exercise: int
    period: int
    periodicity: str
    status: str | None
    delivered_at: datetime


def plain_decimal(value: Decimal) -> str:
    """Canonical text of a value: no exponent, no trailing zeros (1000.10 and 1000.1 match)."""
    if value.is_zero():
        return "0"  # -0 and 0 are the same value
    return format(value.normalize(), "f")


def rows_hash(rows: list[ReportRow]) -> str:
    canonical = json.dumps(
        sorted([*row.key, plain_decimal(row.value)] for row in rows),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _require(item: dict[str, Any], key: str, kind: type, where: str) -> Any:
    value = item.get(key)
    if not isinstance(value, kind) or isinstance(value, bool):
        raise SiconfiPayloadError(f"Field {key!r} missing or not {kind.__name__} in {where}")
    return value


def _decimal(value: Any, where: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal | int):
        raise SiconfiPayloadError(f"Non-numeric valor in {where}: {value!r}")
    result = Decimal(value)
    if not result.is_finite():
        raise SiconfiPayloadError(f"Non-finite valor in {where}: {value!r}")
    # Must fit NUMERIC(24,8) exactly: never round silently.
    exponent = result.normalize().as_tuple().exponent
    if (isinstance(exponent, int) and exponent < -8) or result.adjusted() >= 16:
        raise SiconfiPayloadError(f"valor does not fit NUMERIC(24,8) in {where}: {value!r}")
    return result


def parse_report_items(
    items: list[Any], request: ReportRequest
) -> tuple[list[ReportRow], str | None, int | None]:
    """Validate report rows against the request; return rows, institution and population.

    Raises ``SiconfiPayloadError`` when a row is malformed, belongs to another entity, period,
    annex, sphere or power, or repeats the key of another row.
    """
    rows: dict[tuple[str, str, str, str], ReportRow] = {}
    institution: str | None = None
    population: int | None = None
    for index, item in enumerate(items):
        where = f"row {index}"
        if not isinstance(item, dict):
            raise SiconfiPayloadError(f"Unexpected item at {where}")
        expected: dict[str, Any] = {
            "exercicio": request.exercise,
            "periodo": request.period,
            "periodicidade": request.periodicity,
            "anexo": request.annex,
            "esfera": request.sphere,
        }
        if request.report_type == "RGF":
            expected["co_poder"] = request.power
        else:
            expected["demonstrativo"] = request.report_type
        for key, value in expected.items():
            if item.get(key) != value:
                raise SiconfiPayloadError(
                    f"{where}: {key}={item.get(key)!r} does not match the request ({value!r})"
                )
        if str(item.get("cod_ibge")) != request.entity_code:
            raise SiconfiPayloadError(
                f"{where}: cod_ibge={item.get('cod_ibge')!r} is not entity {request.entity_code}"
            )
        row = ReportRow(
            label=_require(item, "rotulo", str, where),
            column=_require(item, "coluna", str, where),
            account_code=_require(item, "cod_conta", str, where),
            account=_require(item, "conta", str, where),
            value=_decimal(item.get("valor"), where),
        )
        if row.key in rows:
            raise SiconfiPayloadError(f"Duplicate row {row.key} at {where}")
        rows[row.key] = row
        if isinstance(item.get("instituicao"), str):
            institution = item["instituicao"]
        if isinstance(item.get("populacao"), int) and not isinstance(item["populacao"], bool):
            population = item["populacao"]
    return list(rows.values()), institution, population


def parse_deliveries(items: list[Any], entity_code: str, year: int) -> list[Delivery]:
    deliveries: list[Delivery] = []
    for index, item in enumerate(items):
        where = f"delivery {index}"
        if not isinstance(item, dict):
            raise SiconfiPayloadError(f"Unexpected item at {where}")
        if str(item.get("cod_ibge")) != entity_code or item.get("exercicio") != year:
            raise SiconfiPayloadError(f"{where} belongs to another entity or year")
        raw_date = _require(item, "data_status", str, where)
        try:
            delivered_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SiconfiPayloadError(f"Invalid data_status in {where}: {raw_date!r}") from exc
        if delivered_at.tzinfo is None:
            delivered_at = delivered_at.replace(tzinfo=UTC)
        status = item.get("status_relatorio")
        deliveries.append(
            Delivery(
                deliverable=_require(item, "entregavel", str, where),
                institution=_require(item, "instituicao", str, where),
                exercise=year,
                period=_require(item, "periodo", int, where),
                periodicity=_require(item, "periodicidade", str, where),
                status=status if isinstance(status, str) else None,
                delivered_at=delivered_at,
            )
        )
    return deliveries


def latest_delivery(
    deliveries: list[Delivery], report_type: str, period: int, periodicity: str
) -> datetime | None:
    """Latest delivery (or rectification) of a report for a period, across all bodies.

    Taking the maximum over every body is conservative: a rectification by any power makes the
    report be collected again, which is harmless (unchanged rows stay unchanged).
    """
    dates = [
        d.delivered_at
        for d in deliveries
        if d.deliverable == DELIVERABLES[report_type]
        and d.period == period
        and d.periodicity == periodicity
    ]
    return max(dates, default=None)


def _decode_page(response: httpx.Response) -> dict[str, Any] | None:
    """Parse an ORDS page keeping numbers exact; ``None`` if the body is not JSON."""
    try:
        payload = json.loads(response.content, parse_float=Decimal)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


class SiconfiClient:
    """HTTP client for the SICONFI API: ≤ 1 request/s, retry with backoff and pagination."""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings or get_settings()
        self._sleep = sleep
        self.rate_limiter = RateLimiter(
            self.settings.siconfi_min_request_interval_seconds, clock=clock, sleep=sleep
        )
        self.requests_made = 0
        self._client = httpx.Client(
            base_url=self.settings.siconfi_base_url,
            timeout=httpx.Timeout(self.settings.http_timeout_seconds),
            headers={"User-Agent": self.settings.http_user_agent, "Accept": "application/json"},
            transport=transport,
        )

    def __enter__(self) -> SiconfiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def fetch_report(self, request: ReportRequest) -> ReportResult:
        path = "/rreo" if request.report_type == "RREO" else "/rgf"
        items: list[Any] = []
        url = ""
        pages = 0
        for page_url, page_items in self._pages(path, request.params()):
            url = url or page_url
            items.extend(page_items)
            pages += 1
        rows, institution, population = parse_report_items(items, request)
        return ReportResult(
            request=request,
            url=url,
            institution=institution,
            population=population,
            rows=rows,
            content_hash=rows_hash(rows),
            pages=pages,
        )

    def fetch_deliveries(self, entity_code: str, year: int) -> list[Delivery]:
        items: list[Any] = []
        params = {"id_ente": entity_code, "an_referencia": str(year)}
        for _, page_items in self._pages("/extrato_entregas", params):
            items.extend(page_items)
        return parse_deliveries(items, entity_code, year)

    def _pages(self, path: str, params: dict[str, str]) -> Iterator[tuple[str, list[Any]]]:
        offset = 0
        for _ in range(MAX_PAGES):
            page_params = {**params, "offset": str(offset), "limit": str(PAGE_SIZE)}
            url, page = self._get(path, page_params)
            items, has_more = page.get("items"), page.get("hasMore")
            if not isinstance(items, list) or not isinstance(has_more, bool):
                raise SiconfiPayloadError(f"Page without items/hasMore from {url}")
            if page.get("offset", offset) != offset:
                raise SiconfiPayloadError(f"Page offset {page.get('offset')} != {offset} ({url})")
            yield url, items
            if not has_more:
                return
            if not items:
                raise SiconfiPayloadError(f"hasMore with an empty page from {url}")
            offset += len(items)
        raise SiconfiPayloadError(f"Pagination did not end after {MAX_PAGES} pages ({path})")

    def _get(self, path: str, params: dict[str, str]) -> tuple[str, dict[str, Any]]:
        max_attempts = self.settings.http_max_retries + 1
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            self.rate_limiter.wait()
            self.requests_made += 1
            try:
                response = self._client.get(path, params=params)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                url = str(response.request.url)
                if response.status_code == 200:
                    page = _decode_page(response)
                    if page is not None:
                        return url, page
                    last_error = "HTTP 200 with a non-JSON body"
                elif response.status_code in _RETRYABLE_STATUS:
                    last_error = f"HTTP {response.status_code}"
                else:
                    raise SiconfiError(f"Unexpected HTTP {response.status_code} from {url}")
            if attempt < max_attempts:
                delay = self.settings.http_backoff_base_seconds * 2 ** (attempt - 1)
                logger.warning(
                    "siconfi_request_retry",
                    extra={"path": path, "attempt": attempt, "delay_s": delay},
                )
                self._sleep(delay)
        raise SiconfiUnavailableError(
            f"SICONFI {path} failed after {max_attempts} attempts: {last_error}"
        )
