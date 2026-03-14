"""
tools/analytics_tools.py
─────────────────────────
SQL aggregation tools for Reporting and Performance agents.
Pure data — no decisions. Returns structured JSON for LLM analysis.
"""

import json
from datetime import date, timedelta
from calendar import monthrange

from langchain.tools import tool
from sqlalchemy import func, and_

from models.database import (
    SessionLocal, Employee, Attendance, LeaveRequest,
    PerformanceReview, LeaveBalance,
)


@tool
def get_monthly_summary(period: str) -> str:
    """
    Aggregate HR metrics for a full month (period='2026-03').
    Returns: headcount, attendance rate, leave stats, OT hours.
    """
    db = SessionLocal()
    try:
        year, month = int(period[:4]), int(period[5:7])
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end   = date(year, month, last_day)

        total_employees = db.query(func.count(Employee.id)).filter(
            Employee.is_active == True).scalar() or 0

        att_records = db.query(Attendance).filter(
            Attendance.work_date >= start,
            Attendance.work_date <= end,
        ).all()
        present_count = sum(1 for r in att_records if not r.is_absent)
        absent_count  = sum(1 for r in att_records if r.is_absent)
        late_count    = sum(1 for r in att_records if r.is_late)
        ot_hours      = sum(r.overtime_hours or 0.0 for r in att_records)

        leave_requests = db.query(LeaveRequest).filter(
            LeaveRequest.start_date >= start,
            LeaveRequest.end_date   <= end,
        ).all()
        leave_by_status = {}
        for lr in leave_requests:
            leave_by_status[lr.status] = leave_by_status.get(lr.status, 0) + 1

        working_days = last_day - sum(
            1 for d in range(1, last_day + 1)
            if date(year, month, d).weekday() == 6
        )
        att_rate = round(present_count / max(1, total_employees * working_days) * 100, 1)

        return json.dumps({
            "period":           period,
            "total_employees":  total_employees,
            "working_days":     working_days,
            "attendance_rate":  att_rate,
            "present_count":    present_count,
            "absent_count":     absent_count,
            "late_count":       late_count,
            "overtime_hours":   round(ot_hours, 2),
            "leave_requests":   leave_by_status,
            "total_leave_apps": len(leave_requests),
        })
    finally:
        db.close()


@tool
def get_department_breakdown(period: str) -> str:
    """
    Break down attendance and leave metrics by department_id.
    Useful for identifying high-absenteeism departments.
    """
    db = SessionLocal()
    try:
        year, month = int(period[:4]), int(period[5:7])
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end   = date(year, month, last_day)

        employees = db.query(Employee).filter(Employee.is_active == True).all()
        dept_map  = {}
        for emp in employees:
            dept = str(emp.department_id) if emp.department_id else "Unassigned"
            if dept not in dept_map:
                dept_map[dept] = {"count": 0, "present": 0, "absent": 0, "ot_hours": 0.0}
            dept_map[dept]["count"] += 1

            records = db.query(Attendance).filter(
                Attendance.employee_id == emp.id,
                Attendance.work_date   >= start,
                Attendance.work_date   <= end,
            ).all()
            dept_map[dept]["present"]  += sum(1 for r in records if not r.is_absent)
            dept_map[dept]["absent"]   += sum(1 for r in records if r.is_absent)
            dept_map[dept]["ot_hours"] += sum(r.overtime_hours or 0 for r in records)

        return json.dumps({"period": period, "departments": dept_map})
    finally:
        db.close()


@tool
def get_leave_utilisation(year: int = None) -> str:
    """
    Calculate leave utilisation rates across all leave types.
    Shows how much of each leave entitlement is actually being used.
    """
    if not year:
        year = date.today().year
    db = SessionLocal()
    try:
        balances = db.query(LeaveBalance).filter(LeaveBalance.year == year).all()
        summary = {}
        for b in balances:
            code = b.leave_type.code if b.leave_type else "UNK"
            if code not in summary:
                summary[code] = {"total": 0.0, "used": 0.0, "name": ""}
            summary[code]["total"] += b.total_days
            summary[code]["used"]  += b.used_days
            summary[code]["name"]   = b.leave_type.name if b.leave_type else code

        for code in summary:
            t = summary[code]["total"]
            u = summary[code]["used"]
            summary[code]["utilisation_pct"] = round(u / t * 100, 1) if t > 0 else 0.0

        return json.dumps({"year": year, "leave_utilisation": summary})
    finally:
        db.close()


@tool
def get_top_performers(period_start: str, period_end: str, limit: int = 5) -> str:
    """
    Get top N employees by performance score for a given period range.
    period_start and period_end are ISO date strings (e.g. '2026-01-01', '2026-03-31').
    Returns ranked list with scores and ratings.
    """
    db = SessionLocal()
    try:
        from datetime import date as dt
        start = dt.fromisoformat(period_start)
        end   = dt.fromisoformat(period_end)
        reviews = db.query(PerformanceReview).filter(
            PerformanceReview.period_start >= start,
            PerformanceReview.period_end   <= end,
            PerformanceReview.overall_score != None,
        ).order_by(PerformanceReview.overall_score.desc()).limit(limit).all()
        return json.dumps({
            "period_start": period_start,
            "period_end":   period_end,
            "top_performers": [
                {
                    "employee_id": r.employee_id,
                    "score":       r.overall_score,
                    "rating":      r.rating,
                    "is_promotion_eligible": r.is_promotion_eligible,
                    "requires_pip": r.requires_pip,
                }
                for r in reviews
            ],
        })
    finally:
        db.close()
