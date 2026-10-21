"""Business rules for serving observations (frequency conversion and summary statistics)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Frequency
from app.repositories import observations as repo
from app.repositories.observations import ObservationRow

_FREQUENCY_ORDER = {
    Frequency.DAILY: 0,
    Frequency.MONTHLY: 1,
    Frequency.QUARTERLY: 2,
    Frequency.ANNUAL: 3,
}

AGGREGATION_DESCRIPTIONS = {
    "none": "Valores na frequência original da fonte, sem transformação.",
    "last_value_of_period": (
        "Valor mensal: último valor oficialmente disponível em cada mês (no mês corrente, o "
        "valor da última atualização, marcado como parcial). Sem médias nem interpolação."
    ),
}

SUPPORTED_TARGETS = {Frequency.MONTHLY}


class FrequencyNotSupportedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SeriesResult:
    rows: list[ObservationRow]
    partial_flags: list[bool]
    aggregation: str


def load_series(
    session: Session,
    *,
    indicator_id: int,
    geographic_unit_id: int,
    original_frequency: Frequency,
    target_frequency: Frequency,
    start: date | None,
    end: date | None,
    first_stored_date: date | None,
    last_stored_date: date | None,
) -> SeriesResult:
    if target_frequency == original_frequency:
        rows = repo.fetch_observations(session, indicator_id, geographic_unit_id, start, end)
        return SeriesResult(rows, [False] * len(rows), "none")

    if _FREQUENCY_ORDER[target_frequency] < _FREQUENCY_ORDER[original_frequency]:
        raise FrequencyNotSupportedError(
            f"Não é possível converter {original_frequency} para uma frequência mais alta "
            f"({target_frequency}) sem inventar valores."
        )
    if target_frequency not in SUPPORTED_TARGETS or original_frequency != Frequency.DAILY:
        raise FrequencyNotSupportedError(
            f"Conversão {original_frequency} → {target_frequency} ainda não suportada."
        )

    rows = repo.fetch_last_value_per_month(session, indicator_id, geographic_unit_id, start, end)
    # A month is partial when it is not fully covered: it extends past the last stored date
    # (month still running) or the requested end, or begins before the requested start or the
    # first stored date (month cut at the beginning).
    end_cutoffs = [d for d in (last_stored_date, end) if d is not None]
    end_cutoff = min(end_cutoffs) if end_cutoffs else None
    start_cutoffs = [d for d in (first_stored_date, start) if d is not None]
    start_cutoff = max(start_cutoffs) if start_cutoffs else None
    flags = [
        (end_cutoff is not None and row.period_end > end_cutoff)
        or (start_cutoff is not None and row.period_start < start_cutoff)
        for row in rows
    ]
    return SeriesResult(rows, flags, "last_value_of_period")


@dataclass(frozen=True, slots=True)
class Stats:
    first: ObservationRow
    last: ObservationRow
    change: Decimal
    min: ObservationRow
    max: ObservationRow


def compute_stats(rows: list[ObservationRow]) -> Stats | None:
    if not rows:
        return None
    first, last = rows[0], rows[-1]
    # Ties resolve to the earliest date (stable min/max over a date-ordered list).
    minimum = min(rows, key=lambda r: r.value)
    maximum = max(rows, key=lambda r: r.value)
    return Stats(first, last, last.value - first.value, minimum, maximum)
