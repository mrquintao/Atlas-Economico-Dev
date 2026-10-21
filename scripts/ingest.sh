#!/usr/bin/env sh
# Incremental collection of all implemented indicators. Suitable for cron, e.g. daily at 21:30
# (after the BCB publishes):  30 21 * * * /path/to/repo/scripts/ingest.sh >> /var/log/atlas-ingest.log 2>&1
set -eu
cd "$(dirname "$0")/../services/api"
for indicator in SELIC_TARGET DBGG_GDP IPCA_12M; do
  uv run python -m app.ingestion.cli ingest "$indicator"
done
