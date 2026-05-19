from __future__ import annotations

from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    from backports.zoneinfo import ZoneInfo  # type: ignore

TIMEZONE = ZoneInfo("America/New_York")
WEDDING_DATE = date(2026, 6, 20)

PHASE_WINDOWS = [
    ("This Week (5/19-22)",        date(2026, 5, 19), date(2026, 5, 22)),
    ("Memorial Weekend (5/23-25)", date(2026, 5, 23), date(2026, 5, 25)),
    ("Pre-bachelorette (5/26-27)", date(2026, 5, 26), date(2026, 5, 27)),
    ("Bachelorette (5/28-31)",     date(2026, 5, 28), date(2026, 5, 31)),
    ("Early June (6/1-4)",         date(2026, 6, 1),  date(2026, 6, 4)),
    ("Frank + Tori (6/5-7)",       date(2026, 6, 5),  date(2026, 6, 7)),
    ("Production Week (6/8-14)",   date(2026, 6, 8),  date(2026, 6, 14)),
    ("Wedding Week (6/15-19)",     date(2026, 6, 15), date(2026, 6, 19)),
    ("Wedding Day (6/20)",         date(2026, 6, 20), date(2026, 6, 20)),
    ("Brunch (6/21)",              date(2026, 6, 21), date(2026, 6, 21)),
]

POST_WEDDING_CUTOFF = date(2026, 6, 21)


def today_ny() -> date:
    return datetime.now(TIMEZONE).date()


def now_ny() -> datetime:
    return datetime.now(TIMEZONE)


def current_phase(today: date) -> str:
    if today > POST_WEDDING_CUTOFF:
        return "Post-wedding"
    for name, start, end in PHASE_WINDOWS:
        if start <= today <= end:
            return name
    return "Pre-window"


def days_until_wedding(today: date) -> int:
    return (WEDDING_DATE - today).days


def next_3_days_range(today: date) -> tuple[date, date]:
    """Returns (start_exclusive, end_inclusive) for the 'next 3 days' window.

    A task with start_date strictly after today and on-or-before today+3 falls in.
    """
    return today, today + timedelta(days=3)
