import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password, create_access_token, create_approval_token,
    create_refresh_token, decode_token,
    get_current_employee, require_role, hash_password
)

logger = logging.getLogger(__name__)

from app.schemas.auth import (
    LoginRequest, FirebaseTokenRequest, RefreshRequest,
    TokenResponse, MessageResponse,
    EmployeeRegisterRequest, EmployeeRegisterResponse,
    SetPasswordRequest, ForgotPasswordRequest, ResetPasswordRequest,
    SelfRegisterRequest, SelfRegisterResponse,
)
from app.services.employee_service import (
    generate_employee_number,
    generate_temp_password,
    unique_work_email,
)

router = APIRouter()

# Add this SEPARATE login route for Swagger OAuth2 form
@router.post("/token", include_in_schema=False)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    This endpoint is ONLY for Swagger UI authorization.
    It accepts username/password form data.
    username field = your email address
    """
    from app.models.employee import Employee

    from sqlalchemy import or_
    employee = db.query(Employee).filter(
        or_(
            Employee.personal_email  == form_data.username,
            Employee.employee_number == form_data.username.upper(),
        ),
        Employee.is_active == True
    ).first()

    if not employee or not verify_password(form_data.password, employee.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({
        "sub":   str(employee.id),
        "email": employee.personal_email,
        "role":  employee.role.access_level if employee.role else 1,
    })

    return {
        "access_token": access_token,
        "token_type":   "bearer"
    }

# ── Tracks failed login attempts per IP
import time
_failed_attempts: dict = {}
_blocked_ips: set = set()
MAX_ATTEMPTS = 5
BLOCK_SECONDS = 900  # 15 minutes


def _check_ip_blocked(ip: str):
    if ip in _blocked_ips:
        data = _failed_attempts.get(ip, {})
        blocked_at = data.get("blocked_at", 0)
        if time.time() - blocked_at < BLOCK_SECONDS:
            remaining = int(BLOCK_SECONDS - (time.time() - blocked_at))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed attempts. Try again in {remaining} seconds."
            )
        else:
            _blocked_ips.discard(ip)
            _failed_attempts.pop(ip, None)


def _record_failed(ip: str):
    if ip not in _failed_attempts:
        _failed_attempts[ip] = {"count": 0}
    _failed_attempts[ip]["count"] += 1
    if _failed_attempts[ip]["count"] >= MAX_ATTEMPTS:
        _blocked_ips.add(ip)
        _failed_attempts[ip]["blocked_at"] = time.time()
        logger.warning("IP blocked due to repeated failed logins: %s", ip)


def _record_success(ip: str):
    _failed_attempts.pop(ip, None)
    _blocked_ips.discard(ip)


def _build_token_response(employee, must_change_password: bool = False) -> TokenResponse:
    # Safely get role and department
    access_level = 1
    role_title   = None
    dept_name    = None

    try:
        if employee.role:
            access_level = employee.role.access_level
            role_title   = employee.role.title
    except Exception as e:
        logger.warning("Could not load role for employee %s: %s", employee.id, e)

    try:
        if employee.department:
            dept_name = employee.department.name
    except Exception as e:
        logger.warning("Could not load department for employee %s: %s", employee.id, e)

    access_token  = create_access_token({
        "sub":   str(employee.id),
        "email": employee.personal_email,
        "role":  access_level,
    })
    refresh_token = create_refresh_token({"sub": str(employee.id)})

    return TokenResponse(
        access_token          = access_token,
        refresh_token         = refresh_token,
        expires_in            = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        employee_id           = employee.id,
        employee_name         = employee.full_name,
        email                 = employee.personal_email,
        access_level          = access_level,
        department            = dept_name,
        role                  = role_title,
        profile_photo         = employee.profile_photo,
        must_change_password  = must_change_password,
    )
# Route: Register New Employee (HR Manager / Admin only)

@router.post(
    "/register",
    response_model=EmployeeRegisterResponse,
    summary="Register new employee — HR Manager or Admin only",
)
def register_employee(
    body: EmployeeRegisterRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(3))   # Level 3 = HR Manager minimum
):
    """
    Creates a new employee account.

    Only HR Manager (level 3) and Admin (level 4) can do this.

    After registration:
      - Employee gets a temporary password via this response
      - HR should share temp password with the employee securely
      - Employee logs in and MUST change password immediately
      - Employee can also use Google login if their Gmail matches
    """
    from app.models.employee import Employee, EmployeeStatus
    from app.models.department import Department
    from app.models.role import Role
    from datetime import date

    # Check email not already registered
    existing = db.query(Employee).filter(
        Employee.personal_email == body.personal_email
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {body.personal_email} is already registered."
        )

    # Generate temp password
    temp_password = generate_temp_password()

    # Resolve department name for ID prefix
    dept_name = None
    if body.department_id:
        dept_obj = db.query(Department).filter(Department.id == body.department_id).first()
        if dept_obj:
            dept_name = dept_obj.name

    # Generate department-based employee number (e.g. IT0001, HR0003)
    employee_number = generate_employee_number(db, dept_name)

    # Build full name
    full_name = f"{body.first_name} {body.last_name}"

    work_email = unique_work_email(db, body.first_name, body.last_name, employee_number)

    # Create employee
    new_employee = Employee(
        employee_number  = employee_number,
        first_name       = body.first_name,
        last_name        = body.last_name,
        full_name        = full_name,
        personal_email   = body.personal_email,
        work_email       = work_email,
        phone_number     = body.phone_number,
        department_id    = body.department_id,
        role_id          = body.role_id,
        employment_type  = body.employment_type,
        base_salary      = body.base_salary,
        language_pref    = body.language_pref,
        hashed_password  = hash_password(temp_password),
        status           = EmployeeStatus.PROBATION,
        is_active        = True,
        face_registered  = False,
        hire_date        = date.today(),
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    # Get department and role names for response
    dept = db.query(Department).filter(
        Department.id == body.department_id
    ).first()
    role = db.query(Role).filter(
        Role.id == body.role_id
    ).first()

    # Initialize leave balances for new employee
    _create_leave_balances(db, new_employee.id)

    logger.info("New employee registered: %s - %s (by user_id=%s)", employee_number, full_name, current_user.id)

    return EmployeeRegisterResponse(
        message         = f"Employee {full_name} registered successfully.",
        employee_id     = new_employee.id,
        employee_number = employee_number,
        full_name       = full_name,
        email           = body.personal_email,
        temp_password   = temp_password,
        department      = dept.name if dept else None,
        role            = role.title if role else None,
    )


def _create_leave_balances(db, employee_id: int):
    """Create initial leave balance records for new employee."""
    from app.models.leave import LeaveType, LeaveBalance
    from datetime import date

    current_year = date.today().year
    leave_types = db.query(LeaveType).filter(LeaveType.is_active == True).all()

    for lt in leave_types:
        balance = LeaveBalance(
            employee_id    = employee_id,
            leave_type_id  = lt.id,
            year           = current_year,
            total_days     = lt.max_days_per_year,
            used_days      = 0.0,
            pending_days   = 0.0,
            remaining_days = float(lt.max_days_per_year),
            carried_over   = 0.0,
        )
        db.add(balance)

    db.commit()

# Route: Set Password (First Login)

@router.post(
    "/set-password",
    response_model=MessageResponse,
    summary="Set new password on first login",
)
def set_password(
    body: SetPasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee)
):
    """
    Employee calls this after first login to replace temp password.
    Must provide their current temp password to verify identity.
    """
    # Verify temp password
    if not verify_password(body.temp_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    # Set new password
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()

    return {"message": "Password updated successfully. Please log in again."}

# Route: Forgot Password

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset email",
)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Employee submits their email.
    System sends a password reset link.
    """
    from app.models.employee import Employee
    from datetime import timedelta

    employee = db.query(Employee).filter(
        Employee.personal_email == body.email,
        Employee.is_active == True
    ).first()

    # Always return success even if email not found
    # This prevents email enumeration attacks
    if not employee:
        return {"message": "If your email is registered, you will receive a reset link."}

    # Generate reset token (valid 30 minutes)
    reset_token = create_access_token({
        "sub": str(employee.id),
        "type": "password_reset",
        "email": employee.personal_email,
    })

    # TODO: Implement email delivery before enabling in production.
    # reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    # send_email(to=body.email, subject="Password Reset", body=reset_link)

    return {"message": "If your email is registered, you will receive a reset link."}


# Route: Reset Password

@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using token from email",
)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Employee uses reset token from email to set new password.
    """
    from app.models.employee import Employee

    # Decode reset token
    try:
        payload = decode_token(body.reset_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token."
        )

    employee = db.query(Employee).filter(
        Employee.id == int(payload["sub"]),
        Employee.is_active == True
    ).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found."
        )

    # Set new password
    employee.hashed_password = hash_password(body.new_password)
    db.commit()

    return {"message": "Password reset successful. Please log in with your new password."}

# Route: Self-Registration (HR Admin / Management — pending approval)

APPROVAL_EMAIL = "hr.agent.automation@gmail.com"

@router.post(
    "/self-register",
    response_model=SelfRegisterResponse,
    summary="HR Admin / Management self-registration — requires email approval",
)
def self_register(body: SelfRegisterRequest, db: Session = Depends(get_db)):
    """
    Anyone can submit a registration request for an HR Admin or Management account.
    The account is created as inactive (is_active=False).
    An approval email is sent to hr.agent.automation@gmail.com.
    Clicking the link in that email activates the account.
    """
    from app.models.employee import Employee, EmployeeStatus
    from app.models.role import Role
    from app.services.notification_service import _send_email
    from datetime import date

    # Check email not already taken
    existing = db.query(Employee).filter(
        Employee.personal_email == body.personal_email
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {body.personal_email} is already registered."
        )

    # Find matching role by access_level
    role_level = 3 if body.requested_role == "hr_admin" else 4
    role = db.query(Role).filter(Role.access_level == role_level).first()

    # Generate employee number
    employee_number = generate_employee_number(db)
    full_name = f"{body.first_name} {body.last_name}"
    work_email = unique_work_email(db, body.first_name, body.last_name, employee_number)

    new_employee = Employee(
        employee_number = employee_number,
        first_name      = body.first_name,
        last_name       = body.last_name,
        full_name       = full_name,
        personal_email  = body.personal_email,
        work_email      = work_email,
        phone_number    = body.phone_number,
        role_id         = role.id if role else None,
        employment_type = "full_time",
        hashed_password = hash_password(body.password),
        status          = EmployeeStatus.PROBATION,  # Safe enum value; is_active=False blocks login
        is_active       = False,   # Blocked until HR approves
        hire_date       = date.today(),
        language_pref   = "en",
    )
    try:
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
    except Exception as db_err:
        db.rollback()
        logger.error("[self_register] DB error: %s", db_err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create account: {str(db_err)}"
        )

    # Initialize leave balances (non-critical — ignore failures)
    try:
        _create_leave_balances(db, new_employee.id)
    except Exception:
        pass

    # Build approval token (24h expiry) — uses create_approval_token so type is preserved
    approval_token = create_approval_token({
        "sub":            str(new_employee.id),
        "type":           "registration_approval",
        "requested_role": body.requested_role,
        "email":          body.personal_email,
    }, expires_hours=24)

    # Send approval email to HR
    role_label = "HR Admin" if body.requested_role == "hr_admin" else "Management"
    approve_link = f"{settings.BACKEND_URL}/api/auth/approve/{approval_token}"
    email_body = (
        f"New Account Registration Request\n\n"
        f"Name    : {full_name}\n"
        f"Email   : {body.personal_email}\n"
        f"Role    : {role_label}\n"
        f"Phone   : {body.phone_number or 'N/A'}\n\n"
        f"To approve this account and allow them to log in, click the link below:\n\n"
        f"{approve_link}\n\n"
        f"If you did not expect this request, you can safely ignore this email.\n"
        f"The link expires in 24 hours."
    )
    sent = _send_email(
        APPROVAL_EMAIL,
        f"[HRAgent] Account Approval Request — {full_name} ({role_label})",
        email_body,
    )

    if sent:
        logger.info("Approval email sent to %s for new user %s", APPROVAL_EMAIL, body.personal_email)
    else:
        logger.warning("Could not send approval email (SMTP not configured). Token: %s", approval_token)

    return SelfRegisterResponse(
        message=(
            "Registration submitted successfully. "
            "An approval request has been sent to hr.agent.automation@gmail.com. "
            "You will be able to log in once your account is approved."
        )
    )


# Route: Approve Registration (clicked from email link)

@router.get(
    "/approve/{token}",
    summary="Approve a pending registration (called via email link)",
    include_in_schema=False,
)
def approve_registration(token: str, db: Session = Depends(get_db)):
    """
    Called when the HR approver clicks the link in the approval email.
    Activates the employee account and sends a welcome email.
    Returns an HTML confirmation page.
    """
    from fastapi.responses import HTMLResponse
    from app.models.employee import Employee

    def _html(title: str, heading: str, body_text: str, color: str = "#00C9B1") -> HTMLResponse:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title}</title>
<style>
  body{{font-family:'Segoe UI',sans-serif;background:#FFFBF0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
  .card{{background:#fff;border:4px solid #0A0A0A;box-shadow:6px 6px 0 #0A0A0A;padding:40px;max-width:480px;width:100%}}
  .badge{{background:{color};border:3px solid #0A0A0A;display:inline-block;padding:6px 16px;font-weight:700;font-size:12px;letter-spacing:1px;margin-bottom:16px}}
  h1{{font-size:24px;font-weight:800;margin:0 0 12px}}
  p{{color:#555;line-height:1.6;margin:0 0 20px}}
  a{{display:inline-block;background:#FFE135;border:3px solid #0A0A0A;box-shadow:4px 4px 0 #0A0A0A;padding:10px 24px;font-weight:700;text-decoration:none;color:#0A0A0A;transition:all .15s}}
  a:hover{{box-shadow:none;transform:translate(4px,4px)}}
</style></head>
<body><div class="card">
  <div class="badge">{title.upper()}</div>
  <h1>{heading}</h1>
  <p>{body_text}</p>
  <a href="{settings.FRONTEND_URL}/login">Go to Login →</a>
</div></body></html>"""
        return HTMLResponse(content=html)

    # Decode token
    try:
        payload = decode_token(token)
    except Exception:
        return _html("Error", "Invalid or Expired Link",
                     "This approval link is invalid or has expired. Please ask the user to register again.",
                     color="#FF6B6B")

    if payload.get("type") != "registration_approval":
        return _html("Error", "Invalid Link",
                     "This link is not a valid registration approval link.",
                     color="#FF6B6B")

    employee_id = int(payload["sub"])
    employee = db.query(Employee).filter(Employee.id == employee_id).first()

    if not employee:
        return _html("Error", "Account Not Found",
                     "No account was found for this approval link.",
                     color="#FF6B6B")

    if employee.is_active:
        return _html("Already Active", "Account Already Approved",
                     f"{employee.full_name}'s account is already active. They can log in at any time.")

    # Activate the account
    employee.is_active = True
    from app.models.employee import EmployeeStatus
    employee.status = EmployeeStatus.ACTIVE
    db.commit()
    db.refresh(employee)

    logger.info("Account approved for employee %s (%s)", employee.full_name, employee.personal_email)

    # Send welcome email to the new user
    from app.services.notification_service import _send_email as send_email
    role_label = "HR Admin" if payload.get("requested_role") == "hr_admin" else "Management"
    welcome_body = (
        f"Hi {employee.first_name},\n\n"
        f"Your HRAgent account has been approved! You can now log in.\n\n"
        f"Login URL : {settings.FRONTEND_URL}/login\n"
        f"Email     : {employee.personal_email}\n"
        f"Role      : {role_label}\n\n"
        f"Please keep your credentials secure.\n\n"
        f"— HRAgent Team"
    )
    send_email(
        employee.personal_email,
        "[HRAgent] Your account has been approved — You can now log in",
        welcome_body,
    )

    return _html(
        "Approved",
        f"{employee.full_name}'s Account Approved",
        f"The account for <strong>{employee.full_name}</strong> ({employee.personal_email}) "
        f"has been activated as <strong>{role_label}</strong>. "
        f"They have been notified by email and can now log in.",
    )


# Route 1: Email + Password Login

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db)
):
    from app.models.employee import Employee

    client_ip = request.client.host
    _check_ip_blocked(client_ip)

    # Find employee by Employee ID (e.g. IT0001) or personal email
    from sqlalchemy import or_
    employee = db.query(Employee).filter(
        or_(
            Employee.personal_email   == body.identifier,
            Employee.employee_number  == body.identifier.upper(),
        )
    ).first()

    # Pending approval check (better UX than a generic 401)
    if employee and not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval. Please wait for HR to approve your registration."
        )

    # Verify credentials
    if not employee or not verify_password(body.password, employee.hashed_password):
        _record_failed(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Employee ID/email or password."
        )

    _record_success(client_ip)

    # Detect first-ever login (temp password not yet changed)
    is_first_login = employee.last_login is None

    # Update last login
    employee.last_login = datetime.utcnow()
    db.commit()

    return _build_token_response(employee, must_change_password=is_first_login)

# Route 2: Firebase Google Login

@router.post(
    "/google/firebase",
    response_model=TokenResponse,
    summary="Login with Google via Firebase",
)
def firebase_google_login(
    request: Request,
    body: FirebaseTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Frontend sends Firebase ID token.
    We verify it and return our own JWT tokens.

    Steps:
      1. User clicks "Sign in with Google" on frontend
      2. Firebase handles Google popup
      3. Frontend gets ID token from Firebase
      4. Frontend sends ID token here
      5. We verify + find employee + return JWT
    """
    from app.models.employee import Employee
    from app.core.firebase import verify_firebase_token

    client_ip = request.client.host
    _check_ip_blocked(client_ip)

    # Verify Firebase token
    try:
        firebase_user = verify_firebase_token(body.id_token)
    except Exception:
        # Do not expose internal Firebase SDK error details to the client.
        _record_failed(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed. Please try again."
        )

    google_email = firebase_user.get("email")
    google_photo = firebase_user.get("picture")

    if not google_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not get email from Google account."
        )

    # Find employee by Google email
    employee = db.query(Employee).filter(
        Employee.personal_email == google_email,
        Employee.is_active == True
    ).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Your Google account is not registered in the HR system.",
                "email": google_email,
                "action": "Please contact HR to register your account first."
            }
        )

    # Update profile photo from Google if not already set
    if not employee.profile_photo and google_photo:
        employee.profile_photo = google_photo

    employee.last_login = datetime.utcnow()
    db.commit()

    _record_success(client_ip)
    return _build_token_response(employee)


# Route 3: Refresh Token

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Get new access token using refresh token",
)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    from app.models.employee import Employee

    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token."
        )

    employee = db.query(Employee).filter(
        Employee.id == int(payload["sub"]),
        Employee.is_active == True
    ).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee not found."
        )

    return _build_token_response(employee)


# Route 4: Get Current User

@router.get(
    "/me",
    summary="Get currently logged in employee info",
)
def get_me(current_employee=Depends(get_current_employee)):
    return {
        "id":              current_employee.id,
        "employee_number": current_employee.employee_number,
        "full_name":       current_employee.full_name,
        "email":           current_employee.personal_email,
        "work_email":      current_employee.work_email,
        "department":      current_employee.department.name if current_employee.department else None,
        "role":            current_employee.role.title if current_employee.role else None,
        "access_level":    current_employee.role.access_level if current_employee.role else 1,
        "status":          current_employee.status,
        "face_registered": current_employee.face_registered,
        "language_pref":   current_employee.language_pref,
        "profile_photo":   current_employee.profile_photo,
        "hire_date":       str(current_employee.hire_date) if current_employee.hire_date else None,
    }

# Route 5: Logout

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current employee",
)
def logout(current_employee=Depends(get_current_employee)):
    return {
        "message": f"Goodbye {current_employee.first_name}! Logged out successfully."
    }