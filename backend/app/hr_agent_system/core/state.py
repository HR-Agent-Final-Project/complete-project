"""
core/state.py
─────────────
HRSystemState — the single shared TypedDict that ALL 8 agents read and write.

Think of it as a shared whiteboard:
  Supervisor writes:   intent = "leave_request"
  Leave Agent reads:   intent → knows what to do
  Leave Agent writes:  decision = "APPROVED"
  API reads:           decision → sends response to user

KEY CONCEPT — Reducers:
  Normal field:   new value REPLACES old value
  add_messages:   new messages APPEND to list (never replace)
  operator.add:   new audit entries APPEND to list (accumulate full trace)
"""

from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph.message import add_messages
import operator


class HRSystemState(TypedDict):
    # ── Identity ──────────────────────────────────────────────────────────────
    employee_id:   Optional[str]             # "EMP005"
    employee_data: Optional[Dict[str, Any]]  # full employee DB record
    user_role:     Optional[str]             # "employee" | "hr_manager" | "admin"

    # ── Conversation ──────────────────────────────────────────────────────────
    # add_messages reducer: APPENDS new messages — never overwrites history
    messages:   Annotated[List, add_messages]
    user_input: Optional[str]               # raw user text

    # ── Routing (set by supervisor) ───────────────────────────────────────────
    intent:        Optional[str]            # classified intent
    current_agent: Optional[str]            # which agent is active

    # ── Task (agent-specific input) ───────────────────────────────────────────
    task_type: Optional[str]
    task_data: Optional[Dict[str, Any]]     # leave dates, image, period, etc.

    # ── Results (set by agents) ───────────────────────────────────────────────
    agent_response:       Optional[str]     # final text to show user
    decision:             Optional[str]     # APPROVED / REJECTED / ESCALATED
    decision_explanation: Optional[str]
    structured_output:    Optional[Dict[str, Any]]  # typed agent output data

    # ── Control Flags ─────────────────────────────────────────────────────────
    requires_human_review: bool             # pause graph, wait for HR input
    is_complete:           bool
    error:                 Optional[str]

    # ── Audit Trail ───────────────────────────────────────────────────────────
    # operator.add reducer: each agent APPENDS its steps — full trace preserved
    audit_trail: Annotated[List[Dict[str, Any]], operator.add]


def blank_state(
    employee_id: str    = None,
    user_input:  str    = None,
    role:        str    = "employee",
    task_data:   dict   = None,
    intent:      str    = None,
) -> HRSystemState:
    """Helper: returns a clean initial state dict."""
    return {
        "employee_id":          employee_id,
        "employee_data":        None,
        "user_role":            role,
        "messages":             [],
        "user_input":           user_input,
        "intent":               intent,
        "current_agent":        None,
        "task_type":            None,
        "task_data":            task_data or {},
        "agent_response":       None,
        "decision":             None,
        "decision_explanation": None,
        "structured_output":    None,
        "requires_human_review": False,
        "is_complete":          False,
        "error":                None,
        "audit_trail":          [],
    }
