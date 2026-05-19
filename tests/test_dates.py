from datetime import date

import pytest

from helpers.dates import (
    WEDDING_DATE,
    current_phase,
    days_until_wedding,
    next_3_days_range,
)


@pytest.mark.parametrize(
    "today,expected",
    [
        (date(2026, 5, 18), "Pre-window"),
        (date(2026, 5, 19), "This Week (5/19-22)"),
        (date(2026, 5, 22), "This Week (5/19-22)"),
        (date(2026, 5, 23), "Memorial Weekend (5/23-25)"),
        (date(2026, 5, 25), "Memorial Weekend (5/23-25)"),
        (date(2026, 5, 26), "Pre-bachelorette (5/26-27)"),
        (date(2026, 5, 28), "Bachelorette (5/28-31)"),
        (date(2026, 5, 31), "Bachelorette (5/28-31)"),
        (date(2026, 6, 1), "Early June (6/1-4)"),
        (date(2026, 6, 4), "Early June (6/1-4)"),
        (date(2026, 6, 5), "Frank + Tori (6/5-7)"),
        (date(2026, 6, 7), "Frank + Tori (6/5-7)"),
        (date(2026, 6, 8), "Production Week (6/8-14)"),
        (date(2026, 6, 14), "Production Week (6/8-14)"),
        (date(2026, 6, 15), "Wedding Week (6/15-19)"),
        (date(2026, 6, 19), "Wedding Week (6/15-19)"),
        (date(2026, 6, 20), "Wedding Day (6/20)"),
        (date(2026, 6, 21), "Brunch (6/21)"),
        (date(2026, 6, 22), "Post-wedding"),
        (date(2027, 1, 1), "Post-wedding"),
    ],
)
def test_current_phase(today, expected):
    assert current_phase(today) == expected


def test_no_phase_gaps_between_windows():
    """Every date from 5/19 through 6/21 must map to a real phase."""
    today = date(2026, 5, 19)
    while today <= date(2026, 6, 21):
        assert current_phase(today) != "Pre-window"
        assert current_phase(today) != "Post-wedding"
        today = date.fromordinal(today.toordinal() + 1)


@pytest.mark.parametrize(
    "today,expected",
    [
        (date(2026, 6, 20), 0),
        (date(2026, 6, 19), 1),
        (date(2026, 5, 18), 33),
        (date(2026, 6, 21), -1),
    ],
)
def test_days_until_wedding(today, expected):
    assert days_until_wedding(today) == expected


def test_wedding_date_constant():
    assert WEDDING_DATE == date(2026, 6, 20)


def test_next_3_days_range_excludes_today():
    """A task starting *today* is 'active', not 'coming up'.

    The range returned is (today, today+3]. Caller uses `today < start <= today+3`.
    """
    today = date(2026, 5, 19)
    start, end = next_3_days_range(today)
    assert start == today
    assert end == date(2026, 5, 22)
    assert not (start < start <= end)        # today is NOT in window
    assert date(2026, 5, 20) > start         # day+1 is in window
    assert date(2026, 5, 22) == end          # day+3 is in window
    assert not (start < date(2026, 5, 23) <= end)  # day+4 is NOT in window
