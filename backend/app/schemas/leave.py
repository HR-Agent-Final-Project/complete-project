"""
Pydantic v2 schemas for Leave Management endpoints.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


# ── Request schemas
class LeaveApplyRequest(BaseModel):
    leave_type_id: int
    start_date:    str           # ISO: "2026-04-01"
    end_date:      str           # ISO: "2026-04-03"
    reason:        str
    is_half_day:   bool = False

    @field_validator("start_date", "end_date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in ISO format: YYYY-MM-DD")
        return v

    @field_validator("reason")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Reason cannot be blank.")
        return v.strip()


class LeaveApproveRequest(BaseModel):
    note: Optional[str] = None    # Optional HR comment on approval


class LeaveRejectRequest(BaseModel):
    reason: str                   # Required reason for rejection

    @field_validator("reason")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Rejection reason cannot be blank.")
        return v.strip()


class LeaveCancelRequest(BaseModel):
    reason: Optional[str] = None  # Optional reason for cancellation


class LeaveAppealRequest(BaseModel):
    appeal_reason: str            # Why the employee is appealing

    @field_validator("appeal_reason")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Appeal reason cannot be blank.")
        return v.strip()


class LeaveChatRequest(BaseModel):
    question: str                 # Employee's question about leave policy

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Please provide a question.")
        return v.strip()


class LeaveTypeCreateRequest(BaseModel):
    name:                 str
    code:                 str
    max_days_per_year:    int
    description:          Optional[str]  = None
    max_consecutive_days: Optional[int]  = None
    requires_document:    bool           = False
    is_paid:              bool           = True
    gender_specific:      Optional[str]  = None  # "male", "female", or None
    requires_approval:    bool           = False

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()
