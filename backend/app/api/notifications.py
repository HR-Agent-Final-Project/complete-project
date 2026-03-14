"""
api/notifications.py
─────────────────────
Module 8 — Notifications REST API + WebSocket

REST endpoints (all authenticated via Bearer token):
  GET    /                  → my notifications (paginated, filter unread)
  GET    /unread-count      → badge count for notification bell
  PATCH  /{id}/read         → mark one notification as read
  PATCH  /read-all          → mark ALL my notifications as read
  DELETE /{id}              → delete one notification
  DELETE /clear-all         → delete all my read notifications
  POST   /send              → HR sends to one or more employees
  POST   /broadcast         → HR broadcasts to all employees / one department

WebSocket (real-time push):
  WS /ws?token=<JWT>        → connect to receive notifications in real time

WebSocket message format (server → client):
  {
    "event":      "notification",
    "id":         42,
    "type":       "leave_approved",
    "title":      "Leave Approved",
    "message":    "Your annual leave 15–16 Jan has been approved.",
    "priority":   "normal",
    "action_url": "/leave/requests/42",
    "created_at": "2026-03-13T10:23:00"
  }

  {
    "event": "ping",          // server keepalive (every 30s)
    "ts":    "2026-03-13T..."
  }

  {
    "event": "unread_count",  // sent on connect to update the bell badge
    "count": 5
  }
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException,
    Query, WebSocket, WebSocketDisconnect, status
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_employee, require_role, decode_token
from app.models.employee import Employee
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationOut, SendNotificationRequest, BroadcastRequest,
)
from app.services.notification_service import (
    notify, notify_many, notify_department,
    register_ws, unregister_ws, _push_ws,
)

router = APIRouter()


# ── REST ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[NotificationOut])
def list_notifications(
    unread_only : bool           = Query(False),
    limit       : int            = Query(50, ge=1, le=200),
    offset      : int            = Query(0, ge=0),
    current_user: Employee       = Depends(get_current_employee),
    db          : Session        = Depends(get_db),
):
    """
    List my notifications, newest first.
    Use unread_only=true to fetch only unread ones (for the notification panel).
    """
    q = db.query(Notification).filter(
        Notification.employee_id == current_user.id
    )
    if unread_only:
        q = q.filter(Notification.is_read == False)

    notifications = q.order_by(Notification.id.desc()).offset(offset).limit(limit).all()
    return notifications


@router.get("/unread-count")
def unread_count(
    current_user: Employee = Depends(get_current_employee),
    db          : Session  = Depends(get_db),
):
    """Returns the count for the notification bell badge."""
    count = db.query(Notification).filter(
        Notification.employee_id == current_user.id,
        Notification.is_read     == False,
    ).count()
    return {"unread_count": count}


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user   : Employee = Depends(get_current_employee),
    db             : Session  = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.id          == notification_id,
        Notification.employee_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notif.is_read = True
    notif.read_at = datetime.utcnow().isoformat()
    db.commit()
    return {"message": "Marked as read."}


@router.patch("/read-all")
def mark_all_read(
    current_user: Employee = Depends(get_current_employee),
    db          : Session  = Depends(get_db),
):
    """Mark ALL my unread notifications as read at once."""
    updated = db.query(Notification).filter(
        Notification.employee_id == current_user.id,
        Notification.is_read     == False,
    ).all()
    now = datetime.utcnow().isoformat()
    for n in updated:
        n.is_read = True
        n.read_at = now
    db.commit()
    return {"message": f"Marked {len(updated)} notification(s) as read."}


# NOTE: /clear-all MUST be declared before /{notification_id} so FastAPI does not
# attempt to cast the literal string "clear-all" as an integer path parameter.
@router.delete("/clear-all", status_code=204)
def clear_read_notifications(
    current_user: Employee = Depends(get_current_employee),
    db          : Session  = Depends(get_db),
):
    """Delete all already-read notifications for the current user."""
    db.query(Notification).filter(
        Notification.employee_id == current_user.id,
        Notification.is_read     == True,
    ).delete()
    db.commit()


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: int,
    current_user   : Employee = Depends(get_current_employee),
    db             : Session  = Depends(get_db),
):
    """Delete one notification (employee can only delete their own)."""
    notif = db.query(Notification).filter(
        Notification.id          == notification_id,
        Notification.employee_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    db.delete(notif)
    db.commit()


@router.post("/send", status_code=201)
def send_notification(
    body        : SendNotificationRequest,
    current_user: Employee = Depends(require_role(2)),
    db          : Session  = Depends(get_db),
):
    """
    HR Staff+ manually sends a notification to one or more employees.
    """
    count = notify_many(
        db           = db,
        employee_ids = body.employee_ids,
        ntype        = body.notification_type,
        title        = body.title,
        message      = body.message,
        action_url   = body.action_url,
        channel      = body.channel,
        priority     = body.priority,
    )
    return {
        "message":    f"Sent to {count} employee(s).",
        "sent_count": count,
    }


@router.post("/broadcast", status_code=201)
def broadcast_notification(
    body        : BroadcastRequest,
    current_user: Employee = Depends(require_role(3)),
    db          : Session  = Depends(get_db),
):
    """
    HR Manager+ broadcasts to all employees or a single department.
    """
    if body.department_id:
        count = notify_department(
            db            = db,
            department_id = body.department_id,
            ntype         = body.notification_type,
            title         = body.title,
            message       = body.message,
            action_url    = body.action_url,
            priority      = body.priority,
        )
    else:
        # All active employees
        all_employees = db.query(Employee).filter(
            Employee.is_active == True
        ).all()
        count = notify_many(
            db           = db,
            employee_ids = [e.id for e in all_employees],
            ntype        = body.notification_type,
            title        = body.title,
            message      = body.message,
            action_url   = body.action_url,
            priority     = body.priority,
        )

    return {
        "message":    f"Broadcast sent to {count} employee(s).",
        "sent_count": count,
        "department_id": body.department_id,
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def notifications_ws(
    websocket: WebSocket,
    token    : str = Query(..., description="JWT access token"),
    db       : Session = Depends(get_db),
):
    """
    Real-time notification WebSocket.

    Connect: ws://localhost:8000/api/notifications/ws?token=<JWT>

    On connect:
      1. Validates JWT
      2. Sends current unread count immediately
      3. Keeps connection alive with 30-second pings

    On new notification (triggered by any module via notify()):
      Server pushes JSON to this socket automatically.

    Client can send:
      {"action": "mark_read", "id": 42}   → marks that notification as read
      {"action": "ping"}                   → client keepalive
    """
    # ── Authenticate via token query param ───────────────────────────────────
    try:
        payload     = decode_token(token)
        employee_id = int(payload.get("sub", 0))
        if not employee_id:
            await websocket.close(code=4001)
            return
        emp = db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.is_active == True,
        ).first()
        if not emp:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    register_ws(employee_id, websocket)

    # ── Send unread count immediately on connect ──────────────────────────────
    unread = db.query(Notification).filter(
        Notification.employee_id == employee_id,
        Notification.is_read     == False,
    ).count()
    await websocket.send_json({"event": "unread_count", "count": unread})

    # ── Listen for client messages + send keepalive pings ────────────────────
    ping_task = None
    try:
        async def send_pings():
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({
                        "event": "ping",
                        "ts":    datetime.utcnow().isoformat(),
                    })
                except Exception:
                    break

        ping_task = asyncio.ensure_future(send_pings())

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
            except asyncio.TimeoutError:
                continue

            action = data.get("action")

            if action == "mark_read":
                nid = data.get("id")
                if nid:
                    notif = db.query(Notification).filter(
                        Notification.id          == nid,
                        Notification.employee_id == employee_id,
                    ).first()
                    if notif and not notif.is_read:
                        notif.is_read = True
                        notif.read_at = datetime.utcnow().isoformat()
                        db.commit()
                    new_unread = db.query(Notification).filter(
                        Notification.employee_id == employee_id,
                        Notification.is_read     == False,
                    ).count()
                    await websocket.send_json({
                        "event": "unread_count",
                        "count": new_unread,
                    })

            elif action == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error for emp {employee_id}: {e}")
    finally:
        if ping_task:
            ping_task.cancel()
        unregister_ws(employee_id, websocket)
