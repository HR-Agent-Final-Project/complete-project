"""
Pydantic v2 schemas for Employee endpoints.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import date
from enum import Enum


class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract  = "contract"
    intern    = "intern"


class GenderEnum(str, Enum):
    male   = "male"
    female = "female"
    other  = "other"


class LanguagePref(str, Enum):
    en = "en"
    si = "si"
    ta = "ta"


# ── Request schemas

class EmployeeCreate(BaseModel):
    first_name:      str
    last_name:       str
    personal_email:  EmailStr
    phone_number:    Optional[str]          = None
    department_id:   Optional[int]          = None
    role_id:         Optional[int]          = None
    employment_type: EmploymentType         = EmploymentType.full_time
    base_salary:     Optional[float]        = None
    language_pref:   LanguagePref           = LanguagePref.en
    nic_number:      Optional[str]          = None
    date_of_birth:   Optional[date]         = None
    gender:          Optional[GenderEnum]   = None
    manager_id:      Optional[int]          = None
    address:         Optional[str]          = None
    city:            Optional[str]          = None
    district:        Optional[str]          = None
    bank_account:    Optional[str]          = None
    bank_name:       Optional[str]          = None

    @field_validator("first_name", "last_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank.")
        return v.strip()


class EmployeeUpdate(BaseModel):
    first_name:      Optional[str]          = None
    last_name:       Optional[str]          = None
    phone_number:    Optional[str]          = None
    department_id:   Optional[int]          = None
    role_id:         Optional[int]          = None
    employment_type: Optional[EmploymentType] = None
    base_salary:     Optional[float]        = None
    language_pref:   Optional[LanguagePref] = None
    work_email:      Optional[str]          = None
    address:         Optional[str]          = None
    city:            Optional[str]          = None
    district:        Optional[str]          = None
    bank_account:    Optional[str]          = None
    bank_name:       Optional[str]          = None


class StatusUpdateRequest(BaseModel):
    is_active: bool
    reason:    Optional[str] = None


class FaceEnrollRequest(BaseModel):
    image_base64: str   # base64-encoded JPEG


# ── Response schemas

class EmployeeResponse(BaseModel):
    id:              int
    employee_number: str
    first_name:      str
    last_name:       str
    full_name:       str
    personal_email:  str
    work_email:      Optional[str]  = None
    phone_number:    Optional[str]  = None
    department:      Optional[str]  = None
    department_id:   Optional[int]  = None
    role:            Optional[str]  = None
    role_id:         Optional[int]  = None
    access_level:    int            = 1
    status:          str
    employment_type: str
    hire_date:       Optional[str]  = None
    base_salary:     Optional[float] = None
    face_registered: bool
    language_pref:   str
    profile_photo:   Optional[str]  = None
    is_active:       bool
    created_at:      str

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    total:     int
    page:      int
    page_size: int
    employees: list[EmployeeResponse]
