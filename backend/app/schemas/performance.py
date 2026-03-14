"""
Pydantic v2 schemas for Performance Tracking endpoints.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum


class ReviewPeriodEnum(str, Enum):
    monthly   = "monthly"
    quarterly = "quarterly"
    annual    = "annual"
    probation = "probation"


# ── Request schemas ────────────────────────────────────────────────────────────

class GenerateReviewRequest(BaseModel):
    period_type: ReviewPeriodEnum = ReviewPeriodEnum.quarterly
    period_start: Optional[str]   = None   # ISO "YYYY-MM-DD" — defaults to quarter start
    period_end:   Optional[str]   = None   # ISO "YYYY-MM-DD" — defaults to today


class ManagerCommentsRequest(BaseModel):
    manager_comments:  str
    strengths:         Optional[str] = None
    areas_to_improve:  Optional[str] = None
    goals_next_period: Optional[str] = None

    @field_validator("manager_comments")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Manager comments cannot be blank.")
        return v.strip()


class DisputeRequest(BaseModel):
    dispute_reason: str

    @field_validator("dispute_reason")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Dispute reason cannot be blank.")
        return v.strip()


class ResolveDisputeRequest(BaseModel):
    resolution:     str
    revised_score:  Optional[float] = None   # HR may revise the score

    @field_validator("resolution")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Resolution cannot be blank.")
        return v.strip()
