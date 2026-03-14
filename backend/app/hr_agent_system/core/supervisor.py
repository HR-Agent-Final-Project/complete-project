"""
core/supervisor.py
──────────────────
Supervisor Agent — the entry point for every request.

Role: classify user intent → update state → LangGraph routes to correct agent.

The supervisor does NOT answer questions. It ONLY classifies and routes.
All reasoning uses with_structured_output() — no if-else string matching.

Flow:
  User message → supervisor_node → IntentClassification (typed)
      → state["intent"] set → route_to_agent() → correct agent sub-graph
"""

from datetime import datetime
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core.state import HRSystemState
from models.schemas import IntentClassification
from config.settings import settings


# ── LLM ───────────────────────────────────────────────────────────────────────

def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
    )


# ── System Prompt ─────────────────────────────────────────────────────────────

SUPERVISOR_PROMPT = """
You are the routing supervisor for an AI-powered HR management system.
Your ONLY job is to classify the user's request into the correct intent category.

Intent categories and when to use them:
  hr_chat            → general HR questions, policy queries, greetings, anything else
  leave_request      → applying, checking, cancelling, or querying leave
  attendance         → clock in/out, face recognition, attendance records, hours
  performance_review → performance evaluation, KPIs, scores, appraisals
  recruitment        → job applications, CV screening, interviews, hiring
  security_alert     → unregistered persons, access violations, suspicious activity
  analytics_report   → monthly reports, statistics, dashboards, trend analysis

Always extract any useful entities from the message:
  employee_id, dates, leave_type, period, position, department

When in doubt, route to hr_chat.
"""


# ── Supervisor Node ───────────────────────────────────────────────────────────

def supervisor_node(state: HRSystemState) -> Dict[str, Any]:
    """
    LangGraph node function.
    Receives full state → classifies intent → returns only changed fields.

    This is the ONLY node that runs before routing.
    No tools, no loops — pure LLM classification.
    """
    llm        = get_llm(temperature=0.0)
    classifier = llm.with_structured_output(IntentClassification, method="function_calling")

    user_input = state.get("user_input", "")
    emp_id     = state.get("employee_id", "Unknown")
    role       = state.get("user_role", "employee")

    result: IntentClassification = classifier.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=(
            f"Employee ID: {emp_id}\n"
            f"Role:        {role}\n"
            f"Message:     {user_input}"
        )),
    ])

    print(f"[Supervisor] intent='{result.intent}' confidence={result.confidence:.2f}")
    print(f"             reason: {result.reasoning}")

    audit_entry = {
        "timestamp":  datetime.utcnow().isoformat(),
        "agent":      "supervisor",
        "action":     "intent_classified",
        "intent":     result.intent,
        "confidence": result.confidence,
        "reasoning":  result.reasoning,
        "input":      user_input[:100],
    }

    # Merge extracted entities into task_data
    existing_task_data = state.get("task_data") or {}
    merged_task_data   = {**existing_task_data, **result.extracted_entities}

    return {
        "intent":        result.intent,
        "current_agent": result.intent,
        "task_data":     merged_task_data,
        "audit_trail":   [audit_entry],
    }


# ── Router ────────────────────────────────────────────────────────────────────

ROUTING_MAP = {
    "hr_chat":           "hr_chat_agent",
    "leave_request":     "leave_agent",
    "attendance":        "attendance_agent",
    "performance_review":"performance_agent",
    "recruitment":       "recruitment_agent",
    "security_alert":    "detection_agent",
    "analytics_report":  "reporting_agent",
}


def route_to_agent(state: HRSystemState) -> str:
    """
    Pure routing function — no LLM, no logic, just reads intent from state.
    Called by LangGraph add_conditional_edges after supervisor_node.
    Returns the name of the next node to execute.
    """
    intent      = state.get("intent", "hr_chat")
    destination = ROUTING_MAP.get(intent, "hr_chat_agent")
    print(f"[Router] '{intent}' → '{destination}'")
    return destination
