"""
agents/attendance_agent.py
───────────────────────────
Agent 4 — Attendance & Face Recognition Agent

Sequential 7-node workflow for tablet-based face clock-in/out.

Node flow:
  capture_face_frame      (receive + decode base64 image)
       ↓
  liveness_detection      (anti-spoofing via DeepFace)
       ↓
  identify_employee       (face match against stored embeddings)
       ↓
  verify_registration     (confirm employee is registered & active)
       ↓
  record_attendance       (write timestamp + confidence to DB)
       ↓
  detect_anomaly          (unusual time, duplicate, patterns)
       ↓
  trigger_alert_if_needed (route to detection_agent if anomaly HIGH)
       ↓
  END
"""

import json
from typing import Dict, Any, Literal
from datetime import datetime, date

from langgraph.graph import StateGraph, END

from core.state import HRSystemState
from models.schemas import AttendanceResult
from models.database import SessionLocal, Attendance, SecurityAlert, AlertSeverity
from tools.face_recognition_tools import check_liveness, match_employee_face, identify_unknown_face
from tools.email_tools import send_hr_manager_alert
from config.settings import settings


# ── NODE 1: Capture Face Frame ────────────────────────────────────────────────

def node_capture_face(state: HRSystemState) -> Dict[str, Any]:
    task_data = state.get("task_data") or {}
    image     = task_data.get("image_base64", "")
    if not image:
        return {"error": "No image provided.", "is_complete": True}
    print(f"  [Att 1/7] Image received ({len(image)} chars b64)")
    return {"audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "capture_face"}]}


# ── NODE 2: Liveness Detection ────────────────────────────────────────────────

def node_liveness(state: HRSystemState) -> Dict[str, Any]:
    task_data = state.get("task_data") or {}
    image     = task_data.get("image_base64", "")
    result    = json.loads(check_liveness.invoke({"image_base64": image}))
    passed    = result.get("passed", False)
    score     = result.get("score", 0.0)
    print(f"  [Att 2/7] Liveness: {'PASS' if passed else 'FAIL'} score={score:.2f}")
    if not passed:
        return {
            "agent_response": "Liveness check failed. Please present your face directly to the camera.",
            "is_complete":    True,
            "audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                              "node": "liveness", "result": "FAILED"}],
        }
    return {
        "task_data":   {**task_data, "liveness_score": score},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "liveness", "result": "PASSED"}],
    }


# ── NODE 3: Identify Employee ─────────────────────────────────────────────────

def node_identify(state: HRSystemState) -> Dict[str, Any]:
    task_data = state.get("task_data") or {}
    image     = task_data.get("image_base64", "")
    emp_id    = state.get("employee_id") or task_data.get("employee_id", "")

    if emp_id:
        # Verification mode: employee claimed their ID (e.g., tapped card)
        result     = json.loads(match_employee_face.invoke({"image_base64": image, "employee_id": emp_id}))
        matched    = result.get("matched", False)
        confidence = result.get("confidence", 0.0)
    else:
        # Identification mode: scan all registered faces
        result     = json.loads(identify_unknown_face.invoke({"image_base64": image}))
        matched    = result.get("identified", False)
        emp_id     = result.get("employee_id")
        confidence = result.get("confidence", 0.0)

    print(f"  [Att 3/7] Face match: {'✅' if matched else '❌'} confidence={confidence:.2f}")

    if not matched or confidence < settings.FACE_CONFIDENCE_THRESHOLD:
        return {
            "agent_response": "Face not recognized. Please try again or use manual check-in.",
            "is_complete":    True,
            "audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                              "node": "identify", "result": "NO_MATCH"}],
        }
    return {
        "employee_id": emp_id,
        "task_data":   {**task_data, "face_confidence": confidence},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                          "node": "identify", "employee_id": emp_id, "confidence": confidence}],
    }


# ── NODE 4: Verify Registration ───────────────────────────────────────────────

def node_verify_registration(state: HRSystemState) -> Dict[str, Any]:
    emp_id = state.get("employee_id", "")
    db     = SessionLocal()
    try:
        from models.database import Employee
        emp = db.query(Employee).filter(Employee.id == emp_id, Employee.is_active == True).first()
        if not emp:
            return {
                "agent_response": f"Employee {emp_id} not found or inactive. Contact HR.",
                "is_complete":    True,
            }
        print(f"  [Att 4/7] Verified: {emp.full_name}")
        task = state.get("task_data") or {}
        return {
            "employee_data": {"id": emp.id, "name": emp.full_name, "dept": emp.department_id},
            "task_data":     {**task, "employee_name": emp.full_name},
            "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "verify_reg"}],
        }
    finally:
        db.close()


# ── NODE 5: Record Attendance ─────────────────────────────────────────────────

def node_record_attendance(state: HRSystemState) -> Dict[str, Any]:
    now       = datetime.now()
    emp_id    = state.get("employee_id", "")
    task_data = state.get("task_data") or {}
    action    = task_data.get("action", "clock_in")
    conf      = task_data.get("face_confidence", 0.0)

    # Late detection
    work_start  = now.replace(hour=settings.WORK_START_HOUR,
                               minute=settings.WORK_START_MINUTE, second=0)
    grace_end   = now.replace(hour=settings.WORK_START_HOUR,
                               minute=settings.WORK_START_MINUTE + settings.GRACE_PERIOD_MINUTES, second=0)
    is_late     = action == "clock_in" and now > grace_end
    late_min    = max(0, int((now - work_start).total_seconds() / 60)) if is_late else 0

    db = SessionLocal()
    try:
        if action == "clock_in":
            record = Attendance(
                employee_id      = emp_id,
                work_date        = now.date(),
                clock_in         = now,
                confidence_score = conf,
                is_late          = is_late,
                late_minutes     = late_min,
                is_absent        = False,
                is_verified      = True,
            )
            db.add(record)
        else:
            # Update existing clock_in record for today
            record = db.query(Attendance).filter(
                Attendance.employee_id == emp_id,
                Attendance.work_date   == now.date(),
            ).first()
            if record:
                record.clock_out  = now
                wh = (now - record.clock_in).total_seconds() / 3600 if record.clock_in else 0
                record.work_hours = round(wh, 2)
            else:
                db.add(Attendance(
                    employee_id  = emp_id,
                    work_date    = now.date(),
                    clock_out    = now,
                    is_absent    = False,
                    is_verified  = True,
                ))
        db.commit()
        print(f"  [Att 5/7] Recorded: {action} {'LATE' if is_late else 'ON TIME'}")
    except Exception as e:
        db.rollback()
        print(f"  [Att 5/7] DB error: {e}")
    finally:
        db.close()

    name = task_data.get("employee_name", emp_id)
    msg  = (
        f"{'⚠️ Late! ' if is_late else ''}Good {'morning' if action == 'clock_in' else 'evening'}, "
        f"{name}! Clocked {'in' if action == 'clock_in' else 'out'} at {now.strftime('%H:%M')}."
    )
    result = AttendanceResult(
        status=f"clocked_{'in' if action=='clock_in' else 'out'}",
        employee_id=emp_id, employee_name=name,
        timestamp=now.isoformat(), confidence=conf,
        is_late=is_late, late_minutes=late_min,
        anomaly_detected=False, message=msg,
    )
    return {
        "structured_output": result.model_dump(),
        "agent_response":    msg,
        "decision":          result.status,
        "task_data": {**task_data, "is_late": is_late, "late_minutes": late_min,
                      "hour": now.hour},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                          "node": "record_attendance", "status": result.status}],
    }


# ── NODE 6: Detect Anomaly ────────────────────────────────────────────────────

def node_detect_anomaly(state: HRSystemState) -> Dict[str, Any]:
    task_data = state.get("task_data") or {}
    hour      = task_data.get("hour", 9)
    anomaly   = hour < 5 or hour > 22
    details   = f"Access at unusual hour: {hour}:00" if anomaly else ""
    if anomaly:
        print(f"  [Att 6/7] ⚠️  Anomaly detected: {details}")
        out = state.get("structured_output") or {}
        out["anomaly_detected"] = True
        out["anomaly_details"]  = details
        return {
            "structured_output": out,
            "task_data": {**task_data, "anomaly": True, "anomaly_details": details},
            "audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                              "node": "detect_anomaly", "anomaly": True}],
        }
    print(f"  [Att 6/7] No anomaly detected")
    return {"audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                              "node": "detect_anomaly", "anomaly": False}]}


# ── NODE 7: Trigger Alert ─────────────────────────────────────────────────────

def node_trigger_alert(state: HRSystemState) -> Dict[str, Any]:
    task_data = state.get("task_data") or {}
    if task_data.get("anomaly"):
        details = task_data.get("anomaly_details", "Unusual activity")
        emp_id  = state.get("employee_id", "")
        db      = SessionLocal()
        try:
            db.add(SecurityAlert(
                alert_type  = "unusual_access_time",
                severity    = AlertSeverity.MEDIUM,
                details     = details,
                employee_id = emp_id,
                is_resolved = False,
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        send_hr_manager_alert.invoke({
            "subject": f"⚠️ Attendance Anomaly — {emp_id}",
            "message": f"Anomaly detected for {emp_id}: {details}",
        })
        print(f"  [Att 7/7] Alert triggered → HR notified")
    else:
        print(f"  [Att 7/7] No alert needed")
    return {
        "is_complete": True,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "trigger_alert"}],
    }


# ── SUB-GRAPH ─────────────────────────────────────────────────────────────────

def build_attendance_subgraph():
    g = StateGraph(HRSystemState)
    g.add_node("capture_face",      node_capture_face)
    g.add_node("liveness",          node_liveness)
    g.add_node("identify",          node_identify)
    g.add_node("verify_reg",        node_verify_registration)
    g.add_node("record_attendance", node_record_attendance)
    g.add_node("detect_anomaly",    node_detect_anomaly)
    g.add_node("trigger_alert",     node_trigger_alert)

    g.set_entry_point("capture_face")
    g.add_edge("capture_face",      "liveness")
    g.add_edge("liveness",          "identify")
    g.add_edge("identify",          "verify_reg")
    g.add_edge("verify_reg",        "record_attendance")
    g.add_edge("record_attendance", "detect_anomaly")
    g.add_edge("detect_anomaly",    "trigger_alert")
    g.add_edge("trigger_alert",     END)
    return g.compile()
