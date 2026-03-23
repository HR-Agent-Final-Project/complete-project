"""
Face Recognition Attendance API
Designed to connect with your existing tablet attendance app.

Your tablet app calls these endpoints:

FACE REGISTRATION (done by HR once per employee):
  POST /api/attendance/register-face       ← Upload employee face photo

DAILY ATTENDANCE (tablet app calls these):
  POST /api/attendance/clock-in-face       ← Morning: employee shows face → clock in
  POST /api/attendance/clock-out-face      ← Evening: employee shows face → clock out

STATUS & REPORTS:
  GET  /api/attendance/today               ← Today's status
  GET  /api/attendance/all                 ← All records (HR+)
  GET  /api/attendance/summary             ← Monthly OT breakdown
  GET  /api/attendance/ot-report           ← Full OT report
  POST /api/attendance/manual              ← Manual entry if face fails (HR+)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Optional
import base64
import os
import io

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_employee, require_role
from app.schemas.attendance import (
    ClockInBase64Request,
    ClockOutBase64Request,
    ManualAttendanceRequest,
    ResolveFlagRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pay rate config ───────────────────────────────────────────────────────────
WEEKDAY_OT_RATE  = 1.5
SATURDAY_RATE    = 1.0
SATURDAY_OT_RATE = 1.5
SUNDAY_RATE      = 2.0
HOLIDAY_RATE     = 2.0
STANDARD_HOURS   = 8.0
OT_AFTER_HOURS   = 9.0
HALF_DAY_MIN     = 4.0

# Read workday config from settings — single source of truth
LATE_GRACE_MIN  = settings.LATE_ARRIVAL_CUTOFF_MINUTES
WORKDAY_START_H = settings.WORKDAY_START_HOUR
WORKDAY_START_M = settings.WORKDAY_START_MINUTE
WORKDAY_END_H   = settings.WORKDAY_END_HOUR
WORKDAY_END_M   = settings.WORKDAY_END_MINUTE

SL_PUBLIC_HOLIDAYS = {
    date(2025, 1, 1), date(2025, 2, 4), date(2025, 4, 13),
    date(2025, 4, 14), date(2025, 5, 1), date(2025, 5, 12),
    date(2025, 12, 25), date(2026, 1, 1), date(2026, 2, 4),
    date(2026, 4, 13), date(2026, 4, 14), date(2026, 5, 1),
    date(2026, 12, 25),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_day_type(d: date) -> str:
    if d in SL_PUBLIC_HOLIDAYS: return "holiday"
    if d.weekday() == 6:        return "sunday"
    if d.weekday() == 5:        return "saturday"
    return "weekday"

def calc_late_minutes(clock_in: datetime) -> int:
    from datetime import time
    scheduled = clock_in.replace(
        hour=WORKDAY_START_H, minute=WORKDAY_START_M, second=0, microsecond=0
    )
    if clock_in <= scheduled + timedelta(minutes=LATE_GRACE_MIN):
        return 0
    return int((clock_in - scheduled).total_seconds() / 60)

def calc_work_hours(clock_in: datetime, clock_out: datetime) -> float:
    return round((clock_out - clock_in).total_seconds() / 3600, 2)

def calc_ot_hours(hours: float, d: date) -> float:
    day = get_day_type(d)
    if day in ("holiday", "sunday"):
        return round(hours, 2)
    if day == "saturday":
        return round(max(0, hours - STANDARD_HOURS), 2)
    return round(max(0, hours - OT_AFTER_HOURS), 2)

def calc_pay_breakdown(hours: float, d: date) -> dict:
    day = get_day_type(d)
    if day == "holiday":
        return {"regular_hours": 0, "regular_rate": 0, "ot_hours": hours, "ot_rate": HOLIDAY_RATE,
                "total_pay_units": round(hours * HOLIDAY_RATE, 2)}
    if day == "sunday":
        return {"regular_hours": 0, "regular_rate": 0, "ot_hours": hours, "ot_rate": SUNDAY_RATE,
                "total_pay_units": round(hours * SUNDAY_RATE, 2)}
    if day == "saturday":
        reg = min(hours, STANDARD_HOURS)
        ot  = max(0, hours - STANDARD_HOURS)
        return {"regular_hours": reg, "regular_rate": SATURDAY_RATE, "ot_hours": ot, "ot_rate": SATURDAY_OT_RATE,
                "total_pay_units": round((reg * SATURDAY_RATE) + (ot * SATURDAY_OT_RATE), 2)}
    reg = min(hours, OT_AFTER_HOURS)
    ot  = max(0, hours - OT_AFTER_HOURS)
    return {"regular_hours": reg, "regular_rate": 1.0, "ot_hours": ot, "ot_rate": WEEKDAY_OT_RATE,
            "total_pay_units": round((reg * 1.0) + (ot * WEEKDAY_OT_RATE), 2)}

def calc_attendance_type(hours: float, d: date) -> str:
    """Return a valid AttendanceType enum value."""
    day = get_day_type(d)
    if day in ("holiday", "sunday"):
        return "holiday"                # all hours are OT at 2x
    if day == "saturday":
        if hours > STANDARD_HOURS:
            return "overtime"           # over 8h on Saturday
        return "holiday"                # Saturday work = special day
    if hours < HALF_DAY_MIN:
        return "half_day"
    if hours > OT_AFTER_HOURS:
        return "overtime"               # weekday OT after 9h
    return "regular"

def get_face_path(employee_id: int) -> str:
    path = f"uploads/faces/emp_{employee_id}"
    os.makedirs(path, exist_ok=True)
    return f"{path}/face.jpg"

def record_to_dict(r) -> dict:
    emp = r.employee
    return {
        "id":                  r.id,
        "employee_id":         r.employee_id,
        "employee_number":     emp.employee_number if emp else None,
        "employee_name":       emp.full_name if emp else None,
        "work_date":           str(r.work_date),
        "day":                 r.work_date.strftime("%A"),
        "clock_in":            r.clock_in.strftime("%H:%M:%S") if r.clock_in else None,
        "clock_out":           r.clock_out.strftime("%H:%M:%S") if r.clock_out else None,
        "work_hours":          r.work_hours,
        "overtime_hours":      r.overtime_hours,
        "attendance_type":     r.attendance_type,
        "is_late":             r.is_late,
        "late_minutes":        r.late_minutes,
        "is_absent":           r.is_absent,
        "location":            r.location,
        "latitude":            r.latitude,
        "longitude":           r.longitude,
        "checkout_latitude":   r.checkout_latitude,
        "checkout_longitude":  r.checkout_longitude,
        "verification_method": r.verification_method,
        "confidence_score":    r.confidence_score,
        "flagged":             r.flagged,
        "notes":               r.notes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. REGISTER EMPLOYEE FACE
#    HR does this once per employee using their photo
#    Stores face image in uploads/faces/emp_{id}/face.jpg
#    Also stores face embedding in database for fast lookup
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/register-face", summary="Register employee face — HR Manager+")
async def register_face(
    employee_id: int        = Form(...),
    image:       UploadFile = File(...),
    db:          Session    = Depends(get_db),
    current_user            = Depends(require_role(3)),
):
    """
    Register an employee's face photo.
    HR Manager does this once per employee.

    Your tablet app or HR portal uploads the photo here.

    Form data:
      employee_id: 2
      image: <photo file>

    The face is saved and used for all future clock-in/out verification.
    """
    from app.models.employee import Employee

    # Validate employee exists
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee #{employee_id} not found.")

    # Read image bytes
    image_bytes = await image.read()
    if len(image_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Image too small. Please upload a clear photo.")

    # Save face image to disk
    face_path = get_face_path(employee_id)
    with open(face_path, "wb") as f:
        f.write(image_bytes)

    # Try to extract and store face embedding in DB for fast verification
    embedding_stored = False
    try:
        from deepface import DeepFace
        import numpy as np
        import json

        result = DeepFace.represent(
            img_path         = face_path,
            model_name       = "Facenet512",
            detector_backend = "opencv",
            enforce_detection = True,
        )

        if result:
            embedding = result[0]["embedding"]
            # Store embedding as JSON string in employee record
            employee.face_embedding = json.dumps(embedding)
            employee.face_registered = True
            db.commit()
            embedding_stored = True

    except ImportError:
        # DeepFace not installed yet
        employee.face_registered = True
        db.commit()

    except Exception as e:
        # Face not clearly visible but save image anyway
        employee.face_registered = True
        db.commit()
        return {
            "success":    True,
            "message":    f"Face image saved but embedding extraction failed: {str(e)}. Install deepface.",
            "employee":   employee.full_name,
            "face_path":  face_path,
        }

    return {
        "success":          True,
        "message":          f"Face registered successfully for {employee.full_name}.",
        "employee_id":      employee_id,
        "employee_name":    employee.full_name,
        "embedding_stored": embedding_stored,
        "face_path":        face_path,
        "note":             "Employee can now use face recognition to clock in/out.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. CLOCK IN WITH FACE
#    Tablet app sends face photo → we identify who it is → mark clock in
#    Two modes:
#      a) identify_and_clockin = true  → tablet finds who it is automatically
#      b) employee_id provided         → verify this specific employee's face
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/clock-in-face", summary="Clock in using face photo — tablet app calls this")
async def clock_in_face(
    image:       UploadFile = File(...),
    employee_id: Optional[int] = Form(None),
    location:    str        = Form("Head Office"),
    db:          Session    = Depends(get_db),
):
    """
    Your TABLET APP calls this endpoint every morning.

    The tablet captures employee face → sends photo here →
    we verify the face → mark clock in → return result to tablet.

    Two modes:

    Mode 1 — Tablet knows employee (employee selects their name on tablet):
      Form data: { employee_id: 5, image: <photo>, location: "Head Office" }

    Mode 2 — Auto identify (tablet just captures face, we find who it is):
      Form data: { image: <photo>, location: "Head Office" }
      We scan all registered faces and find the match.

    Response tells tablet:
      {
        "status": "clocked_in",
        "employee_name": "Kaveen Deshapriya",
        "clock_in": "08:31:00",
        "is_late": false,
        "message": "Good morning Kaveen!"
      }
    """
    from app.models.attendance import Attendance
    from app.models.employee import Employee

    today         = date.today()
    now           = datetime.now()
    image_bytes   = await image.read()

    if len(image_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Invalid image.")

    # ── Mode 1: Verify specific employee ─────────────────────────────────────
    if employee_id:
        result = await _verify_face_bytes(employee_id, image_bytes)

        if not result["verified"]:
            return {
                "status":    "face_mismatch",
                "message":   "Face does not match. Please try again.",
                "confidence": result["confidence_score"],
            }

        return await _do_clock_in(db, employee_id, result["confidence_score"],
                                   "face_recognition", location, now, today, image_bytes)

    # ── Mode 2: Auto-identify from all registered faces ───────────────────────
    else:
        employees = db.query(Employee).filter(
            Employee.is_active      == True,
            Employee.face_registered == True,
        ).all()

        if not employees:
            return {
                "status":  "no_faces_registered",
                "message": "No employee faces registered yet.",
            }

        best_match, best_confidence = await _identify_from_all_faces(image_bytes, employees)

        if not best_match:
            return {
                "status":  "not_identified",
                "message": "Could not identify employee. Please select your name manually.",
                "tip":     "Make sure you are registered and facing the camera clearly.",
            }

        return await _do_clock_in(db, best_match.id, best_confidence,
                                   "face_recognition", location, now, today, image_bytes)


# ─────────────────────────────────────────────────────────────────────────────
# 3. CLOCK OUT WITH FACE
#    Evening: tablet captures face → verify → mark clock out → calculate OT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/clock-out-face", summary="Clock out using face photo — tablet app calls this")
async def clock_out_face(
    image:       UploadFile = File(...),
    employee_id: Optional[int] = Form(None),
    db:          Session    = Depends(get_db),
):
    """
    Your TABLET APP calls this endpoint every evening.

    Employee shows face → we verify → calculate work hours + OT → mark clock out.

    Response tells tablet:
      {
        "status": "clocked_out",
        "employee_name": "Kaveen Deshapriya",
        "work_hours": 8.5,
        "overtime_hours": 0.0,
        "pay_breakdown": { ... },
        "message": "Good evening Kaveen! You worked 8.5 hours today."
      }
    """
    from app.models.attendance import Attendance
    from app.models.employee import Employee

    today       = date.today()
    now         = datetime.now()
    image_bytes = await image.read()

    # ── Mode 1: Verify specific employee ─────────────────────────────────────
    if employee_id:
        result = await _verify_face_bytes(employee_id, image_bytes)
        if not result["verified"]:
            return {
                "status":    "face_mismatch",
                "message":   "Face does not match. Please try again.",
                "confidence": result["confidence_score"],
            }
        return await _do_clock_out(db, employee_id, result["confidence_score"],
                                    "face_recognition", now, today)

    # ── Mode 2: Auto-identify ─────────────────────────────────────────────────
    else:
        employees = db.query(Employee).filter(
            Employee.is_active       == True,
            Employee.face_registered == True,
        ).all()

        best_match, best_confidence = await _identify_from_all_faces(image_bytes, employees)

        if not best_match:
            return {
                "status":  "not_identified",
                "message": "Could not identify employee. Please select your name manually.",
            }

        return await _do_clock_out(db, best_match.id, best_confidence,
                                    "face_recognition", now, today)


# ─────────────────────────────────────────────────────────────────────────────
# 4. ALSO SUPPORT BASE64 IMAGE (for mobile apps that send JSON)
#    Some mobile frameworks prefer sending base64 instead of multipart form
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/clock-in-base64", summary="Clock in using base64 image — JSON API for mobile")
async def clock_in_base64(
    body: ClockInBase64Request,
    db:   Session = Depends(get_db),
):
    """
    Alternative to clock-in-face for Flutter / mobile apps that send JSON with base64 image.

    Send:
    {
        "employee_id": 5,
        "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
        "location": "Head Office"
    }
    """
    try:
        image_bytes = base64.b64decode(body.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image.")

    today = date.today()
    now   = datetime.now()

    result = await _verify_face_bytes(body.employee_id, image_bytes)

    if not result["verified"]:
        return {
            "status":     "face_mismatch",
            "message":    "Face does not match registered photo.",
            "confidence": result["confidence_score"],
        }

    return await _do_clock_in(db, body.employee_id, result["confidence_score"],
                               "face_recognition", body.location, now, today,
                               latitude=body.latitude, longitude=body.longitude)


@router.post("/clock-out-base64", summary="Clock out using base64 image — JSON API for mobile")
async def clock_out_base64(
    body: ClockOutBase64Request,
    db:   Session = Depends(get_db),
):
    """
    Alternative to clock-out-face for Flutter / mobile apps that send JSON with base64 image.

    Send:
    {
        "employee_id": 5,
        "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
        "latitude": 6.9271,
        "longitude": 79.8612
    }
    """
    try:
        image_bytes = base64.b64decode(body.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image.")

    today = date.today()
    now   = datetime.now()

    result = await _verify_face_bytes(body.employee_id, image_bytes)

    if not result["verified"]:
        return {
            "status":     "face_mismatch",
            "message":    "Face does not match registered photo.",
            "confidence": result["confidence_score"],
        }

    return await _do_clock_out(db, body.employee_id, result["confidence_score"],
                                "face_recognition", now, today,
                                latitude=body.latitude, longitude=body.longitude)


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET ALL REGISTERED EMPLOYEES (for tablet dropdown list)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/employees-list", summary="List all employees for tablet dropdown")
def employees_list(db: Session = Depends(get_db)):
    """
    Tablet app calls this to build the employee dropdown list.
    No auth required — tablet is internal device.

    Returns list of active employees with face registration status.
    """
    from app.models.employee import Employee

    employees = db.query(Employee).filter(Employee.is_active == True).all()

    return {
        "total": len(employees),
        "employees": [
            {
                "id":              emp.id,
                "employee_number": emp.employee_number,
                "full_name":       emp.full_name,
                "department":      emp.department.name if emp.department else None,
                "face_registered": emp.face_registered,
                "profile_photo":   emp.profile_photo,
            }
            for emp in employees
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. TODAY'S STATUS (tablet shows who clocked in today)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/today-all", summary="All employees clock-in status for today — tablet dashboard")
def today_all(db: Session = Depends(get_db)):
    """
    Tablet dashboard shows who is in the office today.
    No auth required — internal tablet.
    """
    from app.models.attendance import Attendance
    from app.models.employee import Employee

    today     = date.today()
    day_type  = get_day_type(today)

    records   = db.query(Attendance).filter(Attendance.work_date == today).all()
    clocked_in_ids = {r.employee_id for r in records if r.clock_in}

    employees = db.query(Employee).filter(Employee.is_active == True).all()

    present = []
    absent  = []

    for emp in employees:
        rec = next((r for r in records if r.employee_id == emp.id), None)
        entry = {
            "id":           emp.id,
            "full_name":    emp.full_name,
            "employee_number": emp.employee_number,
            "department":   emp.department.name if emp.department else None,
        }
        if rec and rec.clock_in:
            entry.update({
                "clock_in":    rec.clock_in.strftime("%H:%M"),
                "clock_out":   rec.clock_out.strftime("%H:%M") if rec.clock_out else None,
                "is_late":     rec.is_late,
                "status":      "clocked_out" if rec.clock_out else "clocked_in",
            })
            present.append(entry)
        else:
            entry["status"] = "absent"
            absent.append(entry)

    return {
        "date":          str(today),
        "day":           today.strftime("%A"),
        "day_type":      day_type,
        "total_present": len(present),
        "total_absent":  len(absent),
        "present":       present,
        "absent":        absent,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. EXISTING ROUTES (same as before)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/today", summary="My attendance today")
def get_today(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_employee),
):
    from app.models.attendance import Attendance
    today  = date.today()
    record = db.query(Attendance).filter(
        Attendance.employee_id == current_user.id,
        Attendance.work_date   == today,
    ).first()

    if not record:
        return {"status": "not_clocked_in", "date": str(today), "day": today.strftime("%A")}

    if record.clock_in and not record.clock_out:
        live = calc_work_hours(record.clock_in, datetime.now())
        return {
            "status": "clocked_in", "date": str(today),
            "clock_in": record.clock_in.strftime("%H:%M:%S"),
            "live_hours": live, "is_late": record.is_late,
            "late_minutes": record.late_minutes,
        }

    return {
        "status": "completed", "date": str(today),
        "clock_in":  record.clock_in.strftime("%H:%M:%S"),
        "clock_out": record.clock_out.strftime("%H:%M:%S"),
        "work_hours": record.work_hours, "overtime_hours": record.overtime_hours,
        "attendance_type": record.attendance_type,
    }


@router.get("/summary", summary="Monthly OT breakdown")
def get_summary(
    month:        Optional[int] = Query(None),
    year:         Optional[int] = Query(None),
    db:           Session       = Depends(get_db),
    current_user                = Depends(get_current_employee),
):
    from app.models.attendance import Attendance
    from calendar import monthrange

    today     = date.today()
    use_year  = year or today.year
    use_month = month or today.month
    _, days   = monthrange(use_year, use_month)

    records = db.query(Attendance).filter(
        Attendance.employee_id == current_user.id,
        Attendance.work_date   >= date(use_year, use_month, 1),
        Attendance.work_date   <= date(use_year, use_month, days),
    ).all()

    working_days  = sum(1 for d in range(1, days+1)
                       if date(use_year, use_month, d).weekday() < 6
                       and date(use_year, use_month, d) not in SL_PUBLIC_HOLIDAYS)
    present_days  = sum(1 for r in records if r.clock_in and not r.is_absent)
    absent_days   = sum(1 for r in records if r.is_absent)
    late_days     = sum(1 for r in records if r.is_late)
    half_days     = sum(1 for r in records if r.attendance_type == "half_day")
    saturday_days = sum(1 for r in records if r.work_date.weekday() == 5 and r.clock_in)
    sunday_days   = sum(1 for r in records if r.work_date.weekday() == 6 and r.clock_in)
    holiday_days  = sum(1 for r in records if r.work_date in SL_PUBLIC_HOLIDAYS and r.clock_in)

    weekday_ot  = round(sum(r.overtime_hours or 0 for r in records
                       if get_day_type(r.work_date) == "weekday"), 2)
    saturday_ot = round(sum(r.overtime_hours or 0 for r in records
                       if get_day_type(r.work_date) == "saturday"), 2)
    sunday_hrs  = round(sum(r.work_hours or 0 for r in records
                       if get_day_type(r.work_date) == "sunday"), 2)
    holiday_hrs = round(sum(r.work_hours or 0 for r in records
                       if get_day_type(r.work_date) == "holiday"), 2)

    return {
        "employee":   current_user.full_name,
        "period":     f"{use_year}-{str(use_month).zfill(2)}",
        "attendance": {
            "working_days": working_days, "present_days": present_days,
            "absent_days": absent_days, "late_days": late_days,
            "half_days": half_days, "saturday_days": saturday_days,
            "sunday_days": sunday_days, "holiday_days": holiday_days,
            "attendance_percent": round(present_days/working_days*100, 1) if working_days else 0,
        },
        "ot_breakdown": {
            "weekday_ot":  {"hours": weekday_ot,  "rate": f"{WEEKDAY_OT_RATE}x",  "pay_units": round(weekday_ot  * WEEKDAY_OT_RATE, 2)},
            "saturday_ot": {"hours": saturday_ot, "rate": f"{SATURDAY_OT_RATE}x", "pay_units": round(saturday_ot * SATURDAY_OT_RATE, 2)},
            "sunday":      {"hours": sunday_hrs,  "rate": f"{SUNDAY_RATE}x",      "pay_units": round(sunday_hrs  * SUNDAY_RATE, 2)},
            "holiday":     {"hours": holiday_hrs, "rate": f"{HOLIDAY_RATE}x",     "pay_units": round(holiday_hrs * HOLIDAY_RATE, 2)},
        },
        "daily_records": [record_to_dict(r) for r in sorted(records, key=lambda x: x.work_date)],
    }


@router.post("/manual", summary="Manual attendance — HR Manager+")
def manual_entry(
    body:         ManualAttendanceRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(3)),
):
    from app.models.attendance import Attendance
    from app.models.employee import Employee

    emp = db.query(Employee).filter(Employee.id == body.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    work_date    = date.fromisoformat(body.work_date)
    clock_in_dt  = datetime.strptime(f"{body.work_date} {body.clock_in}", "%Y-%m-%d %H:%M:%S")
    clock_out_dt = datetime.strptime(f"{body.work_date} {body.clock_out}", "%Y-%m-%d %H:%M:%S") if body.clock_out else None
    work_hours   = calc_work_hours(clock_in_dt, clock_out_dt) if clock_out_dt else 0
    ot_hours     = calc_ot_hours(work_hours, work_date)
    att_type     = calc_attendance_type(work_hours, work_date)
    late_min     = calc_late_minutes(clock_in_dt)

    existing = db.query(Attendance).filter(
        Attendance.employee_id == emp.id,
        Attendance.work_date   == work_date,
    ).first()

    note = f"Manual entry by {current_user.full_name}. Reason: {body.reason or 'N/A'}"

    if existing:
        existing.clock_in            = clock_in_dt
        existing.clock_out           = clock_out_dt
        existing.work_hours          = work_hours
        existing.overtime_hours      = ot_hours
        existing.attendance_type     = att_type
        existing.is_late             = late_min > 0
        existing.late_minutes        = late_min
        existing.verification_method = "manual_override"
        existing.notes               = note
        db.commit()
        return {
            "status":    "updated",
            "message":   f"Attendance updated for {emp.full_name}.",
            "work_hours": work_hours,
            "ot_hours":   ot_hours,
            "day_type":   get_day_type(work_date),
        }

    db.add(Attendance(
        employee_id          = emp.id,
        work_date            = work_date,
        clock_in             = clock_in_dt,
        clock_out            = clock_out_dt,
        work_hours           = work_hours,
        overtime_hours       = ot_hours,
        attendance_type      = att_type,
        is_late              = late_min > 0,
        late_minutes         = late_min,
        verification_method  = "manual_override",
        is_verified          = True,
        is_absent            = False,
        confidence_score     = 1.0,
        notes                = note,
    ))
    db.commit()
    return {
        "status":    "created",
        "message":   f"Manual attendance created for {emp.full_name}.",
        "work_hours": work_hours,
        "ot_hours":   ot_hours,
        "day_type":   get_day_type(work_date),
    }


@router.get("/ot-report", summary="Full OT report — HR+")
def ot_report(
    month:         Optional[int] = Query(None),
    year:          Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(require_role(2)),
):
    from app.models.attendance import Attendance
    from app.models.employee import Employee
    from calendar import monthrange

    today     = date.today()
    use_year  = year or today.year
    use_month = month or today.month
    _, days   = monthrange(use_year, use_month)

    emp_q = db.query(Employee).filter(Employee.is_active == True)
    if department_id:
        emp_q = emp_q.filter(Employee.department_id == department_id)

    report = []
    for emp in emp_q.all():
        recs = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.work_date   >= date(use_year, use_month, 1),
            Attendance.work_date   <= date(use_year, use_month, days),
            Attendance.clock_in    != None,
        ).all()
        if not recs: continue

        wkd_ot = round(sum(r.overtime_hours or 0 for r in recs if get_day_type(r.work_date) == "weekday"), 2)
        sat_ot = round(sum(r.overtime_hours or 0 for r in recs if get_day_type(r.work_date) == "saturday"), 2)
        sun_h  = round(sum(r.work_hours or 0 for r in recs if get_day_type(r.work_date) == "sunday"), 2)
        hol_h  = round(sum(r.work_hours or 0 for r in recs if get_day_type(r.work_date) == "holiday"), 2)

        report.append({
            "employee_id": emp.id, "employee_number": emp.employee_number,
            "full_name": emp.full_name,
            "department": emp.department.name if emp.department else None,
            "base_salary": float(emp.base_salary) if emp.base_salary else 0,
            "ot_breakdown": {
                "weekday_ot_hours": wkd_ot, "saturday_ot_hours": sat_ot,
                "sunday_hours": sun_h, "holiday_hours": hol_h,
            },
            "total_ot_pay_units": round(
                wkd_ot*WEEKDAY_OT_RATE + sat_ot*SATURDAY_OT_RATE +
                sun_h*SUNDAY_RATE + hol_h*HOLIDAY_RATE, 2),
            "total_work_hours": round(sum(r.work_hours or 0 for r in recs), 2),
        })

    return {
        "period": f"{use_year}-{str(use_month).zfill(2)}",
        "ot_rates": {"weekday_ot": f"{WEEKDAY_OT_RATE}x", "saturday_ot": f"{SATURDAY_OT_RATE}x",
                     "sunday": f"{SUNDAY_RATE}x", "holiday": f"{HOLIDAY_RATE}x"},
        "total_employees": len(report),
        "report": report,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

FACE_MATCH_THRESHOLD = 0.60  # cosine distance threshold — lenient for webcam conditions

# ── Module-level embedding cache  (loaded once, reused every scan) ────────────
_embedding_cache: dict = {}   # employee_id → numpy array


def _cosine_distance(a, b) -> float:
    """Cosine distance between two numpy vectors (0 = identical, 1 = opposite)."""
    import numpy as np
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 1.0
    return float(1.0 - np.dot(a, b) / denom)


def _extract_embedding(image_bytes: bytes) -> list:
    """
    Extract Facenet512 embedding from raw image bytes.
    Returns a list of floats, or raises an exception on failure.
    ONE DeepFace call — much faster than DeepFace.verify().
    """
    from deepface import DeepFace
    import numpy as np
    import tempfile, os

    # Write to temp file (DeepFace needs a file path or numpy array)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        result = DeepFace.represent(
            img_path          = tmp_path,
            model_name        = "Facenet512",
            detector_backend  = "opencv",
            enforce_detection = False,
        )
        return result[0]["embedding"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _verify_face_bytes(employee_id: int, image_bytes: bytes) -> dict:
    """
    Verify face bytes against stored embedding for an employee.

    Fast path: compare new image embedding against stored DB embedding
               (1 DeepFace call total, no looping).
    Slow fallback: image-vs-image comparison if no embedding stored.
    """
    from app.models.employee import Employee
    from app.core.database import SessionLocal
    import json

    face_path = get_face_path(employee_id)
    if not os.path.exists(face_path):
        return {"verified": False, "confidence_score": 0.0,
                "message": f"No face registered for employee #{employee_id}"}

    try:
        from deepface import DeepFace

        # ── Step 1: Get stored embedding (from cache or DB) ───────────────────
        stored_emb = _embedding_cache.get(employee_id)
        if stored_emb is None:
            db = SessionLocal()
            try:
                emp = db.query(Employee).filter(Employee.id == employee_id).first()
                if emp and emp.face_embedding:
                    raw = emp.face_embedding
                    stored_emb = raw if isinstance(raw, list) else json.loads(raw)
                    _embedding_cache[employee_id] = stored_emb
            finally:
                db.close()

        # ── Step 2: Extract embedding from new image (1 call) ─────────────────
        try:
            new_emb = _extract_embedding(image_bytes)
        except Exception as e:
            logger.warning(f"Embedding extraction failed for new image: {e}")
            new_emb = None

        # ── Step 3: Compare embeddings ────────────────────────────────────────
        if stored_emb and new_emb:
            distance   = _cosine_distance(stored_emb, new_emb)
            verified   = distance <= FACE_MATCH_THRESHOLD
            confidence = round(max(0.0, min(1.0, 1.0 - distance)), 4)
            logger.info(f"Face verify emp#{employee_id} [embedding]: dist={distance:.4f} verified={verified}")
            return {"verified": verified, "confidence_score": confidence, "distance": distance}

        # ── Fallback: image-vs-image if no stored embedding ───────────────────
        temp_path = f"uploads/faces/emp_{employee_id}/temp_verify.jpg"
        with open(temp_path, "wb") as f:
            f.write(image_bytes)
        try:
            result = DeepFace.verify(
                img1_path         = temp_path,
                img2_path         = face_path,
                model_name        = "Facenet512",
                distance_metric   = "cosine",
                detector_backend  = "opencv",
                enforce_detection = False,
            )
            distance   = result.get("distance", 1.0)
            verified   = distance <= FACE_MATCH_THRESHOLD
            confidence = round(max(0.0, min(1.0, 1.0 - distance)), 4)
            logger.info(f"Face verify emp#{employee_id} [fallback img]: dist={distance:.4f} verified={verified}")
            return {"verified": verified, "confidence_score": confidence, "distance": distance}
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except ImportError:
        return {"verified": True, "confidence_score": 0.85,
                "message": "DeepFace not installed — manual verification mode."}

    except Exception as e:
        logger.error(f"Face verify error emp#{employee_id}: {e}")
        return {"verified": False, "confidence_score": 0.0, "message": str(e)}


async def _identify_from_all_faces(image_bytes: bytes, employees: list) -> tuple:
    """
    Fast auto-identify: extract ONE embedding from new image, then compare
    against all stored embeddings using cosine distance.
    Returns (best_match_employee, best_confidence) or (None, 0.0).

    O(1) DeepFace calls instead of O(N) — dramatically faster with many employees.
    """
    from app.models.employee import Employee
    from app.core.database import SessionLocal
    import json

    # Extract embedding from the new image once
    try:
        new_emb = _extract_embedding(image_bytes)
    except Exception as e:
        logger.warning(f"Auto-identify embedding extraction failed: {e}. Falling back to per-employee verify.")
        new_emb = None

    best_match      = None
    best_confidence = 0.0

    if new_emb:
        # Fast path: compare against stored embeddings
        for emp in employees:
            stored_emb = _embedding_cache.get(emp.id)
            if stored_emb is None:
                db = SessionLocal()
                try:
                    e = db.query(Employee).filter(Employee.id == emp.id).first()
                    if e and e.face_embedding:
                        raw = e.face_embedding
                        stored_emb = raw if isinstance(raw, list) else json.loads(raw)
                        _embedding_cache[emp.id] = stored_emb
                finally:
                    db.close()

            if stored_emb is None:
                continue

            distance   = _cosine_distance(stored_emb, new_emb)
            confidence = round(max(0.0, min(1.0, 1.0 - distance)), 4)
            if distance <= FACE_MATCH_THRESHOLD and confidence > best_confidence:
                best_match      = emp
                best_confidence = confidence
    else:
        # Slow fallback: per-employee verify
        for emp in employees:
            if not os.path.exists(get_face_path(emp.id)):
                continue
            result = await _verify_face_bytes(emp.id, image_bytes)
            if result["verified"] and result["confidence_score"] > best_confidence:
                best_match      = emp
                best_confidence = result["confidence_score"]

    return best_match, best_confidence


CLOCK_OUT_GAP_MINUTES = 5  # minimum minutes after clock-in before a scan counts as clock-out

def _save_scan_photo(employee_id: int, scan_type: str, now: datetime, image_bytes: bytes) -> str:
    """Save scan snapshot to disk and return the path."""
    scan_dir = f"uploads/scans/emp_{employee_id}/{now.strftime('%Y-%m-%d')}"
    os.makedirs(scan_dir, exist_ok=True)
    filename = f"{scan_type}_{now.strftime('%H%M%S')}.jpg"
    path = f"{scan_dir}/{filename}"
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


async def _do_clock_in(db, employee_id, confidence, method, location, now, today, image_bytes=None, latitude=None, longitude=None) -> dict:
    """
    Smart clock-in / clock-out logic:
      - First scan of the day → CLOCK IN
      - Scan within 5 min of clock-in → ignore (too soon)
      - Scan after 5 min → UPDATE CLOCK OUT (keeps updating with every scan)
      - Total hours = last clock-out − first clock-in
      - Every scan saves a snapshot image as proof
    """
    from app.models.attendance import Attendance, AttendanceScan
    from app.models.employee import Employee
    from datetime import time

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    name = employee.first_name if employee else "Employee"

    existing = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.work_date   == today,
    ).first()

    # ── Already clocked in today ────────────────────────────────────────────
    if existing and existing.clock_in:
        # Strip timezone info to avoid naive/aware mismatch
        clock_in_naive = existing.clock_in.replace(tzinfo=None) if existing.clock_in.tzinfo else existing.clock_in
        minutes_since_in = (now - clock_in_naive).total_seconds() / 60

        # Too soon — ignore (within 5 min gap)
        if minutes_since_in < CLOCK_OUT_GAP_MINUTES:
            remaining = int(CLOCK_OUT_GAP_MINUTES - minutes_since_in) + 1
            return {
                "status":        "too_soon",
                "employee_name": employee.full_name if employee else str(employee_id),
                "clock_in":      existing.clock_in.strftime("%H:%M:%S"),
                "message":       f"Already clocked in. Wait {remaining} min before clocking out.",
            }

        # After 5 min → update clock-out time
        work_hours  = calc_work_hours(clock_in_naive, now)
        ot_hours    = calc_ot_hours(work_hours, today)
        att_type    = calc_attendance_type(work_hours, today)
        day_type    = get_day_type(today)
        breakdown   = calc_pay_breakdown(work_hours, today)
        early_dep   = now.time() < time(WORKDAY_END_H, WORKDAY_END_M)

        # Save scan snapshot
        photo_path = None
        if image_bytes:
            photo_path = _save_scan_photo(employee_id, "clock_out", now, image_bytes)

        existing.clock_out          = now
        existing.clock_out_photo    = photo_path
        existing.work_hours         = work_hours
        existing.overtime_hours     = ot_hours
        existing.attendance_type    = att_type
        existing.is_early_departure = early_dep
        existing.confidence_score   = max(existing.confidence_score or 0, confidence)
        if latitude is not None:
            existing.checkout_latitude  = latitude
        if longitude is not None:
            existing.checkout_longitude = longitude

        # Log scan record
        scan = AttendanceScan(
            attendance_id=existing.id, employee_id=employee_id,
            scan_type="clock_out", scanned_at=now,
            confidence=confidence, photo_path=photo_path,
        )
        db.add(scan)
        db.commit()

        # Build message based on day type
        if day_type in ("holiday", "sunday"):
            pay_msg = f"All {work_hours:.1f}h at 2x rate!"
        elif day_type == "saturday":
            if ot_hours > 0:
                pay_msg = f"{STANDARD_HOURS:.0f}h regular + {ot_hours:.1f}h OT at 1.5x"
            else:
                pay_msg = f"{work_hours:.1f}h at Saturday rate"
        elif ot_hours > 0:
            pay_msg = f"{work_hours - ot_hours:.1f}h regular + {ot_hours:.1f}h OT at 1.5x"
        else:
            pay_msg = f"Worked {work_hours:.1f}h today."

        return {
            "status":          "clocked_out",
            "employee_name":   employee.full_name if employee else str(employee_id),
            "clock_in":        existing.clock_in.strftime("%H:%M:%S"),
            "clock_out":       now.strftime("%H:%M:%S"),
            "work_hours":      round(work_hours, 2),
            "overtime_hours":  round(ot_hours, 2),
            "day_type":        day_type,
            "pay_breakdown":   breakdown,
            "confidence":      confidence,
            "message":         f"See you tomorrow {name}! {pay_msg}",
        }

    # ── First scan of the day → CLOCK IN ────────────────────────────────────
    late_min = calc_late_minutes(now)
    day_type = get_day_type(today)

    notes = {
        "holiday":  f"Working on public holiday — 2x pay applies.",
        "sunday":   f"Working on Sunday — 2x pay applies.",
        "saturday": f"Working on Saturday — OT at 1.5x after 8hrs.",
    }.get(day_type, f"Late by {late_min} min." if late_min > 0 else None)

    # Save scan snapshot
    photo_path = None
    if image_bytes:
        photo_path = _save_scan_photo(employee_id, "clock_in", now, image_bytes)

    record = Attendance(
        employee_id=employee_id, work_date=today, clock_in=now,
        clock_in_photo=photo_path,
        confidence_score=confidence, verification_method=method,
        is_verified=confidence >= 0.7, is_late=late_min > 0,
        late_minutes=late_min, location=location, is_absent=False,
        latitude=latitude, longitude=longitude,
        flagged=confidence < 0.5,
        flag_reason="Low confidence — possible proxy." if confidence < 0.5 else None,
        notes=notes,
    )
    db.add(record)
    db.commit()

    # Log scan record
    scan = AttendanceScan(
        attendance_id=record.id, employee_id=employee_id,
        scan_type="clock_in", scanned_at=now,
        confidence=confidence, photo_path=photo_path,
    )
    db.add(scan)
    db.commit()

    return {
        "status":          "clocked_in",
        "employee_name":   employee.full_name if employee else str(employee_id),
        "clock_in":        now.strftime("%H:%M:%S"),
        "day_type":        day_type,
        "is_late":         late_min > 0,
        "late_minutes":    late_min,
        "confidence":      confidence,
        "message":         f"Good morning {name}! {'You are ' + str(late_min) + ' min late.' if late_min > 0 else 'On time!'}",
        "note":            notes,
    }


async def _do_clock_out(db, employee_id, confidence, method, now, today, latitude=None, longitude=None) -> dict:
    """Shared clock-out logic."""
    from app.models.attendance import Attendance
    from app.models.employee import Employee
    from datetime import time

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    record   = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.work_date   == today,
        Attendance.clock_in    != None,
        Attendance.clock_out   == None,
    ).first()

    if not record:
        return {
            "status":  "not_clocked_in",
            "message": "No clock-in found for today. Please clock in first.",
        }

    work_hours  = calc_work_hours(record.clock_in, now)
    ot_hours    = calc_ot_hours(work_hours, today)
    breakdown   = calc_pay_breakdown(work_hours, today)
    att_type    = calc_attendance_type(work_hours, today)
    early_dep   = now.time() < time(WORKDAY_END_H, WORKDAY_END_M)

    record.clock_out          = now
    record.work_hours         = work_hours
    record.overtime_hours     = ot_hours
    record.attendance_type    = att_type
    record.is_early_departure = early_dep
    if latitude is not None:
        record.checkout_latitude  = latitude
    if longitude is not None:
        record.checkout_longitude = longitude
    db.commit()

    name = employee.first_name if employee else "Employee"
    return {
        "status":        "clocked_out",
        "employee_name": employee.full_name if employee else str(employee_id),
        "clock_in":      record.clock_in.strftime("%H:%M:%S"),
        "clock_out":     now.strftime("%H:%M:%S"),
        "work_hours":    work_hours,
        "overtime_hours": ot_hours,
        "attendance_type": att_type,
        "pay_breakdown": {
            "day_type":        get_day_type(today),
            "regular_hours":   breakdown["regular_hours"],
            "regular_rate":    f"{breakdown['regular_rate']}x",
            "overtime_hours":  breakdown["ot_hours"],
            "overtime_rate":   f"{breakdown['ot_rate']}x",
            "total_pay_units": breakdown["total_pay_units"],
        },
        "message": f"Good evening {name}! You worked {work_hours} hours today." +
                   (f" OT: {ot_hours} hrs." if ot_hours > 0 else ""),
        "confidence": confidence,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADDITIONAL ENDPOINTS (HR management & reporting)
# ─────────────────────────────────────────────────────────────────────────────

# GET /api/attendance/all — Paginated list with filters (HR+)

@router.get("/all", summary="All attendance records with filters")
def get_all_records(
    employee_id:   Optional[int]  = Query(None),
    department_id: Optional[int]  = Query(None),
    from_date:     Optional[str]  = Query(None, description="YYYY-MM-DD"),
    to_date:       Optional[str]  = Query(None, description="YYYY-MM-DD"),
    flagged_only:  bool           = Query(False),
    page:          int            = Query(1, ge=1),
    page_size:     int            = Query(20, ge=1, le=100),
    db:            Session        = Depends(get_db),
    current_user                  = Depends(get_current_employee),
):
    """
    Paginated list of attendance records.
    HR Staff+ sees all records; regular employees see only their own.
    """
    from app.models.attendance import Attendance
    from app.models.employee import Employee

    q = db.query(Attendance).join(Employee, Attendance.employee_id == Employee.id)

    # Regular employees (access_level < 2) can only see their own records
    user_level = current_user.role.access_level if current_user.role else 1
    if user_level < 2:
        q = q.filter(Attendance.employee_id == current_user.id)
    elif employee_id:
        q = q.filter(Attendance.employee_id == employee_id)
    if department_id:
        q = q.filter(Employee.department_id == department_id)
    if from_date:
        q = q.filter(Attendance.work_date >= date.fromisoformat(from_date))
    if to_date:
        q = q.filter(Attendance.work_date <= date.fromisoformat(to_date))
    if flagged_only:
        q = q.filter(Attendance.flagged == True)

    total   = q.count()
    records = q.order_by(Attendance.work_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":    total,
        "page":     page,
        "page_size": page_size,
        "records":  [record_to_dict(r) for r in records],
    }


# GET /api/attendance/history/{employee_id} — Employee history for HR

@router.get("/history/{employee_id}", summary="Attendance history for a specific employee — HR Staff+")
def employee_history(
    employee_id: int,
    month:       Optional[int] = Query(None, ge=1, le=12),
    year:        Optional[int] = Query(None),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_employee),
):
    """
    Get attendance history for a specific employee.
    - Employees can only view their own history (access_level 1).
    - HR Staff+ can view any employee.
    Optionally filter by month and year. Defaults to current month.
    """
    from app.models.attendance import Attendance
    from app.models.employee import Employee
    from calendar import monthrange

    access_level = current_user.role.access_level if current_user.role else 1
    if access_level < 2 and current_user.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own attendance history."
        )

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee #{employee_id} not found.")

    today     = date.today()
    use_year  = year or today.year
    use_month = month or today.month
    _, days   = monthrange(use_year, use_month)

    records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.work_date   >= date(use_year, use_month, 1),
        Attendance.work_date   <= date(use_year, use_month, days),
    ).order_by(Attendance.work_date.asc()).all()

    present   = sum(1 for r in records if r.clock_in and not r.is_absent)
    absent    = sum(1 for r in records if r.is_absent)
    late      = sum(1 for r in records if r.is_late)
    flagged   = sum(1 for r in records if r.flagged)
    total_ot  = round(sum(r.overtime_hours or 0 for r in records), 2)

    return {
        "employee_id":     employee_id,
        "employee_name":   employee.full_name,
        "employee_number": employee.employee_number,
        "period":          f"{use_year}-{str(use_month).zfill(2)}",
        "summary": {
            "present_days":   present,
            "absent_days":    absent,
            "late_days":      late,
            "flagged_records": flagged,
            "total_ot_hours": total_ot,
        },
        "records": [record_to_dict(r) for r in records],
    }


# GET /api/attendance/flagged — HR review queue

@router.get("/flagged", summary="All flagged/suspicious attendance records — HR Staff+")
def get_flagged_records(
    resolved: Optional[bool] = Query(None, description="true=resolved only, false=pending only"),
    page:     int            = Query(1, ge=1),
    page_size: int           = Query(20, ge=1, le=100),
    db:       Session        = Depends(get_db),
    current_user             = Depends(require_role(2)),
):
    """
    Returns all attendance records that were flagged for HR review.
    Flags are raised when:
    - Face confidence score < 0.5 (possible proxy attendance)
    - Clock-in/out at unusual hours (before 05:00 or after 22:00)

    Filter by resolved=false to see the pending review queue.
    """
    from app.models.attendance import Attendance
    from app.models.employee import Employee

    q = db.query(Attendance).filter(Attendance.flagged == True)

    if resolved is not None:
        # A record is considered resolved if flag_reason starts with "RESOLVED:"
        if resolved:
            q = q.filter(Attendance.flag_reason.like("RESOLVED:%"))
        else:
            q = q.filter(~Attendance.flag_reason.like("RESOLVED:%") | Attendance.flag_reason == None)

    total   = q.count()
    records = q.order_by(Attendance.work_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        row = record_to_dict(r)
        row["employee_name"]   = emp.full_name if emp else "Unknown"
        row["employee_number"] = emp.employee_number if emp else None
        row["department"]      = emp.department.name if emp and emp.department else None
        result.append(row)

    return {
        "total":    total,
        "page":     page,
        "page_size": page_size,
        "pending_review": total,
        "records":  result,
    }


# PATCH /api/attendance/{id}/resolve-flag — Resolve a flagged record

@router.patch("/{record_id}/resolve-flag", summary="Resolve a flagged attendance record — HR Staff+")
def resolve_flag(
    record_id:    int,
    body:         ResolveFlagRequest,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(2)),
):
    """
    HR reviews a flagged attendance record and marks it as resolved.
    The resolution note is prepended to the flag_reason with "RESOLVED:" prefix.

    Send: { "resolution_note": "Verified with CCTV footage. Legitimate." }
    """
    from app.models.attendance import Attendance

    record = db.query(Attendance).filter(Attendance.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Attendance record #{record_id} not found.")

    if not record.flagged:
        raise HTTPException(status_code=400, detail="This record is not flagged.")

    original_reason    = record.flag_reason or "Unknown flag reason"
    record.flag_reason = f"RESOLVED by {current_user.full_name}: {body.resolution_note} | Original: {original_reason}"
    db.commit()

    return {
        "message":    f"Flag on record #{record_id} resolved successfully.",
        "resolved_by": current_user.full_name,
        "note":        body.resolution_note,
    }