"""Command-line entry point for data collection.

Examples:
    python -m app.ingestion.cli ingest SELIC_TARGET            # incremental
    python -m app.ingestion.cli ingest SELIC_TARGET --full     # full official history
    python -m app.ingestion.cli ingest SELIC_TARGET --start 2020-01-01 --end 2020-12-31
    python -m app.ingestion.cli ingest --all                   # every catalog indicator
    python -m app.ingestion.cli ingest-boundaries              # IBGE state mesh (S2)
    python -m app.ingestion.cli ingest-boundaries --year 2021  # another mesh edition
    python -m app.ingestion.cli ingest-siconfi --report RREO --annex "RREO-Anexo 03" \
        --state SP --state RJ --year 2024                     # SICONFI report annex (S3)
    python -m app.ingestion.cli ingest-siconfi --report RGF --annex "RGF-Anexo 02" \
        --state SP --year 2023 --year 2024 --period 3 --refresh

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
from app.ingestion.boundaries import ingest_state_boundaries
from app.ingestion.series_ingestion import IngestionError, format_error
from app.ingestion.siconfi import ingest_siconfi_reports
from app.integrations.tesouro.siconfi import POWERS

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
    boundaries = sub.add_parser(
        "ingest-boundaries", help="Collect the official IBGE boundaries of the 27 states"
    )
    boundaries.add_argument(
        "--year", type=int, help="Mesh edition (IBGE `periodo`); default: IBGE_MESH_YEAR"
    )
    siconfi = sub.add_parser(
        "ingest-siconfi", help="Collect a SICONFI report annex (RREO/RGF) of states"
    )
    siconfi.add_argument("--report", required=True, choices=("RREO", "RGF"))
    siconfi.add_argument("--annex", required=True, help='e.g. "RREO-Anexo 03", "RGF-Anexo 02"')
    siconfi.add_argument(
        "--state", action="append", required=True, help="UF acronym (repeatable), e.g. SP"
    )
    siconfi.add_argument("--year", type=int, action="append", required=True, help="Exercise")
    siconfi.add_argument("--period", type=int, action="append", help="Default: every period")
    siconfi.add_argument("--power", choices=POWERS, help="RGF only; default: E (executive)")
    siconfi.add_argument(
        "--refresh", action="store_true", help="Collect again even if no newer delivery is listed"
    )
    args = parser.parse_args(argv)
    if args.command == "ingest-siconfi":
        if any(not 2015 <= y <= brazil_today().year for y in args.year):
            parser.error("--year must be between 2015 and the current year")
        if args.power and args.report != "RGF":
            parser.error("--power applies only to the RGF")
        return _ingest_siconfi(args)
    if args.command == "ingest-boundaries":
        if args.year is not None and not 2000 <= args.year <= brazil_today().year:
            parser.error("--year must be between 2000 and the current year")
        return _ingest_boundaries(args.year)
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


def _ingest_boundaries(year: int | None) -> int:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    try:
        with get_session_factory()() as session:
            summary = ingest_state_boundaries(session, settings, mesh_year=year)
    except Exception as exc:  # recorded in ingestion_runs by the ingestion itself
        print(f"error: {format_error(exc)}", file=sys.stderr)
        return EXIT_FAILED
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return EXIT_OK


def _ingest_siconfi(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    try:
        with get_session_factory()() as session:
            summary = ingest_siconfi_reports(
                session,
                settings,
                report_type=args.report,
                annex=args.annex,
                states=args.state,
                exercises=sorted(set(args.year)),
                periods=sorted(set(args.period)) if args.period else None,
                power=args.power,
                refresh=args.refresh,
            )
    except Exception as exc:  # invalid request, or a failure recorded in ingestion_runs
        print(f"error: {format_error(exc)}", file=sys.stderr)
        return EXIT_FAILED
    report = asdict(summary)
    report["revisions"] = report["revisions"][:20]  # full list in ingestion_runs.metadata_json
    print(json.dumps(report, ensure_ascii=False, indent=2))
    delivered = [o for o in summary.reports if o.status != "not_delivered"]
    if delivered and all(o.status == "not_available" for o in delivered):
        # Usually a wrong annex name (the API answers an empty list instead of an error).
        print(
            "error: every delivered period came back empty; check the annex name",
            file=sys.stderr,
        )
        return EXIT_FAILED
    return EXIT_OK


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
