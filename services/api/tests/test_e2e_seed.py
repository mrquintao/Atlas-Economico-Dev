"""The SYNTHETIC E2E fixture (tests/fixtures/e2e_seed.py) stays tagged and never mixes with data."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import GeographicBoundary, Indicator, IngestionRun, Observation
from tests.fixtures import e2e_seed

# SP: 4 bimonthly x 18 + 5 four-monthly x 9; DF: SP minus one bimonthly; MG: 18 + 9.
STATE_ROWS = 117 + 99 + 27


def test_seeds_tagged_synthetic_series_with_consistent_periods(db: Session) -> None:
    counts = e2e_seed.seed(db)
    assert counts.pop("boundaries") == 27
    national = {k: v for k, v in counts.items() if "/" not in k}
    assert national == {"SELIC_TARGET": 8217, "DBGG_GDP": 234, "IPCA_12M": 317}
    assert sum(v for k, v in counts.items() if "/" in k) == STATE_ROWS
    assert "STATE_NOMINAL_RESULT/DF" not in counts
    assert {k.split("/")[1] for k in counts if "/" in k} == {"SP", "DF", "MG"}

    rows = db.scalars(select(Observation)).all()
    assert {r.source_reference for r in rows} == {e2e_seed.SOURCE_REFERENCE}
    assert all(r.metadata_json == {"synthetic": True} for r in rows)
    assert all(r.value != 0 for r in rows)  # never zero in place of a value

    dbgg = db.scalar(select(Indicator).where(Indicator.code == "DBGG_GDP"))
    assert dbgg is not None
    feb = db.scalar(
        select(Observation).where(
            Observation.indicator_id == dbgg.id, Observation.reference_date == date(2024, 2, 1)
        )
    )
    assert feb is not None
    assert (feb.period_start, feb.period_end) == (date(2024, 2, 1), date(2024, 2, 29))

    # State rows cover whole bimesters and four-month periods.
    rcl = db.scalar(select(Indicator).where(Indicator.code == "STATE_RCL"))
    assert rcl is not None
    last = db.scalar(
        select(Observation)
        .where(Observation.indicator_id == rcl.id)
        .order_by(Observation.period_start.desc())
        .limit(1)
    )
    assert last is not None
    assert (last.period_start, last.period_end) == (date(2025, 11, 1), date(2025, 12, 31))

    runs = db.scalars(select(IngestionRun)).all()
    assert len(runs) == 3
    assert all(r.status == "success" and (r.metadata_json or {}).get("synthetic") for r in runs)


def test_seeds_synthetic_boundaries_served_by_the_api(db: Session) -> None:
    e2e_seed.seed(db)
    boundaries = db.scalars(select(GeographicBoundary)).all()
    assert len(boundaries) == 27
    assert {b.source_url for b in boundaries} == {e2e_seed.SOURCE_REFERENCE}
    assert len({b.geometry_hash for b in boundaries}) == 27
    ring = boundaries[0].geometry["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 5


def test_refuses_a_database_with_boundaries(db: Session) -> None:
    e2e_seed.seed_boundaries(db)
    db.flush()
    with pytest.raises(SystemExit, match="already has geographic_boundaries rows"):
        e2e_seed.seed(db)


def test_series_are_deterministic() -> None:
    assert e2e_seed.selic_series()[:2] == [
        (date(2004, 1, 1), Decimal("2.00")),
        (date(2004, 1, 2), Decimal("2.00")),
    ]
    assert e2e_seed.selic_series()[45][1] == Decimal("2.75")
    assert e2e_seed.selic_series()[-1][0] == date(2026, 6, 30)
    assert e2e_seed.dbgg_series()[-1][0] == date(2026, 5, 1)
    assert e2e_seed.ipca_series() == e2e_seed.ipca_series()
    assert e2e_seed.state_series("STATE_PRIMARY_RESULT")[:2] == [
        (date(2023, 1, 1), date(2023, 2, 28), Decimal("3000000000.00")),
        (date(2023, 3, 1), date(2023, 4, 30), Decimal("6000000000.00")),
    ]
    # Year-to-date flows restart in January.
    assert e2e_seed.state_series("STATE_PRIMARY_RESULT")[6][2] == Decimal("3000000000.00")
    assert e2e_seed.state_series("STATE_DC")[-1][:2] == (date(2025, 9, 1), date(2025, 12, 31))


def test_refuses_a_database_that_already_has_observations(db: Session) -> None:
    e2e_seed.seed(db)
    with pytest.raises(SystemExit, match="already has observations rows"):
        e2e_seed.seed(db)
    assert db.scalar(select(func.count()).select_from(Observation)) == 8217 + 234 + 317 + STATE_ROWS


def test_refuses_a_database_with_collection_runs_but_no_observations(db: Session) -> None:
    indicator = db.scalar(select(Indicator).where(Indicator.code == "SELIC_TARGET"))
    assert indicator is not None
    db.add(IngestionRun(source_id=indicator.source_id, indicator_id=indicator.id, status="failed"))
    db.flush()
    with pytest.raises(SystemExit, match="already has ingestion_runs rows"):
        e2e_seed.seed(db)


@pytest.mark.parametrize("name", ["atlas", "atlas_prod", "", None])
def test_refuses_databases_not_named_as_test_databases(name: str | None) -> None:
    with pytest.raises(SystemExit, match="Refusing to seed database"):
        e2e_seed.check_database_name(name)


@pytest.mark.parametrize("name", ["atlas_e2e", "atlas_test", "atlas_qa_e2e"])
def test_accepts_test_database_names(name: str) -> None:
    e2e_seed.check_database_name(name)


def test_refuses_to_run_without_the_explicit_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_E2E_SEED", raising=False)
    with pytest.raises(SystemExit, match="ATLAS_E2E_SEED=1"):
        e2e_seed.main()
