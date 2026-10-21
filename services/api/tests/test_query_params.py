"""Unit tests for the unknown/repeated query parameter guard on routes of every shape."""

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.api.errors import register_error_handlers
from app.api.query_params import reject_unknown_query_params


class Filters(BaseModel):
    limit: int = 10
    order_by: str = Field("date", alias="orderBy")


def paging(page: int = 1) -> int:
    return page


@pytest.fixture
def client() -> TestClient:
    app = FastAPI(dependencies=[Depends(reject_unknown_query_params)])
    register_error_handlers(app)

    @app.get("/model")
    def model_route(f: Annotated[Filters, Query()]) -> dict[str, object]:
        return f.model_dump()

    @app.get("/plain")
    def plain_route(
        tags: Annotated[list[str] | None, Query()] = None,
        q: Annotated[str | None, Query(alias="qq")] = None,
        page: int = Depends(paging),
    ) -> dict[str, object]:
        return {"tags": tags, "q": q, "page": page}

    @app.get("/none")
    def no_params() -> dict[str, str]:
        return {"ok": "yes"}

    return TestClient(app)


def test_fields_of_a_query_model_are_accepted(client: TestClient) -> None:
    assert client.get("/model", params={"limit": 5, "orderBy": "value"}).json() == {
        "limit": 5,
        "order_by": "value",
    }


def test_unknown_parameter_on_a_query_model_route(client: TestClient) -> None:
    body = client.get("/model", params={"offset": 1}).json()["error"]
    assert body["code"] == "unknown_parameter"
    assert body["details"]["allowed"] == ["limit", "orderBy"]


def test_aliases_lists_and_dependency_params(client: TestClient) -> None:
    response = client.get("/plain?tags=a&tags=b&qq=x&page=2")
    assert response.status_code == 200
    assert response.json() == {"tags": ["a", "b"], "q": "x", "page": 2}
    # The Python name is not an accepted query name when an alias is declared.
    assert client.get("/plain", params={"q": "x"}).json()["error"]["code"] == "unknown_parameter"


def test_repeated_scalar_parameter_is_rejected(client: TestClient) -> None:
    body = client.get("/plain?qq=a&qq=b").json()["error"]
    assert body["code"] == "repeated_parameter"
    assert body["details"]["repeated"] == ["qq"]


def test_route_without_parameters(client: TestClient) -> None:
    assert client.get("/none").status_code == 200
    assert client.get("/none?x=1").status_code == 422


def test_empty_parameter_name_is_readable(client: TestClient) -> None:
    body = client.get("/none?=1").json()["error"]
    assert body["details"]["unknown"] == [""]
    assert '""' in body["message"]
