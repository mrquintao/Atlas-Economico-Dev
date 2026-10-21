import json
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise

import pytest

from app.integrations.bcb.sgs import (
    SGSPayloadError,
    format_sgs_date,
    parse_sgs_date,
    parse_sgs_payload,
    parse_sgs_value,
    split_into_windows,
)
from tests.conftest import load_fixture


class TestDates:
    def test_parses_brazilian_format(self) -> None:
        assert parse_sgs_date("05/03/1999") == date(1999, 3, 5)
        assert parse_sgs_date(" 29/02/2024 ") == date(2024, 2, 29)

    def test_formats_brazilian_format(self) -> None:
        assert format_sgs_date(date(2008, 1, 1)) == "01/01/2008"

    @pytest.mark.parametrize("raw", ["2024-01-01", "31/02/2024", "", "01/13/2024", None])
    def test_rejects_invalid_dates(self, raw: str) -> None:
        with pytest.raises(SGSPayloadError):
            parse_sgs_date(raw)


class TestValues:
    def test_parses_decimal_exactly(self) -> None:
        assert parse_sgs_value("13.75") == Decimal("13.75")
        assert parse_sgs_value("0.10") == Decimal("0.10")
        assert parse_sgs_value("-1.5") == Decimal("-1.5")

    @pytest.mark.parametrize("raw", [None, "", "  ", "null", "-"])
    def test_missing_values_become_none_not_zero(self, raw: str | None) -> None:
        assert parse_sgs_value(raw) is None

    @pytest.mark.parametrize("raw", ["13,75", "abc", "NaN", "Infinity", "1.2.3"])
    def test_rejects_invalid_numbers(self, raw: str) -> None:
        with pytest.raises(SGSPayloadError):
            parse_sgs_value(raw)


class TestPayload:
    def test_real_fixture(self) -> None:
        points, skipped = parse_sgs_payload(json.loads(load_fixture("sgs_432_sample.json")))
        assert skipped == 0
        assert [p.reference_date for p in points] == [
            date(2026, 9, 14) + timedelta(days=i) for i in range(7)
        ]
        # Copom decision effective from 17/09/2026: 14.00 -> 13.75
        assert points[2].value == Decimal("14.00")
        assert points[3].value == Decimal("13.75")

    def test_sorts_and_skips_nulls(self) -> None:
        payload = [
            {"data": "03/01/2024", "valor": "11.75"},
            {"data": "01/01/2024", "valor": "11.75"},
            {"data": "02/01/2024", "valor": ""},
        ]
        points, skipped = parse_sgs_payload(payload)
        assert [p.reference_date.day for p in points] == [1, 3]
        assert skipped == 1

    def test_empty_list(self) -> None:
        assert parse_sgs_payload([]) == ([], 0)

    @pytest.mark.parametrize(
        "payload",
        [
            {"erro": "x"},
            "text",
            [{"data": "01/01/2024"}],
            [{"valor": "1"}],
            ["01/01/2024"],
        ],
    )
    def test_rejects_unexpected_structure(self, payload: object) -> None:
        with pytest.raises(SGSPayloadError):
            parse_sgs_payload(payload)

    def test_rejects_duplicate_dates(self) -> None:
        payload = [{"data": "01/01/2024", "valor": "1"}, {"data": "01/01/2024", "valor": "2"}]
        with pytest.raises(SGSPayloadError, match="Duplicate"):
            parse_sgs_payload(payload)


class TestWindows:
    def test_ten_year_windows_cover_range_without_gaps_or_overlap(self) -> None:
        start, end = date(1999, 3, 5), date(2026, 10, 21)
        windows = list(split_into_windows(start, end, 10))
        assert windows[0][0] == start
        assert windows[-1][1] == end
        for (_, prev_end), (next_start, _) in pairwise(windows):
            assert next_start == prev_end + timedelta(days=1)
        for w_start, w_end in windows:
            assert w_end < w_start.replace(year=w_start.year + 10)
        assert windows[:2] == [
            (date(1999, 3, 5), date(2009, 3, 4)),
            (date(2009, 3, 5), date(2019, 3, 4)),
        ]

    def test_short_range_is_single_window(self) -> None:
        assert list(split_into_windows(date(2024, 1, 1), date(2024, 1, 1), 10)) == [
            (date(2024, 1, 1), date(2024, 1, 1))
        ]

    def test_leap_day_start(self) -> None:
        windows = list(split_into_windows(date(2024, 2, 29), date(2026, 1, 1), 1))
        assert windows[0] == (date(2024, 2, 29), date(2025, 2, 27))
        assert windows[1][0] == date(2025, 2, 28)

    def test_rejects_inverted_range(self) -> None:
        with pytest.raises(ValueError):
            list(split_into_windows(date(2024, 1, 2), date(2024, 1, 1), 10))
