"""
Attendance Service — all business logic for attendance calculations.

Handles:
  - Clock in / Clock out
  - OT (Overtime) calculation
  - Half day detection
  - Saturday working (1x normal, OT at 1.5x)
  - Sunday working (2x double pay)
  - Public holiday (2x double pay)
  - Late arrival detection
  - Monthly summary for payroll
"""

from datetime import datetime, date, time, timedelta
from typing import Optional
from sqlalchemy.orm import Session


# ── Sri Lanka Public Holidays
SL_PUBLIC_HOLIDAYS = {
    date(2025, 1, 1),   date(2025, 2, 4),   date(2025, 4, 13),
    date(2025, 4, 14),  date(2025, 5, 1),   date(2025, 5, 12),
    date(2025, 12, 25), date(2026, 1, 1),   date(2026, 2, 4),
    date(2026, 4, 13),  date(2026, 4, 14),  date(2026, 5, 1),
    date(2026, 12, 25),
}

# ── Work Config 
WORKDAY_START  = time(8, 30)   # 8:30 AM
WORKDAY_END    = time(17, 30)  # 5:30 PM
STANDARD_HOURS = 8.0           # Hours per normal day
LATE_GRACE     = 15            # Minutes grace before marked late
HALF_DAY_MIN   = 4.0           # Less than 4 hours = half day
OT_AFTER_HOURS = 9.0           # OT starts after 9 hours on weekday

# ── Pay Rate Multipliers
WEEKDAY_OT_RATE  = 1.5   # Weekday OT
SATURDAY_RATE    = 1.0   # Saturday standard hours
SATURDAY_OT_RATE = 1.5   # Saturday OT (after 8hrs)
SUNDAY_RATE      = 2.0   # All Sunday hours
HOLIDAY_RATE     = 2.0   # All public holiday hours


class AttendanceCalculator:

    @staticmethod
    def is_public_holiday(d: date) -> bool:
        return d in SL_PUBLIC_HOLIDAYS

    @staticmethod
    def is_saturday(d: date) -> bool:
        return d.weekday() == 5

    @staticmethod
    def is_sunday(d: date) -> bool:
        return d.weekday() == 6

    @staticmethod
    def get_day_type(d: date) -> str:
        if d in SL_PUBLIC_HOLIDAYS: return "holiday"
        if d.weekday() == 6:        return "sunday"
        if d.weekday() == 5:        return "saturday"
        return "weekday"

    @staticmethod
    def calc_work_hours(clock_in: datetime, clock_out: datetime) -> float:
        return round((clock_out - clock_in).total_seconds() / 3600, 2)

    @staticmethod
    def calc_late_minutes(clock_in: datetime) -> int:
        scheduled = clock_in.replace(
            hour=WORKDAY_START.hour, minute=WORKDAY_START.minute,
            second=0, microsecond=0
        )
        if clock_in <= scheduled + timedelta(minutes=LATE_GRACE):
            return 0
        return int((clock_in - scheduled).total_seconds() / 60)

    @staticmethod
    def calc_attendance_type(d: date, hours: float) -> str:
        if d in SL_PUBLIC_HOLIDAYS: return "holiday"
        if d.weekday() == 6:        return "sunday"
        if d.weekday() == 5:        return "saturday"
        if hours < HALF_DAY_MIN:    return "half_day"
        if hours > OT_AFTER_HOURS:  return "overtime"
        return "regular"

    @staticmethod
    def calc_ot_hours(hours: float, d: date) -> float:
        """OT hours based on day type."""
        if d in SL_PUBLIC_HOLIDAYS or d.weekday() == 6:
            return round(hours, 2)           # All hours = OT on holiday/Sunday
        if d.weekday() == 5:
            return round(max(0, hours - STANDARD_HOURS), 2)  # Saturday OT after 8hrs
        return round(max(0, hours - OT_AFTER_HOURS), 2)      # Weekday OT after 9hrs

    @staticmethod
    def calc_pay_breakdown(hours: float, d: date) -> dict:
        """
        Full pay breakdown for a day.
        Returns regular hours, OT hours, rates, and total pay units.
        """
        day_type = AttendanceCalculator.get_day_type(d)

        if day_type in ("holiday", "sunday"):
            rate           = HOLIDAY_RATE if day_type == "holiday" else SUNDAY_RATE
            regular_hours  = 0.0
            ot_hours       = hours
            ot_rate        = rate
        elif day_type == "saturday":
            regular_hours  = min(hours, STANDARD_HOURS)
            ot_hours       = max(0.0, hours - STANDARD_HOURS)
            ot_rate        = SATURDAY_OT_RATE
            rate           = SATURDAY_RATE
        else:  # weekday
            regular_hours  = min(hours, OT_AFTER_HOURS)
            ot_hours       = max(0.0, hours - OT_AFTER_HOURS)
            ot_rate        = WEEKDAY_OT_RATE
            rate           = 1.0

        total_pay_units = (regular_hours * rate) + (ot_hours * ot_rate)

        return {
            "day_type":       day_type,
            "regular_hours":  round(regular_hours, 2),
            "regular_rate":   rate,
            "ot_hours":       round(ot_hours, 2),
            "ot_rate":        ot_rate,
            "total_pay_units": round(total_pay_units, 2),
        }