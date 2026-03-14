"""
agents/leave_agent.py
──────────────────────
Agent 2 — Leave Management Agent

Architecture: Sequential 9-node LangGraph sub-graph + interrupt for HR review.

Why sequential (not ReAct)?
  We ALWAYS need all 4 data points before deciding.
  A ReAct agent might skip steps. Sequential guarantees completeness.

Node flow:
  fetch_employee_data
       ↓
  check_leave_balance
       ↓
  fetch_attendance_history
       ↓
  retrieve_leave_policy  (RAG)
       ↓
  evaluate_and_decide    (LLM reasons over all gathered data)
       ↓
  ┌────┴──────────────────────────────┐
  │ ESCALATED               APPROVED/REJECTED
  ↓                              ↓
human_review_checkpoint    update_database
  ↓                              ↓
update_database            send_notification
       ↓                         ↓
  send_notification             END
       ↓
      END

INTERRUPT: graph pauses at human_review_checkpoint
           HR Manager reviews and resumes via API.
"""

from typing import Dict, Any, Literal
from datetime import date, datetime

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from core.state import HRSystemState
from models.schemas import LeaveDecision
from models.database import (
    SessionLocal, LeaveRequest, LeaveBalance, LeaveStatus, Notification
)
from tools.database_tools import (
    get_employee_profile, get_leave_balance,
    get_attendance_stats, get_leave_history, check_leave_overlap,
)
from tools.rag_tools import get_leave_type_policy
from tools.email_tools import send_employee_notification, send_hr_manager_alert
from config.settings import settings


def _llm():
    return ChatOpenAI(model=settings.LLM_MODEL, temperature=0.0,
                      api_key=settings.OPENAI_API_KEY)


# ── EVALUATOR PROMPT ──────────────────────────────────────────────────────────

LEAVE_EVALUATOR_PROMPT = """
You are a senior HR Leave Evaluator for a company in Sri Lanka.
Evaluate the leave request below using ALL the data provided.

Reason carefully through each factor:
1. Does the employee have enough leave balance?
2. Is their attendance rate acceptable (above 85% threshold)?
3. Does the request comply with the HR policy (notice period, probation, etc.)?
4. Are there any scheduling conflicts?
5. Is the reason legitimate and reasonable?
6. Are there any special circumstances that need HR judgment?

Guidelines (not hard rules — use judgment):
  - Straightforward requests (sufficient balance, good attendance, AL/SL/CL) → APPROVED
  - ML, PL, NPL always require HR judgment → ESCALATED
  - Insufficient balance, overlap, or policy violation → REJECTED
  - Borderline cases → ESCALATED with clear note for HR Manager

Always reference actual numbers in your reasoning.
Be fair, consistent, and considerate.
"""


# ── NODE 1: Fetch Employee ────────────────────────────────────────────────────

def node_fetch_employee(state: HRSystemState) -> Dict[str, Any]:
    emp_id = state.get("employee_id", "")
    result = get_employee_profile.invoke({"employee_id": emp_id})
    import json
    data   = json.loads(result)
    print(f"  [Leave 1/9] Employee: {data.get('name', emp_id)}")
    return {
        "employee_data": data,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                          "node": "fetch_employee", "employee": emp_id}],
    }


# ── NODE 2: Check Leave Balance ───────────────────────────────────────────────

def node_check_balance(state: HRSystemState) -> Dict[str, Any]:
    emp_id       = state.get("employee_id", "")
    task_data    = state.get("task_data") or {}
    leave_type_id = task_data.get("leave_type_id", 1)
    result = get_leave_balance.invoke({"employee_id": emp_id, "leave_type_id": leave_type_id})
    import json
    data = json.loads(result)
    print(f"  [Leave 2/9] Balance: {data.get('remaining_days', '?')} days remaining")
    existing = state.get("task_data") or {}
    return {
        "task_data":   {**existing, "leave_balance": data},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "check_balance"}],
    }


# ── NODE 3: Attendance History ────────────────────────────────────────────────

def node_attendance_history(state: HRSystemState) -> Dict[str, Any]:
    emp_id = state.get("employee_id", "")
    result = get_attendance_stats.invoke({"employee_id": emp_id, "days": 90})
    import json
    data   = json.loads(result)
    pct    = data.get("attendance_percent", 100)
    print(f"  [Leave 3/9] Attendance: {pct}%")
    existing = state.get("task_data") or {}
    return {
        "task_data":   {**existing, "attendance_stats": data},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "attendance_history",
                          "attendance_pct": pct}],
    }


# ── NODE 4: Retrieve Policy ───────────────────────────────────────────────────

def node_retrieve_policy(state: HRSystemState) -> Dict[str, Any]:
    task_data  = state.get("task_data") or {}
    leave_code = task_data.get("leave_type_code", task_data.get("leave_type", "AL"))
    result     = get_leave_type_policy.invoke({"leave_type_code": leave_code})
    import json
    data = json.loads(result)
    policy_text = data.get("policy_text", "Policy not found.")
    print(f"  [Leave 4/9] Policy retrieved for '{leave_code}' ({len(policy_text)} chars)")
    existing = state.get("task_data") or {}
    return {
        "task_data":   {**existing, "policy_text": policy_text},
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(), "node": "retrieve_policy"}],
    }


# ── NODE 5: Evaluate & Decide ─────────────────────────────────────────────────

def node_evaluate_and_decide(state: HRSystemState) -> Dict[str, Any]:
    """
    THE AI BRAIN — LLM reads all gathered data and fills LeaveDecision schema.
    No if-else. No hardcoded rules. Pure LLM reasoning over real data.
    """
    llm          = _llm()
    decision_llm = llm.with_structured_output(LeaveDecision, method="function_calling")

    emp        = state.get("employee_data")   or {}
    task_data  = state.get("task_data")       or {}
    balance    = task_data.get("leave_balance", {})
    attendance = task_data.get("attendance_stats", {})
    policy     = task_data.get("policy_text", "No policy available.")

    context = f"""
LEAVE REQUEST:
  Employee:    {emp.get('name', 'Unknown')} ({emp.get('id', '')})
  Department:  {emp.get('department', 'N/A')}
  On Probation: {emp.get('is_probation', False)}
  Leave Type:  {task_data.get('leave_type', 'Annual Leave')} (code: {task_data.get('leave_type_code', 'AL')})
  Days:        {task_data.get('days', 0)} {'(half day)' if task_data.get('is_half_day') else ''}
  From:        {task_data.get('start_date', 'N/A')}
  To:          {task_data.get('end_date', 'N/A')}
  Reason:      "{task_data.get('reason', 'Not provided')}"

LEAVE BALANCE:
  Type:        {balance.get('leave_type', 'N/A')}
  Total:       {balance.get('total_days', 0)} days
  Used:        {balance.get('used_days', 0)} days
  Remaining:   {balance.get('remaining_days', 0)} days

ATTENDANCE (last 90 days):
  Rate:        {attendance.get('attendance_percent', 0)}%
  Present:     {attendance.get('present_days', 0)} / {attendance.get('total_records', 0)} days
  Late days:   {attendance.get('late_days', 0)}

HR POLICY:
{policy}
"""

    result: LeaveDecision = decision_llm.invoke([
        SystemMessage(content=LEAVE_EVALUATOR_PROMPT),
        HumanMessage(content=context),
    ])

    print(f"  [Leave 5/9] Decision: {result.decision} (confidence: {result.confidence:.2f})")

    return {
        "decision":             result.decision,
        "decision_explanation": result.reasoning,
        "agent_response":       result.employee_message,
        "requires_human_review": result.requires_human_review,
        "structured_output": result.model_dump(),
        "audit_trail": [{
            "timestamp":  datetime.utcnow().isoformat(),
            "node":       "evaluate_and_decide",
            "decision":   result.decision,
            "confidence": result.confidence,
        }],
    }


# ── NODE 6: Human Review Checkpoint ──────────────────────────────────────────

def node_human_review(state: HRSystemState) -> Dict[str, Any]:
    """
    Runs AFTER the graph is interrupted and HR provides input.
    The graph pauses BEFORE this node. When HR resumes, this runs.
    """
    print("  [Leave 6/9] HR Manager reviewed — continuing.")
    return {
        "audit_trail": [{
            "timestamp": datetime.utcnow().isoformat(),
            "node":      "human_review_checkpoint",
            "action":    "hr_reviewed",
        }],
    }


# ── NODE 7: Update Database ───────────────────────────────────────────────────

def node_update_db(state: HRSystemState) -> Dict[str, Any]:
    emp_id    = state.get("employee_id", "")
    decision  = state.get("decision", "REJECTED")
    task_data = state.get("task_data") or {}

    db = SessionLocal()
    try:
        status_map = {
            "APPROVED":  LeaveStatus.APPROVED,
            "REJECTED":  LeaveStatus.REJECTED,
            "ESCALATED": LeaveStatus.ESCALATED,
        }
        from datetime import datetime as dt_
        leave = LeaveRequest(
            employee_id        = emp_id,
            leave_type_id      = task_data.get("leave_type_id", 1),
            start_date         = dt_.strptime(task_data.get("start_date", "2026-01-01"), "%Y-%m-%d"),
            end_date           = dt_.strptime(task_data.get("end_date", "2026-01-01"), "%Y-%m-%d"),
            total_days         = task_data.get("days", 1),
            reason             = task_data.get("reason", ""),
            status             = status_map.get(decision, LeaveStatus.PENDING),
            ai_decision        = decision.lower(),
            ai_decision_reason = state.get("decision_explanation", ""),
            ai_processed_at    = dt_.utcnow().isoformat(),
        )
        db.add(leave)

        # Deduct balance if approved
        if decision == "APPROVED":
            balance = db.query(LeaveBalance).filter(
                LeaveBalance.employee_id   == emp_id,
                LeaveBalance.leave_type_id == task_data.get("leave_type_id", 1),
                LeaveBalance.year          == date.today().year,
            ).first()
            if balance:
                days = task_data.get("days", 1)
                balance.used_days      += days
                balance.remaining_days -= days

        db.commit()
        print(f"  [Leave 7/9] DB updated: {decision} for {emp_id}")
    except Exception as e:
        db.rollback()
        print(f"  [Leave 7/9] DB error: {e}")
    finally:
        db.close()

    return {"audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                              "node": "update_database", "decision": decision}]}


# ── NODE 8: Send Notification ─────────────────────────────────────────────────

def node_send_notification(state: HRSystemState) -> Dict[str, Any]:
    emp_id   = state.get("employee_id", "")
    decision = state.get("decision", "")
    message  = state.get("agent_response", "Your leave request has been processed.")
    icons    = {"APPROVED": "✅", "REJECTED": "❌", "ESCALATED": "⏳"}

    send_employee_notification.invoke({
        "employee_id": emp_id,
        "subject":     f"{icons.get(decision, '📢')} Leave Request Update",
        "message":     message,
    })

    # Notify HR if escalated
    if decision == "ESCALATED":
        output = (state.get("structured_output") or {})
        send_hr_manager_alert.invoke({
            "subject": f"Leave Review Required — {emp_id}",
            "message": output.get("hr_manager_note", message),
        })

    print(f"  [Leave 8/9] Notification sent: {decision}")
    return {
        "is_complete": True,
        "audit_trail": [{"timestamp": datetime.utcnow().isoformat(),
                          "node": "send_notification", "notified": emp_id}],
    }


# ── ROUTER ─────────────────────────────────────────────────────────────────────

def route_after_decision(state: HRSystemState) -> Literal["human_review_checkpoint", "update_database"]:
    if state.get("requires_human_review"):
        return "human_review_checkpoint"
    return "update_database"


# ── SUB-GRAPH ─────────────────────────────────────────────────────────────────

def build_leave_subgraph():
    g = StateGraph(HRSystemState)

    g.add_node("fetch_employee",           node_fetch_employee)
    g.add_node("check_leave_balance",      node_check_balance)
    g.add_node("fetch_attendance_history", node_attendance_history)
    g.add_node("retrieve_leave_policy",    node_retrieve_policy)
    g.add_node("evaluate_and_decide",      node_evaluate_and_decide)
    g.add_node("human_review_checkpoint",  node_human_review)
    g.add_node("update_database",          node_update_db)
    g.add_node("send_notification",        node_send_notification)

    g.set_entry_point("fetch_employee")
    g.add_edge("fetch_employee",           "check_leave_balance")
    g.add_edge("check_leave_balance",      "fetch_attendance_history")
    g.add_edge("fetch_attendance_history", "retrieve_leave_policy")
    g.add_edge("retrieve_leave_policy",    "evaluate_and_decide")

    g.add_conditional_edges("evaluate_and_decide", route_after_decision, {
        "human_review_checkpoint": "human_review_checkpoint",
        "update_database":         "update_database",
    })
    g.add_edge("human_review_checkpoint", "update_database")
    g.add_edge("update_database",         "send_notification")
    g.add_edge("send_notification",       END)

    memory = MemorySaver()
    return g.compile(checkpointer=memory, interrupt_before=["human_review_checkpoint"])
