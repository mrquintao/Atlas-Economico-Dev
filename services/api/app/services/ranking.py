"""Ranking of UFs by the value of one state indicator at a single period (S8)."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

RankingOrder = Literal["desc", "asc"]


@dataclass(frozen=True, slots=True)
class RankedValue:
    position: int
    acronym: str
    value: Decimal


def rank_values(values: Mapping[str, Decimal], order: RankingOrder) -> list[RankedValue]:
    """Standard competition ranking ("1, 2, 2, 4") of the UFs that have a value.

    Ties are decided on the stored decimals (never floats), so equal published values always
    share a position; within a tie the UFs follow their acronyms. UFs without a value are not
    passed here: an absence is never ranked as zero.
    """
    descending = order == "desc"
    items = sorted(values.items(), key=lambda kv: kv[0])
    items.sort(key=lambda kv: kv[1], reverse=descending)
    ranked: list[RankedValue] = []
    for index, (acronym, value) in enumerate(items):
        tied = bool(ranked) and ranked[-1].value == value
        position = ranked[-1].position if tied else index + 1
        ranked.append(RankedValue(position=position, acronym=acronym, value=value))
    return ranked
