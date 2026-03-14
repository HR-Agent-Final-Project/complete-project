"""
Pydantic v2 schemas for Department endpoints.
"""

from pydantic import BaseModel, field_validator
from typing import Optional


class DepartmentCreate(BaseModel):
    name:        str
    code:        str
    description: Optional[str] = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Department name cannot be blank.")
        return v.strip()


class DepartmentUpdate(BaseModel):
    name:        Optional[str]  = None
    code:        Optional[str]  = None
    description: Optional[str] = None
    is_active:   Optional[bool] = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v


class DepartmentResponse(BaseModel):
    id:             int
    name:           str
    code:           str
    description:    Optional[str] = None
    is_active:      bool
    employee_count: int = 0

    model_config = {"from_attributes": True}
