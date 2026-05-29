"""
Dashboard Stats API

GET /api/dashboard/employee    ← Stats for the logged-in employee
GET /api/dashboard/hr          ← HR-level overview (HR Admin+)
GET /api/dashboard/management  ← Company-level overview (Management+)
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.core.database import get_db
from app.core.security import get_current_employee, require_role
from app.core.cache import cache_get, cache_set
from app.models.employee import Employee, EmployeeStatus
from app.models.leave import LeaveRequest, LeaveBalance
from app.models.attendance import Attendance
from app.models.recruitment import JobPosting
from app.models.performance import PerformanceReview

router = APIRouter()


@router.get("/employee")
def employee_dashboard(
    current: Employee = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    cache_key = f"dash:emp:{current.id}:{date.today()}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Leave balance — sum remaining days across all leave types
    leave_balance = db.query(func.coalesce(func.sum(LeaveBalance.remaining_days), 0)).filter(
        LeaveBalance.employee_id == current.id
    ).scalar() or 0

    # Attendance rate this month
    today = date.today()
    month_start = today.replace(day=1)
    total_days = (today - month_start).days + 1
    present_days = db.query(Attendance).filter(
        Attendance.employee_id == current.id,
        Attendance.work_date >= month_start,
        Attendance.work_date <= today,
        Attendance.is_absent == False,
    ).count()
    attendance_rate = round((present_days / total_days) * 100) if total_days > 0 else 0

    # Pending leave requests
    pending_requests = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == current.id,
        LeaveRequest.status == "pending",
    ).count()

    # Next payday (assume 25th of each month)
    payday = today.replace(day=25)
    if today.day > 25:
        # Next month
        if today.month == 12:
            payday = date(today.year + 1, 1, 25)
        else:
            payday = date(today.year, today.month + 1, 25)
    next_payday = payday.isoformat()

    result = {
        "leave_balance": float(leave_balance),
        "attendance_rate": attendance_rate,
        "pending_requests": pending_requests,
        "next_payday": next_payday,
    }
    cache_set(cache_key, result, ttl=60)
    return result


@router.get("/hr")
def hr_dashboard(
    current: Employee = Depends(require_role(2)),
    db: Session = Depends(get_db),
):
    cache_key = f"dash:hr:{date.today()}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Total active employees
    total_employees = db.query(Employee).filter(
        Employee.is_active == True,
        Employee.status == EmployeeStatus.ACTIVE,
    ).count()

    # Today present
    today = date.today()
    today_present = db.query(Attendance).filter(
        Attendance.work_date == today,
        Attendance.is_absent == False,
    ).count()

    # Pending leave requests
    pending_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.status == "pending"
    ).count()

    # Open job positions
    open_positions = db.query(JobPosting).filter(
        JobPosting.is_active == True
    ).count()

    result = {
        "total_employees": total_employees,
        "today_present": today_present,
        "pending_leaves": pending_leaves,
        "open_positions": open_positions,
    }
    cache_set(cache_key, result, ttl=30)
    return result


@router.get("/management")
def management_dashboard(
    current: Employee = Depends(require_role(3)),
    db: Session = Depends(get_db),
):
    cache_key = f"dash:mgmt:{date.today()}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Headcount
    headcount = db.query(Employee).filter(
        Employee.is_active == True,
        Employee.status == EmployeeStatus.ACTIVE,
    ).count()

    # Attendance rate last 30 days — single query with conditional count
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    att = db.query(
        func.count().label("total"),
        func.count(case((Attendance.is_absent == False, 1))).label("present"),
    ).filter(
        Attendance.work_date >= thirty_days_ago,
        Attendance.work_date <= today,
    ).one()
    attendance_rate = round((att.present / att.total) * 100) if att.total > 0 else 0

    # Leave utilization — single aggregation query
    bal = db.query(
        func.coalesce(func.sum(LeaveBalance.total_days), 0).label("total"),
        func.coalesce(func.sum(LeaveBalance.remaining_days), 0).label("remaining"),
    ).one()
    total_entitled  = float(bal.total)
    total_remaining = float(bal.remaining)
    used = total_entitled - total_remaining
    leave_utilization = round((used / float(total_entitled)) * 100) if total_entitled > 0 else 0

    # Average performance score
    avg_score = db.query(func.avg(PerformanceReview.overall_score)).scalar()
    avg_performance_score = round(float(avg_score)) if avg_score else 0

    result = {
        "headcount": headcount,
        "attendance_rate": attendance_rate,
        "leave_utilization": leave_utilization,
        "avg_performance_score": avg_performance_score,
    }
    cache_set(cache_key, result, ttl=30)
    return result
