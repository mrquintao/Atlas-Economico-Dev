"""Command-line entry point for data collection.

Examples:
    python -m app.ingestion.cli ingest SELIC_TARGET            # incremental
    python -m app.ingestion.cli ingest SELIC_TARGET --full     # full official history
    python -m app.ingestion.cli ingest SELIC_TARGET --start 2020-01-01 --end 2020-12-31
    python -m app.ingestion.cli ingest --all                   # every catalog indicator

The exit code is 0 when every requested collection succeeds and 1 when any of them fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from typing import Any

from app.core.clock import brazil_today
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.ingestion.batch import BatchResult, run_batch
from app.ingestion.series_ingestion import IngestionError

EXIT_OK = 0
EXIT_FAILED = 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas-ingest", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="Collect indicators from their official sources")
    target = ingest.add_mutually_exclusive_group(required=True)
    target.add_argument("indicator", nargs="?", help="Internal indicator code, e.g. SELIC_TARGET")
    target.add_argument("--all", action="store_true", help="Every indicator in the catalog")
    ingest.add_argument("--full", action="store_true", help="Reprocess the full history")
    ingest.add_argument("--start", type=date.fromisoformat, help="YYYY-MM-DD")
    ingest.add_argument("--end", type=date.fromisoformat, help="YYYY-MM-DD")
    args = parser.parse_args(argv)
    # Reject operator mistakes here: inside the batch they would be recorded as failed runs and
    # shown publicly as collection failures although no source failed.
    if args.start and args.end and args.start > args.end:
        parser.error("--start must be on or before --end")
    if args.start and args.start > brazil_today():
        parser.error("--start is in the future (Brasília time)")

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    options = {"start": args.start, "end": args.end, "full": args.full}
    codes = None if args.all else [args.indicator]
    try:
        with get_session_factory()() as session:
            result = run_batch(session, settings, codes, **options)
    except IngestionError as exc:  # invalid request, e.g. an unknown indicator code
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAILED
    print(json.dumps(_report(result), default=str, ensure_ascii=False, indent=2))
    return EXIT_OK if result.ok else EXIT_FAILED


def _report(result: BatchResult) -> list[dict[str, Any]]:
    return [
        {
            "indicator": item.indicator_code,
            "status": item.status,
            "run_id": item.run_id,
            "error": item.error,
            "summary": asdict(item.summary) if item.summary else None,
        }
        for item in result.items
    ]


if __name__ == "__main__":
    sys.exit(main())
