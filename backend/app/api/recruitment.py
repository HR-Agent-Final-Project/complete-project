"""
Recruitment API

GET    /api/recruitment/jobs                    ← List all job postings
POST   /api/recruitment/jobs                    ← Create new job posting (HR Manager+)
GET    /api/recruitment/jobs/{id}               ← Get single job posting
PUT    /api/recruitment/jobs/{id}               ← Update job posting (HR Manager+)
DELETE /api/recruitment/jobs/{id}               ← Close/delete job (HR Manager+)
GET    /api/recruitment/jobs/{id}/applicants    ← List applicants for a job
POST   /api/recruitment/jobs/{id}/applicants    ← Submit application (external use)
PATCH  /api/recruitment/applicants/{id}/status  ← Update applicant status (HR+)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_employee, require_role
from app.models.recruitment import JobPosting, JobApplication, ApplicationStatus
from app.models.department import Department

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    title: str
    department: Optional[str] = None
    description: str
    requirements: Optional[str] = None
    salary_range: Optional[str] = None
    employment_type: Optional[str] = "full_time"
    location: Optional[str] = None
    positions_count: Optional[int] = 1
    closing_date: Optional[str] = None


class ApplicantCreateRequest(BaseModel):
    applicant_name: str
    applicant_email: str
    applicant_phone: Optional[str] = None
    cover_letter: Optional[str] = None


class ApplicantStatusUpdate(BaseModel):
    status: str
    hr_notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _job_to_dict(job: JobPosting) -> dict:
    dept_name = job.department.name if hasattr(job, 'department') and job.department else None
    apps_count = len(job.applications) if job.applications else 0
    return {
        "id":                 job.id,
        "title":              job.title,
        "department":         dept_name or "General",
        "department_id":      job.department_id,
        "description":        job.description,
        "requirements":       job.requirements,
        "salary_range":       None,
        "employment_type":    job.employment_type,
        "location":           job.location,
        "positions_count":    job.positions_count,
        "closing_date":       str(job.closing_date) if job.closing_date else None,
        "status":             "active" if job.is_active else "closed",
        "posted_date":        str(job.created_at.date()) if job.created_at else str(date.today()),
        "applications_count": apps_count,
    }


def _app_to_dict(app: JobApplication) -> dict:
    return {
        "id":               app.id,
        "job_id":           app.job_posting_id,
        "name":             app.applicant_name or (app.applicant.full_name if app.applicant else ""),
        "email":            app.applicant_email or (app.applicant.personal_email if app.applicant else ""),
        "phone":            app.applicant_phone or "",
        "status":           app.status.value if app.status else "applied",
        "ai_score":         app.ai_overall_score,
        "ai_recommendation":app.ai_recommendation,
        "interview_status": app.status.value if app.status else "applied",
        "cover_letter":     app.cover_letter,
        "hr_notes":         app.hr_notes,
        "applied_at":       str(app.created_at) if app.created_at else "",
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    query = db.query(JobPosting)
    if active_only:
        query = query.filter(JobPosting.is_active == True)
    jobs = query.order_by(JobPosting.created_at.desc()).all()
    return [_job_to_dict(j) for j in jobs]


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    body: JobCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(2)),
):
    # Resolve department by name if given
    dept_id = None
    if body.department:
        dept = db.query(Department).filter(Department.name.ilike(body.department)).first()
        if dept:
            dept_id = dept.id

    closing = None
    if body.closing_date:
        try:
            closing = date.fromisoformat(body.closing_date)
        except ValueError:
            pass

    job = JobPosting(
        title=body.title,
        department_id=dept_id,
        description=body.description,
        requirements=body.requirements or "",
        employment_type=body.employment_type or "full_time",
        location=body.location,
        positions_count=body.positions_count or 1,
        closing_date=closing,
        is_active=True,
        posted_by_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")
    return _job_to_dict(job)


@router.put("/jobs/{job_id}")
def update_job(
    job_id: int,
    body: JobCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(2)),
):
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")
    job.title = body.title
    job.description = body.description
    if body.requirements:
        job.requirements = body.requirements
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(2)),
):
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")
    job.is_active = False
    db.commit()


@router.get("/jobs/{job_id}/applicants")
def get_applicants(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(2)),
):
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")
    apps = db.query(JobApplication).filter(JobApplication.job_posting_id == job_id).all()
    return [_app_to_dict(a) for a in apps]


@router.post("/jobs/{job_id}/applicants", status_code=status.HTTP_201_CREATED)
def apply_for_job(
    job_id: int,
    body: ApplicantCreateRequest,
    db: Session = Depends(get_db),
):
    job = db.query(JobPosting).filter(JobPosting.id == job_id, JobPosting.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found or closed.")
    app = JobApplication(
        job_posting_id=job_id,
        applicant_name=body.applicant_name,
        applicant_email=body.applicant_email,
        applicant_phone=body.applicant_phone,
        cover_letter=body.cover_letter,
        status=ApplicationStatus.APPLIED,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _app_to_dict(app)


@router.patch("/applicants/{app_id}/status")
def update_applicant_status(
    app_id: int,
    body: ApplicantStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(2)),
):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    try:
        app.status = ApplicationStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
    if body.hr_notes:
        app.hr_notes = body.hr_notes
    app.reviewed_by_id = current_user.id
    db.commit()
    db.refresh(app)
    return _app_to_dict(app)
