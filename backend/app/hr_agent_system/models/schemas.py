"""
models/schemas.py
─────────────────
Pydantic v2 schemas used as:
  - FastAPI request/response bodies
  - Structured output targets for LLM (with_structured_output)
  - Agent decision schemas
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ── Shared helpers ────────────────────────────────────────────────────────────

class BaseResponse(BaseModel):
    success: bool = True
    message: str  = "OK"


# ── Intent Classification (Supervisor) ───────────────────────────────────────

class IntentClassification(BaseModel):
    """LLM fills this when classifying user intent. No string parsing needed."""
    intent: Literal[
        "hr_chat", "leave_request", "attendance",
        "performance_review", "recruitment", "security_alert", "analytics_report"
    ] = Field(description="Classified intent of the request.")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning:  str   = Field(description="One sentence explanation.")
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entities extracted: employee_id, dates, leave_type, period, etc."
    )


# ── Leave Agent ───────────────────────────────────────────────────────────────

class LeaveApplyRequest(BaseModel):
    employee_id:  str
    leave_type:   str   = "Annual Leave"
    leave_type_id: int  = 1
    start_date:   str                    # "2026-04-01"
    end_date:     str                    # "2026-04-03"
    days:         float
    reason:       str
    is_half_day:  bool  = False

class LeaveDecision(BaseModel):
    """LLM structured output for leave evaluation."""
    decision: Literal["APPROVED", "REJECTED", "ESCALATED"]
    reasoning:        str   = Field(description="Step-by-step reasoning with actual data references.")
    employee_message: str   = Field(description="Clear, friendly message for the employee.")
    hr_manager_note:  str   = Field(default="", description="Note for HR if escalated.")
    requires_human_review: bool
    confidence: float = Field(ge=0.0, le=1.0)

class LeaveResponse(BaseResponse):
    decision:    str
    explanation: str
    message:     str
    needs_review: bool = False


# ── Attendance Agent ──────────────────────────────────────────────────────────

class AttendanceCheckInRequest(BaseModel):
    employee_id:  str
    action:       Literal["clock_in", "clock_out"] = "clock_in"
    image_base64: str = Field(description="Base64-encoded face image from tablet.")

class AttendanceResult(BaseModel):
    """Structured output for attendance recording."""
    status:           str
    employee_id:      str
    employee_name:    str  = ""
    timestamp:        str
    confidence:       float
    is_late:          bool
    late_minutes:     int
    anomaly_detected: bool
    anomaly_details:  str  = ""
    message:          str



# ── Performance Agent ─────────────────────────────────────────────────────────

class PerformanceOutput(BaseModel):
    employee_id:       str
    period:            str
    attendance_score:  float
    punctuality_score: float
    overtime_score:    float
    overall_score:     float
    rating:            str
    narrative:         str
    flags:             List[str] = []


# ── Detection Agent ───────────────────────────────────────────────────────────

class SecurityAlertOutput(BaseModel):
    """LLM structured output for security classification."""
    severity:     Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    alert_type:   str
    details:      str
    action_taken: str
    requires_immediate_response: bool

class DetectionRequest(BaseModel):
    image_base64: str
    location:     str = "main_entrance"
    timestamp:    str = ""


# ── Recruitment Agent ─────────────────────────────────────────────────────────

class RecruitmentRequest(BaseModel):
    candidate_name: str
    position:       str
    resume_text:    str
    job_id:         str  = ""

class CandidateEvaluation(BaseModel):
    candidate_name:      str
    position:            str
    technical_score:     float
    cultural_fit_score:  float
    overall_score:       float
    recommendation:      Literal["SHORTLIST", "REJECT", "HOLD"]
    interview_questions: List[str] = []
    evaluation_notes:    str


# ── Reporting Agent ───────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    report_type:  str  = "monthly_summary"   # monthly_summary | attendance | compliance
    period:       str  = ""                  # "2026-03"
    department:   str  = ""                  # filter by dept, empty = all
    generated_by: str  = "hr_manager"

class ReportOutput(BaseModel):
    report_type:   str
    period:        str
    title:         str
    kpis:          Dict[str, Any] = {}
    trends:        List[str]      = []
    narrative:     str
    data:          Dict[str, Any] = {}


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    employee_id: str
    user_role:   str  = "employee"
    message:     str
    session_id:  str  = ""

class ChatResponse(BaseResponse):
    response:   str
    agent_used: str  = ""
    sources:    List[str] = []
