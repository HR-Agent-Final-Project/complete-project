"""
config/settings.py
──────────────────
Central configuration using Pydantic Settings.
All environment variables are read from .env file.
Change ONE value here → affects the entire system.
"""

import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── LLM ───────────────────────────────────────────────────────────────────
    OPENAI_API_KEY:  str = os.getenv("OPENAI_API_KEY", "sk-not-set")
    LLM_MODEL:       str = "gpt-4o-mini"        # gpt-4o for production
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_TEMPERATURE: float = 0.0                 # deterministic for decisions

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/aihrdb"
    )

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    # Set CHROMA_HOST=localhost to use Docker HTTP server (recommended)
    # Leave CHROMA_HOST empty to use local file persistence (dev fallback)
    CHROMA_HOST:         str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT:         int = int(os.getenv("CHROMA_PORT", "8100"))
    CHROMA_PERSIST_PATH: str = "./chroma_db"   # used only if CHROMA_HOST is empty

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── API ───────────────────────────────────────────────────────────────────
    SECRET_KEY:      str  = "change-this-in-production"
    API_HOST:        str  = "0.0.0.0"
    API_PORT:        int  = 8001
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Email ─────────────────────────────────────────────────────────────────
    SMTP_HOST:     str = "smtp.gmail.com"
    SMTP_PORT:     int = 587
    SMTP_USER:     str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM:    str = "noreply@company.com"

    # ── Face Recognition ──────────────────────────────────────────────────────
    FACE_UPLOADS_DIR:           str   = "./uploads/faces"
    FACE_CONFIDENCE_THRESHOLD:  float = 0.70
    FACE_MODEL:                 str   = "Facenet512"

    # ── Leave Rules (Sri Lanka defaults) ──────────────────────────────────────
    ANNUAL_LEAVE_DAYS:   int = 14
    SICK_LEAVE_DAYS:     int = 7
    CASUAL_LEAVE_DAYS:   int = 7
    MATERNITY_LEAVE_DAYS: int = 84

    # ── OT & Statutory Rates (Sri Lanka EPF/ETF) ─────────────────────────────
    EPF_EMPLOYEE_RATE: float = 0.08
    EPF_EMPLOYER_RATE: float = 0.12
    ETF_RATE:          float = 0.03
    OT_WEEKDAY_RATE:   float = 1.5
    OT_WEEKEND_RATE:   float = 2.0

    # ── Attendance ────────────────────────────────────────────────────────────
    WORK_START_HOUR:          int = 8
    WORK_START_MINUTE:        int = 30
    GRACE_PERIOD_MINUTES:     int = 15
    MIN_ATTENDANCE_PERCENT:   float = 85.0

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
