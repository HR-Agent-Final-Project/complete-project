"""
Application settings — reads from your .env file.

Create a file called .env in your project root with these values
(copy from .env.example and fill in your details).
"""

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ── App
    APP_NAME: str = "AI-HR Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # Set False in production

    # ── Database
    # REQUIRED — Format: postgresql://username:password@host:port/database_name
    DATABASE_URL: str

    # ── JWT Auth
    # REQUIRED — generate with: python -c "import secrets; print(secrets.token_hex(64))"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60       # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7          # 7 days

    # Firebase
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"

    # ── Server
    PORT: int = 8080                                     # uvicorn listen port
    BACKEND_URL: str = "http://localhost:8080"           # used in email approval links

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8080/api/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Security ──────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ]
    RATE_LIMIT_PER_MINUTE: int = 60
    LOGIN_RATE_LIMIT: int = 5

    # ── OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"           # Use mini for dev (cheaper)

    # ── ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"     # Local folder for vector store

    # ── Email (Gmail API)
    GMAIL_USER: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None

    # ── File Storage
    UPLOAD_DIR: str = "./uploads"               # Local uploads folder

    # ── HR Business Rules
    # These are used by the AI agent when making leave decisions
    ATTENDANCE_THRESHOLD_PERCENT: float = 85.0
    # Employee must have >= 85% attendance to qualify for discretionary leave

    LATE_ARRIVAL_CUTOFF_MINUTES: int = 15
    # If more than 15 min late = marked as "late"

    WORKDAY_START_HOUR: int = 8
    WORKDAY_START_MINUTE: int = 30
    # Official start time: 8:30 AM

    WORKDAY_END_HOUR: int = 17
    WORKDAY_END_MINUTE: int = 30
    # Official end time: 5:30 PM

    OVERTIME_MULTIPLIER: float = 1.5
    # OT hours paid at 1.5x normal rate

    # ── Sri Lanka Statutory Rates
    EPF_EMPLOYEE_RATE: float = 0.08    # 8%
    EPF_EMPLOYER_RATE: float = 0.12   # 12%
    ETF_RATE: float = 0.03            # 3%

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Single instance used throughout the app
settings = Settings()