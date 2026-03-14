"""
Pydantic v2 schemas for Role endpoints.
"""

from pydantic import BaseModel, field_validator
from typing import Optional


class RoleCreate(BaseModel):
    title:        str
    code:         str
    access_level: int             # must be 1, 2, 3, or 4
    description:  Optional[str]   = None
    base_salary:  Optional[float] = None

    @field_validator("access_level")
    @classmethod
    def valid_level(cls, v: int) -> int:
        if v not in (1, 2, 3, 4):
            raise ValueError("access_level must be 1 (Employee), 2 (HR Staff), 3 (HR Manager), or 4 (Admin).")
        return v

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class RoleUpdate(BaseModel):
    title:        Optional[str]   = None
    code:         Optional[str]   = None
    access_level: Optional[int]   = None
    description:  Optional[str]   = None
    base_salary:  Optional[float] = None
    is_active:    Optional[bool]  = None

    @field_validator("access_level")
    @classmethod
    def valid_level(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (1, 2, 3, 4):
            raise ValueError("access_level must be 1, 2, 3, or 4.")
        return v

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip().upper() if v else v


class RoleResponse(BaseModel):
    id:             int
    title:          str
    code:           str
    access_level:   int
    description:    Optional[str]   = None
    base_salary:    Optional[float] = None
    is_active:      bool
    employee_count: int = 0

    model_config = {"from_attributes": True}
