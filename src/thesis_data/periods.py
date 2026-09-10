"""Calendar-aware period helpers."""

from calendar import monthrange
from datetime import date
import re


_QUARTER_PATTERN = re.compile(r"^(?P<year>\d{4})_Q(?P<quarter>[1-4])$")


def validate_period_bounds(period: str) -> tuple[date, date]:
    """Return real calendar boundaries for a ``YYYY_QN`` period."""
    match = _QUARTER_PATTERN.fullmatch(period)
    if match is None:
        raise ValueError("period must use YYYY_QN format")

    year = int(match.group("year"))
    quarter = int(match.group("quarter"))
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    return date(year, start_month, 1), date(
        year,
        end_month,
        monthrange(year, end_month)[1],
    )
