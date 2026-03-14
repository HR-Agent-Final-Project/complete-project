"""tests/test_leave_agent.py — Leave agent node-level tests"""
import pytest
from unittest.mock import patch, MagicMock
import json
from core.state import blank_state


def make_leave_state(days=3, balance=10, att_pct=92.3, decision_override=None):
    state = blank_state(
        employee_id = "EMP_TEST",
        user_input  = f"Apply {days} days annual leave",
        intent      = "leave_request",
        task_data   = {
            "leave_type":      "Annual Leave",
            "leave_type_id":   1,
            "leave_type_code": "AL",
            "start_date":      "2026-04-01",
            "end_date":        "2026-04-03",
            "days":            days,
            "reason":          "Family vacation",
        },
    )
    state["employee_data"]   = {"id": "EMP_TEST", "name": "Test User",
                                 "department": "IT", "is_probation": False}
    state["task_data"]["leave_balance"]    = {"remaining_days": balance, "total_days": 14}
    state["task_data"]["attendance_stats"] = {"attendance_percent": att_pct, "late_days": 0}
    state["task_data"]["policy_text"]      = "AL: 14 days/year, 3 days notice, 85% attendance required."
    if decision_override:
        state["decision"] = decision_override
    return state


# ── Node 7: update_database (mock DB) ────────────────────────────────────────
def test_update_db_node():
    from agents.leave_agent import node_update_db
    state = make_leave_state(decision_override="APPROVED")
    with patch("agents.leave_agent.SessionLocal") as mock_session:
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        result = node_update_db(state)
        assert "audit_trail" in result


# ── Router: routing logic ─────────────────────────────────────────────────────
def test_route_approved_skips_human_review():
    from agents.leave_agent import route_after_decision
    state = make_leave_state()
    state["decision"]             = "APPROVED"
    state["requires_human_review"] = False
    assert route_after_decision(state) == "update_database"

def test_route_escalated_goes_to_human_review():
    from agents.leave_agent import route_after_decision
    state = make_leave_state()
    state["decision"]             = "ESCALATED"
    state["requires_human_review"] = True
    assert route_after_decision(state) == "human_review_checkpoint"

# Run: pytest tests/test_leave_agent.py -v
