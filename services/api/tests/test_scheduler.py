"""Scheduler unit tests: schedule parsing, next-run computation and the run loop (no database)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, time, timedelta

import pytest

from app.core.clock import BRAZIL_TZ
from app.ingestion import scheduler
from app.ingestion.scheduler import ScheduleError, next_run_after, parse_schedule, run_forever


def test_parse_schedule_sorts_and_deduplicates() -> None:
    assert parse_schedule(" 18:30,06:00 ,06:00") == [time(6, 0), time(18, 30)]


@pytest.mark.parametrize("text", ["", "6:00", "06:60", "24:00", "06h00", "06:00,", "noon"])
def test_parse_schedule_rejects_invalid_entries(text: str) -> None:
    with pytest.raises(ScheduleError, match="INGEST_SCHEDULE"):
        parse_schedule(text)


def brt(*args: int) -> datetime:
    return datetime(*args, tzinfo=BRAZIL_TZ)


def test_next_run_is_later_today_in_brasilia_time() -> None:
    # 08:00 UTC is 05:00 in Brasília: the 06:00 run of the same day comes next.
    now = datetime(2024, 3, 10, 8, 0, tzinfo=UTC)
    assert next_run_after(now, [time(6), time(18)]) == brt(2024, 3, 10, 6)


def test_next_run_rolls_over_to_the_next_day() -> None:
    # 23:30 UTC on the 10th is 20:30 in Brasília: next run is 06:00 on the 11th.
    now = datetime(2024, 3, 10, 23, 30, tzinfo=UTC)
    assert next_run_after(now, [time(6), time(18)]) == brt(2024, 3, 11, 6)


def test_next_run_is_strictly_after_now() -> None:
    assert next_run_after(brt(2024, 3, 10, 6), [time(6)]) == brt(2024, 3, 11, 6)


def test_next_run_crosses_year_end() -> None:
    assert next_run_after(brt(2024, 12, 31, 23, 59), [time(6)]) == brt(2025, 1, 1, 6)


class FakeClock:
    """Virtual time: ``wait`` on the stop event advances the clock instead of sleeping."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def make_stop(clock: FakeClock) -> threading.Event:
    stop = threading.Event()

    def wait(timeout: float | None = None) -> bool:
        clock.now += timedelta(seconds=timeout or 0)
        return stop.is_set()

    stop.wait = wait  # type: ignore[method-assign]
    return stop


def test_runs_at_each_scheduled_time_and_survives_failures() -> None:
    clock = FakeClock(brt(2024, 3, 10, 5))
    stop = make_stop(clock)
    calls: list[datetime] = []

    def run() -> None:
        calls.append(clock.now)
        if len(calls) == 1:
            raise RuntimeError("synthetic crash")  # must not stop the scheduler
        if len(calls) == 3:
            stop.set()

    run_forever([time(6), time(18)], run, stop=stop, clock=clock)
    assert calls == [brt(2024, 3, 10, 6), brt(2024, 3, 10, 18), brt(2024, 3, 11, 6)]


def test_long_waits_are_split_so_clock_changes_are_noticed() -> None:
    clock = FakeClock(brt(2024, 3, 10, 6, 1))
    stop = make_stop(clock)
    waits: list[float] = []
    original_wait = stop.wait

    def recording_wait(timeout: float | None = None) -> bool:
        waits.append(timeout or 0)
        return original_wait(timeout)

    stop.wait = recording_wait  # type: ignore[method-assign]
    run_forever([time(6)], stop.set, stop=stop, clock=clock)
    assert max(waits) <= 3600
    assert clock.now == brt(2024, 3, 11, 6)


def test_run_on_start_collects_immediately() -> None:
    clock = FakeClock(brt(2024, 3, 10, 12))
    stop = make_stop(clock)
    calls: list[datetime] = []

    def run() -> None:
        calls.append(clock.now)
        stop.set()

    run_forever([time(6)], run, stop=stop, run_on_start=True, clock=clock)
    assert calls == [brt(2024, 3, 10, 12)]


def test_stop_before_the_first_run_exits_without_collecting() -> None:
    stop = threading.Event()
    stop.set()
    calls: list[int] = []
    run_forever([time(6)], lambda: calls.append(1), stop=stop)
    assert calls == []


def test_check_validates_configuration(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    from app.core.config import Settings

    monkeypatch.setattr(scheduler, "configure_logging", lambda *_: None)
    monkeypatch.setattr(scheduler, "get_settings", lambda: Settings(ingest_schedule="18:30,06:00"))
    assert scheduler.main(["--check"]) == 0
    assert "06:00, 18:30" in capsys.readouterr().out

    monkeypatch.setattr(scheduler, "get_settings", lambda: Settings(ingest_schedule="25:00"))
    assert scheduler.main(["--check"]) == scheduler.EXIT_CONFIG_ERROR
