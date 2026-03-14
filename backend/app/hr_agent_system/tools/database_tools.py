"""
tools/database_tools.py
────────────────────────
Pure data-fetching LangChain tools for all agents.
ZERO decision logic here — tools return raw data as JSON strings.
The LLM agent reads the data and reasons about it.

Used by: leave_agent, performance_agent, reporting_agent
"""

import json
from datetime import date, timedelta
from typing import Optional

from langchain.tools import tool
from sqlalchemy.orm import Session

from models.database import (
    SessionLocal, Employee, Attendance, LeaveRequest,
    LeaveBalance, LeaveType, PerformanceReview,
)


# ── Helper ────────────────────────────────────────────────────────────────────

def _db() -> Session:
    return SessionLocal()


# ── Employee Tools ────────────────────────────────────────────────────────────

@tool
def get_employee_profile(employee_id: int) -> str:
    """
    Fetch full employee profile from the database.
    Returns: name, department, role, salary, probation status, hire date.
    """
    db = _db()
    try:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            return json.dumps({"found": False, "message": f"Employee {employee_id} not found."})
        return json.dumps({
            "found":           True,
            "id":              emp.id,
            "employee_number": emp.employee_number,
            "name":            emp.full_name,
            "personal_email":  emp.personal_email,
            "work_email":      emp.work_email,
            "department_id":   emp.department_id,
            "role_id":         emp.role_id,
            "base_salary":     float(emp.base_salary) if emp.base_salary else None,
            "status":          emp.status,
            "is_probation":    emp.status == "probation",
            "hire_date":       str(emp.hire_date) if emp.hire_date else None,
            "probation_end":   str(emp.probation_end) if emp.probation_end else None,
            "is_active":       emp.is_active,
            "face_registered": emp.face_registered,
        })
    finally:
        db.close()


# ── Leave Balance Tools ───────────────────────────────────────────────────────

@tool
def get_leave_balance(employee_id: int, leave_type_id: int) -> str:
    """
    Fetch current leave balance for an employee and leave type.
    Returns: total, used, pending, remaining days for current year.
    """
    db = _db()
    try:
        bal = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id   == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year          == date.today().year,
        ).first()
        if not bal:
            return json.dumps({"found": False, "message": "No balance record found."})
        return json.dumps({
            "found":          True,
            "leave_type":     bal.leave_type.name if bal.leave_type else "Unknown",
            "code":           bal.leave_type.code if bal.leave_type else "",
            "year":           bal.year,
            "total_days":     float(bal.total_days),
            "used_days":      float(bal.used_days),
            "pending_days":   float(bal.pending_days),
            "remaining_days": float(bal.remaining_days),
            "carried_over":   float(bal.carried_over),
        })
    finally:
        db.close()


@tool
def get_all_leave_balances(employee_id: int) -> str:
    """
    Fetch leave balances for ALL leave types for an employee.
    Returns: summary of all leave types with remaining days.
    """
    db = _db()
    try:
        bals = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year        == date.today().year,
        ).all()
        if not bals:
            return json.dumps({"found": False, "message": "No balance records found."})
        return json.dumps({
            "found":    True,
            "year":     date.today().year,
            "balances": [
                {
                    "type":      b.leave_type.name if b.leave_type else "Unknown",
                    "code":      b.leave_type.code if b.leave_type else "",
                    "total":     float(b.total_days),
                    "used":      float(b.used_days),
                    "remaining": float(b.remaining_days),
                }
                for b in bals if b.leave_type
            ],
        })
    finally:
        db.close()


# ── Attendance Tools ──────────────────────────────────────────────────────────

@tool
def get_attendance_stats(employee_id: int, days: int = 90) -> str:
    """
    Get attendance statistics for the last N days.
    Returns: attendance percentage, present/absent/late counts.
    """
    db = _db()
    try:
        since   = date.today() - timedelta(days=days)
        records = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.work_date   >= since,
        ).all()
        if not records:
            return json.dumps({"message": f"No records in last {days} days.", "attendance_percent": 100.0})

        total   = len(records)
        present = sum(1 for r in records if not r.is_absent)
        absent  = sum(1 for r in records if r.is_absent)
        late    = sum(1 for r in records if r.is_late)
        ot_hrs  = sum(r.overtime_hours or 0.0 for r in records)
        flagged = sum(1 for r in records if r.flagged)
        pct     = round(present / total * 100, 1) if total > 0 else 100.0

        return json.dumps({
            "employee_id":        employee_id,
            "period_days":        days,
            "total_records":      total,
            "present_days":       present,
            "absent_days":        absent,
            "late_days":          late,
            "flagged_records":    flagged,
            "overtime_hours":     round(ot_hrs, 2),
            "attendance_percent": pct,
        })
    finally:
        db.close()


@tool
def get_monthly_attendance(employee_id: int, period: str) -> str:
    """
    Get detailed attendance for a specific month (period='2026-03').
    Returns: daily records with clock-in/out, OT, late flags.
    """
    db = _db()
    try:
        year, month = int(period[:4]), int(period[5:7])
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = date(year, month, 1)
        end   = date(year, month, last_day)

        records = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.work_date   >= start,
            Attendance.work_date   <= end,
        ).order_by(Attendance.work_date).all()

        return json.dumps({
            "employee_id": employee_id,
            "period":      period,
            "records": [
                {
                    "date":        str(r.work_date)[:10],
                    "clock_in":    str(r.clock_in)[:19] if r.clock_in else None,
                    "clock_out":   str(r.clock_out)[:19] if r.clock_out else None,
                    "work_hours":  r.work_hours,
                    "is_late":     r.is_late,
                    "late_min":    r.late_minutes,
                    "is_absent":   r.is_absent,
                    "ot_hours":    r.overtime_hours,
                    "flagged":     r.flagged,
                    "flag_reason": r.flag_reason,
                }
                for r in records
            ],
            "total": len(records),
        })
    finally:
        db.close()


# ── Leave History Tools ───────────────────────────────────────────────────────

@tool
def get_leave_history(employee_id: int, limit: int = 10) -> str:
    """
    Get recent leave requests for an employee.
    Returns: last N leave requests with status, type, and dates.
    """
    db = _db()
    try:
        leaves = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == employee_id,
        ).order_by(LeaveRequest.id.desc()).limit(limit).all()
        return json.dumps({
            "count": len(leaves),
            "history": [
                {
                    "id":     l.id,
                    "type":   l.leave_type.name if l.leave_type else "Unknown",
                    "start":  str(l.start_date)[:10],
                    "end":    str(l.end_date)[:10],
                    "days":   float(l.total_days),
                    "status": l.status,
                    "reason": l.reason,
                    "ai_decision": l.ai_decision,
                }
                for l in leaves
            ],
        })
    finally:
        db.close()


@tool
def check_leave_overlap(employee_id: int, start_date: str, end_date: str) -> str:
    """
    Check if there is any approved/pending leave overlapping with the requested dates.
    Returns: conflict details if found, or no_conflict.
    """
    db = _db()
    try:
        start  = date.fromisoformat(start_date)
        end    = date.fromisoformat(end_date)
        exists = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date  <= end,
            LeaveRequest.end_date    >= start,
        ).first()
        if exists:
            return json.dumps({
                "has_conflict": True,
                "conflict": {
                    "type":   exists.leave_type.name if exists.leave_type else "Unknown",
                    "start":  str(exists.start_date)[:10],
                    "end":    str(exists.end_date)[:10],
                    "status": exists.status,
                },
            })
        return json.dumps({"has_conflict": False})
    finally:
        db.close()


# ── Performance Tools ─────────────────────────────────────────────────────────

@tool
def get_performance_reviews(employee_id: int, limit: int = 5) -> str:
    """
    Get recent performance reviews for an employee.
    Returns: review scores, ratings, and AI summaries.
    """
    db = _db()
    try:
        reviews = db.query(PerformanceReview).filter(
            PerformanceReview.employee_id == employee_id,
        ).order_by(PerformanceReview.period_end.desc()).limit(limit).all()
        return json.dumps({
            "count": len(reviews),
            "reviews": [
                {
                    "id":                  r.id,
                    "period_type":         r.period_type,
                    "period_start":        str(r.period_start)[:10],
                    "period_end":          str(r.period_end)[:10],
                    "overall_score":       r.overall_score,
                    "rating":              r.rating,
                    "attendance_score":    r.attendance_score,
                    "punctuality_score":   r.punctuality_score,
                    "overtime_score":      r.overtime_score,
                    "is_promotion_eligible": r.is_promotion_eligible,
                    "requires_pip":        r.requires_pip,
                    "ai_summary":          r.ai_summary,
                    "status":              r.status,
                }
                for r in reviews
            ],
        })
    finally:
        db.close()
