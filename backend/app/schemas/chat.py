from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class ChatMessageOut(BaseModel):
    id         : int
    role       : str      # "user" or "assistant"
    content    : str
    sources    : Optional[List[str]] = []
    created_at : Optional[datetime]

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id         : int
    title      : Optional[str]
    is_active  : bool
    created_at : Optional[datetime]
    messages   : List[ChatMessageOut] = []

    model_config = {"from_attributes": True}


class ChatSessionSummary(BaseModel):
    id         : int
    title      : Optional[str]
    is_active  : bool
    created_at : Optional[datetime]
    message_count: int = 0

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty.")
        return v.strip()


class QuickChatRequest(BaseModel):
    """Single message without creating a session (stateless)."""
    message: str

    @field_validator("message")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty.")
        return v.strip()


class ChatResponseOut(BaseModel):
    session_id : int
    message_id : int
    response   : str
    sources    : List[str] = []
