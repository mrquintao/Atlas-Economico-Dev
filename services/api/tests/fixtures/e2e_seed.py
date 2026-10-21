"""SYNTHETIC test data for the browser end-to-end tests (apps/web/e2e). Not official data.

Fills the three national dashboard indicators with deterministic, made-up values over fixed
date ranges, so the E2E tests never call the official sources and always see the same series:

- SELIC_TARGET (daily): 2004-01-01 to 2026-06-30, a step level that changes every 45 days;
- DBGG_GDP (monthly): 2006-12 to 2026-05;
- IPCA_12M (monthly): 2000-01 to 2026-05;
- the nine state fiscal indicators (STATE_*, bimonthly and four-monthly) from 2023 to 2025 for
  three UFs: SP with all nine, DF without STATE_NOMINAL_RESULT and MG with STATE_RCL and
  STATE_DCL_RCL only (the other UFs have no state data), so the state pages show values,
  explicit absences and the DF note.

Every row is tagged `source_reference = "synthetic-e2e-fixture"` and every run carries
`{"synthetic": true}`. The script refuses to run unless `ATLAS_E2E_SEED=1`, the database name says
it is a test database (contains "e2e" or "test", e.g. `atlas_e2e`) and the database has no
observations nor collection runs yet, so it can never mix synthetic values with official data.

    ATLAS_E2E_SEED=1 DATABASE_URL=... uv run python -m tests.fixtures.e2e_seed
"""

import os
import re
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


# State fiscal indicators: (frequency in months, kind, base value). "level" grows 2% per period,
# "ytd" accumulates from January (base x bimester of the year), "ratio" adds 0.5 per period.
STATE_YEARS = (2023, 2024, 2025)
STATE_INDICATORS: dict[str, tuple[int, str, Decimal]] = {
    "STATE_RCL": (2, "level", Decimal("200000000000")),
    "STATE_PERSONNEL_EXEC": (4, "level", Decimal("80000000000")),
    "STATE_PERSONNEL_EXEC_RCL": (4, "ratio", Decimal("40")),
    "STATE_INVESTMENTS": (2, "ytd", Decimal("1500000000")),
    "STATE_PRIMARY_RESULT": (2, "ytd", Decimal("3000000000")),
    "STATE_NOMINAL_RESULT": (2, "ytd", Decimal("-2000000000")),
    "STATE_DC": (4, "level", Decimal("300000000000")),
    "STATE_DCL": (4, "level", Decimal("250000000000")),
    "STATE_DCL_RCL": (4, "ratio", Decimal("110")),
}
# Scale of each UF's values and the indicators it has (None = all nine).
STATE_UFS: dict[str, tuple[Decimal, set[str] | None]] = {
    "SP": (Decimal("1"), None),
    "DF": (Decimal("0.2"), set(STATE_INDICATORS) - {"STATE_NOMINAL_RESULT"}),
    "MG": (Decimal("0.5"), {"STATE_RCL", "STATE_DCL_RCL"}),
}
CENTS = Decimal("0.01")


def state_series(code: str, scale: Decimal = Decimal("1")) -> list[tuple[date, date, Decimal]]:
    """(period start, period end, value) of a state indicator, one row per bimester or
    four-month period of 2023-2025. Ratios (% of RCL) are not scaled."""
    months, kind, base = STATE_INDICATORS[code]
    rows: list[tuple[date, date, Decimal]] = []
    for year in STATE_YEARS:
        for index, month in enumerate(range(1, 13, months)):
            i = len(rows)
            if kind == "level":
                value = base * scale * (1 + Decimal("0.02") * i)
            elif kind == "ytd":
                value = base * scale * (index + 1)
            else:
                value = base + Decimal("0.5") * i
            end_year, end_month = divmod(month + months - 1, 12)
            end = date(year + end_year, end_month + 1, 1) - timedelta(days=1)
            rows.append((date(year, month, 1), end, value.quantize(CENTS)))
    return rows


SERIES = {
    "SELIC_TARGET": selic_series,
    "DBGG_GDP": dbgg_series,
    "IPCA_12M": ipca_series,
}


# Only disposable test databases: the default DATABASE_URL points to `atlas`, the real data.
TEST_DATABASE_NAME = re.compile(r"(e2e|test)", re.IGNORECASE)


def check_database_name(name: str | None) -> None:
    if not name or not TEST_DATABASE_NAME.search(name):
        raise SystemExit(
            f"Refusing to seed database {name!r}: its name must contain 'e2e' or 'test' "
            "(a disposable test database, never the one with collected data)."
        )


def seed(session: Session) -> dict[str, int]:
    for model in (Observation, IngestionRun):
        if session.scalar(select(func.count()).select_from(model)):
            raise SystemExit(
                f"Refusing to seed: the database already has {model.__tablename__} rows."
            )
    geo = session.scalar(
        select(GeographicUnit).where(
            GeographicUnit.geographic_level == "country", GeographicUnit.acronym == "BR"
        )
    )
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
    counts.update(seed_states(session))
    session.commit()
    return counts


def seed_states(session: Session) -> dict[str, int]:
    """State fiscal indicators for the UFs in STATE_UFS (derived indicators: no ingestion run)."""
    counts: dict[str, int] = {}
    for uf, (scale, codes) in STATE_UFS.items():
        geo = session.scalar(
            select(GeographicUnit).where(
                GeographicUnit.geographic_level == "state", GeographicUnit.acronym == uf
            )
        )
        if geo is None:
            raise SystemExit("Run the migrations first (UFs not seeded).")
        for code in STATE_INDICATORS:
            if codes is not None and code not in codes:
                continue
            indicator = session.scalar(select(Indicator).where(Indicator.code == code))
            if indicator is None:
                raise SystemExit(f"Indicator {code} missing from the catalog.")
            rows = state_series(code, scale)
            session.execute(
                insert(Observation),
                [
                    {
                        "indicator_id": indicator.id,
                        "geographic_unit_id": geo.id,
                        "reference_date": start,
                        "period_start": start,
                        "period_end": end,
                        "value": value,
                        "collected_at": COLLECTED_AT,
                        "source_reference": SOURCE_REFERENCE,
                        "metadata_json": {"synthetic": True},
                    }
                    for start, end, value in rows
                ],
            )
            counts[f"{code}/{uf}"] = len(rows)
    return counts


def main() -> None:
    if os.environ.get("ATLAS_E2E_SEED") != "1":
        sys.exit("Refusing to seed synthetic data: set ATLAS_E2E_SEED=1 (test databases only).")
    engine = get_engine()
    check_database_name(engine.url.database)
    with Session(engine) as session:
        counts = seed(session)
    print("Seeded SYNTHETIC E2E data:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
