"""Where each state fiscal indicator is published in the SICONFI annexes (S4, ADR 0010).

Validated by the economist against the official API on 2026-10-21 (docs/state-fiscal-indicators.md
lists the decisions and the official samples used by the regression tests). Each indicator is one
published row, matched by exact account code and column; an exercise outside every selector has
no observation. The ``rotulo`` is not used: it is "Padrão" since 2017 and null before.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.ingestion.fiscal_indicators import FiscalIndicator, RowSelector

# RGF Anexo 02 republishes earlier periods; column n is read only from the report of period n.
RGF_PERIOD_COLUMN = "Até o {period}º Quadrimestre"


def _rgf2(account_code: str, first_exercise: int) -> RowSelector:
    return RowSelector("RGF", "RGF-Anexo 02", "E", account_code, RGF_PERIOD_COLUMN, first_exercise)


FISCAL_INDICATORS: dict[str, FiscalIndicator] = {
    definition.code: definition
    for definition in (
        FiscalIndicator(
            "STATE_RCL",
            (
                RowSelector(
                    "RREO",
                    "RREO-Anexo 03",
                    None,
                    "RREO3ReceitaCorrenteLiquida",
                    "TOTAL (ÚLTIMOS 12 MESES)",
                    2018,
                ),
            ),
        ),
        FiscalIndicator("STATE_DC", (_rgf2("DividaConsolidada", 2018),)),
        FiscalIndicator("STATE_DCL", (_rgf2("DividaConsolidadaLiquida", 2018),)),
        # From 2020 the published denominator is the RCL adjusted for the debt limits; earlier
        # exercises used the plain RCL and are left out so that one definition is shown.
        FiscalIndicator("STATE_DCL_RCL", (_rgf2("PercentualDaDCLSobreARCL", 2020),)),
        FiscalIndicator(
            "STATE_PERSONNEL_EXEC",
            (RowSelector("RGF", "RGF-Anexo 01", "E", "DespesaComPessoalTotal", "Valor", 2018),),
        ),
        FiscalIndicator(
            "STATE_PERSONNEL_EXEC_RCL",
            (
                RowSelector(
                    "RGF",
                    "RGF-Anexo 01",
                    "E",
                    "DespesaComPessoalTotal",
                    "% sobre a RCL Ajustada",
                    2018,
                ),
            ),
        ),
        # MDF 13th edition (2023) separated the RPPS; earlier lines are another concept.
        FiscalIndicator(
            "STATE_PRIMARY_RESULT",
            (
                RowSelector(
                    "RREO",
                    "RREO-Anexo 06",
                    None,
                    "ResultadoPrimarioSemRPPSAcimaDaLinha",
                    "VALOR",
                    2023,
                ),
            ),
            year_to_date=True,
        ),
        FiscalIndicator(
            "STATE_NOMINAL_RESULT",
            (
                RowSelector(
                    "RREO",
                    "RREO-Anexo 06",
                    None,
                    "ResultadoNominalAcimaDaLinhaSemRPPS",
                    "VALOR",
                    2023,
                ),
            ),
            year_to_date=True,
        ),
        FiscalIndicator(
            "STATE_INVESTMENTS",
            (
                RowSelector(
                    "RREO",
                    "RREO-Anexo 01",
                    None,
                    "Investimentos",
                    "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)",
                    2018,
                ),
            ),
            year_to_date=True,
        ),
    )
}


# Year-to-date flows: statistics across periods would compare non-comparable values.
YEAR_TO_DATE_CODES = frozenset(c for c, d in FISCAL_INDICATORS.items() if d.year_to_date)


def required_annexes(
    definitions: Iterable[FiscalIndicator], exercises: Sequence[int]
) -> dict[tuple[str, str, str | None], list[int]]:
    """(report type, annex, power) needed by the definitions -> the exercises it is needed for."""
    needed: dict[tuple[str, str, str | None], set[int]] = {}
    for definition in definitions:
        for selector in definition.selectors:
            covered = {exercise for exercise in exercises if selector.covers(exercise)}
            if covered:
                key = (selector.report_type, selector.annex, selector.power)
                needed.setdefault(key, set()).update(covered)
    return {key: sorted(years) for key, years in needed.items()}
