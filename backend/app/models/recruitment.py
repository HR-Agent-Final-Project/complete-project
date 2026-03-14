"""
Recruitment models — 2 tables:

  1. JobPosting     → an open position the company is hiring for
  2. JobApplication → a candidate who applied for a JobPosting

The AI agent:
  1. Screens resumes against job requirements
  2. Conducts preliminary text interviews via chat
  3. Scores candidates using RAG (company culture + job requirements)
  4. Ranks candidates for HR to review
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    ForeignKey, Numeric, Enum, Float, Date, JSON
)
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ApplicationStatus(str, enum.Enum):
    APPLIED      = "applied"       # Just submitted
    SCREENING    = "screening"     # AI is screening resume
    AI_INTERVIEW = "ai_interview"  # AI preliminary interview in progress
    SHORTLISTED  = "shortlisted"   # Passed AI screen, waiting for HR interview
    HR_INTERVIEW = "hr_interview"  # In HR interview process
    OFFERED      = "offered"       # Job offer extended
    ACCEPTED     = "accepted"      # Candidate accepted offer
    REJECTED     = "rejected"      # Not moving forward
    WITHDRAWN    = "withdrawn"     # Candidate withdrew


# 1. Job Posting

class JobPosting(Base, TimestampMixin):
    __tablename__ = "job_postings"

    id               = Column(Integer, primary_key=True, index=True)
    title            = Column(String(200), nullable=False)
    department_id    = Column(Integer, ForeignKey("departments.id"), nullable=True)
    description      = Column(Text, nullable=False)
    requirements     = Column(Text, nullable=False)
                       # Skills, experience, qualifications required
    responsibilities = Column(Text, nullable=True)
    salary_min       = Column(Numeric(12, 2), nullable=True)
    salary_max       = Column(Numeric(12, 2), nullable=True)
    employment_type  = Column(String(50), default="full_time")
    location         = Column(String(200), nullable=True)
    positions_count  = Column(Integer, default=1)
                       # How many people are being hired for this role
    closing_date     = Column(Date, nullable=True)
    is_active        = Column(Boolean, default=True, nullable=False)
    posted_by_id     = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # ── AI Interview Config
    ai_interview_questions = Column(JSON, nullable=True)
                             # List of questions the AI will ask candidates
                             # e.g. ["Tell me about your experience with FastAPI",
                             #        "How do you handle tight deadlines?"]
    culture_keywords       = Column(JSON, nullable=True)
                             # Keywords from company culture for RAG matching
                             # e.g. ["teamwork", "innovation", "customer-first"]

    applications  = relationship("JobApplication", back_populates="job_posting")
    posted_by     = relationship("Employee", foreign_keys=[posted_by_id])

    def __repr__(self):
        return f"<JobPosting '{self.title}' active={self.is_active}>"


# 2. Job Application

class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"

    id              = Column(Integer, primary_key=True, index=True)
    job_posting_id  = Column(Integer, ForeignKey("job_postings.id"), nullable=False, index=True)

    # ── Applicant Info
    applicant_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
                      # Null if external applicant (not yet an employee)
    # External applicant details (filled if applicant_id is null)
    applicant_name  = Column(String(200), nullable=True)
    applicant_email = Column(String(200), nullable=True)
    applicant_phone = Column(String(20), nullable=True)
    resume_url      = Column(String(500), nullable=True)   # S3 URL of uploaded CV
    cover_letter    = Column(Text, nullable=True)

    # ── AI Screening
    status              = Column(Enum(ApplicationStatus), default=ApplicationStatus.APPLIED, nullable=False)
    ai_resume_score     = Column(Float, nullable=True)
                          # 0-100: how well resume matches job requirements
    ai_interview_score  = Column(Float, nullable=True)
                          # 0-100: score from AI preliminary interview
    ai_culture_fit      = Column(Float, nullable=True)
                          # 0-100: how well candidate matches company culture
    ai_overall_score    = Column(Float, nullable=True)
                          # Weighted average of above 3 scores
    ai_recommendation   = Column(String(50), nullable=True)
                          # "shortlist", "reject", "hold"
    ai_feedback         = Column(Text, nullable=True)
                          # AI's detailed feedback on the candidate
    interview_transcript = Column(JSON, nullable=True)
                           # Full Q&A transcript from AI interview
                           # [{"q": "...", "a": "...", "score": 7.5}, ...]

    # ── HR Review
    hr_notes        = Column(Text, nullable=True)
    reviewed_by_id  = Column(Integer, ForeignKey("employees.id"), nullable=True)
    hr_score        = Column(Float, nullable=True)

    job_posting = relationship("JobPosting", back_populates="applications")
    applicant   = relationship("Employee", foreign_keys=[applicant_id], back_populates="job_applications")
    reviewed_by = relationship("Employee", foreign_keys=[reviewed_by_id])

    def __repr__(self):
        return f"<JobApplication job={self.job_posting_id} [{self.status}] ai_score={self.ai_overall_score}>"