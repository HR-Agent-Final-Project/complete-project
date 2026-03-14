"""
api/reports.py
───────────────
Module 7 — Reporting & Analytics REST API

All analytics are computed directly from the PostgreSQL DB using SQLAlchemy
aggregations (no LangGraph needed for data). OpenAI is only called for the
optional AI narrative on full report generation.

Endpoints:
  GET  /dashboard          → live KPI tiles for the HR dashboard
  GET  /attendance/summary → monthly attendance breakdown
  GET  /attendance/trends  → last 6 months attendance rate (chart data)
  GET  /leave/summary      → leave utilisation by type
  GET  /leave/trends       → monthly leave request counts (chart)
  GET  /performance/summary→ rating distribution + top/low performers
  GET  /headcount          → total, active, by department, new hires
  GET  /department/{id}    → deep dive for one department
  POST /generate           → full AI report (KPIs + narrative + saved to DB)
  GET  /history            → list all saved reports
  GET  /history/{id}       → get one saved report
"""

import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_employee, require_role
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest, LeaveBalance, LeaveType, LeaveStatus
from app.models.performance import PerformanceReview
from app.models.department import Department
from app.models.report import HRReport
from app.schemas.report import GenerateReportRequest, ReportOut, ReportSummary

router = APIRouter()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_period(period: Optional[str]) -> tuple[date, date]:
    """Parse 'YYYY-MM' → (first_day, last_day). Defaults to current month."""
    if not period:
        today = date.today()
        period = today.strftime("%Y-%m")
    year, month = int(period[:4]), int(period[5:7])
    _, last = monthrange(year, month)
    return date(year, month, 1), date(year, month, last)


def _working_days(start: date, end: date) -> int:
    """Count Mon–Sat (Sri Lanka works 5 or 6 days; exclude Sunday only)."""
    total = 0
    d = start
    while d <= end:
        if d.weekday() != 6:   # 6 = Sunday
            total += 1
        d += timedelta(days=1)
    return total


def _rating_band(score: float) -> str:
    if score >= 90:  return "Excellent"
    if score >= 75:  return "Good"
    if score >= 60:  return "Average"
    if score >= 40:  return "Needs Improvement"
    return "Critical"


# ── 1. Dashboard KPIs ─────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(
    current_user: Employee = Depends(require_role(2)),
    db: Session            = Depends(get_db),
):
    """
    Live KPI tiles for the HR dashboard home page.
    Returns headcount, today's attendance, pending leaves, flagged records.
    HR Staff+ only.
    """
    today = date.today()

    # Headcount
    total_active = db.query(func.count(Employee.id)).filter(
        Employee.is_active == True
    ).scalar() or 0

    # Today's attendance
    clocked_in_today = db.query(func.count(Attendance.id)).filter(
        Attendance.work_date == today,
        Attendance.clock_in  != None,
        Attendance.is_absent == False,
    ).scalar() or 0

    late_today = db.query(func.count(Attendance.id)).filter(
        Attendance.work_date == today,
        Attendance.is_late   == True,
    ).scalar() or 0

    # This month attendance rate
    start_m, end_m = _parse_period(None)
    wdays = _working_days(start_m, min(today, end_m))
    att_records_m = db.query(Attendance).filter(
        Attendance.work_date >= start_m,
        Attendance.work_date <= today,
    ).all()
    present_m = sum(1 for r in att_records_m if not r.is_absent)
    att_rate  = round(present_m / max(1, total_active * wdays) * 100, 1) if wdays > 0 else 0.0

    # Pending leaves
    pending_leaves = db.query(func.count(LeaveRequest.id)).filter(
        LeaveRequest.status.in_(["pending", "escalated"])
    ).scalar() or 0

    # Flagged attendance records (unresolved)
    flagged_att = db.query(func.count(Attendance.id)).filter(
        Attendance.flagged   == True,
        Attendance.flag_reason != None,
    ).scalar() or 0

    # OT hours this month
    ot_month = db.query(func.sum(Attendance.overtime_hours)).filter(
        Attendance.work_date >= start_m,
        Attendance.work_date <= today,
    ).scalar() or 0.0

    # On leave today
    on_leave_today = db.query(func.count(LeaveRequest.id)).filter(
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date   >= today,
        LeaveRequest.status     == "approved",
    ).scalar() or 0

    # Performance reviews (current quarter)
    q_start = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    reviews_this_quarter = db.query(func.count(PerformanceReview.id)).filter(
        PerformanceReview.period_start >= q_start,
    ).scalar() or 0

    return {
        "date": str(today),
        "headcount": {
            "total_active":   total_active,
            "on_leave_today": on_leave_today,
        },
        "attendance_today": {
            "clocked_in":     clocked_in_today,
            "late":           late_today,
            "absent":         total_active - clocked_in_today - on_leave_today,
        },
        "attendance_month": {
            "rate_percent":   att_rate,
            "ot_hours":       round(ot_month, 1),
        },
        "leave": {
            "pending_requests": pending_leaves,
        },
        "flags": {
            "flagged_attendance": flagged_att,
        },
        "performance": {
            "reviews_this_quarter": reviews_this_quarter,
        },
    }


# ── 2. Attendance Summary ─────────────────────────────────────────────────────

@router.get("/attendance/summary")
def attendance_summary(
    period      : Optional[str] = Query(None, description="YYYY-MM, default = current month"),
    department_id: Optional[int] = Query(None),
    current_user: Employee      = Depends(require_role(2)),
    db          : Session       = Depends(get_db),
):
    """Monthly attendance breakdown: present, absent, late, OT, by employee."""
    start, end = _parse_period(period)
    wdays      = _working_days(start, end)

    q = db.query(Employee).filter(Employee.is_active == True)
    if department_id:
        q = q.filter(Employee.department_id == department_id)
    employees = q.all()

    rows = []
    total_present = total_absent = total_late = total_ot = 0

    for emp in employees:
        records = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.work_date   >= start,
            Attendance.work_date   <= end,
        ).all()
        present  = sum(1 for r in records if not r.is_absent)
        absent   = sum(1 for r in records if r.is_absent)
        late     = sum(1 for r in records if r.is_late)
        ot       = sum(r.overtime_hours or 0.0 for r in records)
        att_rate = round(present / wdays * 100, 1) if wdays > 0 else 0.0

        total_present += present
        total_absent  += absent
        total_late    += late
        total_ot      += ot

        rows.append({
            "employee_id":     emp.id,
            "employee_number": emp.employee_number,
            "name":            emp.full_name,
            "present_days":    present,
            "absent_days":     absent,
            "late_days":       late,
            "overtime_hours":  round(ot, 2),
            "attendance_rate": att_rate,
            "below_threshold": att_rate < settings.ATTENDANCE_THRESHOLD_PERCENT,
        })

    overall_rate = round(
        total_present / max(1, len(employees) * wdays) * 100, 1
    ) if employees else 0.0

    # Sort: worst attendance first (useful for HR review)
    rows.sort(key=lambda r: r["attendance_rate"])

    return {
        "period":        period or date.today().strftime("%Y-%m"),
        "working_days":  wdays,
        "total_employees": len(employees),
        "summary": {
            "overall_attendance_rate": overall_rate,
            "total_present":   total_present,
            "total_absent":    total_absent,
            "total_late":      total_late,
            "total_ot_hours":  round(total_ot, 2),
            "below_threshold": sum(1 for r in rows if r["below_threshold"]),
        },
        "employees": rows,
    }


# ── 3. Attendance Trends (6-month chart data) ─────────────────────────────────

@router.get("/attendance/trends")
def attendance_trends(
    months      : int      = Query(6, ge=1, le=24),
    current_user: Employee = Depends(require_role(2)),
    db          : Session  = Depends(get_db),
):
    """
    Returns month-by-month attendance rate for chart rendering.
    Data: [{month, attendance_rate, late_count, ot_hours}]
    """
    total_active = db.query(func.count(Employee.id)).filter(
        Employee.is_active == True
    ).scalar() or 1

    today   = date.today()
    results = []

    for i in range(months - 1, -1, -1):
        # Go back i months
        year  = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year  -= 1

        _, last = monthrange(year, month)
        start   = date(year, month, 1)
        end     = date(year, month, last)
        wdays   = _working_days(start, end)

        records = db.query(Attendance).filter(
            Attendance.work_date >= start,
            Attendance.work_date <= end,
        ).all()

        present = sum(1 for r in records if not r.is_absent)
        late    = sum(1 for r in records if r.is_late)
        ot      = sum(r.overtime_hours or 0.0 for r in records)
        rate    = round(present / max(1, total_active * wdays) * 100, 1) if wdays > 0 else 0.0

        results.append({
            "month":            f"{year}-{month:02d}",
            "label":            date(year, month, 1).strftime("%b %Y"),
            "attendance_rate":  rate,
            "late_count":       late,
            "ot_hours":         round(ot, 1),
            "working_days":     wdays,
        })

    return {"months": months, "data": results}


# ── 4. Leave Summary ──────────────────────────────────────────────────────────

@router.get("/leave/summary")
def leave_summary(
    year        : Optional[int] = Query(None),
    current_user: Employee      = Depends(require_role(2)),
    db          : Session       = Depends(get_db),
):
    """Leave utilisation by type: total entitlement vs used days."""
    yr = year or date.today().year

    balances = db.query(LeaveBalance).filter(
        LeaveBalance.year == yr
    ).all()

    # Group by leave type
    by_type: dict = {}
    for b in balances:
        code = b.leave_type.code if b.leave_type else "UNK"
        name = b.leave_type.name if b.leave_type else code
        if code not in by_type:
            by_type[code] = {
                "code":          code,
                "name":          name,
                "total_days":    0.0,
                "used_days":     0.0,
                "pending_days":  0.0,
                "remaining_days":0.0,
                "employees":     0,
            }
        by_type[code]["total_days"]     += float(b.total_days)
        by_type[code]["used_days"]      += float(b.used_days)
        by_type[code]["pending_days"]   += float(b.pending_days)
        by_type[code]["remaining_days"] += float(b.remaining_days)
        by_type[code]["employees"]      += 1

    for v in by_type.values():
        t = v["total_days"]
        v["utilisation_pct"] = round(v["used_days"] / t * 100, 1) if t > 0 else 0.0

    # Pending / escalated leave counts
    pending_by_type = {}
    pending_leaves  = db.query(LeaveRequest).filter(
        LeaveRequest.status.in_(["pending", "escalated"])
    ).all()
    for lr in pending_leaves:
        code = lr.leave_type.code if lr.leave_type else "UNK"
        pending_by_type[code] = pending_by_type.get(code, 0) + 1

    # Total leave requests this year by status
    this_year_start = date(yr, 1, 1)
    this_year_end   = date(yr, 12, 31)
    year_requests   = db.query(LeaveRequest).filter(
        LeaveRequest.start_date >= this_year_start,
        LeaveRequest.start_date <= this_year_end,
    ).all()
    status_counts: dict = {}
    for lr in year_requests:
        s = str(lr.status.value) if hasattr(lr.status, "value") else str(lr.status)
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "year":            yr,
        "leave_types":     list(by_type.values()),
        "pending_by_type": pending_by_type,
        "request_status_counts": status_counts,
        "total_requests":  len(year_requests),
    }


# ── 5. Leave Trends (monthly chart) ──────────────────────────────────────────

@router.get("/leave/trends")
def leave_trends(
    months      : int      = Query(6, ge=1, le=24),
    current_user: Employee = Depends(require_role(2)),
    db          : Session  = Depends(get_db),
):
    """Monthly leave request counts split by status (chart data)."""
    today   = date.today()
    results = []

    for i in range(months - 1, -1, -1):
        year  = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year  -= 1

        _, last = monthrange(year, month)
        start   = date(year, month, 1)
        end     = date(year, month, last)

        leaves = db.query(LeaveRequest).filter(
            LeaveRequest.start_date >= start,
            LeaveRequest.start_date <= end,
        ).all()

        by_status = {}
        for lr in leaves:
            s = str(lr.status.value) if hasattr(lr.status, "value") else str(lr.status)
            by_status[s] = by_status.get(s, 0) + 1

        results.append({
            "month":    f"{year}-{month:02d}",
            "label":    date(year, month, 1).strftime("%b %Y"),
            "total":    len(leaves),
            "approved": by_status.get("approved", 0),
            "rejected": by_status.get("rejected", 0),
            "pending":  by_status.get("pending", 0) + by_status.get("escalated", 0),
        })

    return {"months": months, "data": results}


# ── 6. Performance Summary ────────────────────────────────────────────────────

@router.get("/performance/summary")
def performance_summary(
    period      : Optional[str] = Query(None, description="YYYY-MM, defaults to last 3 months"),
    department_id: Optional[int] = Query(None),
    current_user: Employee      = Depends(require_role(2)),
    db          : Session       = Depends(get_db),
):
    """Rating distribution, average scores, top and low performers."""
    today = date.today()
    if period:
        start, end = _parse_period(period)
    else:
        # Last 3 months
        end   = today
        start = today - timedelta(days=90)

    q = db.query(PerformanceReview).filter(
        PerformanceReview.period_end >= start,
        PerformanceReview.period_end <= end,
        PerformanceReview.overall_score != None,
    )
    if department_id:
        q = q.join(Employee).filter(Employee.department_id == department_id)

    reviews = q.all()

    if not reviews:
        return {"period_start": str(start), "period_end": str(end),
                "total_reviews": 0, "message": "No performance reviews found."}

    # Rating distribution
    distribution = {"Excellent": 0, "Good": 0, "Average": 0,
                    "Needs Improvement": 0, "Critical": 0}
    scores = []
    for r in reviews:
        band = _rating_band(r.overall_score)
        distribution[band] = distribution.get(band, 0) + 1
        scores.append(r.overall_score)

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    # Top 5 performers
    top5 = sorted(reviews, key=lambda r: r.overall_score, reverse=True)[:5]

    # Bottom 5 (potential PIP candidates)
    bottom5 = sorted(reviews, key=lambda r: r.overall_score)[:5]

    def _emp_name(emp_id):
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        return emp.full_name if emp else f"EMP{emp_id}"

    return {
        "period_start":   str(start),
        "period_end":     str(end),
        "total_reviews":  len(reviews),
        "average_score":  avg_score,
        "distribution":   distribution,
        "promotion_eligible": sum(1 for r in reviews if r.is_promotion_eligible),
        "pip_required":      sum(1 for r in reviews if r.requires_pip),
        "top_performers": [
            {
                "employee_id":   r.employee_id,
                "name":          _emp_name(r.employee_id),
                "overall_score": r.overall_score,
                "rating":        r.rating,
                "period_type":   r.period_type,
            }
            for r in top5
        ],
        "needs_attention": [
            {
                "employee_id":   r.employee_id,
                "name":          _emp_name(r.employee_id),
                "overall_score": r.overall_score,
                "rating":        r.rating,
                "requires_pip":  r.requires_pip,
            }
            for r in bottom5
        ],
    }


# ── 7. Headcount Analytics ────────────────────────────────────────────────────

@router.get("/headcount")
def headcount(
    current_user: Employee = Depends(require_role(2)),
    db          : Session  = Depends(get_db),
):
    """Employee headcount by status, department, gender, employment type."""
    today = date.today()

    total   = db.query(func.count(Employee.id)).scalar() or 0
    active  = db.query(func.count(Employee.id)).filter(Employee.is_active == True).scalar() or 0
    inactive= total - active

    # By status
    statuses = db.query(Employee.status, func.count(Employee.id)).filter(
        Employee.is_active == True
    ).group_by(Employee.status).all()
    by_status = {s: c for s, c in statuses}

    # By department
    depts = db.query(
        Department.name,
        func.count(Employee.id)
    ).join(Employee, Employee.department_id == Department.id, isouter=True).filter(
        Employee.is_active == True
    ).group_by(Department.name).all()
    by_department = {name: count for name, count in depts}

    # By gender
    genders = db.query(Employee.gender, func.count(Employee.id)).filter(
        Employee.is_active == True
    ).group_by(Employee.gender).all()
    by_gender = {str(g) if g else "Not specified": c for g, c in genders}

    # New hires this month
    start_m, end_m = _parse_period(None)
    new_this_month = db.query(func.count(Employee.id)).filter(
        Employee.hire_date >= start_m,
        Employee.hire_date <= end_m,
    ).scalar() or 0

    # New hires this year
    new_this_year = db.query(func.count(Employee.id)).filter(
        Employee.hire_date >= date(today.year, 1, 1),
        Employee.hire_date <= today,
    ).scalar() or 0

    # On probation
    on_probation = db.query(func.count(Employee.id)).filter(
        Employee.status == "probation",
        Employee.is_active == True,
    ).scalar() or 0

    return {
        "total_employees":  total,
        "active":           active,
        "inactive":         inactive,
        "on_probation":     on_probation,
        "by_status":        by_status,
        "by_department":    by_department,
        "by_gender":        by_gender,
        "new_hires": {
            "this_month": new_this_month,
            "this_year":  new_this_year,
        },
    }


# ── 8. Department Deep Dive ───────────────────────────────────────────────────

@router.get("/department/{department_id}")
def department_report(
    department_id: int,
    period       : Optional[str] = Query(None),
    current_user : Employee      = Depends(require_role(2)),
    db           : Session       = Depends(get_db),
):
    """Full analytics for a single department: headcount, attendance, leave, performance."""
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    start, end = _parse_period(period)
    wdays      = _working_days(start, end)

    employees = db.query(Employee).filter(
        Employee.department_id == department_id,
        Employee.is_active     == True,
    ).all()
    emp_ids = [e.id for e in employees]

    # Attendance
    att_records = db.query(Attendance).filter(
        Attendance.employee_id.in_(emp_ids),
        Attendance.work_date   >= start,
        Attendance.work_date   <= end,
    ).all() if emp_ids else []

    present = sum(1 for r in att_records if not r.is_absent)
    absent  = sum(1 for r in att_records if r.is_absent)
    late    = sum(1 for r in att_records if r.is_late)
    ot      = sum(r.overtime_hours or 0.0 for r in att_records)
    att_rate = round(present / max(1, len(employees) * wdays) * 100, 1) if wdays > 0 else 0.0

    # Leave
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id.in_(emp_ids),
        LeaveRequest.start_date >= start,
        LeaveRequest.start_date <= end,
    ).all() if emp_ids else []
    leave_days = sum(lr.total_days for lr in leaves if str(getattr(lr.status, 'value', lr.status)) == "approved")

    # Performance (latest review per employee)
    perf_scores = []
    for eid in emp_ids:
        rev = db.query(PerformanceReview).filter(
            PerformanceReview.employee_id == eid,
            PerformanceReview.overall_score != None,
        ).order_by(PerformanceReview.period_end.desc()).first()
        if rev:
            perf_scores.append(rev.overall_score)

    avg_perf = round(sum(perf_scores) / len(perf_scores), 1) if perf_scores else None

    return {
        "department": {"id": dept.id, "name": dept.name, "code": dept.code},
        "period":     period or date.today().strftime("%Y-%m"),
        "headcount":  len(employees),
        "attendance": {
            "working_days":    wdays,
            "attendance_rate": att_rate,
            "present_days":    present,
            "absent_days":     absent,
            "late_days":       late,
            "overtime_hours":  round(ot, 2),
        },
        "leave": {
            "total_requests":  len(leaves),
            "approved_days":   leave_days,
        },
        "performance": {
            "avg_score":       avg_perf,
            "rating":          _rating_band(avg_perf) if avg_perf else None,
            "reviews_count":   len(perf_scores),
        },
    }


# ── 9. Generate Full AI Report ────────────────────────────────────────────────

@router.post("/generate", status_code=201)
def generate_report(
    body        : GenerateReportRequest,
    current_user: Employee = Depends(require_role(3)),
    db          : Session  = Depends(get_db),
):
    """
    Generate a full HR report with AI narrative and save to DB.
    HR Manager+ only.

    Report types: monthly_summary | attendance | leave | performance | department
    """
    period     = body.period or date.today().strftime("%Y-%m")
    start, end = _parse_period(period)
    rtype      = body.report_type
    title      = f"HR {rtype.replace('_', ' ').title()} Report — {period}"

    # ── Gather data based on report type ─────────────────────────────────────
    content: dict = {"period": period, "start": str(start), "end": str(end)}

    if rtype in ("monthly_summary", "attendance"):
        wdays = _working_days(start, end)
        total_active = db.query(func.count(Employee.id)).filter(
            Employee.is_active == True).scalar() or 0

        att_records = db.query(Attendance).filter(
            Attendance.work_date >= start,
            Attendance.work_date <= end,
        ).all()
        present = sum(1 for r in att_records if not r.is_absent)
        absent  = sum(1 for r in att_records if r.is_absent)
        late    = sum(1 for r in att_records if r.is_late)
        ot      = sum(r.overtime_hours or 0.0 for r in att_records)
        att_rate = round(present / max(1, total_active * wdays) * 100, 1) if wdays > 0 else 0.0
        content["headcount"]       = total_active
        content["working_days"]    = wdays
        content["attendance_rate"] = att_rate
        content["present_count"]   = present
        content["absent_count"]    = absent
        content["late_count"]      = late
        content["overtime_hours"]  = round(ot, 2)
        content["absenteeism_rate"]= round(100 - att_rate, 1)

    if rtype in ("monthly_summary", "leave"):
        year = start.year
        bals = db.query(LeaveBalance).filter(LeaveBalance.year == year).all()
        by_type: dict = {}
        for b in bals:
            code = b.leave_type.code if b.leave_type else "UNK"
            if code not in by_type:
                by_type[code] = {"total": 0.0, "used": 0.0}
            by_type[code]["total"] += float(b.total_days)
            by_type[code]["used"]  += float(b.used_days)
        for v in by_type.values():
            t = v["total"]
            v["utilisation_pct"] = round(v["used"] / t * 100, 1) if t > 0 else 0.0
        content["leave_utilisation"] = by_type

        pending_count = db.query(func.count(LeaveRequest.id)).filter(
            LeaveRequest.status.in_(["pending", "escalated"])
        ).scalar() or 0
        content["pending_leaves"] = pending_count

    if rtype in ("monthly_summary", "performance"):
        reviews = db.query(PerformanceReview).filter(
            PerformanceReview.period_start >= start,
            PerformanceReview.period_end   <= end,
            PerformanceReview.overall_score != None,
        ).all()
        if reviews:
            scores = [r.overall_score for r in reviews]
            avg = round(sum(scores) / len(scores), 1)
            dist = {"Excellent": 0, "Good": 0, "Average": 0,
                    "Needs Improvement": 0, "Critical": 0}
            for s in scores:
                dist[_rating_band(s)] += 1
            content["performance_avg"]      = avg
            content["performance_dist"]     = dist
            content["promotion_eligible"]   = sum(1 for r in reviews if r.is_promotion_eligible)
            content["pip_required"]         = sum(1 for r in reviews if r.requires_pip)

    # ── KPIs for narrative ────────────────────────────────────────────────────
    kpis = {
        "attendance_rate":  content.get("attendance_rate"),
        "absenteeism_rate": content.get("absenteeism_rate"),
        "overtime_hours":   content.get("overtime_hours"),
        "pending_leaves":   content.get("pending_leaves"),
        "performance_avg":  content.get("performance_avg"),
    }

    # ── Detect trends ─────────────────────────────────────────────────────────
    trends = []
    if kpis.get("attendance_rate") and kpis["attendance_rate"] < 85:
        trends.append(f"Attendance below 85% threshold: {kpis['attendance_rate']}%")
    if kpis.get("overtime_hours") and kpis["overtime_hours"] > 200:
        trends.append(f"High overtime hours: {kpis['overtime_hours']:.0f}h — review workload")
    if kpis.get("pending_leaves") and kpis["pending_leaves"] > 10:
        trends.append(f"{kpis['pending_leaves']} leave requests awaiting approval")
    if not trends:
        trends.append("All key metrics are within normal ranges.")
    content["trends"] = trends

    # ── AI Narrative ──────────────────────────────────────────────────────────
    narrative = _generate_narrative(period, rtype, kpis, trends)

    # ── Save to DB ────────────────────────────────────────────────────────────
    report = HRReport(
        report_type  = rtype,
        period       = period,
        title        = title,
        content      = content,
        narrative    = narrative,
        generated_by = current_user.full_name or current_user.employee_number,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id":          report.id,
        "title":       title,
        "report_type": rtype,
        "period":      period,
        "kpis":        kpis,
        "trends":      trends,
        "narrative":   narrative,
        "content":     content,
        "generated_at": str(report.created_at),
        "generated_by": report.generated_by,
    }


def _generate_narrative(period: str, rtype: str, kpis: dict, trends: list) -> str:
    """Call OpenAI for a 4-sentence executive summary. Falls back to template."""
    if not settings.OPENAI_API_KEY:
        att = kpis.get("attendance_rate", "N/A")
        ot  = kpis.get("overtime_hours", 0)
        return (
            f"HR {rtype.replace('_', ' ').title()} Report for {period}. "
            f"Attendance rate: {att}%. Overtime: {ot:.0f}h. "
            f"Key observations: {'; '.join(trends)}"
        )
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.3,
                         api_key=settings.OPENAI_API_KEY)
        response = llm.invoke([
            SystemMessage(content=(
                "You are an HR analyst writing executive reports for a company in Sri Lanka. "
                "Write a concise 4-sentence narrative summarising the HR metrics. "
                "Highlight any concerns and suggest one actionable recommendation."
            )),
            HumanMessage(content=(
                f"Period: {period}\n"
                f"Report Type: {rtype}\n"
                f"Key Metrics: {json.dumps(kpis)}\n"
                f"Observed Trends: {trends}"
            )),
        ])
        return response.content
    except Exception as e:
        return (
            f"HR report for {period}. "
            f"Attendance: {kpis.get('attendance_rate', 'N/A')}%. "
            f"Key trends: {'; '.join(trends)}. "
            f"(AI narrative unavailable: {type(e).__name__})"
        )


# ── 10. Report History ────────────────────────────────────────────────────────

@router.get("/history", response_model=List[ReportSummary])
def report_history(
    report_type : Optional[str] = Query(None),
    limit       : int           = Query(20, ge=1, le=100),
    current_user: Employee      = Depends(require_role(2)),
    db          : Session       = Depends(get_db),
):
    """List all saved reports, newest first."""
    q = db.query(HRReport)
    if report_type:
        q = q.filter(HRReport.report_type == report_type)
    reports = q.order_by(HRReport.id.desc()).limit(limit).all()
    return [
        ReportSummary(
            id          = r.id,
            report_type = r.report_type,
            period      = r.period,
            title       = r.title,
            created_at  = r.created_at,
        )
        for r in reports
    ]


@router.get("/history/{report_id}", response_model=ReportOut)
def get_report(
    report_id   : int,
    current_user: Employee = Depends(require_role(2)),
    db          : Session  = Depends(get_db),
):
    """Get a previously generated report by ID."""
    report = db.query(HRReport).filter(HRReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report
