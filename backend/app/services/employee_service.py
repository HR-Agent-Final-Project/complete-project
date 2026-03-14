"""
services/employee_service.py
─────────────────────────────
Shared helpers for employee registration used by both api/auth.py and api/employees.py.
"""
import secrets
import string
import re

from sqlalchemy.orm import Session


# Department name → 2–3 letter prefix map
_DEPT_PREFIX_MAP = {
    "information technology": "IT",
    "it":                     "IT",
    "engineering":            "ENG",
    "software":               "ENG",
    "human resources":        "HR",
    "hr":                     "HR",
    "finance":                "FIN",
    "accounts":               "FIN",
    "marketing":              "MKT",
    "sales":                  "SAL",
    "operations":             "OPS",
    "legal":                  "LEG",
    "administration":         "ADM",
    "admin":                  "ADM",
    "management":             "MAN",
    "executive":              "MAN",
    "customer service":       "CSR",
    "support":                "SUP",
    "logistics":              "LOG",
    "procurement":            "PRO",
    "research":               "RND",
}


def _dept_prefix(department_name: str | None) -> str:
    """Return the 2–3 letter prefix for a department name."""
    if not department_name:
        return "EMP"
    key = department_name.strip().lower()
    if key in _DEPT_PREFIX_MAP:
        return _DEPT_PREFIX_MAP[key]
    # Fallback: first 3 letters, uppercase, alpha only
    letters = re.sub(r"[^a-zA-Z]", "", department_name)
    return letters[:3].upper() or "EMP"


def generate_employee_number(db: Session, department_name: str | None = None) -> str:
    """
    Auto-generate a department-based sequential employee number.
    Examples:  IT0001, HR0001, ENG0003, FIN0002, EMP0001 (fallback)

    Finds the highest existing number for this prefix and increments by 1.
    """
    from app.models.employee import Employee

    prefix = _dept_prefix(department_name)

    # Count how many employees already have this prefix
    count = db.query(Employee).filter(
        Employee.employee_number.like(f"{prefix}%")
    ).count()

    candidate = f"{prefix}{str(count + 1).zfill(4)}"

    # Guard against duplicates (e.g., if records were deleted)
    while db.query(Employee).filter(Employee.employee_number == candidate).first():
        count += 1
        candidate = f"{prefix}{str(count + 1).zfill(4)}"

    return candidate


def generate_temp_password(length: int = 12) -> str:
    """
    Generate a secure temporary password that satisfies:
      - At least one uppercase letter
      - At least one digit
      - At least one special character
    """
    alphabet = string.ascii_letters + string.digits + "!@#$"
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$"),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 3)]
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def unique_work_email(db: Session, first_name: str, last_name: str, employee_number: str) -> str:
    """
    Generate a unique work email address.
    Falls back to appending the employee number if the base address is already taken.
    """
    from app.models.employee import Employee
    base = f"{first_name.lower()}.{last_name.lower()}@company.com"
    if not db.query(Employee).filter(Employee.work_email == base).first():
        return base
    return f"{first_name.lower()}.{last_name.lower()}.{employee_number.lower()}@company.com"


def send_welcome_email(personal_email: str, full_name: str, employee_number: str, temp_password: str) -> bool:
    """
    Send a welcome email to the new employee with their login credentials.
    Returns True on success, False on failure (non-fatal — registration still succeeds).
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from app.core.config import settings
        if not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
            logger.warning("Email not configured — skipping welcome email for %s", employee_number)
            return False

        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        subject = f"Welcome to HRAgent — Your Login Credentials ({employee_number})"
        html = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 3px solid #0A0A0A;">
  <div style="background: #FFE135; border-bottom: 3px solid #0A0A0A; padding: 20px;">
    <h1 style="margin: 0; font-size: 28px; color: #0A0A0A;">HRAgent</h1>
    <p style="margin: 4px 0 0; font-size: 13px; color: #333;">AI-Powered HR Management</p>
  </div>
  <div style="padding: 24px;">
    <h2 style="color: #0A0A0A;">Welcome, {full_name}!</h2>
    <p>Your employee account has been created. Use the credentials below to sign in.</p>
    <table style="border: 2px solid #0A0A0A; width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="background: #f5f5f5;">
        <td style="padding: 10px 14px; border-bottom: 2px solid #0A0A0A; font-weight: bold;">Employee ID</td>
        <td style="padding: 10px 14px; border-bottom: 2px solid #0A0A0A; font-family: monospace; font-size: 18px; color: #0A0A0A;"><strong>{employee_number}</strong></td>
      </tr>
      <tr>
        <td style="padding: 10px 14px; font-weight: bold;">Temporary Password</td>
        <td style="padding: 10px 14px; font-family: monospace; font-size: 18px; color: #0A0A0A;"><strong>{temp_password}</strong></td>
      </tr>
    </table>
    <div style="background: #FFE135; border: 2px solid #0A0A0A; padding: 12px; margin-top: 12px;">
      <strong>Important:</strong> Please log in and change your password immediately.
    </div>
    <p style="color: #555; font-size: 13px; margin-top: 20px;">
      Login at: <a href="http://localhost:3001">http://localhost:3001</a>
    </p>
  </div>
</div>
"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.GMAIL_USER
        msg["To"]      = personal_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            smtp.sendmail(settings.GMAIL_USER, personal_email, msg.as_string())

        logger.info("Welcome email sent to %s (%s)", personal_email, employee_number)
        return True

    except Exception as exc:
        logger.warning("Failed to send welcome email to %s: %s", personal_email, exc)
        return False
