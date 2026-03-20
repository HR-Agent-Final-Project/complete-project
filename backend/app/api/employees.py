import logging
import shutil
from pathlib import Path
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_employee,
    require_role,
    hash_password
)
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, StatusUpdateRequest, FaceEnrollRequest
from app.models.employee import EmployeeStatus
from app.services.employee_service import (
    generate_employee_number,
    generate_temp_password,
    unique_work_email,
    send_welcome_email,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def employee_to_dict(emp) -> dict:
    """Convert employee object to response dict."""
    return {
        "id":              emp.id,
        "employee_number": emp.employee_number,
        "first_name":      emp.first_name,
        "last_name":       emp.last_name,
        "full_name":       emp.full_name,
        "personal_email":  emp.personal_email,
        "work_email":      emp.work_email,
        "phone_number":    emp.phone_number,
        "department":      emp.department.name if emp.department else None,
        "department_id":   emp.department_id,
        "role":            emp.role.title if emp.role else None,
        "role_id":         emp.role_id,
        "access_level":    emp.role.access_level if emp.role else 1,
        "status":          emp.status,
        "employment_type": emp.employment_type,
        "hire_date":       str(emp.hire_date) if emp.hire_date else None,
        "base_salary":     float(emp.base_salary) if emp.base_salary else None,
        "face_registered": emp.face_registered,
        "language_pref":   emp.language_pref,
        "profile_photo":   emp.profile_photo,
        "is_active":       emp.is_active,
        "created_at":      str(emp.created_at),
        # Extended personal info
        "nic_number":      emp.nic_number,
        "date_of_birth":   str(emp.date_of_birth) if emp.date_of_birth else None,
        "gender":          emp.gender,
        "address":         emp.address,
        "city":            emp.city,
        "district":        emp.district,
        "bank_account":    emp.bank_account,
        "bank_name":       emp.bank_name,
        "manager_id":      emp.manager_id,
        "manager_name":    emp.manager.full_name if emp.manager else None,
    }


# GET /api/employees — List all employees

@router.get("", summary="List all employees — HR Staff and above")
def list_employees(
    department_id: Optional[int]            = Query(None),
    role_id:       Optional[int]            = Query(None),
    status:        Optional[EmployeeStatus] = Query(None),
    search:        Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=100),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(require_role(2)),   # HR Staff+
):
    """
    List all employees with optional filters.
    Supports search by name or email.
    """
    from app.models.employee import Employee

    query = db.query(Employee)

    # Filters
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if role_id:
        query = query.filter(Employee.role_id == role_id)
    if status:
        query = query.filter(Employee.status == status)
    if search:
        query = query.filter(
            Employee.full_name.ilike(f"%{search}%") |
            Employee.personal_email.ilike(f"%{search}%") |
            Employee.employee_number.ilike(f"%{search}%")
        )

    total = query.count()
    employees = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "employees": [employee_to_dict(e) for e in employees],
    }

# GET /api/employees/me — Own profile

@router.get("/me", summary="Get own profile — any employee")
def get_my_profile(current_user=Depends(get_current_employee)):
    """Any logged in employee can see their own profile."""
    return employee_to_dict(current_user)

# GET /api/employees/{id} — Get one employee

@router.get("/{employee_id}", summary="Get employee by ID — HR Staff and above")
def get_employee(
    employee_id: int,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_employee),
):
    """
    Get a specific employee.
    - Employees can only see their own profile
    - HR Staff and above can see anyone
    """
    from app.models.employee import Employee

    # Level 1 employees can only see themselves
    access_level = current_user.role.access_level if current_user.role else 1
    if access_level < 2 and current_user.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile."
        )

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee #{employee_id} not found."
        )

    return employee_to_dict(employee)

# POST /api/employees/register — Create new employee

@router.post("/register", summary="Register new employee — HR Manager and above")
def register_employee(
    body:         EmployeeCreate,
    db:           Session = Depends(get_db),
    current_user          = Depends(require_role(3)),   # HR Manager+
):
    """
    Create a new employee account.
    Only HR Manager (level 3) and Admin (level 4) can do this.

    Send:
    {
        "first_name": "Kaveen",
        "last_name": "Deshapriya",
        "personal_email": "kaveen@gmail.com",
        "phone_number": "0771234567",
        "department_id": 1,
        "role_id": 1,
        "employment_type": "full_time",
        "base_salary": 150000,
        "language_pref": "en"
    }
    """
    from app.models.employee import Employee, EmployeeStatus
    from app.models.leave import LeaveType, LeaveBalance
    from app.models.department import Department

    # Check email not already taken
    existing = db.query(Employee).filter(
        Employee.personal_email == body.personal_email
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {body.personal_email} is already registered."
        )

    first_name  = body.first_name
    last_name   = body.last_name
    full_name   = f"{first_name} {last_name}"

    # Resolve department name for ID prefix
    dept_name = None
    if body.department_id:
        dept_obj = db.query(Department).filter(Department.id == body.department_id).first()
        if dept_obj:
            dept_name = dept_obj.name

    emp_number = generate_employee_number(db, dept_name)
    temp_pass  = generate_temp_password()
    work_email = unique_work_email(db, first_name, last_name, emp_number)

    new_emp = Employee(
        employee_number = emp_number,
        first_name      = first_name,
        last_name       = last_name,
        full_name       = full_name,
        personal_email  = body.personal_email,
        work_email      = work_email,
        phone_number    = body.phone_number,
        department_id   = body.department_id,
        role_id         = body.role_id,
        employment_type = body.employment_type,
        base_salary     = body.base_salary,
        language_pref   = body.language_pref,
        nic_number      = body.nic_number,
        date_of_birth   = body.date_of_birth,
        gender          = body.gender,
        manager_id      = body.manager_id,
        address         = body.address,
        city            = body.city,
        district        = body.district,
        bank_account    = body.bank_account,
        bank_name       = body.bank_name,
        hashed_password = hash_password(temp_pass),
        status          = EmployeeStatus.PROBATION,
        is_active       = True,
        face_registered = False,
        hire_date       = date.today(),
    )

    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    # Create leave balances for this employee
    current_year = date.today().year
    leave_types  = db.query(LeaveType).filter(LeaveType.is_active == True).all()
    for lt in leave_types:
        db.add(LeaveBalance(
            employee_id    = new_emp.id,
            leave_type_id  = lt.id,
            year           = current_year,
            total_days     = float(lt.max_days_per_year),
            used_days      = 0.0,
            pending_days   = 0.0,
            remaining_days = float(lt.max_days_per_year),
            carried_over   = 0.0,
        ))
    db.commit()

    logger.info("New employee registered: %s - %s (by user_id=%s)", emp_number, full_name, current_user.id)

    # Send welcome email with credentials (non-fatal if email fails)
    email_sent = send_welcome_email(body.personal_email, full_name, emp_number, temp_pass)

    return {
        "message":         f"Employee {full_name} registered successfully.",
        "employee_id":     new_emp.id,
        "employee_number": emp_number,
        "full_name":       full_name,
        "email":           body.personal_email,
        "work_email":      work_email,
        "temp_password":   temp_pass,
        "department_id":   body.department_id,
        "role_id":         body.role_id,
        "email_sent":      email_sent,
        "note": "Credentials have been emailed to the employee. They must change the password on first login."
    }

# PUT /api/employees/{id} — Update employee

@router.put("/{employee_id}", summary="Update employee — HR Manager and above")
def update_employee(
    employee_id: int,
    body:        EmployeeUpdate,
    db:          Session = Depends(get_db),
    current_user         = Depends(require_role(3)),   # HR Manager+
):
    from app.models.employee import Employee

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee #{employee_id} not found."
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(employee, field, value)

    # Update full_name if name changed
    if body.first_name or body.last_name:
        employee.full_name = f"{employee.first_name} {employee.last_name}"

    db.commit()
    db.refresh(employee)

    return {
        "message":  f"Employee {employee.full_name} updated successfully.",
        "employee": employee_to_dict(employee),
    }

# DELETE /api/employees/{id} — Delete employee (Admin only)

@router.delete("/{employee_id}", summary="Delete employee — HR Manager and above (Level 3+)")
def delete_employee(
    employee_id: int,
    db:          Session = Depends(get_db),
    current_user         = Depends(require_role(3)),   # HR Manager+
):
    """
    Permanently delete an employee.
    HR Manager (level 3) and Admin (level 4) can do this.
    """
    from app.models.employee import Employee

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee #{employee_id} not found."
        )

    # Prevent deleting yourself
    if employee.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account."
        )

    name = employee.full_name
    eid = employee.id

    # Manually delete all child records to avoid DB-level FK violations
    # (the DB constraints don't have ON DELETE CASCADE)
    from app.models.chat import ChatSession, ChatMessage
    from app.models.leave import LeaveRequest, LeaveBalance
    from app.models.attendance import Attendance
    from app.models.performance import PerformanceReview
    from app.models.notification import Notification
    from app.models.audit_log import AuditLog

    # Chat messages belong to sessions, delete them first
    session_ids = [s.id for s in db.query(ChatSession.id).filter(ChatSession.employee_id == eid).all()]
    if session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(synchronize_session=False)
    db.query(ChatSession).filter(ChatSession.employee_id == eid).delete(synchronize_session=False)

    db.query(LeaveBalance).filter(LeaveBalance.employee_id == eid).delete(synchronize_session=False)
    db.query(LeaveRequest).filter(LeaveRequest.employee_id == eid).delete(synchronize_session=False)
    db.query(Attendance).filter(Attendance.employee_id == eid).delete(synchronize_session=False)
    db.query(PerformanceReview).filter(PerformanceReview.employee_id == eid).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.employee_id == eid).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.employee_id == eid).delete(synchronize_session=False)

    # Nullify reviewer references in performance reviews by other employees
    db.query(PerformanceReview).filter(PerformanceReview.reviewer_id == eid).update({"reviewer_id": None}, synchronize_session=False)

    # Nullify job application references (applicant_id is nullable)
    from app.models.recruitment import JobApplication
    db.query(JobApplication).filter(JobApplication.applicant_id == eid).update({"applicant_id": None}, synchronize_session=False)

    # Clear manager references from other employees
    db.query(Employee).filter(Employee.manager_id == eid).update({"manager_id": None}, synchronize_session=False)

    # Now safe to delete the employee
    db.delete(employee)
    db.commit()

    logger.info("Employee deleted: %s (by user_id=%s)", name, current_user.id)

    return {"message": f"Employee {name} deleted permanently."}

# PATCH /api/employees/{id}/status — Activate or Deactivate


@router.patch("/{employee_id}/status", summary="Activate or deactivate employee — HR Manager+")
def update_status(
    employee_id: int,
    body:        StatusUpdateRequest,
    db:          Session = Depends(get_db),
    current_user         = Depends(require_role(3)),   # HR Manager+
):
    """
    Activate or deactivate an employee without deleting.
    Use this instead of delete in most cases.

    Send: { "is_active": false, "reason": "Employee resigned" }
    """
    from app.models.employee import Employee, EmployeeStatus

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee #{employee_id} not found."
        )

    is_active = body.is_active
    employee.is_active = is_active

    if not is_active:
        employee.status = EmployeeStatus.TERMINATED
    else:
        employee.status = EmployeeStatus.ACTIVE

    db.commit()

    action = "activated" if is_active else "deactivated"
    logger.info("Employee %s %s (by user_id=%s)", employee.full_name, action, current_user.id)

    return {
        "message":   f"Employee {employee.full_name} {action} successfully.",
        "is_active": is_active,
        "status":    employee.status,
    }


# POST /api/employees/{id}/enroll-face — Biometric face enrollment

@router.post("/{employee_id}/enroll-face", summary="Enroll employee face — HR Manager+")
def enroll_face(
    employee_id: int,
    body:        FaceEnrollRequest,
    db:          Session = Depends(get_db),
    current_user         = Depends(require_role(3)),   # HR Manager+
):
    """
    Enroll or re-enroll the face biometric for an employee.
    Runs liveness detection (anti-spoofing), extracts DeepFace embedding,
    saves the photo, and marks face_registered = True in the database.

    Send: { "image_base64": "<base64-encoded JPEG>" }
    """
    from app.services.face_enrollment_service import enroll_face as _enroll
    return _enroll(employee_id, body.image_base64, db)


# POST /api/employees/{id}/upload-photo — Profile photo upload

PROFILE_PHOTOS_DIR = "uploads/profile_photos"

@router.post("/{employee_id}/upload-photo", summary="Upload profile photo — HR Manager+ or self")
def upload_profile_photo(
    employee_id: int,
    file:        UploadFile = File(...),
    db:          Session    = Depends(get_db),
    current_user            = Depends(get_current_employee),
):
    """
    Upload a profile photo for an employee.
    - Employees can upload their own photo.
    - HR Manager+ can upload for any employee.
    Accepts: image/jpeg or image/png. Max recommended size: 5 MB.
    """
    from app.models.employee import Employee

    # Access check: employee can only upload own photo
    access_level = current_user.role.access_level if current_user.role else 1
    if access_level < 3 and current_user.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload your own profile photo."
        )

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee #{employee_id} not found."
        )

    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG and PNG images are accepted."
        )

    MAX_PHOTO_SIZE_MB = 5
    MAX_PHOTO_BYTES   = MAX_PHOTO_SIZE_MB * 1024 * 1024
    # Read once to check size, then seek back so shutil.copyfileobj can read it
    contents = file.file.read()
    if len(contents) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Photo must be {MAX_PHOTO_SIZE_MB} MB or smaller."
        )
    file.file.seek(0)   # rewind so the write below reads the full file

    ext      = "jpg" if file.content_type == "image/jpeg" else "png"
    save_dir = Path(PROFILE_PHOTOS_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{employee_id}.{ext}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    employee.profile_photo = f"/{PROFILE_PHOTOS_DIR}/{employee_id}.{ext}"
    db.commit()

    return {
        "message":       "Profile photo uploaded successfully.",
        "profile_photo": employee.profile_photo,
    }