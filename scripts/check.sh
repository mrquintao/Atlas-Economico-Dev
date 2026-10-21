#!/usr/bin/env bash
# Runs locally the same gates as the API and Web CI jobs (the Docker job runs only in CI).
# Requires TEST_DATABASE_URL pointing to a DISPOSABLE PostgreSQL database: it is dropped and
# re-created by the migration check and the test suite.
#
#   TEST_DATABASE_URL=postgresql+psycopg://atlas:atlas@localhost:5432/atlas_ci scripts/check.sh
set -euo pipefail
: "${TEST_DATABASE_URL:?set TEST_DATABASE_URL to a disposable database}"
root="$(cd "$(dirname "$0")/.." && pwd)"

echo "== API =="
cd "$root/services/api"
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head
DATABASE_URL="$TEST_DATABASE_URL" uv run alembic downgrade base
DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head
REQUIRE_DB_TESTS=1 uv run pytest -q

echo "== Web =="
cd "$root/apps/web"
export NEXT_TELEMETRY_DISABLED=1
npm ci
npm run lint
npm run typecheck
npm test
npm run build
echo "All local gates passed."
