from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

# Official Brazilian series are dated in Brasília time. Using UTC would treat the evening of
# day D (21:00-24:00 BRT) as day D+1 and store a pre-published value that has not started yet.
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def brazil_today(now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(BRAZIL_TZ).date()
