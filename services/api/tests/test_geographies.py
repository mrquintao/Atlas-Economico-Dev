"""Geographic units seeded by migration 0006 (regions and UFs) and the /geographies endpoint.

Expected codes come from the official IBGE localidades API (checked on 2026-10-21).
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import GeographicUnit
from app.repositories import catalog as repo
from tests.conftest import API_ROOT, TEST_DATABASE_URL

URL = "/api/v1/geographies"

EXPECTED_STATES = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}  # fmt: skip
EXPECTED_REGIONS = {"N": "1", "NE": "2", "SE": "3", "S": "4", "CO": "5"}


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _units(db: Session, level: str) -> list[GeographicUnit]:
    return list(db.scalars(select(GeographicUnit).where(GeographicUnit.geographic_level == level)))


def test_seeds_27_states_and_5_regions_with_official_codes(db: Session) -> None:
    states = {g.acronym: g.ibge_code for g in _units(db, "state")}
    regions = {g.acronym: g.ibge_code for g in _units(db, "region")}
    assert states == EXPECTED_STATES
    assert regions == EXPECTED_REGIONS
    names = {g.acronym: g.name for g in _units(db, "state")}
    assert names["DF"] == "Distrito Federal"
    assert names["SP"] == "São Paulo"


def test_hierarchy_country_region_state(db: Session) -> None:
    country = _units(db, "country")
    assert [(g.acronym, g.ibge_code, g.parent_id) for g in country] == [("BR", "1", None)]
    for region in _units(db, "region"):
        assert region.parent_id == country[0].id
    regions_by_id = {g.id: g for g in _units(db, "region")}
    for state in _units(db, "state"):
        # The first digit of a UF code is the code of its region.
        assert regions_by_id[state.parent_id].ibge_code == state.ibge_code[0]


def test_ambiguous_keys_resolve_by_level(db: Session) -> None:
    # "SE" is Sergipe and the Sudeste region; "1" is Brasil and the Norte region.
    sergipe = repo.get_geography(db, "se")
    assert sergipe is not None and sergipe.name == "Sergipe"
    sudeste = repo.get_geography(db, "SE", "region")
    assert sudeste is not None and sudeste.name == "Sudeste"
    brazil = repo.get_geography(db, "1")
    assert brazil is not None and brazil.acronym == "BR"
    norte = repo.get_geography(db, "1", "region")
    assert norte is not None and norte.name == "Norte"
    assert repo.get_geography(db, "31", "state") is not None
    assert repo.get_geography(db, "31", "region") is None


def test_lists_all_units_ordered_by_level_and_code(client: TestClient) -> None:
    body = client.get(URL).json()
    assert len(body) == 1 + 27 + 5
    assert [g["geographic_level"] for g in body] == ["country"] + ["state"] * 27 + ["region"] * 5
    assert body[0] == {
        "ibge_code": "1",
        "acronym": "BR",
        "name": "Brasil",
        "geographic_level": "country",
        "parent": None,
    }
    assert [g["ibge_code"] for g in body[1:28]] == sorted(EXPECTED_STATES.values())


def test_filters_by_level(client: TestClient) -> None:
    states = client.get(URL, params={"level": "state"}).json()
    assert len(states) == 27
    mg = next(g for g in states if g["acronym"] == "MG")
    assert mg["ibge_code"] == "31"
    assert mg["parent"] == {
        "ibge_code": "3",
        "acronym": "SE",
        "name": "Sudeste",
        "geographic_level": "region",
    }
    regions = client.get(URL, params={"level": "region"}).json()
    assert [g["acronym"] for g in regions] == ["N", "NE", "SE", "S", "CO"]
    assert all(g["parent"]["acronym"] == "BR" for g in regions)
    assert client.get(URL, params={"level": "municipality"}).json() == []


def test_rejects_unknown_level(client: TestClient) -> None:
    response = client.get(URL, params={"level": "city"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_national_series_refused_for_states_and_regions(client: TestClient) -> None:
    url = "/api/v1/indicators/SELIC_TARGET/observations"
    for key in ("SP", "35", "DF", "SE", "CO"):
        response = client.get(url, params={"geography": key})
        assert response.status_code == 422, key
        assert response.json()["error"]["code"] == "geography_not_available"
    # "1" is also the Norte region, but a national indicator resolves it to Brasil.
    assert client.get(url, params={"geography": "1"}).status_code == 200


def test_migration_0006_round_trip(engine: Engine) -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    count = text("SELECT count(*) FROM geographic_units")
    try:
        command.downgrade(config, "0005")
        with engine.connect() as conn:
            assert conn.execute(count).scalar_one() == 1
            constraints = set(
                conn.scalars(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conrelid = 'geographic_units'::regclass AND contype = 'u'"
                    )
                )
            )
        assert constraints == {"uq_geographic_units_acronym", "uq_geographic_units_ibge_code"}
    finally:
        command.upgrade(config, "head")
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(GeographicUnit)) == 33
