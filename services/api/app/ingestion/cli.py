"""Command-line entry point for data collection.

Examples:
    python -m app.ingestion.cli ingest SELIC_TARGET            # incremental
    python -m app.ingestion.cli ingest SELIC_TARGET --full     # full official history
    python -m app.ingestion.cli ingest SELIC_TARGET --start 2020-01-01 --end 2020-12-31
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.ingestion.series_ingestion import (
    IngestionError,
    ingest_sgs_indicator,
    ingest_sidra_indicator,
)
from app.integrations.bcb.sgs import SGSClient
from app.integrations.ibge.sidra import SIDRAClient
from app.models import Indicator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas-ingest", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="Collect an indicator from its official source")
    ingest.add_argument("indicator", help="Internal indicator code, e.g. SELIC_TARGET")
    ingest.add_argument("--full", action="store_true", help="Reprocess the full history")
    ingest.add_argument("--start", type=date.fromisoformat, help="YYYY-MM-DD")
    ingest.add_argument("--end", type=date.fromisoformat, help="YYYY-MM-DD")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    options = {"start": args.start, "end": args.end, "full": args.full}
    with get_session_factory()() as session:
        indicator = session.scalar(select(Indicator).where(Indicator.code == args.indicator))
        if indicator is None:
            raise IngestionError(f"Unknown indicator: {args.indicator}")
        # Dispatch by data source: BCB -> SGS, IBGE -> SIDRA.
        if indicator.source.acronym == "IBGE":
            with SIDRAClient(settings) as sidra:
                summary = ingest_sidra_indicator(session, sidra, args.indicator, **options)
        else:
            with SGSClient(settings) as sgs:
                summary = ingest_sgs_indicator(session, sgs, args.indicator, **options)
    print(json.dumps(asdict(summary), default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
