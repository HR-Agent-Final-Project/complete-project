"""tests/test_graph_flow.py — Integration smoke tests"""
import pytest
from unittest.mock import patch, MagicMock
from core.state import blank_state


def test_blank_state_has_required_keys():
    state = blank_state("EMP001", "Hello", "employee")
    required = [
        "employee_id", "user_input", "user_role", "messages",
        "intent", "current_agent", "task_data", "agent_response",
        "decision", "requires_human_review", "is_complete",
        "audit_trail", "structured_output",
    ]
    for key in required:
        assert key in state, f"Missing key: {key}"


def test_blank_state_audit_trail_is_list():
    state = blank_state()
    assert isinstance(state["audit_trail"], list)
    assert len(state["audit_trail"]) == 0


def test_blank_state_flags_default_false():
    state = blank_state()
    assert state["requires_human_review"] is False
    assert state["is_complete"] is False



# Run: pytest tests/ -v
