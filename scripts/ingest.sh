#!/usr/bin/env sh
# Incremental collection of every catalog indicator, for a host cron (outside Docker), e.g.
#   0 6 * * * /path/to/repo/scripts/ingest.sh >> /var/log/atlas-ingest.log 2>&1
# A failing indicator does not stop the others; the exit code is 1 if any of them failed.
# With Docker Compose, prefer the `scheduler` service (README, "Coleta automática").
set -eu
cd "$(dirname "$0")/../services/api"
exec uv run python -m app.ingestion.cli ingest --all
