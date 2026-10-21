"""The SYNTHETIC E2E fixture (tests/fixtures/e2e_seed.py) stays tagged and never mixes with data."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Indicator, IngestionRun, Observation
from tests.fixtures import e2e_seed


def test_seeds_tagged_synthetic_series_with_consistent_periods(db: Session) -> None:
    counts = e2e_seed.seed(db)
    assert counts == {"SELIC_TARGET": 8217, "DBGG_GDP": 234, "IPCA_12M": 317}

    rows = db.scalars(select(Observation)).all()
    assert {r.source_reference for r in rows} == {e2e_seed.SOURCE_REFERENCE}
    assert all(r.metadata_json == {"synthetic": True} for r in rows)
    assert all(r.value > 0 for r in rows)  # never zero in place of a value

    dbgg = db.scalar(select(Indicator).where(Indicator.code == "DBGG_GDP"))
    assert dbgg is not None
    feb = db.scalar(
        select(Observation).where(
            Observation.indicator_id == dbgg.id, Observation.reference_date == date(2024, 2, 1)
        )
    )
    assert feb is not None
    assert (feb.period_start, feb.period_end) == (date(2024, 2, 1), date(2024, 2, 29))

    runs = db.scalars(select(IngestionRun)).all()
    assert len(runs) == 3
    assert all(r.status == "success" and (r.metadata_json or {}).get("synthetic") for r in runs)


def test_series_are_deterministic() -> None:
    assert e2e_seed.selic_series()[:2] == [
        (date(2004, 1, 1), Decimal("2.00")),
        (date(2004, 1, 2), Decimal("2.00")),
    ]
    assert e2e_seed.selic_series()[45][1] == Decimal("2.75")
    assert e2e_seed.selic_series()[-1][0] == date(2026, 6, 30)
    assert e2e_seed.dbgg_series()[-1][0] == date(2026, 5, 1)
    assert e2e_seed.ipca_series() == e2e_seed.ipca_series()


def test_refuses_a_database_that_already_has_observations(db: Session) -> None:
    e2e_seed.seed(db)
    with pytest.raises(SystemExit, match="already has observations"):
        e2e_seed.seed(db)
    assert db.scalar(select(func.count()).select_from(Observation)) == 8217 + 234 + 317


def test_refuses_to_run_without_the_explicit_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATLAS_E2E_SEED", raising=False)
    with pytest.raises(SystemExit, match="ATLAS_E2E_SEED=1"):
        e2e_seed.main()
