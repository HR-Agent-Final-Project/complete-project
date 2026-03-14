"""
Chat models — 2 tables:

  1. ChatSession  → one conversation thread per employee
  2. ChatMessage  → each individual message (user + assistant) in a session

The AI Chat Agent reads these to maintain conversation context.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    title       = Column(String(200), nullable=True)
                  # Auto-set from first message, e.g. "How many leave days do I have?"
    is_active   = Column(Boolean, default=True, nullable=False)

    employee = relationship("Employee", foreign_keys=[employee_id])
    messages = relationship("ChatMessage", back_populates="session",
                            order_by="ChatMessage.id", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession emp={self.employee_id} title='{self.title}'>"


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role       = Column(String(20), nullable=False)
               # "user" or "assistant"
    content    = Column(Text, nullable=False)
               # The actual message text
    sources    = Column(Text, nullable=True)
               # JSON list of policy sources cited by AI, e.g. ["leave_policy.txt"]

    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage session={self.session_id} role={self.role} len={len(self.content)}>"
