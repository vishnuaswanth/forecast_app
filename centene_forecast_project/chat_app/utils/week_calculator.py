"""
Week Calculator Utility

Calculates per-week breakdowns for a given calendar month,
used for ramp configuration workflows in the chat app.
"""
import calendar
from datetime import date, timedelta
from typing import List, Dict


def month_abbr(month: int) -> str:
    """
    Return 3-letter month abbreviation for a given month number (1-12).

    Args:
        month: Month number (1-12)

    Returns:
        3-letter abbreviation, e.g. 'Jan', 'Feb', 'Dec'
    """
    return calendar.month_abbr[month]


def calculate_weeks(year: int, month: int) -> List[Dict]:
    """
    Calculate per-week breakdowns for a calendar month.

    Each entry covers one Mon–Sun week that overlaps the month.
    Weeks are clipped to the month boundary, and any clipped range with
    zero working days (Mon–Fri) is skipped.

    Args:
        year: Calendar year (e.g. 2026)
        month: Calendar month (1-12)

    Returns:
        List of week dicts, each with:
            label       (str)  – e.g. "Jan-1-2026" (first working day of the week portion)
            startDate   (str)  – ISO date "YYYY-MM-DD" (first calendar day of week within month)
            endDate     (str)  – ISO date "YYYY-MM-DD" (last calendar day of week within month)
            workingDays (int)  – Mon–Fri days in [startDate, endDate]
    """
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # Find the Monday of the week that contains first_day
    # weekday(): Monday=0, ..., Sunday=6
    days_since_monday = first_day.weekday()
    if days_since_monday == 5:   # Saturday → next Monday
        initial_monday = first_day + timedelta(days=2)
    elif days_since_monday == 6:  # Sunday → next Monday
        initial_monday = first_day + timedelta(days=1)
    else:
        initial_monday = first_day - timedelta(days=days_since_monday)

    weeks = []
    monday = initial_monday

    while monday <= last_day:
        sunday = monday + timedelta(days=6)

        # Clip to month boundaries
        week_start = max(monday, first_day)
        week_end = min(sunday, last_day)

        # Count Mon–Fri days in [week_start, week_end]
        working_days = sum(
            1 for offset in range((week_end - week_start).days + 1)
            if (week_start + timedelta(days=offset)).weekday() < 5
        )

        if working_days > 0:
            # Label = first working day in the clipped range
            label_date = week_start
            while label_date.weekday() >= 5 and label_date <= week_end:
                label_date += timedelta(days=1)

            label = f"{month_abbr(month)}-{label_date.day}-{year}"

            weeks.append({
                "label": label,
                "startDate": week_start.isoformat(),
                "endDate": week_end.isoformat(),
                "workingDays": working_days,
            })

        monday += timedelta(days=7)

    return weeks
