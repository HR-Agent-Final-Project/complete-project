"""
HRPolicy model — stores company HR policies.

These policies are:
  1. Stored here in PostgreSQL (structured metadata)
  2. Also ingested into ChromaDB as vector embeddings (for RAG)

When the AI agent needs to make a decision (e.g. leave approval),
it searches ChromaDB for relevant policy chunks, then uses them
as context when calling the LLM.

The chroma_doc_id links this database record to the vector store.

category examples:
  leave          → leave policies
  attendance     → attendance rules
  payroll        → salary and payment policies
  conduct        → code of conduct, disciplinary policies
  recruitment    → hiring policies
  general        → general HR policies
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, Text, Enum, JSON
from app.models.base import Base, TimestampMixin


class PolicyCategory(str, enum.Enum):
    LEAVE       = "leave"
    ATTENDANCE  = "attendance"
    PAYROLL     = "payroll"
    CONDUCT     = "conduct"
    RECRUITMENT = "recruitment"
    PERFORMANCE = "performance"
    GENERAL     = "general"


class HRPolicy(Base, TimestampMixin):
    __tablename__ = "hr_policies"

    id              = Column(Integer, primary_key=True, index=True)

    # ── Content
    title           = Column(String(300), nullable=False)
                      # e.g. "Annual Leave Policy 2025"
    category        = Column(Enum(PolicyCategory), nullable=False, index=True)
    content         = Column(Text, nullable=False)
                      # Full policy text — this gets chunked and sent to ChromaDB
    version         = Column(String(20), nullable=True)
                      # e.g. "v2.1"
    effective_date  = Column(String(20), nullable=True)
                      # ISO date string: "2025-01-01"
    expiry_date     = Column(String(20), nullable=True)

    # ── RAG Integration
    chroma_doc_id   = Column(String(200), nullable=True, unique=True)
                      # The document ID in ChromaDB — links PostgreSQL ↔ ChromaDB
    is_indexed      = Column(Boolean, default=False, nullable=False)
                      # True = already ingested into ChromaDB
    indexed_at      = Column(Text, nullable=True)
                      # ISO datetime when last indexed
    chunk_count     = Column(Integer, nullable=True)
                      # How many chunks were created in ChromaDB

    # ── Metadata
    is_active       = Column(Boolean, default=True, nullable=False)
    uploaded_by_id  = Column(Integer, nullable=True)
                      # Employee ID of who uploaded this policy
    tags            = Column(JSON, nullable=True)
                      # e.g. ["annual", "leave", "eligibility"]
                      # Used for filtering in RAG queries
    language        = Column(String(5), default="en")
                      # "en", "si", "ta"

    def __repr__(self):
        return f"<HRPolicy [{self.category}] {self.title} (indexed={self.is_indexed})>"