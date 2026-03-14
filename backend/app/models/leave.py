"""
Leave models — 3 tables:

  1. LeaveType     → defines what kinds of leave exist (annual, sick, etc.)
  2. LeaveBalance  → tracks how many days each employee has remaining
  3. LeaveRequest  → each individual leave application by an employee

The AI agent reads LeaveRequest + LeaveBalance + HRPolicy
then makes an approval/rejection decision with an explanation.

ai_decision_reason is the natural language explanation the AI generates,
e.g. "Request approved. Employee has 5 annual leave days remaining.
      Attendance score of 92% exceeds the 85% threshold."
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    ForeignKey, Date, DateTime, Numeric, Enum, Float, JSON
)
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


# 1. Leave Type


class LeaveType(Base, TimestampMixin):
    __tablename__ = "leave_types"

    id                      = Column(Integer, primary_key=True, index=True)
    name                    = Column(String(100), unique=True, nullable=False)
                              # e.g. "Annual Leave", "Sick Leave", "Maternity Leave"
    code                    = Column(String(20), unique=True, nullable=False)
                              # e.g. "AL", "SL", "ML"
    description             = Column(Text, nullable=True)
    max_days_per_year       = Column(Integer, nullable=False)
                              # Total days allowed per year
    max_consecutive_days    = Column(Integer, nullable=True)
                              # Max days in a single request (null = no limit)
    requires_document       = Column(Boolean, default=False)
                              # True = medical cert required (e.g. sick leave > 3 days)
    is_paid                 = Column(Boolean, default=True)
                              # False = unpaid leave type
    gender_specific         = Column(String(10), nullable=True)
                              # "female" for maternity, None for all
    is_active               = Column(Boolean, default=True)

    leave_balances = relationship("LeaveBalance", back_populates="leave_type")
    leave_requests = relationship("LeaveRequest", back_populates="leave_type")

    def __repr__(self):
        return f"<LeaveType {self.code}: {self.name} ({self.max_days_per_year} days/yr)>"



# 2. Leave Balance  (one row per employee per leave type per year)


class LeaveBalance(Base, TimestampMixin):
    __tablename__ = "leave_balances"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id   = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    year            = Column(Integer, nullable=False)
                      # e.g. 2025 or 2026

    total_days      = Column(Float, nullable=False)
                      # Days allocated this year (e.g. 14.0)
    used_days       = Column(Float, default=0.0, nullable=False)
                      # Days already taken
    pending_days    = Column(Float, default=0.0, nullable=False)
                      # Days in pending approval requests
    remaining_days  = Column(Float, nullable=False)
                      # = total_days - used_days - pending_days
    carried_over    = Column(Float, default=0.0, nullable=False)
                      # Days carried over from previous year

    employee   = relationship("Employee", back_populates="leave_balances")
    leave_type = relationship("LeaveType", back_populates="leave_balances")

    def __repr__(self):
        return f"<LeaveBalance emp={self.employee_id} type={self.leave_type_id} remaining={self.remaining_days}>"



# 3. Leave Request

class LeaveStatus(str, enum.Enum):
    PENDING   = "pending"    # Just submitted, AI is evaluating
    APPROVED  = "approved"   # AI or HR approved
    REJECTED  = "rejected"   # AI or HR rejected
    ESCALATED = "escalated"  # AI escalated to HR Manager for manual review
    CANCELLED = "cancelled"  # Employee cancelled before decision
    ON_LEAVE  = "on_leave"   # Currently on this leave
    COMPLETED = "completed"  # Leave period is over


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"

    id               = Column(Integer, primary_key=True, index=True)

    # ── Core Fields
    employee_id      = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id    = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date       = Column(Date, nullable=False)
    end_date         = Column(Date, nullable=False)
    total_days       = Column(Float, nullable=False)
                       # Calculated: working days between start and end
    days_requested   = Column(Float, nullable=True)
                       # Alias column — same as total_days, used by API layer
    reason           = Column(Text, nullable=False)
                       # Employee's reason for the leave
    is_half_day      = Column(Boolean, default=False, nullable=False)

    # ── Status
    status           = Column(
                           Enum(LeaveStatus),
                           default=LeaveStatus.PENDING,
                           nullable=False,
                           index=True
                       )

    # ── AI Decision Fields
    # This is where LangGraph writes its decision
    ai_decision      = Column(String(20), nullable=True)
                       # "approved" or "rejected"
    ai_decision_reason = Column(Text, nullable=True)
                       # Natural language explanation from the LLM
                       # e.g. "Approved. You have 5 annual leave days remaining.
                       #        Your attendance score of 92% meets the 85% threshold."
    ai_confidence    = Column(Float, nullable=True)
                       # How confident the AI was in its decision: 0.0 to 1.0
    ai_policy_refs   = Column(JSON, nullable=True)
                       # Which policy chunks were used in the decision
                       # e.g. ["Section 4.2 Annual Leave", "Section 6.1 Eligibility"]
    ai_processed_at  = Column(Text, nullable=True)
                       # ISO datetime when AI processed this request

    # ── Decision Outcome
    rejection_reason = Column(Text, nullable=True)
                       # Reason for rejection (AI or HR)
    approved_by      = Column(String(200), nullable=True)
                       # Display name of approver: "AI Agent" or "John Smith"
    approved_at      = Column(DateTime, nullable=True)
                       # When the approval/rejection happened

    # ── Human Override
    # If HR overrides the AI decision:
    reviewed_by_id   = Column(Integer, ForeignKey("employees.id"), nullable=True)
    hr_override      = Column(Boolean, default=False, nullable=False)
    hr_notes         = Column(Text, nullable=True)
    reviewed_at      = Column(Text, nullable=True)

    # ── Supporting Documents
    document_url     = Column(String(500), nullable=True)
                       # S3 URL of medical certificate etc.
    document_verified = Column(Boolean, default=False, nullable=False)

    # ── Appeal
    # Employees can appeal rejected decisions
    is_appealed      = Column(Boolean, default=False, nullable=False)
    appeal_reason    = Column(Text, nullable=True)
    appeal_status    = Column(String(20), nullable=True)
                       # "pending", "upheld", "overturned"

    # ── Relationships
    employee     = relationship("Employee", foreign_keys=[employee_id], back_populates="leave_requests")
    leave_type   = relationship("LeaveType", back_populates="leave_requests")
    reviewed_by  = relationship("Employee", foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f"<LeaveRequest emp={self.employee_id} {self.start_date}→{self.end_date} [{self.status}]>"