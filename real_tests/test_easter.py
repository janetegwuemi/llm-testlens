# test_easter.py
# Tests for dateutil.easter - self-contained, Windows-compatible
# Source: adapted from dateutil test suite

import pytest
from dateutil.easter import easter, EASTER_JULIAN, EASTER_ORTHODOX, EASTER_WESTERN
from datetime import date


class TestEasterWestern:
    """Tests for Western (Gregorian) Easter calculation."""

    def test_easter_western_2000(self):
        assert easter(2000) == date(2000, 4, 23)

    def test_easter_western_2001(self):
        assert easter(2001) == date(2001, 4, 15)

    def test_easter_western_2002(self):
        assert easter(2002) == date(2002, 3, 31)

    def test_easter_western_2003(self):
        assert easter(2003) == date(2003, 4, 20)

    def test_easter_western_2004(self):
        assert easter(2004) == date(2004, 4, 11)

    def test_easter_western_2005(self):
        assert easter(2005) == date(2005, 3, 27)

    def test_easter_western_2006(self):
        assert easter(2006) == date(2006, 4, 16)

    def test_easter_western_2007(self):
        assert easter(2007) == date(2007, 4, 8)

    def test_easter_western_2008(self):
        assert easter(2008) == date(2008, 3, 23)

    def test_easter_western_2009(self):
        assert easter(2009) == date(2009, 4, 12)

    def test_easter_western_2010(self):
        assert easter(2010) == date(2010, 4, 4)

    def test_easter_western_2020(self):
        assert easter(2020) == date(2020, 4, 12)

    def test_easter_western_2025(self):
        assert easter(2025) == date(2025, 4, 20)

    def test_easter_western_returns_date(self):
        result = easter(2023)
        assert isinstance(result, date)

    def test_easter_western_is_sunday(self):
        # Easter is always a Sunday (weekday 6)
        for year in range(2000, 2030):
            assert easter(year).weekday() == 6


class TestEasterOrthodox:
    """Tests for Orthodox Easter calculation."""

    def test_easter_orthodox_2000(self):
        assert easter(2000, EASTER_ORTHODOX) == date(2000, 4, 30)

    def test_easter_orthodox_2001(self):
        assert easter(2001, EASTER_ORTHODOX) == date(2001, 4, 15)

    def test_easter_orthodox_2010(self):
        assert easter(2010, EASTER_ORTHODOX) == date(2010, 4, 4)

    def test_easter_orthodox_2020(self):
        assert easter(2020, EASTER_ORTHODOX) == date(2020, 4, 19)

    def test_easter_orthodox_is_sunday(self):
        for year in range(2000, 2020):
            assert easter(year, EASTER_ORTHODOX).weekday() == 6


class TestEasterJulian:
    """Tests for Julian Easter calculation."""

    def test_easter_julian_2000(self):
        assert easter(2000, EASTER_JULIAN) == date(2000, 4, 17)

    def test_easter_julian_2001(self):
        assert easter(2001, EASTER_JULIAN) == date(2001, 4, 2)

    def test_easter_julian_returns_date(self):
        result = easter(2023, EASTER_JULIAN)
        assert isinstance(result, date)


class TestEasterEdgeCases:
    """Edge case tests."""

    def test_easter_invalid_method_raises(self):
        with pytest.raises(ValueError):
            easter(2020, method=0)

    def test_easter_invalid_method_too_high(self):
        with pytest.raises(ValueError):
            easter(2020, method=4)

    def test_easter_default_method_is_western(self):
        assert easter(2020) == easter(2020, EASTER_WESTERN)

    def test_easter_historical_1954(self):
        assert easter(1954) == date(1954, 4, 18)

    def test_easter_historical_1818(self):
        assert easter(1818) == date(1818, 3, 22)