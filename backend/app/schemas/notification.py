from pydantic import BaseModel, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime


class NotificationOut(BaseModel):
    id                  : int
    notification_type   : str
    title               : str
    message             : str
    action_url          : Optional[str] = None
    channel             : str
    is_read             : bool
    read_at             : Optional[str] = None
    priority            : str
    related_entity_type : Optional[str] = None
    related_entity_id   : Optional[int] = None
    extra_data          : Optional[Dict[str, Any]] = None
    created_at          : Optional[datetime] = None

    model_config = {"from_attributes": True}


class SendNotificationRequest(BaseModel):
    """HR sends a manual notification to one or more employees."""
    employee_ids      : List[int]
    notification_type : str = "hr_message"
    title             : str
    message           : str
    action_url        : Optional[str] = None
    channel           : str = "both"   # in_app | email | both
    priority          : str = "normal" # low | normal | high | urgent

    @field_validator("employee_ids")
    @classmethod
    def not_empty(cls, v):
        if not v:
            raise ValueError("At least one employee_id is required.")
        return v

    @field_validator("title", "message")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("Cannot be empty.")
        return v.strip()


class BroadcastRequest(BaseModel):
    """HR broadcasts a notification to all employees or one department."""
    notification_type : str = "hr_announcement"
    title             : str
    message           : str
    action_url        : Optional[str] = None
    department_id     : Optional[int] = None  # None = all employees
    priority          : str = "normal"

    @field_validator("title", "message")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("Cannot be empty.")
        return v.strip()
