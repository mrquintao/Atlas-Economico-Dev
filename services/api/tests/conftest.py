"""Shared fixtures.

Unit tests need nothing external. Database tests run against a real PostgreSQL database given
by TEST_DATABASE_URL (it is reset and migrated at session start) and are skipped otherwise.
Tests never call the real BCB API: HTTP is served by httpx.MockTransport.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"
API_ROOT = Path(__file__).parent.parent
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL or "postgresql+psycopg://unused/unused",
        http_max_retries=3,
        http_backoff_base_seconds=0.01,
        bcb_min_request_interval_seconds=0,
        bcb_daily_window_years=10,
    )


Handler = Callable[[httpx.Request], httpx.Response]


def sgs_json(points: list[tuple[str, str | None]], status: int = 200) -> httpx.Response:
    """Build an SGS-like JSON response from (dd/mm/aaaa, valor) pairs. Synthetic test data."""
    body = [{"data": d, "valor": v} for d, v in points]
    return httpx.Response(
        status, content=json.dumps(body), headers={"content-type": "application/json"}
    )


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    if not TEST_DATABASE_URL:
        if os.environ.get("REQUIRE_DB_TESTS") == "1":
            pytest.fail("REQUIRE_DB_TESTS=1 but TEST_DATABASE_URL is not set")
        pytest.skip("TEST_DATABASE_URL not set; skipping database tests")
    eng = create_engine(TEST_DATABASE_URL)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Session inside an outer transaction rolled back after each test (commits become
    savepoints), so tests are isolated even though the code under test commits."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
