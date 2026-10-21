from datetime import UTC, date, datetime

from app.core.clock import brazil_today


def test_evening_in_brasilia_is_still_the_same_day() -> None:
    # 00:11 UTC on 21/10 is 21:11 on 20/10 in Brasília: 21/10 has not started in Brazil.
    assert brazil_today(datetime(2026, 10, 21, 0, 11, tzinfo=UTC)) == date(2026, 10, 20)


def test_after_midnight_in_brasilia() -> None:
    assert brazil_today(datetime(2026, 10, 21, 3, 0, tzinfo=UTC)) == date(2026, 10, 21)
