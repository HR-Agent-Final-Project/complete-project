"""
Attendance model.
Each row = one clock-in or clock-out event by an employee.

How it works:
  1. Employee stands in front of camera
  2. DeepFace identifies them (confidence_score tells us how sure)
  3. System creates a row here with clock_in time
  4. When they leave, clock_out is updated on the SAME row
  5. work_hours is calculated automatically

attendance_type:
  regular    → normal workday
  overtime   → worked past regular hours
  half_day   → approved half day
  holiday    → worked on a public holiday (gets extra pay)

verification_method:
  face_recognition → camera detected face ✓
  manual_override  → HR manually marked attendance (fallback)
  rfid             → RFID card (for accessibility)
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, Float,
    Boolean, Text, ForeignKey, Enum, Numeric, Date
)
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class AttendanceType(str, enum.Enum):
    REGULAR   = "regular"
    OVERTIME  = "overtime"
    HALF_DAY  = "half_day"
    HOLIDAY   = "holiday"


class VerificationMethod(str, enum.Enum):
    FACE_RECOGNITION = "face_recognition"
    MANUAL_OVERRIDE  = "manual_override"
    RFID             = "rfid"


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"

    id                  = Column(Integer, primary_key=True, index=True)

    # Who & When
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    work_date           = Column(Date, nullable=False, index=True)
                          # The calendar date this record belongs to
                          # (separate from clock_in in case of midnight shifts)

    # Clock Times
    clock_in            = Column(DateTime(timezone=True), nullable=True)
    clock_out           = Column(DateTime(timezone=True), nullable=True)
    work_hours          = Column(Float, nullable=True)
                          # Calculated: (clock_out - clock_in) in hours
                          # e.g. 8.5 means 8 hours 30 minutes

    # Face Recognition Data
    confidence_score    = Column(Float, nullable=True)
                          # How confident DeepFace was: 0.0 to 1.0
                          # Below 0.7 → flag for manual review
    verification_method = Column(
                              Enum(VerificationMethod),
                              default=VerificationMethod.FACE_RECOGNITION,
                              nullable=False
                          )
    is_verified         = Column(Boolean, default=False, nullable=False)
                          # True = face confirmed, False = needs review

    # Attendance Classification
    attendance_type     = Column(
                              Enum(AttendanceType),
                              default=AttendanceType.REGULAR,
                              nullable=False
                          )
    is_late             = Column(Boolean, default=False, nullable=False)
                          # True if clock_in was after official start time
    late_minutes        = Column(Integer, default=0, nullable=False)
                          # How many minutes late (used in performance scoring)
    is_early_departure  = Column(Boolean, default=False, nullable=False)
    overtime_hours      = Column(Float, default=0.0, nullable=False)
                          # Hours worked beyond the standard working day

    # Location
    location            = Column(String(200), nullable=True)
                          # "Head Office", "Matara Branch", "Remote"
    latitude            = Column(Float, nullable=True)            # GPS latitude at clock-in
    longitude           = Column(Float, nullable=True)            # GPS longitude at clock-in
    checkout_latitude   = Column(Float, nullable=True)            # GPS latitude at clock-out
    checkout_longitude  = Column(Float, nullable=True)            # GPS longitude at clock-out

    # Flags & Notes
    is_absent           = Column(Boolean, default=False, nullable=False)
                          # True = no clock-in recorded at all for this date
    absence_reason      = Column(Text, nullable=True)
    notes               = Column(Text, nullable=True)
                          # HR notes (e.g. "Approved WFH")
    flagged             = Column(Boolean, default=False, nullable=False)
                          # True = suspicious activity, needs HR review
    flag_reason         = Column(Text, nullable=True)
                          # e.g. "Low confidence score 0.45 — possible proxy attempt"

    # Snapshot paths
    clock_in_photo      = Column(String(500), nullable=True)
    clock_out_photo     = Column(String(500), nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="attendance_records")
    scans    = relationship("AttendanceScan", back_populates="attendance", cascade="all, delete-orphan",
                            order_by="AttendanceScan.scanned_at")

    def __repr__(self):
        return f"<Attendance emp={self.employee_id} date={self.work_date} in={self.clock_in}>"


class AttendanceScan(Base, TimestampMixin):
    """
    Every face scan is logged here with a snapshot image.
    Builds a visual timeline: who scanned, when, and the photo proof.
    """
    __tablename__ = "attendance_scans"

    id              = Column(Integer, primary_key=True, index=True)
    attendance_id   = Column(Integer, ForeignKey("attendance.id"), nullable=False, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    scan_type       = Column(String(20), nullable=False)       # "clock_in", "clock_out"
    scanned_at      = Column(DateTime(timezone=True), nullable=False)
    confidence      = Column(Float, nullable=True)
    photo_path      = Column(String(500), nullable=True)       # path to saved snapshot

    # Relationships
    attendance = relationship("Attendance", back_populates="scans")
    employee   = relationship("Employee")