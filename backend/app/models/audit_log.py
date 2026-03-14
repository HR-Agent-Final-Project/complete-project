"""
AuditLog model — records every important action in the system.

This is critical for:
  - Compliance (who did what, when)
  - Security (detect unauthorized access)
  - Accountability (HR can see exactly what the AI decided and why)
  - Dispute resolution (proof of actions taken)

Every time something significant happens, the system writes a row here:
  - Employee logs in
  - AI approves/rejects leave
  - HR overrides AI decision
  - Payroll is finalized
  - Policy is uploaded
  - Suspicious attendance detected
  - etc.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id              = Column(Integer, primary_key=True, index=True)

    # ── Who did this
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
                      # Null if action was done by the system/AI automatically
    actor_type      = Column(String(20), nullable=False)
                      # "employee", "hr_manager", "admin", "ai_agent", "system"
    ip_address      = Column(String(50), nullable=True)

    # ── What was done
    action          = Column(String(100), nullable=False, index=True)
                      # e.g. "leave.approved", "employee.login", "payroll.finalized"
                      # Use dot notation: module.verb
    description     = Column(Text, nullable=True)
                      # Human readable: "AI approved leave request #42 for John Doe"

    # ── What was affected
    entity_type     = Column(String(50), nullable=True)
                      # "leave_request", "employee", "payroll", "attendance"
    entity_id       = Column(Integer, nullable=True)
                      # ID of the affected record

    # ── Data Snapshot
    before_state    = Column(JSON, nullable=True)
                      # State of the record BEFORE the action (for undo/audit)
    after_state     = Column(JSON, nullable=True)
                      # State of the record AFTER the action
    extra_data = Column("metadata", JSON, nullable=True)
                      # Any extra info: AI reasoning, policy refs used, etc.

    # ── Result
    status          = Column(String(20), default="success")
                      # "success", "failed", "blocked"
    error_message   = Column(Text, nullable=True)

    employee = relationship("Employee", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog [{self.actor_type}] {self.action} on {self.entity_type}#{self.entity_id}>"