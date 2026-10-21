"""Simple in-process scheduler: collects every catalog indicator at fixed times of day.

No queue, no cron daemon: one long-running process (the Compose ``scheduler`` service) sleeps
until the next configured time in Brasília, runs the same batch as ``ingest --all`` and repeats.

    INGEST_SCHEDULE="06:00,18:30" python -m app.ingestion.scheduler
    python -m app.ingestion.scheduler --check     # validate configuration and database, exit
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta

from app.core.clock import BRAZIL_TZ
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import get_session_factory
from app.ingestion.batch import BatchResult, run_batch, select_indicators
from app.ingestion.series_ingestion import format_error

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


class ScheduleError(ValueError):
    pass


def parse_schedule(text: str) -> list[time]:
    """Parses "HH:MM[,HH:MM...]" (24-hour clock, Brasília time) into sorted unique times."""
    times: set[time] = set()
    for raw in text.split(","):
        item = raw.strip()
        try:
            hours, minutes = item.split(":")
            if len(hours) != 2 or len(minutes) != 2:
                raise ValueError
            times.add(time(int(hours), int(minutes)))
        except ValueError:
            raise ScheduleError(
                f"Invalid INGEST_SCHEDULE entry {item!r}: expected HH:MM, e.g. 06:00"
            ) from None
    return sorted(times)


def next_run_after(now: datetime, times: list[time]) -> datetime:
    """First scheduled instant strictly after ``now`` (an aware datetime), in Brasília time."""
    if not times:
        raise ScheduleError("Empty schedule")
    local_now = now.astimezone(BRAZIL_TZ)
    for day_offset in (0, 1):
        day = local_now.date() + timedelta(days=day_offset)
        for at in times:
            candidate = datetime.combine(day, at, tzinfo=BRAZIL_TZ)
            if candidate > local_now:
                return candidate
    raise AssertionError("unreachable: a schedule always has a time within 24 hours")


def collect_all(settings: Settings, stop: threading.Event | None = None) -> BatchResult:
    """One scheduled execution: every catalog indicator, incrementally."""
    with get_session_factory()() as session:
        return run_batch(session, settings, should_stop=stop.is_set if stop else lambda: False)


def check_database() -> int:
    """Number of catalog indicators; raises if the database is unreachable or not migrated."""
    with get_session_factory()() as session:
        return len(select_indicators(session, None))


def run_forever(
    times: list[time],
    run: Callable[[], object],
    *,
    stop: threading.Event,
    run_on_start: bool = False,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> None:
    """Runs ``run`` at each scheduled time until ``stop`` is set.

    A failing execution is logged and never stops the scheduler; the next one runs as planned.
    """
    if run_on_start:
        _run_safely(run)
    while not stop.is_set():
        target = next_run_after(clock(), times)
        logger.info("scheduler_waiting", extra={"next_run": target.isoformat()})
        # Wake up at least hourly, so a suspended host or clock change is noticed promptly.
        while not stop.is_set() and (remaining := (target - clock()).total_seconds()) > 0:
            stop.wait(min(remaining, 3600))
        if stop.is_set():
            break
        _run_safely(run)
    logger.info("scheduler_stopped")


def _run_safely(run: Callable[[], object]) -> None:
    started = datetime.now(UTC)
    try:
        result = run()
    except Exception:
        logger.exception("scheduled_collection_crashed")
        return
    ok = getattr(result, "ok", True)
    log = logger.info if ok else logger.error
    log(
        "scheduled_collection_finished",
        extra={
            "ok": ok,
            "failed": getattr(result, "failed", []),
            "seconds": round((datetime.now(UTC) - started).total_seconds(), 1),
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas-scheduler", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="Validate the schedule, print the next run and exit"
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    try:
        times = parse_schedule(settings.ingest_schedule)
    except ScheduleError as exc:
        logger.error("scheduler_invalid_config", extra={"error": str(exc)})
        return EXIT_CONFIG_ERROR
    schedule = [t.strftime("%H:%M") for t in times]
    next_run = next_run_after(datetime.now(UTC), times).isoformat()
    if args.check:
        # Also prove the service reaches a migrated database with a non-empty catalog, so a
        # wrong DATABASE_URL shows up at deploy time rather than at the first scheduled run.
        try:
            indicators = check_database()
        except Exception as exc:
            logger.error("scheduler_database_unavailable", extra={"error": format_error(exc)})
            return EXIT_CONFIG_ERROR
        if indicators == 0:
            logger.error("scheduler_empty_catalog")
            return EXIT_CONFIG_ERROR
        print(
            f"schedule (America/Sao_Paulo): {', '.join(schedule)}; next run: {next_run}; "
            f"catalog indicators: {indicators}"
        )
        return EXIT_OK

    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("scheduler_stop_requested", extra={"signal": signal.Signals(signum).name})
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    logger.info(
        "scheduler_started",
        extra={
            "schedule": schedule,
            "timezone": str(BRAZIL_TZ),
            "run_on_start": settings.ingest_on_start,
        },
    )
    run_forever(
        times,
        lambda: collect_all(settings, stop),
        stop=stop,
        run_on_start=settings.ingest_on_start,
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
