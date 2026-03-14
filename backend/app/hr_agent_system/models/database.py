"""
models/database.py
──────────────────
SQLAlchemy ORM models that map to the REAL Neon PostgreSQL database.

IMPORTANT: This file reflects the EXISTING Neon schema exactly.
  - employee_id columns are Integer (not String)
  - Table names match what Neon already has
  - Existing tables: employees, attendance, leave_types, leave_balances,
                     leave_requests, performance_reviews, performance_metrics,
                     notifications, audit_logs
  - New AI-only tables created here: security_alerts, hr_reports

DO NOT call init_db() on tables that already exist in Neon.
Use create_new_tables() which only creates the AI-specific new tables.

NOTE: Payroll is an existing Neon table but is NOT mapped here — the AI
system does not access payroll data.
"""

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON, ForeignKey, Date, Numeric,
    Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import enum

from config.settings import settings

# ── Engine & Session ──────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping   = True,
    pool_recycle    = 300,
    pool_size       = 5,
    max_overflow    = 10,
    connect_args    = {"sslmode": "require"},   # Neon requires SSL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False,
                            bind=engine, expire_on_commit=False)
Base = declarative_base()


# ── Enums (must match existing Neon enum types) ───────────────────────────────

class LeaveStatus(str, enum.Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    CANCELLED = "cancelled"
    ON_LEAVE  = "on_leave"
    COMPLETED = "completed"

class AlertSeverity(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"

class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL  = "email"
    BOTH   = "both"


# ── DB Dependency (FastAPI) ───────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING NEON TABLES — reflect exactly, do NOT recreate
# ─────────────────────────────────────────────────────────────────────────────

class Employee(Base):
    """Maps to existing Neon 'employees' table. Read-only for AI agents."""
    __tablename__  = "employees"
    __table_args__ = {"extend_existing": True}

    id               = Column(Integer, primary_key=True, index=True)
    employee_number  = Column(String(20))           # "EMP001"
    first_name       = Column(String(100))
    last_name        = Column(String(100))
    full_name        = Column(String(200))
    personal_email   = Column(String(200))
    work_email       = Column(String(200))
    phone_number     = Column(String(20))
    department_id    = Column(Integer, ForeignKey("departments.id"), nullable=True)
    role_id          = Column(Integer, ForeignKey("roles.id"), nullable=True)
    base_salary      = Column(Numeric(12, 2))
    is_active        = Column(Boolean, default=True)
    status           = Column(String(20), default="probation")
    face_embedding   = Column(JSON, nullable=True)
    face_registered  = Column(Boolean, default=False)
    hire_date        = Column(Date, nullable=True)
    probation_end    = Column(Date, nullable=True)

    # Relationships
    attendance_records   = relationship("Attendance",       back_populates="employee")
    leave_requests       = relationship("LeaveRequest",     back_populates="employee",
                                        foreign_keys="LeaveRequest.employee_id")
    leave_balances       = relationship("LeaveBalance",     back_populates="employee")
    performance_reviews  = relationship("PerformanceReview",back_populates="employee",
                                        foreign_keys="PerformanceReview.employee_id")
    notifications        = relationship("Notification",     back_populates="employee")
    audit_logs           = relationship("AuditLog",         back_populates="employee")


class Attendance(Base):
    """
    Maps to existing Neon 'attendance' table.
    One row per employee per work day. clock_in and clock_out on same row.
    """
    __tablename__  = "attendance"
    __table_args__ = {"extend_existing": True}

    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    work_date           = Column(Date, nullable=False)
    clock_in            = Column(DateTime(timezone=True), nullable=True)
    clock_out           = Column(DateTime(timezone=True), nullable=True)
    work_hours          = Column(Float, nullable=True)
    confidence_score    = Column(Float, nullable=True)
    verification_method = Column(String(30), default="face_recognition")
    is_verified         = Column(Boolean, default=False)
    attendance_type     = Column(String(20), default="regular")
    is_late             = Column(Boolean, default=False)
    late_minutes        = Column(Integer, default=0)
    is_early_departure  = Column(Boolean, default=False)
    overtime_hours      = Column(Float, default=0.0)
    location            = Column(String(200), nullable=True)
    is_absent           = Column(Boolean, default=False)
    absence_reason      = Column(Text, nullable=True)
    notes               = Column(Text, nullable=True)
    flagged             = Column(Boolean, default=False)
    flag_reason         = Column(Text, nullable=True)

    employee = relationship("Employee", back_populates="attendance_records")


class LeaveType(Base):
    """Maps to existing Neon 'leave_types' table."""
    __tablename__  = "leave_types"
    __table_args__ = {"extend_existing": True}

    id                   = Column(Integer, primary_key=True, index=True)
    name                 = Column(String(100), unique=True, nullable=False)
    code                 = Column(String(20), unique=True, nullable=False)
    description          = Column(Text, nullable=True)
    max_days_per_year    = Column(Integer, nullable=False)
    max_consecutive_days = Column(Integer, nullable=True)
    requires_document    = Column(Boolean, default=False)
    is_paid              = Column(Boolean, default=True)
    gender_specific      = Column(String(10), nullable=True)
    is_active            = Column(Boolean, default=True)

    leave_balances = relationship("LeaveBalance", back_populates="leave_type")
    leave_requests = relationship("LeaveRequest", back_populates="leave_type")


class LeaveBalance(Base):
    """Maps to existing Neon 'leave_balances' table."""
    __tablename__  = "leave_balances"
    __table_args__ = {"extend_existing": True}

    id             = Column(Integer, primary_key=True, index=True)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id  = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    year           = Column(Integer, nullable=False)
    total_days     = Column(Float, nullable=False)
    used_days      = Column(Float, default=0.0, nullable=False)
    pending_days   = Column(Float, default=0.0, nullable=False)
    remaining_days = Column(Float, nullable=False)
    carried_over   = Column(Float, default=0.0, nullable=False)

    employee   = relationship("Employee",  back_populates="leave_balances")
    leave_type = relationship("LeaveType", back_populates="leave_balances")


class LeaveRequest(Base):
    """
    Maps to existing Neon 'leave_requests' table.
    AI writes: ai_decision, ai_decision_reason, ai_confidence, ai_processed_at.
    """
    __tablename__  = "leave_requests"
    __table_args__ = {"extend_existing": True}

    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id    = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date       = Column(Date, nullable=False)
    end_date         = Column(Date, nullable=False)
    total_days       = Column(Float, nullable=False)
    reason           = Column(Text, nullable=False)
    status           = Column(String(20), default="pending", nullable=False, index=True)

    # ── AI writes these fields ─────────────────────────────────────────────
    ai_decision        = Column(String(20), nullable=True)   # "approved" / "rejected"
    ai_decision_reason = Column(Text, nullable=True)         # LLM explanation
    ai_confidence      = Column(Float, nullable=True)        # 0.0–1.0
    ai_policy_refs     = Column(JSON, nullable=True)         # policy chunks used
    ai_processed_at    = Column(Text, nullable=True)         # ISO datetime string

    # ── HR override ────────────────────────────────────────────────────────
    reviewed_by_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    hr_override       = Column(Boolean, default=False)
    hr_notes          = Column(Text, nullable=True)
    reviewed_at       = Column(Text, nullable=True)

    employee    = relationship("Employee", foreign_keys=[employee_id], back_populates="leave_requests")
    leave_type  = relationship("LeaveType", back_populates="leave_requests")
    reviewed_by = relationship("Employee", foreign_keys=[reviewed_by_id])


class PerformanceReview(Base):
    """Maps to existing Neon 'performance_reviews' table."""
    __tablename__  = "performance_reviews"
    __table_args__ = {"extend_existing": True}

    id                = Column(Integer, primary_key=True, index=True)
    employee_id       = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    reviewer_id       = Column(Integer, ForeignKey("employees.id"), nullable=True)
    period_type       = Column(String(20), nullable=False)
    period_start      = Column(Date, nullable=False)
    period_end        = Column(Date, nullable=False)
    attendance_score  = Column(Float, nullable=True)
    punctuality_score = Column(Float, nullable=True)
    overtime_score    = Column(Float, nullable=True)
    overall_score     = Column(Float, nullable=True)
    rating            = Column(String(50), nullable=True)
    strengths         = Column(Text, nullable=True)
    areas_to_improve  = Column(Text, nullable=True)
    goals_next_period = Column(Text, nullable=True)
    manager_comments  = Column(Text, nullable=True)
    ai_summary        = Column(Text, nullable=True)   # AI writes here
    status            = Column(String(20), default="draft")
    is_promotion_eligible = Column(Boolean, default=False)
    requires_pip      = Column(Boolean, default=False)

    employee  = relationship("Employee", foreign_keys=[employee_id], back_populates="performance_reviews")
    reviewer  = relationship("Employee", foreign_keys=[reviewer_id])
    metrics   = relationship("PerformanceMetric", back_populates="review", cascade="all, delete-orphan")


class PerformanceMetric(Base):
    """Maps to existing Neon 'performance_metrics' table."""
    __tablename__  = "performance_metrics"
    __table_args__ = {"extend_existing": True}

    id          = Column(Integer, primary_key=True, index=True)
    review_id   = Column(Integer, ForeignKey("performance_reviews.id"), nullable=False, index=True)
    metric_name = Column(String(200), nullable=False)
    value       = Column(Float, nullable=False)
    score       = Column(Float, nullable=True)
    weight      = Column(Float, default=1.0)
    note        = Column(Text, nullable=True)

    review = relationship("PerformanceReview", back_populates="metrics")


class Notification(Base):
    """Maps to existing Neon 'notifications' table."""
    __tablename__  = "notifications"
    __table_args__ = {"extend_existing": True}

    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    notification_type   = Column(String(50), nullable=False, index=True)
    title               = Column(String(300), nullable=False)
    message             = Column(Text, nullable=False)
    action_url          = Column(String(500), nullable=True)
    channel             = Column(String(10), default="both")   # in_app / email / both
    is_read             = Column(Boolean, default=False)
    read_at             = Column(Text, nullable=True)
    email_sent          = Column(Boolean, default=False)
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id   = Column(Integer, nullable=True)
    priority            = Column(String(20), default="normal")
    extra_data          = Column(JSON, nullable=True)

    employee = relationship("Employee", back_populates="notifications")


class AuditLog(Base):
    """Maps to existing Neon 'audit_logs' table."""
    __tablename__  = "audit_logs"
    __table_args__ = {"extend_existing": True}

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    actor_type   = Column(String(20), nullable=False)   # "ai_agent", "employee", "system"
    ip_address   = Column(String(50), nullable=True)
    action       = Column(String(100), nullable=False, index=True)
    description  = Column(Text, nullable=True)
    entity_type  = Column(String(50), nullable=True)
    entity_id    = Column(Integer, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state  = Column(JSON, nullable=True)
    extra_data   = Column("metadata", JSON, nullable=True)
    status       = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)

    employee = relationship("Employee", back_populates="audit_logs")


# ─────────────────────────────────────────────────────────────────────────────
# NEW AI-ONLY TABLES — created by init_new_tables()
# ─────────────────────────────────────────────────────────────────────────────

class SecurityAlert(Base):
    """NEW table — created by AI system for detection agent alerts."""
    __tablename__ = "security_alerts"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    alert_type   = Column(String(100), nullable=False)
    severity     = Column(String(20), nullable=False)           # LOW/MEDIUM/HIGH/CRITICAL
    details      = Column(Text)
    employee_id  = Column(Integer, nullable=True)               # null if unregistered person
    face_image   = Column(String(500))
    is_resolved  = Column(Boolean, default=False)
    resolved_by  = Column(String(200))
    resolved_at  = Column(DateTime)
    created_at   = Column(DateTime, default=func.now())


class HRReport(Base):
    """NEW table — stores generated analytics reports."""
    __tablename__ = "hr_reports"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    report_type  = Column(String(100), nullable=False)
    period       = Column(String(50))
    title        = Column(String(300))
    content      = Column(JSON, default={})
    narrative    = Column(Text)
    generated_at = Column(DateTime, default=func.now())
    generated_by = Column(String(200), default="AI Agent")


# ── Init function ─────────────────────────────────────────────────────────────

def init_new_tables():
    """
    Creates ONLY the new AI-specific tables (security_alerts, hr_reports).
    Safe to call on startup — existing Neon tables are NOT touched.
    """
    SecurityAlert.__table__.create(bind=engine, checkfirst=True)
    HRReport.__table__.create(bind=engine, checkfirst=True)
    print("✅ AI-specific tables ready (security_alerts, hr_reports)")
