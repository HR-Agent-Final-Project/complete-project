"""
Performance models — 2 tables:

  1. PerformanceReview  → periodic review of an employee (quarterly/annual)
  2. PerformanceMetric  → individual measurable scores for each review

How scores are calculated:
  - punctuality_score   : from attendance data (late_days vs total days)
  - attendance_score    : present_days / working_days * 100
  - overtime_score      : based on voluntary overtime contribution
  - overall_score       : weighted average of all metrics

The AI uses overall_score when making leave approval decisions.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    ForeignKey, Numeric, Enum, Float, Date, JSON
)
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ReviewPeriod(str, enum.Enum):
    MONTHLY   = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL    = "annual"
    PROBATION = "probation"    # Special review at end of probation period


class ReviewStatus(str, enum.Enum):
    DRAFT     = "draft"        # Being calculated
    PENDING   = "pending"      # Waiting for manager review
    COMPLETED = "completed"    # Finalized
    DISPUTED  = "disputed"     # Employee challenged results


# 1. Performance Review

class PerformanceReview(Base, TimestampMixin):
    __tablename__ = "performance_reviews"

    id              = Column(Integer, primary_key=True, index=True)

    # ── Who & When
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    reviewer_id     = Column(Integer, ForeignKey("employees.id"), nullable=True)
                      # Can be null if fully AI-generated
    period_type     = Column(Enum(ReviewPeriod), nullable=False)
    period_start    = Column(Date, nullable=False)
    period_end      = Column(Date, nullable=False)

    # ── Scores
    # All scores are 0.0 to 100.0
    attendance_score   = Column(Float, nullable=True)
                         # (present_days / working_days) * 100
    punctuality_score  = Column(Float, nullable=True)
                         # 100 - (late_days / present_days * 100)
    overtime_score     = Column(Float, nullable=True)
                         # Based on voluntary overtime contribution
    overall_score      = Column(Float, nullable=True)
                         # Weighted average — THE main score used by AI

    # ── Rating Label
    rating             = Column(String(50), nullable=True)
                         # "Excellent" / "Good" / "Satisfactory" / "Needs Improvement"

    # ── Content
    strengths          = Column(Text, nullable=True)         # What went well
    areas_to_improve   = Column(Text, nullable=True)         # Where to improve
    goals_next_period  = Column(Text, nullable=True)         # Goals set for next period
    manager_comments   = Column(Text, nullable=True)
    ai_summary         = Column(Text, nullable=True)
                         # AI-generated performance narrative

    # ── Flags
    status             = Column(Enum(ReviewStatus), default=ReviewStatus.DRAFT, nullable=False)
    is_promotion_eligible = Column(Boolean, default=False)
    requires_pip       = Column(Boolean, default=False)
                         # PIP = Performance Improvement Plan (for low performers)
    employee_acknowledged = Column(Boolean, default=False)
                         # True = employee has read and acknowledged this review

    # ── Relationships
    employee  = relationship("Employee", foreign_keys=[employee_id], back_populates="performance_reviews")
    reviewer  = relationship("Employee", foreign_keys=[reviewer_id])
    metrics   = relationship("PerformanceMetric", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PerformanceReview emp={self.employee_id} {self.period_start}→{self.period_end} score={self.overall_score}>"


# 2. Performance Metric (individual data points for a review)

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id          = Column(Integer, primary_key=True, index=True)
    review_id   = Column(Integer, ForeignKey("performance_reviews.id"), nullable=False, index=True)

    metric_name = Column(String(200), nullable=False)
                  # e.g. "Days Present", "Times Late", "Overtime Hours"
    value       = Column(Float, nullable=False)
                  # The raw number
    score       = Column(Float, nullable=True)
                  # The 0-100 score derived from value
    weight      = Column(Float, default=1.0)
                  # How much this metric counts toward overall_score
    note        = Column(Text, nullable=True)

    review = relationship("PerformanceReview", back_populates="metrics")

    def __repr__(self):
        return f"<PerformanceMetric {self.metric_name}: {self.value} → score {self.score}>"