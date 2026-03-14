"""
Performance Tracking API

Endpoints:
  POST /api/performance/generate/{employee_id}     ← AI generates performance review (HR+)
  GET  /api/performance/my-reviews                 ← Employee's own review history
  GET  /api/performance/my-summary                 ← Employee's latest scores (quick view)
  GET  /api/performance/review/{review_id}         ← Get one specific review
  GET  /api/performance/employee/{employee_id}     ← All reviews for an employee (HR+)
  GET  /api/performance/all                        ← All reviews with filters (HR+)
  GET  /api/performance/team                       ← Team overview (HR Manager+)
  PATCH /api/performance/review/{id}/acknowledge   ← Employee acknowledges review
  PATCH /api/performance/review/{id}/comments      ← Manager adds comments
  POST  /api/performance/review/{id}/dispute       ← Employee disputes result
  PATCH /api/performance/review/{id}/resolve       ← HR resolves a dispute (HR Manager+)

Scoring Formula (objective — no bias):
  attendance_score  = (present_days / working_days) * 100            weight: 35%
  punctuality_score = 100 - (late_days / present_days * 100)         weight: 30%
  leave_score       = 100 - (leave_days_taken / total_leave * 100)   weight: 15%
  overtime_score    = min(100, overtime_hours * 2.5)                  weight: 20%
  overall_score     = weighted average of above

Rating bands:
  90+  → Excellent
  75+  → Good
  60+  → Average
  40+  → Needs Improvement
  <40  → Critical (triggers PIP)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Optional
from calendar import monthrange

from app.core.database import get_db
from app.core.security import get_current_employee, require_role

logger = logging.getLogger(__name__)
from app.schemas.performance import (
    GenerateReviewRequest,
    ManagerCommentsRequest,
    DisputeRequest,
    ResolveDisputeRequest,
)

router = APIRouter()


# ── Scoring constants ──────────────────────────────────────────────────────────
W_ATTENDANCE  = 0.35
W_PUNCTUALITY = 0.30
W_LEAVE       = 0.15
W_OVERTIME    = 0.20
COMPANY_AVG   = 78.5   # baseline benchmark


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rating_label(score: float) -> str:
    if score >= 90: return "Excellent"
    if score >= 75: return "Good"
    if score >= 60: return "Average"
    if score >= 40: return "Needs Improvement"
    return "Critical"


def _compute_scores(db: Session, employee_id: int, period_start: date, period_end: date) -> dict:
    """
    Calculate all performance scores from raw attendance + leave data.
    Fully objective — reads from database, no human input.
    """
    from app.models.attendance import Attendance
    from app.models.leave import LeaveRequest, LeaveBalance, LeaveStatus

    # ── Attendance data ────────────────────────────────────────────────────────
    records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.work_date   >= period_start,
        Attendance.work_date   <= period_end,
    ).all()

    # Working days in period (exclude Sundays)
    working_days = sum(
        1 for i in range((period_end - period_start).days + 1)
        if (period_start + timedelta(days=i)).weekday() != 6
    )

    present_days  = sum(1 for r in records if r.clock_in and not r.is_absent)
    late_days     = sum(1 for r in records if r.is_late)
    overtime_hrs  = round(sum(r.overtime_hours or 0 for r in records), 2)
    avg_work_hrs  = round(
        sum(r.work_hours or 0 for r in records if r.work_hours) /
        max(present_days, 1), 2
    )

    # ── Leave data ────────────────────────────────────────────────────────────
    leave_days_taken = sum(
        (lr.days_requested or lr.total_days or 0)
        for lr in db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status      == LeaveStatus.APPROVED,
            LeaveRequest.start_date  >= period_start,
            LeaveRequest.end_date    <= period_end,
        ).all()
    )

    # Use 30 days as annual entitlement for scoring (AL + SL + CL combined)
    annual_leave_entitlement = 30.0
    period_fraction          = (period_end - period_start).days / 365
    period_leave_entitlement = annual_leave_entitlement * period_fraction

    # ── Score calculation ─────────────────────────────────────────────────────
    att_score  = round(min(100.0, (present_days / max(working_days, 1)) * 100), 1)
    punc_score = round(max(0.0, 100.0 - (late_days / max(present_days, 1)) * 100), 1)
    leave_score = round(max(0.0, 100.0 - (leave_days_taken / max(period_leave_entitlement, 1)) * 100), 1)
    ot_score   = round(min(100.0, overtime_hrs * 2.5), 1)

    overall = round(
        att_score  * W_ATTENDANCE +
        punc_score * W_PUNCTUALITY +
        leave_score * W_LEAVE +
        ot_score   * W_OVERTIME,
        1
    )

    flags = []
    if att_score < 85:           flags.append(f"Low attendance: {att_score}%")
    if late_days > 3:            flags.append(f"Frequent late arrivals: {late_days} times")
    if leave_days_taken > period_leave_entitlement * 0.8:
        flags.append(f"High leave usage: {leave_days_taken} days in period")

    return {
        "working_days":       working_days,
        "present_days":       present_days,
        "absent_days":        max(0, working_days - present_days),
        "late_days":          late_days,
        "overtime_hours":     overtime_hrs,
        "avg_work_hours":     avg_work_hrs,
        "leave_days_taken":   round(leave_days_taken, 1),
        "attendance_score":   att_score,
        "punctuality_score":  punc_score,
        "leave_score":        leave_score,
        "overtime_score":     ot_score,
        "overall_score":      overall,
        "rating":             _rating_label(overall),
        "vs_company_avg":     round(overall - COMPANY_AVG, 1),
        "is_promotion_eligible": overall >= 90,
        "requires_pip":       overall < 40,
        "flags":              flags,
    }


def _get_period_dates(period_type: str, custom_start=None, custom_end=None):
    """Derive period start/end dates from period_type if not provided."""
    today = date.today()
    if custom_start and custom_end:
        return date.fromisoformat(custom_start), date.fromisoformat(custom_end)

    if period_type == "monthly":
        start = date(today.year, today.month, 1)
        _, last = monthrange(today.year, today.month)
        end = date(today.year, today.month, last)
    elif period_type == "quarterly":
        q     = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1)
        end_m = min((q + 1) * 3, 12)
        _, last = monthrange(today.year, end_m)
        end = date(today.year, end_m, last)
    elif period_type == "annual":
        start = date(today.year, 1, 1)
        end   = date(today.year, 12, 31)
    else:  # probation — last 6 months
        start = today - timedelta(days=180)
        end   = today
    return start, end


def _generate_ai_narrative(employee_name: str, dept: str, scores: dict) -> str:
    """Generate a 3-sentence narrative using OpenAI. Falls back to template."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        from app.core.config import settings
        llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.4, api_key=settings.OPENAI_API_KEY)
        prompt = (
            f"Employee: {employee_name}, Department: {dept}\n"
            f"Attendance: {scores['attendance_score']}% | Punctuality: {scores['punctuality_score']}% | "
            f"Leave usage: {scores['leave_days_taken']} days | Overtime: {scores['overtime_hours']} hrs\n"
            f"Overall Rating: {scores['rating']} ({scores['overall_score']}/100)"
        )
        response = llm.invoke([
            SystemMessage(content=(
                "Write a professional 3-sentence performance evaluation. "
                "Reference specific data. Be constructive and fair. "
                "Do NOT mention raw scores — use qualitative language."
            )),
            HumanMessage(content=prompt),
        ])
        return response.content
    except Exception:
        r = scores["rating"]
        a = scores["attendance_score"]
        p = scores["punctuality_score"]
        return (
            f"{employee_name} has demonstrated {r.lower()} performance this period. "
            f"{'Attendance has been consistent and reliable.' if a >= 85 else 'Attendance requires improvement.'} "
            f"{'Punctuality standards have been maintained.' if p >= 85 else 'Punctuality has been an area of concern and should be addressed.'}"
        )


def review_to_dict(review) -> dict:
    return {
        "id":                   review.id,
        "employee_id":          review.employee_id,
        "period_type":          review.period_type,
        "period_start":         str(review.period_start),
        "period_end":           str(review.period_end),
        "attendance_score":     review.attendance_score,
        "punctuality_score":    review.punctuality_score,
        "overtime_score":       review.overtime_score,
        "overall_score":        review.overall_score,
        "rating":               review.rating,
        "strengths":            review.strengths,
        "areas_to_improve":     review.areas_to_improve,
        "goals_next_period":    review.goals_next_period,
        "manager_comments":     review.manager_comments,
        "ai_summary":           review.ai_summary,
        "status":               review.status,
        "is_promotion_eligible": review.is_promotion_eligible,
        "requires_pip":         review.requires_pip,
        "employee_acknowledged": review.employee_acknowledged,
        "created_at":           str(review.created_at),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. GENERATE AI PERFORMANCE REVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/generate/{employee_id}",
    status_code=status.HTTP_201_CREATED,
    summary="AI generates a performance review for an employee — HR Staff+",
)
def generate_review(
    employee_id:  int,
    body:         GenerateReviewRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    """
    Triggers the AI to generate a full performance review for an employee.

    Steps performed:
      1. Pulls attendance data for the period
      2. Calculates objective scores (attendance, punctuality, leave usage, overtime)
      3. Generates AI narrative using OpenAI
      4. Saves the review to the database
      5. Flags for PIP if overall score < 40

    period_type: "monthly" | "quarterly" | "annual" | "probation"
    """
    from app.models.performance import PerformanceReview, PerformanceMetric, ReviewStatus
    from app.models.employee import Employee

    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee #{employee_id} not found.")

    period_start, period_end = _get_period_dates(
        body.period_type, body.period_start, body.period_end
    )

    # Prevent duplicate reviews for the same employee + period
    existing = db.query(PerformanceReview).filter(
        PerformanceReview.employee_id  == employee_id,
        PerformanceReview.period_start == period_start,
        PerformanceReview.period_end   == period_end,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A {body.period_type} review already exists for {emp.full_name} "
                f"({period_start} – {period_end}). Review ID: {existing.id}"
            ),
        )

    # ── Calculate scores ──────────────────────────────────────────────────────
    scores    = _compute_scores(db, employee_id, period_start, period_end)
    dept_name = emp.department.name if emp.department else "N/A"
    narrative = _generate_ai_narrative(emp.full_name, dept_name, scores)

    # ── Save review ───────────────────────────────────────────────────────────
    review = PerformanceReview(
        employee_id           = employee_id,
        reviewer_id           = current_user.id,
        period_type           = body.period_type,
        period_start          = period_start,
        period_end            = period_end,
        attendance_score      = scores["attendance_score"],
        punctuality_score     = scores["punctuality_score"],
        overtime_score        = scores["overtime_score"],
        overall_score         = scores["overall_score"],
        rating                = scores["rating"],
        ai_summary            = narrative,
        status                = ReviewStatus.COMPLETED,
        is_promotion_eligible = scores["is_promotion_eligible"],
        requires_pip          = scores["requires_pip"],
        employee_acknowledged = False,
    )
    db.add(review)
    db.flush()   # get review.id before adding metrics

    # ── Save individual metrics ───────────────────────────────────────────────
    metrics_data = [
        ("Days Present",    scores["present_days"],     scores["attendance_score"],  W_ATTENDANCE),
        ("Late Arrivals",   scores["late_days"],         scores["punctuality_score"], W_PUNCTUALITY),
        ("Leave Days Used", scores["leave_days_taken"],  scores["leave_score"],       W_LEAVE),
        ("Overtime Hours",  scores["overtime_hours"],    scores["overtime_score"],    W_OVERTIME),
    ]
    for name, value, score, weight in metrics_data:
        db.add(PerformanceMetric(
            review_id   = review.id,
            metric_name = name,
            value       = value,
            score       = score,
            weight      = weight,
        ))

    db.commit()
    db.refresh(review)

    # ── Send notification to employee ─────────────────────────────────────────
    try:
        from app.services.notification_service import notify, notify_hr_managers
        notify(
            db, employee_id,
            ntype      = "performance_review",
            title      = f"Performance Review Ready — {scores['rating']}",
            message    = (
                f"Your {body.period_type} performance review is complete. "
                f"Overall score: {scores['overall_score']}/100 ({scores['rating']}). "
                f"Please acknowledge your review in the portal."
            ),
            action_url          = f"/performance/reviews/{review.id}",
            related_entity_type = "performance_review",
            related_entity_id   = review.id,
            priority            = "high" if scores["requires_pip"] else "normal",
        )
    except Exception as e:
        logger.warning("Failed to send performance review notification to employee %s: %s", employee_id, e)

    # ── Flag for PIP via HR notification ─────────────────────────────────────
    if scores["requires_pip"]:
        try:
            from app.services.notification_service import notify_hr_managers
            notify_hr_managers(
                db,
                ntype   = "pip_required",
                title   = f"PIP Required — {emp.full_name}",
                message = (
                    f"{emp.full_name} scored {scores['overall_score']}/100 "
                    f"({scores['rating']}) in their {body.period_type} review. "
                    f"A Performance Improvement Plan (PIP) is recommended."
                ),
                action_url          = f"/performance/reviews/{review.id}",
                related_entity_type = "performance_review",
                related_entity_id   = review.id,
            )
        except Exception as e:
            logger.warning("Failed to send PIP notification to HR managers for employee %s: %s", employee_id, e)

    return {
        "message":     f"Performance review generated for {emp.full_name}.",
        "review_id":   review.id,
        "employee":    emp.full_name,
        "period":      f"{period_start} → {period_end}",
        "scores": {
            "attendance":  scores["attendance_score"],
            "punctuality": scores["punctuality_score"],
            "leave_usage": scores["leave_score"],
            "overtime":    scores["overtime_score"],
            "overall":     scores["overall_score"],
        },
        "rating":             scores["rating"],
        "vs_company_avg":     scores["vs_company_avg"],
        "is_promotion_eligible": scores["is_promotion_eligible"],
        "requires_pip":       scores["requires_pip"],
        "flags":              scores["flags"],
        "ai_summary":         narrative,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. MY REVIEWS (employee's own)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my-reviews", summary="My performance review history")
def my_reviews(
    year:         Optional[int] = Query(None),
    db:           Session       = Depends(get_db),
    current_user                = Depends(get_current_employee),
):
    from app.models.performance import PerformanceReview

    q = db.query(PerformanceReview).filter(
        PerformanceReview.employee_id == current_user.id
    )
    if year:
        q = q.filter(PerformanceReview.period_start >= date(year, 1, 1))

    reviews = q.order_by(PerformanceReview.period_start.desc()).all()

    return {
        "employee": current_user.full_name,
        "total":    len(reviews),
        "reviews":  [review_to_dict(r) for r in reviews],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. MY SUMMARY (quick stats — no full review needed)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my-summary", summary="My live performance summary — calculated from attendance data")
def my_summary(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    """
    Returns live performance scores calculated from the current month's data.
    No review needs to have been generated — this reads raw attendance directly.
    """
    today        = date.today()
    period_start = date(today.year, today.month, 1)
    period_end   = today

    scores = _compute_scores(db, current_user.id, period_start, period_end)

    return {
        "employee":    current_user.full_name,
        "period":      f"{period_start} → {period_end}",
        "scores": {
            "attendance":       scores["attendance_score"],
            "punctuality":      scores["punctuality_score"],
            "leave_usage":      scores["leave_score"],
            "overtime":         scores["overtime_score"],
            "overall":          scores["overall_score"],
        },
        "rating":          scores["rating"],
        "vs_company_avg":  scores["vs_company_avg"],
        "raw_data": {
            "present_days":     scores["present_days"],
            "absent_days":      scores["absent_days"],
            "late_days":        scores["late_days"],
            "overtime_hours":   scores["overtime_hours"],
            "avg_work_hours":   scores["avg_work_hours"],
            "leave_days_taken": scores["leave_days_taken"],
        },
        "flags": scores["flags"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET ONE REVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/review/{review_id}", summary="Get a specific performance review")
def get_review(
    review_id:    int,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    from app.models.performance import PerformanceReview, PerformanceMetric

    review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review #{review_id} not found.")

    # Employees can only see their own reviews
    access_level = current_user.role.access_level if current_user.role else 1
    if access_level < 2 and review.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own reviews.")

    metrics = db.query(PerformanceMetric).filter(
        PerformanceMetric.review_id == review_id
    ).all()

    result           = review_to_dict(review)
    result["metrics"] = [
        {
            "metric":  m.metric_name,
            "value":   m.value,
            "score":   m.score,
            "weight":  f"{int(m.weight * 100)}%",
            "note":    m.note,
        }
        for m in metrics
    ]
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 5. ALL REVIEWS FOR ONE EMPLOYEE (HR+)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/employee/{employee_id}", summary="All reviews for a specific employee — HR Staff+")
def employee_reviews(
    employee_id:  int,
    year:         Optional[int] = Query(None),
    db:           Session       = Depends(get_db),
    current_user                = Depends(require_role(2)),
):
    from app.models.performance import PerformanceReview
    from app.models.employee import Employee

    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee #{employee_id} not found.")

    q = db.query(PerformanceReview).filter(PerformanceReview.employee_id == employee_id)
    if year:
        q = q.filter(PerformanceReview.period_start >= date(year, 1, 1))

    reviews = q.order_by(PerformanceReview.period_start.desc()).all()

    return {
        "employee":    emp.full_name,
        "employee_id": employee_id,
        "total":       len(reviews),
        "reviews":     [review_to_dict(r) for r in reviews],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. ALL REVIEWS WITH FILTERS (HR+)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/all", summary="All performance reviews with filters")
def all_reviews(
    department_id: Optional[int] = Query(None),
    period_type:   Optional[str] = Query(None),
    rating:        Optional[str] = Query(None),
    requires_pip:  Optional[bool] = Query(None),
    year:          Optional[int] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=100),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_employee),
):
    from app.models.performance import PerformanceReview
    from app.models.employee import Employee
    from app.models.department import Department
    from sqlalchemy.orm import joinedload

    q = db.query(PerformanceReview).join(
        Employee, PerformanceReview.employee_id == Employee.id
    ).options(
        joinedload(PerformanceReview.employee).joinedload(Employee.department)
    )

    # Regular employees can only see their own reviews
    user_level = current_user.role.access_level if current_user.role else 1
    if user_level < 2:
        q = q.filter(PerformanceReview.employee_id == current_user.id)

    if department_id:  q = q.filter(Employee.department_id == department_id)
    if period_type:    q = q.filter(PerformanceReview.period_type == period_type)
    if rating:         q = q.filter(PerformanceReview.rating == rating)
    if requires_pip is not None:
        q = q.filter(PerformanceReview.requires_pip == requires_pip)
    if year:
        q = q.filter(PerformanceReview.period_start >= date(year, 1, 1))

    total   = q.count()
    reviews = q.order_by(PerformanceReview.period_start.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # pip_count scoped to the same filters as the result set
    pip_q = db.query(PerformanceReview).join(
        Employee, PerformanceReview.employee_id == Employee.id
    ).filter(PerformanceReview.requires_pip == True)
    if department_id: pip_q = pip_q.filter(Employee.department_id == department_id)
    if year:          pip_q = pip_q.filter(PerformanceReview.period_start >= date(year, 1, 1))
    pip_count = pip_q.count()

    result = []
    for r in reviews:
        emp = r.employee   # already loaded via joinedload — no extra query
        row = review_to_dict(r)
        row["employee_name"]   = emp.full_name if emp else "Unknown"
        row["employee_number"] = emp.employee_number if emp else None
        row["department"]      = emp.department.name if emp and emp.department else None
        result.append(row)

    return {
        "total":       total,
        "page":        page,
        "page_size":   page_size,
        "pip_count":   pip_count,
        "reviews":     result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. TEAM OVERVIEW (HR Manager+)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/team", summary="Team performance overview — HR Manager+")
def team_overview(
    department_id: Optional[int] = Query(None),
    period_type:   str           = Query("quarterly"),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(require_role(3)),
):
    """
    Aggregated performance overview for HR dashboard.
    Shows average scores, rating distribution, top performers, and PIP candidates.
    """
    from app.models.performance import PerformanceReview
    from app.models.employee import Employee
    from sqlalchemy.orm import joinedload

    q = db.query(PerformanceReview).join(
        Employee, PerformanceReview.employee_id == Employee.id
    ).options(
        joinedload(PerformanceReview.employee)
    ).filter(PerformanceReview.period_type == period_type)

    if department_id:
        q = q.filter(Employee.department_id == department_id)

    reviews = q.order_by(PerformanceReview.period_start.desc()).all()

    if not reviews:
        return {"message": "No reviews found for the selected filters.", "total": 0}

    # Latest review per employee
    latest: dict = {}
    for r in reviews:
        if r.employee_id not in latest:
            latest[r.employee_id] = r

    latest_reviews = list(latest.values())
    scores = [r.overall_score for r in latest_reviews if r.overall_score]

    rating_dist = {}
    for r in latest_reviews:
        label = r.rating or "Unknown"
        rating_dist[label] = rating_dist.get(label, 0) + 1

    top_performers = sorted(
        [r for r in latest_reviews if r.overall_score],
        key=lambda x: x.overall_score, reverse=True
    )[:5]

    pip_candidates = [r for r in latest_reviews if r.requires_pip]

    def _emp_row(r):
        # employee already loaded via joinedload — no extra DB query
        emp = r.employee
        return {
            "employee_id":   r.employee_id,
            "employee_name": emp.full_name if emp else "Unknown",
            "score":         r.overall_score,
            "rating":        r.rating,
        }

    return {
        "period_type":       period_type,
        "total_reviewed":    len(latest_reviews),
        "avg_overall_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "company_benchmark": COMPANY_AVG,
        "rating_distribution": rating_dist,
        "top_performers":    [_emp_row(r) for r in top_performers],
        "pip_candidates":    [_emp_row(r) for r in pip_candidates],
        "promotion_eligible": sum(1 for r in latest_reviews if r.is_promotion_eligible),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. EMPLOYEE ACKNOWLEDGES REVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/review/{review_id}/acknowledge", summary="Employee acknowledges their review")
def acknowledge_review(
    review_id:    int,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    """Employee marks that they have read their performance review."""
    from app.models.performance import PerformanceReview

    review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review #{review_id} not found.")
    if review.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only acknowledge your own reviews.")
    if review.employee_acknowledged:
        return {"message": "Already acknowledged.", "review_id": review_id}

    review.employee_acknowledged = True
    db.commit()

    return {
        "message":   "Review acknowledged successfully.",
        "review_id": review_id,
        "acknowledged_by": current_user.full_name,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 9. MANAGER ADDS COMMENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/review/{review_id}/comments", summary="Manager adds comments to a review — HR Staff+")
def add_comments(
    review_id:    int,
    body:         ManagerCommentsRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    """
    HR Staff or Manager adds qualitative comments to an AI-generated review.
    Scores are NOT changed — only narrative fields are updated.
    """
    from app.models.performance import PerformanceReview

    review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review #{review_id} not found.")

    review.manager_comments  = body.manager_comments
    review.reviewer_id       = current_user.id
    if body.strengths:
        review.strengths = body.strengths
    if body.areas_to_improve:
        review.areas_to_improve = body.areas_to_improve
    if body.goals_next_period:
        review.goals_next_period = body.goals_next_period

    db.commit()

    # Notify employee that their review has been commented on
    try:
        from app.models.notification import Notification, NotificationChannel
        db.add(Notification(
            employee_id = review.employee_id,
            title       = "Your Performance Review Has Been Updated",
            message     = f"{current_user.full_name} has added comments to your performance review. Please review and acknowledge.",
            channel     = NotificationChannel.IN_APP,
            is_read     = False,
        ))
        db.commit()
    except Exception as e:
        logger.warning("Failed to notify employee of comment on review %s: %s", review_id, e)

    return {
        "message":    "Comments added to review successfully.",
        "review_id":  review_id,
        "updated_by": current_user.full_name,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 10. EMPLOYEE DISPUTES REVIEW
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/review/{review_id}/dispute", summary="Employee disputes a performance review result")
def dispute_review(
    review_id:    int,
    body:         DisputeRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    """
    Employee can dispute their performance review once.
    Flags the review as DISPUTED and notifies HR Managers.
    """
    from app.models.performance import PerformanceReview, ReviewStatus

    review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review #{review_id} not found.")
    if review.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only dispute your own reviews.")
    if review.status == ReviewStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="This review has already been disputed.")

    review.status    = ReviewStatus.DISPUTED
    review.hr_notes  = f"DISPUTE by {current_user.full_name}: {body.dispute_reason}"
    db.commit()

    # Notify HR Managers
    try:
        from app.models.employee import Employee
        from app.models.role import Role
        from app.models.notification import Notification, NotificationChannel

        managers = db.query(Employee).join(Role).filter(
            Role.access_level >= 3, Employee.is_active == True
        ).all()
        for mgr in managers:
            db.add(Notification(
                employee_id = mgr.id,
                title       = f"Review Disputed — {current_user.full_name}",
                message     = (
                    f"{current_user.full_name} has disputed their performance review "
                    f"(Review #{review_id}, Score: {review.overall_score}/100). "
                    f"Reason: {body.dispute_reason}"
                ),
                channel = NotificationChannel.IN_APP,
                is_read = False,
            ))
        db.commit()
    except Exception as e:
        logger.warning("Failed to notify HR managers of dispute on review %s: %s", review_id, e)

    return {
        "message":      "Dispute submitted successfully.",
        "review_id":    review_id,
        "status":       "disputed",
        "next_step":    "HR Manager will review your dispute and respond shortly.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 11. HR RESOLVES DISPUTE
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/review/{review_id}/resolve", summary="HR Manager resolves a disputed review — HR Manager+")
def resolve_dispute(
    review_id:    int,
    body:         ResolveDisputeRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(3)),
):
    """
    HR Manager reviews the dispute and resolves it.
    Optionally revises the overall score if the dispute has merit.
    """
    from app.models.performance import PerformanceReview, ReviewStatus

    review = db.query(PerformanceReview).filter(PerformanceReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail=f"Review #{review_id} not found.")
    if review.status != ReviewStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="This review is not in disputed status.")

    review.status   = ReviewStatus.COMPLETED
    resolution_note = f"RESOLVED by {current_user.full_name}: {body.resolution}"

    if body.revised_score is not None:
        old_score          = review.overall_score
        review.overall_score = round(body.revised_score, 1)
        review.rating        = _rating_label(review.overall_score)
        review.is_promotion_eligible = review.overall_score >= 90
        review.requires_pip          = review.overall_score < 40
        resolution_note += f" | Score revised: {old_score} → {review.overall_score}"

    review.hr_notes  = resolution_note
    review.reviewer_id = current_user.id
    db.commit()

    # Notify employee
    try:
        from app.models.notification import Notification, NotificationChannel
        db.add(Notification(
            employee_id = review.employee_id,
            title       = "Performance Dispute Resolved",
            message     = (
                f"Your performance review dispute (Review #{review_id}) has been resolved by "
                f"{current_user.full_name}. "
                + (f"Score revised to {review.overall_score}/100 ({review.rating})." if body.revised_score else "Original score maintained.")
            ),
            channel = NotificationChannel.IN_APP,
            is_read = False,
        ))
        db.commit()
    except Exception as e:
        logger.warning("Failed to notify employee of dispute resolution on review %s: %s", review_id, e)

    return {
        "message":       "Dispute resolved successfully.",
        "review_id":     review_id,
        "resolved_by":   current_user.full_name,
        "final_score":   review.overall_score,
        "final_rating":  review.rating,
        "score_revised": body.revised_score is not None,
    }
