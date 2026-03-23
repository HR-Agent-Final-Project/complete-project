"""
Pydantic v2 schemas for Attendance endpoints.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


# ── Request schemas ────────────────────────────────────────────────────────────

class ClockInBase64Request(BaseModel):
    employee_id:  int
    image_base64: str          # base64-encoded JPEG (data URL prefix stripped automatically)
    location:     str = "Head Office"
    latitude:     Optional[float] = None   # GPS latitude from mobile
    longitude:    Optional[float] = None   # GPS longitude from mobile

    @field_validator("image_base64")
    @classmethod
    def strip_data_url(cls, v: str) -> str:
        if "base64," in v:
            return v.split("base64,")[1]
        return v


class ClockOutBase64Request(BaseModel):
    employee_id:  int
    image_base64: str          # base64-encoded JPEG
    latitude:     Optional[float] = None   # GPS latitude from mobile
    longitude:    Optional[float] = None   # GPS longitude from mobile

    @field_validator("image_base64")
    @classmethod
    def strip_data_url(cls, v: str) -> str:
        if "base64," in v:
            return v.split("base64,")[1]
        return v


class ManualAttendanceRequest(BaseModel):
    employee_id: int
    work_date:   str           # ISO format: "2026-03-13"
    clock_in:    str           # "HH:MM:SS"
    clock_out:   Optional[str] = None   # "HH:MM:SS"
    reason:      Optional[str] = None

    @field_validator("work_date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("work_date must be in ISO format: YYYY-MM-DD")
        return v


class ResolveFlagRequest(BaseModel):
    resolution_note: str       # HR's explanation of how the flag was resolved
