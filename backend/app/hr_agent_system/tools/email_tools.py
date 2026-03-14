"""
tools/email_tools.py
────────────────────
Email notification tool used by Leave, Recruitment, and Detection agents.
Also writes an in-app Notification row to the database.
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from langchain.tools import tool
from config.settings import settings
from models.database import SessionLocal, Notification, Employee


def _send_smtp(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP. Returns True on success."""
    try:
        msg                  = MIMEMultipart("alternative")
        msg["Subject"]       = subject
        msg["From"]          = settings.EMAIL_FROM
        msg["To"]            = to_email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[Email] SMTP failed: {e}")
        return False


def _save_notification(employee_id: str, title: str, message: str, channel: str = "in_app"):
    """Write notification to database."""
    db = SessionLocal()
    try:
        db.add(Notification(
            employee_id = employee_id,
            title       = title,
            message     = message,
            channel     = channel,
            is_read     = False,
        ))
        db.commit()
    except Exception as e:
        print(f"[Email] DB notification failed: {e}")
    finally:
        db.close()


@tool
def send_employee_notification(
    employee_id: str,
    subject: str,
    message: str,
) -> str:
    """
    Send a notification to an employee via in-app notification and email.
    Looks up the employee's email from the database automatically.
    """
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            return json.dumps({"success": False, "message": f"Employee {employee_id} not found."})
        email_sent = _send_smtp(emp.email, subject, message) if emp.email else False
    finally:
        db.close()

    _save_notification(employee_id, subject, message, "email" if email_sent else "in_app")
    print(f"[Email] Notified {employee_id}: {subject[:50]}")
    return json.dumps({"success": True, "email_sent": email_sent, "in_app": True})


@tool
def send_hr_manager_alert(subject: str, message: str) -> str:
    """
    Send an urgent notification to ALL HR Managers and Admins.
    Used by Detection Agent and Leave Agent for escalation.
    """
    db = SessionLocal()
    try:
        from models.database import Employee
        managers = db.query(Employee).filter(
            Employee.access_level >= 3,
            Employee.is_active    == True,
        ).all()
        count = 0
        for mgr in managers:
            if mgr.email:
                _send_smtp(mgr.email, f"[HR ALERT] {subject}", message)
            _save_notification(mgr.id, subject, message, "in_app")
            count += 1
    finally:
        db.close()

    print(f"[Email] HR Alert sent to {count} managers: {subject[:50]}")
    return json.dumps({"success": True, "notified_managers": count})
