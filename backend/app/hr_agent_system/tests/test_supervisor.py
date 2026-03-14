"""tests/test_supervisor.py — Supervisor intent classification tests"""
import pytest
from unittest.mock import patch, MagicMock
from core.state import blank_state
from core.supervisor import route_to_agent

# ── Route function tests (no LLM needed) ─────────────────────────────────────

def test_route_leave():
    state = blank_state(intent="leave_request")
    assert route_to_agent(state) == "leave_agent"


def test_route_attendance():
    state = blank_state(intent="attendance")
    assert route_to_agent(state) == "attendance_agent"

def test_route_performance():
    state = blank_state(intent="performance_review")
    assert route_to_agent(state) == "performance_agent"

def test_route_chat():
    state = blank_state(intent="hr_chat")
    assert route_to_agent(state) == "hr_chat_agent"

def test_route_security():
    state = blank_state(intent="security_alert")
    assert route_to_agent(state) == "detection_agent"

def test_route_report():
    state = blank_state(intent="analytics_report")
    assert route_to_agent(state) == "reporting_agent"

def test_route_unknown_defaults_to_chat():
    state = blank_state(intent="something_unknown")
    assert route_to_agent(state) == "hr_chat_agent"

def test_route_none_defaults_to_chat():
    state = blank_state()
    assert route_to_agent(state) == "hr_chat_agent"

# Run: pytest tests/test_supervisor.py -v
