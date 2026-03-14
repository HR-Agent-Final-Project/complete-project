"""
agents/detection_agent.py
──────────────────────────
Agent 7 — Illegal Worker / Security Detection Agent

Sequential 7-node workflow:
  scan_attendance_logs → cross_reference_registry → analyze_access_patterns
  → assess_threat_level → generate_alert → notify_management → log_incident
"""

import json
from typing import Dict, Any
from datetime import datetime, date, timedelta

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from core.state import HRSystemState
from models.schemas import SecurityAlertOutput
from models.database import SessionLocal, Attendance, Employee, SecurityAlert, AlertSeverity
from tools.face_recognition_tools import identify_unknown_face
from tools.email_tools import send_hr_manager_alert
from config.settings import settings


def _llm():
    return ChatOpenAI(model=settings.LLM_MODEL, temperature=0.0, api_key=settings.OPENAI_API_KEY)


def node_scan_attendance_logs(state: HRSystemState) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        since   = datetime.now() - timedelta(hours=24)
        anomaly_records = db.query(Attendance).filter(
            Attendance.flagged    == True,
            Attendance.clock_in  >= since,
        ).all()
        anomalies = [
            {"employee_id": r.employee_id, "time": str(r.clock_in), "details": r.flag_reason}
            for r in anomaly_records
        ]
    finally:
        db.close()
    print(f"  [Det 1/7] Scanned logs: {len(anomalies)} anomalies in last 24h")
    task = state.get("task_data") or {}
    return {
        "task_data":   {**task, "anomaly_logs": anomalies},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "scan_logs",
                          "anomaly_count": len(anomalies)}],
    }


def node_cross_reference(state: HRSystemState) -> Dict[str, Any]:
    task_data   = state.get("task_data") or {}
    image       = task_data.get("image_base64", "")
    unregistered = False
    if image:
        result       = json.loads(identify_unknown_face.invoke({"image_base64": image}))
        unregistered = not result.get("is_registered", False)
        print(f"  [Det 2/7] Face check: {'UNREGISTERED' if unregistered else 'REGISTERED'}")
    else:
        print(f"  [Det 2/7] No image — checking log anomalies")
    return {
        "task_data":   {**task_data, "unregistered_face": unregistered},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "cross_reference",
                          "unregistered": unregistered}],
    }


def node_analyze_patterns(state: HRSystemState) -> Dict[str, Any]:
    task_data = state.get("task_data") or {}
    hour      = task_data.get("access_hour", datetime.now().hour)
    anomalies = task_data.get("anomaly_logs", [])
    off_hours = hour < 6 or hour > 21
    repeated  = len(anomalies) >= 3
    print(f"  [Det 3/7] Patterns: off_hours={off_hours}, repeated={repeated}")
    return {
        "task_data": {**task_data, "off_hours_access": off_hours, "repeated_anomalies": repeated,
                      "access_hour": hour},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "analyze_patterns"}],
    }


def node_assess_threat(state: HRSystemState) -> Dict[str, Any]:
    """LLM classifies threat severity using SecurityAlertOutput schema."""
    task_data   = state.get("task_data") or {}
    unregistered = task_data.get("unregistered_face", False)
    off_hours    = task_data.get("off_hours_access", False)
    repeated     = task_data.get("repeated_anomalies", False)
    hour         = task_data.get("access_hour", 9)

    try:
        llm          = _llm()
        decision_llm = llm.with_structured_output(SecurityAlertOutput, method="function_calling")
        result: SecurityAlertOutput = decision_llm.invoke([
            SystemMessage(content="You are a security analyst. Classify the threat level of this event."),
            HumanMessage(content=(
                f"Unregistered face: {unregistered}\n"
                f"Off-hours access:  {off_hours} (hour={hour})\n"
                f"Repeated anomalies: {repeated}\n"
                f"Context: {task_data.get('context', 'Attendance system flag')}"
            )),
        ])
        severity = result.severity
        alert    = result
    except Exception as e:
        severity = ("CRITICAL" if unregistered and off_hours else
                    "HIGH"     if unregistered else
                    "MEDIUM"   if off_hours else "LOW")
        alert = SecurityAlertOutput(
            severity     = severity,
            alert_type   = "access_anomaly",
            details      = f"Unregistered={unregistered}, off_hours={off_hours}",
            action_taken = "Notified management" if severity in ("HIGH","CRITICAL") else "Logged",
            requires_immediate_response = severity in ("HIGH","CRITICAL"),
        )

    print(f"  [Det 4/7] Threat level: {severity}")
    return {
        "task_data":   {**task_data, "threat": alert.model_dump()},
        "decision":    severity,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "assess_threat",
                          "severity": severity}],
    }


def node_generate_alert(state: HRSystemState) -> Dict[str, Any]:
    task  = state.get("task_data") or {}
    threat = task.get("threat", {})
    output = SecurityAlertOutput(**threat) if threat else SecurityAlertOutput(
        severity="LOW", alert_type="unknown", details="", action_taken="Logged",
        requires_immediate_response=False)
    db = SessionLocal()
    try:
        db.add(SecurityAlert(
            alert_type   = output.alert_type,
            severity     = AlertSeverity[output.severity],
            details      = output.details,
            employee_id  = state.get("employee_id"),
            is_resolved  = False,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()
    print(f"  [Det 5/7] Alert saved: {output.severity}")
    return {
        "structured_output": output.model_dump(),
        "agent_response":    f"Security alert ({output.severity}): {output.details}",
        "requires_human_review": output.requires_immediate_response,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "generate_alert"}],
    }


def node_notify_management(state: HRSystemState) -> Dict[str, Any]:
    out = state.get("structured_output") or {}
    if out.get("requires_immediate_response"):
        send_hr_manager_alert.invoke({
            "subject": f"🚨 SECURITY ALERT ({out.get('severity', 'HIGH')})",
            "message": f"Alert Type: {out.get('alert_type')}\nDetails: {out.get('details')}\nAction: {out.get('action_taken')}",
        })
        print(f"  [Det 6/7] Management notified immediately")
    else:
        print(f"  [Det 6/7] Low-severity — logged only")
    return {"audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "notify_management"}]}


def node_log_incident(state: HRSystemState) -> Dict[str, Any]:
    from models.database import AuditLog
    out = state.get("structured_output") or {}
    db  = SessionLocal()
    try:
        db.add(AuditLog(
            agent_name  = "detection_agent",
            action      = f"security_alert_{out.get('severity','').lower()}",
            employee_id = state.get("employee_id"),
            details     = out,
        ))
        db.commit()
        print(f"  [Det 7/7] Incident logged to audit")
    except Exception as e:
        db.rollback()
    finally:
        db.close()
    return {
        "is_complete": True,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "log_incident"}],
    }


def build_detection_subgraph():
    g = StateGraph(HRSystemState)
    nodes = [
        ("scan_attendance_logs", node_scan_attendance_logs),
        ("cross_reference",     node_cross_reference),
        ("analyze_patterns",    node_analyze_patterns),
        ("assess_threat",       node_assess_threat),
        ("generate_alert",      node_generate_alert),
        ("notify_management",   node_notify_management),
        ("log_incident",        node_log_incident),
    ]
    for name, fn in nodes:
        g.add_node(name, fn)
    g.set_entry_point(nodes[0][0])
    for i in range(len(nodes) - 1):
        g.add_edge(nodes[i][0], nodes[i + 1][0])
    g.add_edge(nodes[-1][0], END)
    return g.compile()
