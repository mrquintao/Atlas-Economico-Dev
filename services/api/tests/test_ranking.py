"""Competition ranking of UFs (S8): pure function, no database."""

from decimal import Decimal

from app.services.ranking import rank_values


def test_descending_with_ties_and_negative_values() -> None:
    values = {
        "SP": Decimal("124.23"),
        "ES": Decimal("-14.70"),
        "RJ": Decimal("217.25"),
        "MG": Decimal("124.23"),
        "AP": Decimal("-0.8"),
    }
    ranked = [(r.position, r.acronym) for r in rank_values(values, "desc")]
    assert ranked == [(1, "RJ"), (2, "MG"), (2, "SP"), (4, "AP"), (5, "ES")]


def test_ascending_keeps_acronym_order_within_ties() -> None:
    values = {"SP": Decimal("1"), "BA": Decimal("1"), "AC": Decimal("0")}
    ranked = [(r.position, r.acronym) for r in rank_values(values, "asc")]
    assert ranked == [(1, "AC"), (2, "BA"), (2, "SP")]


def test_ties_use_decimal_equality() -> None:
    # Equal decimals with different scales tie; nearly equal values do not.
    values = {"SP": Decimal("45.740"), "RJ": Decimal("45.74"), "BA": Decimal("45.7400001")}
    ranked = [(r.position, r.acronym) for r in rank_values(values, "desc")]
    assert ranked == [(1, "BA"), (2, "RJ"), (2, "SP")]


def test_empty() -> None:
    assert rank_values({}, "desc") == []
