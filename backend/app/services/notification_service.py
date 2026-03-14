"""
services/notification_service.py
──────────────────────────────────
Central notification service used by ALL modules.

Usage (from any endpoint or background task):
    from app.services.notification_service import notify, notify_hr_managers

    # Notify one employee
    notify(
        db          = db,
        employee_id = 5,
        ntype       = "leave_approved",
        title       = "Leave Approved",
        message     = "Your annual leave 15–16 Jan has been approved.",
        action_url  = "/leave/requests/42",
        priority    = "normal",
    )

    # Notify all HR managers
    notify_hr_managers(
        db      = db,
        ntype   = "leave_escalated",
        title   = "Leave Review Required",
        message = "John Doe's maternity leave needs your review.",
    )

Flow:
  1. Save Notification row to DB
  2. Push to connected WebSocket (if employee is online)
  3. Send email (if channel = email|both and SMTP is configured)
"""

import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification, NotificationChannel
from app.models.employee import Employee

logger = logging.getLogger(__name__)


# ── WebSocket connection registry ─────────────────────────────────────────────
# Maps employee_id → list of active WebSocket connections
# Lives in memory — cleared on server restart (acceptable for real-time push)
from typing import Dict, List
from fastapi import WebSocket

_ws_connections: Dict[int, List[WebSocket]] = {}


def register_ws(employee_id: int, ws: WebSocket):
    if employee_id not in _ws_connections:
        _ws_connections[employee_id] = []
    _ws_connections[employee_id].append(ws)


def unregister_ws(employee_id: int, ws: WebSocket):
    conns = _ws_connections.get(employee_id, [])
    if ws in conns:
        conns.remove(ws)
    if not conns:
        _ws_connections.pop(employee_id, None)


async def _push_ws(employee_id: int, payload: dict):
    """Push JSON payload to all active WebSocket connections for this employee."""
    conns = list(_ws_connections.get(employee_id, []))
    dead  = []
    for ws in conns:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        unregister_ws(employee_id, ws)


# ── Email helper ──────────────────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send plain-text email via SMTP.
    This is a blocking call — always invoke via starlette BackgroundTasks or
    asyncio.ensure_future so it does not block the event loop.
    Returns True on success.
    """
    if not (settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD):
        return False
    try:
        msg            = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.GMAIL_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.warning("[Email] SMTP failed to %s: %s", to_email, e)
        return False


def _send_email_background(to_email: str, subject: str, body: str) -> None:
    """
    Fire-and-forget email wrapper for use with starlette BackgroundTasks.
    Errors are logged but not re-raised so they never crash the caller.
    """
    _send_email(to_email, subject, body)


# ── Core notify function ──────────────────────────────────────────────────────

def notify(
    db                  : Session,
    employee_id         : int,
    ntype               : str,
    title               : str,
    message             : str,
    action_url          : Optional[str]  = None,
    channel             : str            = "both",
    priority            : str            = "normal",
    related_entity_type : Optional[str]  = None,
    related_entity_id   : Optional[int]  = None,
    extra_data          : Optional[Any]  = None,
) -> Notification:
    """
    Save a notification to the DB, push via WebSocket, and optionally send email.
    Email is dispatched as a background thread so it never blocks the event loop.
    Returns the saved Notification object.
    """
    import asyncio
    import threading

    ch = NotificationChannel.BOTH
    if channel == "in_app":
        ch = NotificationChannel.IN_APP
    elif channel == "email":
        ch = NotificationChannel.EMAIL

    notif = Notification(
        employee_id         = employee_id,
        notification_type   = ntype,
        title               = title,
        message             = message,
        action_url          = action_url,
        channel             = ch,
        priority            = priority,
        related_entity_type = related_entity_type,
        related_entity_id   = related_entity_id,
        extra_data          = extra_data,
        is_read             = False,
        email_sent          = False,
    )
    db.add(notif)
    db.flush()   # get ID without committing

    # ── Email delivery (non-blocking background thread) ───────────────────────
    if channel in ("email", "both"):
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        email_addr = emp.work_email or emp.personal_email if emp else None
        if email_addr:
            # Run SMTP in a daemon thread — does not hold up the response
            t = threading.Thread(
                target=_send_email_background,
                args=(email_addr, title, message),
                daemon=True,
            )
            t.start()
            # Mark as sent optimistically; the background thread logs on failure
            notif.email_sent    = True
            notif.email_sent_at = datetime.utcnow()

    db.commit()
    db.refresh(notif)

    # ── Push via WebSocket (fire-and-forget coroutine) ────────────────────────
    payload = {
        "event":      "notification",
        "id":         notif.id,
        "type":       ntype,
        "title":      title,
        "message":    message,
        "priority":   priority,
        "action_url": action_url,
        "created_at": str(notif.created_at),
    }
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_push_ws(employee_id, payload))
        else:
            loop.run_until_complete(_push_ws(employee_id, payload))
    except Exception:
        pass

    return notif


def notify_many(
    db          : Session,
    employee_ids: list,
    ntype       : str,
    title       : str,
    message     : str,
    **kwargs,
) -> int:
    """Notify multiple employees. Returns count saved."""
    count = 0
    for eid in employee_ids:
        try:
            notify(db, eid, ntype, title, message, **kwargs)
            count += 1
        except Exception as e:
            logger.warning("[Notify] Failed for employee %s: %s", eid, e)
    return count


def notify_hr_managers(
    db      : Session,
    ntype   : str,
    title   : str,
    message : str,
    **kwargs,
) -> int:
    """Notify all active HR Managers (access_level >= 3)."""
    from app.models.role import Role
    managers = db.query(Employee).join(Role, Employee.role_id == Role.id).filter(
        Role.access_level >= 3,
        Employee.is_active == True,
    ).all()
    count = 0
    for mgr in managers:
        try:
            notify(db, mgr.id, ntype, title, message, priority="high", **kwargs)
            count += 1
        except Exception as e:
            logger.warning("[Notify] Failed for manager %s: %s", mgr.id, e)
    return count


def notify_department(
    db            : Session,
    department_id : int,
    ntype         : str,
    title         : str,
    message       : str,
    **kwargs,
) -> int:
    """Notify all active employees in a department."""
    employees = db.query(Employee).filter(
        Employee.department_id == department_id,
        Employee.is_active     == True,
    ).all()
    count = 0
    for emp in employees:
        try:
            notify(db, emp.id, ntype, title, message, **kwargs)
            count += 1
        except Exception as e:
            logger.warning("[Notify] Failed for employee %s: %s", emp.id, e)
    return count
