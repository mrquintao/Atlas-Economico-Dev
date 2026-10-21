"""State boundary ingestion (S2) and the /geographies/states/boundaries endpoint.

Geometries here are SYNTHETIC squares (not official boundaries); HTTP is httpx.MockTransport.
"""

import json
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.ingestion import cli
from app.ingestion.boundaries import ingest_state_boundaries
from app.ingestion.series_ingestion import IngestionError
from app.integrations.ibge.malhas import MalhasClient, MalhasUnavailableError
from app.main import app
from app.models import GeographicBoundary, GeographicUnit, IngestionRun
from tests.test_geographies import EXPECTED_STATES

URL = "/api/v1/geographies/states/boundaries"
CODES = sorted(EXPECTED_STATES.values())


def square(offset: float) -> dict[str, Any]:
    x, y = -60.0 + offset, -20.0 + offset / 2
    ring = [[x, y], [x + 0.5, y], [x + 0.5, y + 0.5], [x, y + 0.5], [x, y]]
    return {"type": "Polygon", "coordinates": [ring]}


def mesh(codes: list[str], shift: dict[str, float] | None = None) -> dict[str, Any]:
    shift = shift or {}
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": square(i + shift.get(code, 0.0)),
                "properties": {"codarea": code},
            }
            for i, code in enumerate(codes)
        ],
    }


def mesh_client(settings: Settings, payload: Any) -> MalhasClient:
    handler: Callable[[httpx.Request], httpx.Response] = lambda _: httpx.Response(  # noqa: E731
        200, content=json.dumps(payload)
    )
    return MalhasClient(settings, transport=httpx.MockTransport(handler), sleep=lambda _: None)


def ingest(db: Session, settings: Settings, payload: Any, year: int = 2022):
    return ingest_state_boundaries(db, settings, mesh_client(settings, payload), mesh_year=year)


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _runs(db: Session) -> list[IngestionRun]:
    return list(db.scalars(select(IngestionRun).order_by(IngestionRun.id)))


# --- ingestion ---


def test_ingests_27_states_and_is_idempotent(db: Session, settings: Settings) -> None:
    first = ingest(db, settings, mesh(CODES))
    assert (first.received, first.inserted, first.updated, first.unchanged) == (27, 27, 0, 0)
    stored = db.scalars(select(GeographicBoundary).join(GeographicUnit)).all()
    assert sorted(b.geographic_unit.ibge_code for b in stored) == CODES
    assert {b.geographic_unit.geographic_level for b in stored} == {"state"}
    assert {(b.mesh_year, b.quality) for b in stored} == {(2022, "minima")}
    assert "periodo=2022" in stored[0].source_url

    second = ingest(db, settings, mesh(CODES))
    assert (second.inserted, second.updated, second.unchanged) == (0, 0, 27)
    assert db.scalar(select(func.count()).select_from(GeographicBoundary)) == 27
    runs = _runs(db)
    assert [r.status for r in runs] == ["success", "success"]
    assert runs[0].indicator_id is None
    assert runs[0].records_inserted == 27 and runs[1].records_unchanged == 27
    assert runs[0].metadata_json["dataset"] == "state_boundaries"
    assert len(runs[0].metadata_json["content_hash"]) == 64


def test_changed_geometry_is_updated_and_recorded(db: Session, settings: Settings) -> None:
    ingest(db, settings, mesh(CODES))
    summary = ingest(db, settings, mesh(CODES, shift={"35": 0.25}))
    assert (summary.updated, summary.unchanged, summary.updated_codes) == (1, 26, ["35"])
    sp = db.scalar(
        select(GeographicBoundary).join(GeographicUnit).where(GeographicUnit.ibge_code == "35")
    )
    assert sp is not None
    assert sp.geometry == square(CODES.index("35") + 0.25)
    assert _runs(db)[-1].metadata_json["updated_codes"] == ["35"]


def test_editions_are_stored_side_by_side(db: Session, settings: Settings) -> None:
    ingest(db, settings, mesh(CODES), year=2021)
    ingest(db, settings, mesh(CODES), year=2022)
    years = db.scalars(select(GeographicBoundary.mesh_year).distinct()).all()
    assert sorted(years) == [2021, 2022]


@pytest.mark.parametrize(
    ("codes", "message"),
    [
        (CODES[:-1], r"missing \['53'\]"),
        ([*CODES, "54"], r"unknown \['54'\]"),
        ([c for c in CODES if c != "28"] + ["3"], r"missing \['28'\], unknown \['3'\]"),
    ],
)
def test_codes_must_match_the_27_states(
    db: Session, settings: Settings, codes: list[str], message: str
) -> None:
    with pytest.raises(IngestionError, match=message):
        ingest(db, settings, mesh(codes))
    assert db.scalar(select(func.count()).select_from(GeographicBoundary)) == 0
    (run,) = _runs(db)
    assert run.status == "failed" and run.finished_at is not None
    assert run.error_message and run.error_message.startswith("IngestionError")


def test_failed_update_keeps_the_stored_mesh(db: Session, settings: Settings) -> None:
    ingest(db, settings, mesh(CODES))
    with pytest.raises(IngestionError):
        ingest(db, settings, mesh(CODES[:-1], shift={"35": 0.25}))
    sp = db.scalar(
        select(GeographicBoundary).join(GeographicUnit).where(GeographicUnit.ibge_code == "35")
    )
    assert sp is not None and sp.geometry == square(CODES.index("35"))


def test_source_failure_is_recorded(db: Session, settings: Settings) -> None:
    failing = MalhasClient(
        settings,
        transport=httpx.MockTransport(lambda _: httpx.Response(500)),
        sleep=lambda _: None,
    )
    with pytest.raises(MalhasUnavailableError):
        ingest_state_boundaries(db, settings, failing, mesh_year=2023)
    (run,) = _runs(db)
    assert run.status == "failed"
    assert run.error_message and run.error_message.startswith("MalhasUnavailableError")
    expected = {"dataset": "state_boundaries", "mesh_year": 2023, "quality": "minima"}
    assert run.metadata_json == expected


# --- endpoint ---


def test_endpoint_404_before_collection(client: TestClient) -> None:
    response = client.get(URL)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "boundaries_not_found"


def test_endpoint_serves_27_features_matching_geographic_units(
    client: TestClient, db: Session, settings: Settings
) -> None:
    ingest(db, settings, mesh(CODES))
    response = client.get(URL)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    assert response.headers["cache-control"] == "public, max-age=86400"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    features = body["features"]
    assert [f["id"] for f in features] == CODES
    by_acronym = {f["properties"]["acronym"]: f["properties"]["ibge_code"] for f in features}
    assert by_acronym == EXPECTED_STATES
    df = next(f for f in features if f["id"] == "53")
    assert df["type"] == "Feature"
    assert df["properties"]["name"] == "Distrito Federal"
    assert df["geometry"] == square(CODES.index("53"))
    meta = body["metadata"]
    assert meta["source"]["acronym"] == "IBGE"
    assert meta["mesh_year"] == 2022 and meta["quality"] == "minima"
    assert meta["coordinate_decimals"] == 4
    assert "periodo=2022" in meta["source_url"]
    assert meta["collected_at"]


def test_endpoint_serves_latest_edition_or_the_requested_one(
    client: TestClient, db: Session, settings: Settings
) -> None:
    ingest(db, settings, mesh(CODES), year=2021)
    ingest(db, settings, mesh(CODES, shift={"53": 0.25}), year=2022)
    latest = client.get(URL).json()
    assert latest["metadata"]["mesh_year"] == 2022
    older = client.get(URL, params={"mesh_year": 2021}).json()
    assert older["metadata"]["mesh_year"] == 2021
    assert next(f for f in older["features"] if f["id"] == "53")["geometry"] == square(26)
    missing = client.get(URL, params={"mesh_year": 2010})
    assert missing.status_code == 404
    assert "2010" in missing.json()["error"]["message"]
    assert client.get(URL, params={"mesh_year": 1990}).status_code == 422
    assert client.get(URL, params={"year": 2021}).json()["error"]["code"] == "unknown_parameter"


def test_endpoint_etag_revalidation_and_compression(
    client: TestClient, db: Session, settings: Settings
) -> None:
    ingest(db, settings, mesh(CODES))
    first = client.get(URL, headers={"Accept-Encoding": "gzip"})
    etag = first.headers["etag"]
    assert first.headers["content-encoding"] == "gzip"
    not_modified = client.get(URL, headers={"If-None-Match": etag})
    assert not_modified.status_code == 304
    assert not_modified.headers["etag"] == etag
    assert not_modified.content == b""
    assert client.get(URL, headers={"If-None-Match": '"other"'}).status_code == 200
    # A changed geometry changes the ETag.
    ingest(db, settings, mesh(CODES, shift={"35": 0.25}))
    assert client.get(URL).headers["etag"] != etag
    raw = client.get(URL, headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in raw.headers
    assert json.loads(raw.content)["features"]


@pytest.mark.parametrize("year", ["1999", "2999"])
def test_cli_rejects_out_of_range_edition(year: str) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["ingest-boundaries", "--year", year])
    assert exc.value.code == 2
