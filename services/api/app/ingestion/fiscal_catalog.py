"""Where each state fiscal indicator is published in the SICONFI annexes (S4, ADR 0010).

Validated by the economist against the official API (see docs/state-fiscal-indicators.md, which
also lists the official samples used by the regression tests). Each indicator is one published
row; an exercise outside every selector has no observation.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.ingestion.fiscal_indicators import FiscalIndicator, RowSelector

FISCAL_INDICATORS: dict[str, FiscalIndicator] = {
    definition.code: definition
    for definition in (
        # Filled from the economist's mapping.
    )
}


def required_annexes(
    definitions: Iterable[FiscalIndicator], exercises: Sequence[int]
) -> list[tuple[str, str, str | None]]:
    """Distinct (report type, annex, power) needed by the definitions in these exercises."""
    needed: dict[tuple[str, str, str | None], None] = {}
    for definition in definitions:
        for selector in definition.selectors:
            if any(selector.covers(exercise) for exercise in exercises):
                needed[(selector.report_type, selector.annex, selector.power)] = None
    return list(needed)


__all__ = ["FISCAL_INDICATORS", "RowSelector", "required_annexes"]
