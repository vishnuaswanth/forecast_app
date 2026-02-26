"""
Unit tests for chat_app.utils.week_calculator.
"""
import pytest
from chat_app.utils.week_calculator import calculate_weeks, month_abbr


# ---------------------------------------------------------------------------
# month_abbr helper
# ---------------------------------------------------------------------------

def test_month_abbr_january():
    assert month_abbr(1) == "Jan"


def test_month_abbr_december():
    assert month_abbr(12) == "Dec"


# ---------------------------------------------------------------------------
# January 2026 (starts Thursday → partial first week: Thu + Fri = 2 working days)
# ---------------------------------------------------------------------------

class TestJanuary2026:
    weeks = calculate_weeks(2026, 1)

    def test_first_week_label(self):
        # Thursday Jan-1 is the first working day in the first partial week
        assert self.weeks[0]["label"] == "Jan-1-2026"

    def test_first_week_working_days(self):
        # Thu + Fri only → 2 working days
        assert self.weeks[0]["workingDays"] == 2

    def test_first_week_end_date(self):
        # Clipped to Sunday Jan-4
        assert self.weeks[0]["endDate"] == "2026-01-04"

    def test_total_weeks_count(self):
        # Jan 2026: 5 week segments (partial + 4 full)
        assert len(self.weeks) == 5

    def test_last_week_end_date(self):
        # Last day of Jan = 2026-01-31 (Saturday clipped → Fri Jan-30 is last working day)
        assert self.weeks[-1]["endDate"] == "2026-01-31"

    def test_all_start_dates_in_month(self):
        for w in self.weeks:
            assert w["startDate"].startswith("2026-01")

    def test_all_end_dates_in_month(self):
        for w in self.weeks:
            assert w["endDate"].startswith("2026-01")


# ---------------------------------------------------------------------------
# February 2024 (leap year: 29 days, starts Thursday)
# ---------------------------------------------------------------------------

class TestFebruary2024Leap:
    weeks = calculate_weeks(2024, 2)

    def test_last_day_included(self):
        # Feb 29 exists in leap year
        end_dates = [w["endDate"] for w in self.weeks]
        assert "2024-02-29" in end_dates

    def test_positive_working_days(self):
        for w in self.weeks:
            assert w["workingDays"] > 0

    def test_label_format(self):
        for w in self.weeks:
            assert w["label"].startswith("Feb-")
            assert w["label"].endswith("-2024")

    def test_no_overlap_between_weeks(self):
        from datetime import date
        dates_seen = set()
        for w in self.weeks:
            start = date.fromisoformat(w["startDate"])
            end = date.fromisoformat(w["endDate"])
            for offset in range((end - start).days + 1):
                from datetime import timedelta
                d = start + timedelta(days=offset)
                assert d not in dates_seen, f"Date {d} seen in multiple weeks"
                dates_seen.add(d)


# ---------------------------------------------------------------------------
# February 2025 (non-leap, 28 days; starts Saturday → first working day = Mon Feb 3)
# ---------------------------------------------------------------------------

class TestFebruary2025NonLeap:
    weeks = calculate_weeks(2025, 2)

    def test_first_week_start_is_monday(self):
        # Sat Feb 1 is weekend; first week starts Mon Feb 3
        assert self.weeks[0]["startDate"] == "2025-02-03"

    def test_last_day_is_feb28(self):
        end_dates = [w["endDate"] for w in self.weeks]
        assert "2025-02-28" in end_dates

    def test_first_week_working_days(self):
        # Mon Feb 3 through Fri Feb 7 = 5 working days (full week)
        assert self.weeks[0]["workingDays"] == 5

    def test_feb1_and_feb2_not_in_any_week(self):
        all_dates = []
        from datetime import date, timedelta
        for w in self.weeks:
            start = date.fromisoformat(w["startDate"])
            end = date.fromisoformat(w["endDate"])
            for offset in range((end - start).days + 1):
                all_dates.append(start + timedelta(days=offset))
        assert date(2025, 2, 1) not in all_dates
        assert date(2025, 2, 2) not in all_dates


# ---------------------------------------------------------------------------
# Month starting on Monday → first week is a full 5-day week
# March 2021 starts on Monday
# ---------------------------------------------------------------------------

class TestMonthStartingOnMonday:
    # March 2021 starts on Monday
    weeks = calculate_weeks(2021, 3)

    def test_first_week_starts_on_monday(self):
        assert self.weeks[0]["startDate"] == "2021-03-01"

    def test_first_week_has_five_working_days(self):
        assert self.weeks[0]["workingDays"] == 5

    def test_first_week_label_is_mar1(self):
        assert self.weeks[0]["label"] == "Mar-1-2021"


# ---------------------------------------------------------------------------
# October 2025 — month with 5 full Mon–Fri weeks
# Oct 2025: Oct 1 = Wed
# ---------------------------------------------------------------------------

class TestOctober2025:
    weeks = calculate_weeks(2025, 10)

    def test_at_least_five_weeks(self):
        # Oct has 31 days, starts Wednesday → should have partial first + 4 full + partial last
        assert len(self.weeks) >= 5

    def test_last_day_included(self):
        end_dates = [w["endDate"] for w in self.weeks]
        assert "2025-10-31" in end_dates

    def test_total_working_days_equals_23(self):
        # Oct 2025 has 23 working days (Mon-Fri)
        total = sum(w["workingDays"] for w in self.weeks)
        assert total == 23


# ---------------------------------------------------------------------------
# General invariants for any month
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("year,month", [
    (2025, 1), (2025, 6), (2025, 12),
    (2026, 2), (2026, 7), (2026, 11),
])
def test_all_weeks_have_positive_working_days(year, month):
    weeks = calculate_weeks(year, month)
    for w in weeks:
        assert w["workingDays"] > 0, f"Week {w['label']} has 0 working days"


@pytest.mark.parametrize("year,month", [
    (2025, 1), (2025, 6), (2025, 12),
])
def test_working_days_never_exceed_five(year, month):
    weeks = calculate_weeks(year, month)
    for w in weeks:
        assert w["workingDays"] <= 5, f"Week {w['label']} has more than 5 working days"


@pytest.mark.parametrize("year,month", [
    (2024, 2), (2025, 2), (2026, 2),
])
def test_february_ends_correctly(year, month):
    import calendar as cal
    expected_last = cal.monthrange(year, month)[1]
    weeks = calculate_weeks(year, month)
    last_end = max(w["endDate"] for w in weeks)
    assert last_end == f"{year:04d}-{month:02d}-{expected_last:02d}"
