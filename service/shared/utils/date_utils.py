"""Date utilities for the homeapp service."""

from datetime import date, timedelta


def get_month_lookback_start(ref_date: date, months: int) -> date:
    """Calculate the first day of the month 'months' periods before ref_date.

    Example: If ref_date is 2026-02-15 and months=6, it returns 2025-08-01.
    """
    year = ref_date.year
    month = ref_date.month

    # Subtract months
    total_months = year * 12 + (month - 1) - months
    new_year = total_months // 12
    new_month = (total_months % 12) + 1

    return date(new_year, new_month, 1)


def get_month_range(ref_date: date) -> tuple[date, date]:
    """Get the first and last day of the month for the given ref_date."""
    first_day = ref_date.replace(day=1)
    if first_day.month == 12:
        next_month_first = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month_first = first_day.replace(month=first_day.month + 1)
    last_day = next_month_first - timedelta(days=1)
    return first_day, last_day
