"""
Notification model.
Every automated message sent to an employee is stored here.

notification_type examples:
  leave_approved     → "Your leave request for Jan 15-16 has been approved."
  leave_rejected     → "Your leave request was rejected. Reason: ..."
  payslip_ready      → "Your January 2026 payslip is ready."
  performance_review → "Your Q4 2025 performance review is available."
  warning            → "You have been late 5 times this month."
  system_alert       → For HR/Admin: "Unregistered face detected at entrance."

channel:
  in_app  → shows in the notification bell in the web/mobile app
  email   → sent via Gmail API
  both    → both channels
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL  = "email"
    BOTH   = "both"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id                = Column(Integer, primary_key=True, index=True)

    employee_id       = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # ── Content
    notification_type = Column(String(50), nullable=False, index=True)
                        # e.g. "leave_approved", "payslip_ready", "warning"
    title             = Column(String(300), nullable=False)
                        # Short heading: "Leave Request Approved"
    message           = Column(Text, nullable=False)
                        # Full message body
    action_url        = Column(String(500), nullable=True)
                        # Deep link: "/leave/request/42" or "/payslip/2026/01"

    # ── Delivery
    channel           = Column(Enum(NotificationChannel), default=NotificationChannel.BOTH)
    is_read           = Column(Boolean, default=False, nullable=False)
    read_at           = Column(Text, nullable=True)
    email_sent        = Column(Boolean, default=False, nullable=False)
    email_sent_at     = Column(Text, nullable=True)

    # ── Related Entity
    related_entity_type = Column(String(50), nullable=True)
                          # e.g. "leave_request", "payroll", "performance_review"
    related_entity_id   = Column(Integer, nullable=True)
                          # The ID of the related record

    # ── Metadata
    priority          = Column(String(20), default="normal")
                        # "low", "normal", "high", "urgent"
    extra_data        = Column(JSON, nullable=True)
                        # Any additional structured data needed by the frontend

    employee = relationship("Employee", back_populates="notifications")

    def __repr__(self):
        return f"<Notification emp={self.employee_id} [{self.notification_type}] read={self.is_read}>"