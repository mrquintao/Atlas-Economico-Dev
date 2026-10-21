"""SYNTHETIC test data for the browser end-to-end tests (apps/web/e2e). Not official data.

Fills the three national dashboard indicators with deterministic, made-up values over fixed
date ranges, so the E2E tests never call the official sources and always see the same series:

- SELIC_TARGET (daily): 2004-01-01 to 2026-06-30, a step level that changes every 45 days;
- DBGG_GDP (monthly): 2006-12 to 2026-05;
- IPCA_12M (monthly): 2000-01 to 2026-05.

Every row is tagged `source_reference = "synthetic-e2e-fixture"` and every run carries
`{"synthetic": true}`. The script refuses to run unless `ATLAS_E2E_SEED=1` and the database has no
observations yet, so it can never mix synthetic values with collected official data.

    ATLAS_E2E_SEED=1 DATABASE_URL=... uv run python -m tests.fixtures.e2e_seed
"""

import os
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.ingestion.series_ingestion import period_end
from app.models import (
    Frequency,
    GeographicUnit,
    Indicator,
    IngestionRun,
    IngestionStatus,
    Observation,
)

SOURCE_REFERENCE = "synthetic-e2e-fixture"
COLLECTED_AT = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

SELIC_START, SELIC_END = date(2004, 1, 1), date(2026, 6, 30)
DBGG_START, DBGG_END = date(2006, 12, 1), date(2026, 5, 1)
IPCA_START, IPCA_END = date(2000, 1, 1), date(2026, 5, 1)


def _months(start: date, end: date) -> list[date]:
    months: list[date] = []
    current = start
    while current <= end:
        months.append(current)
        year, month = divmod(current.month, 12)
        current = date(current.year + year, month + 1, 1)
    return months


def selic_series() -> list[tuple[date, Decimal]]:
    """A level that only changes every 45 days, between 2.00 and 14.75 (% a.a.)."""
    days = (SELIC_END - SELIC_START).days + 1
    points: list[tuple[date, Decimal]] = []
    for offset in range(days):
        step = offset // 45
        points.append(
            (SELIC_START + timedelta(days=offset), Decimal(200 + (step * 75) % 1300) / 100)
        )
    return points


def dbgg_series() -> list[tuple[date, Decimal]]:
    """A slow saw-tooth between 55.0 and 79.5 (% do PIB)."""
    return [
        (month, Decimal(550 + (i * 5) % 250) / 10)
        for i, month in enumerate(_months(DBGG_START, DBGG_END))
    ]


def ipca_series() -> list[tuple[date, Decimal]]:
    """Values between 2.00 and 11.80 (%)."""
    return [
        (month, Decimal(200 + (i * 37) % 990) / 100)
        for i, month in enumerate(_months(IPCA_START, IPCA_END))
    ]


SERIES = {
    "SELIC_TARGET": selic_series,
    "DBGG_GDP": dbgg_series,
    "IPCA_12M": ipca_series,
}


def seed(session: Session) -> dict[str, int]:
    if session.scalar(select(func.count()).select_from(Observation)):
        raise SystemExit("Refusing to seed: the database already has observations.")
    geo = session.scalar(select(GeographicUnit).where(GeographicUnit.acronym == "BR"))
    if geo is None:
        raise SystemExit("Run the migrations first (catalog not seeded).")
    counts: dict[str, int] = {}
    for code, build in SERIES.items():
        indicator = session.scalar(select(Indicator).where(Indicator.code == code))
        if indicator is None:
            raise SystemExit(f"Indicator {code} missing from the catalog.")
        frequency = Frequency(indicator.frequency)
        points = build()
        session.execute(
            insert(Observation),
            [
                {
                    "indicator_id": indicator.id,
                    "geographic_unit_id": geo.id,
                    "reference_date": day,
                    "period_start": day,
                    "period_end": period_end(day, frequency),
                    "value": value,
                    "collected_at": COLLECTED_AT,
                    "source_reference": SOURCE_REFERENCE,
                    "metadata_json": {"synthetic": True},
                }
                for day, value in points
            ],
        )
        session.add(
            IngestionRun(
                source_id=indicator.source_id,
                indicator_id=indicator.id,
                started_at=COLLECTED_AT - timedelta(seconds=10),
                finished_at=COLLECTED_AT,
                status=IngestionStatus.SUCCESS,
                records_received=len(points),
                records_inserted=len(points),
                metadata_json={"synthetic": True, "fixture": SOURCE_REFERENCE},
            )
        )
        counts[code] = len(points)
    session.commit()
    return counts


def main() -> None:
    if os.environ.get("ATLAS_E2E_SEED") != "1":
        sys.exit("Refusing to seed synthetic data: set ATLAS_E2E_SEED=1 (test databases only).")
    with Session(get_engine()) as session:
        counts = seed(session)
    print("Seeded SYNTHETIC E2E data:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
