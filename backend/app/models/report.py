"""
Report model — stores generated HR reports and analytics snapshots.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from sqlalchemy.sql import func
from app.models.base import Base, TimestampMixin


class HRReport(Base, TimestampMixin):
    __tablename__ = "hr_reports"

    id           = Column(Integer, primary_key=True, index=True)
    report_type  = Column(String(100), nullable=False, index=True)
                   # monthly_summary | attendance | leave | performance | department
    period       = Column(String(50), nullable=True)
                   # "2026-03" or "2026-Q1" or "2026"
    title        = Column(String(300), nullable=False)
    content      = Column(JSON, default={})
                   # Full structured data (KPIs, breakdowns, etc.)
    narrative    = Column(Text, nullable=True)
                   # AI-generated executive summary
    generated_by = Column(String(200), default="system")
                   # "AI Agent" or employee name

    def __repr__(self):
        return f"<HRReport type={self.report_type} period={self.period}>"
