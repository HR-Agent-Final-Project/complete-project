import logging
import os as _os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Application lifespan (replaces deprecated @app.on_event) ─────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    from app.core.database import engine
    try:
        with engine.connect():
            logger.info("Database connected.")
    except Exception as e:
        logger.error("Database connection failed: %s", e)

    from app.core.firebase import get_firebase_app
    get_firebase_app()

    # Create new module tables (chat, hr_reports) if they don't exist
    try:
        from app.models.base import Base
        from app.models import chat, report  # noqa: register models
        Base.metadata.create_all(bind=engine)
        logger.info("Chat + Report tables ready.")
    except Exception as e:
        logger.warning("Table init: %s", e)

    # Seed ChromaDB with HR policy documents (skips if already loaded)
    try:
        from app.services.knowledge_seeder import seed_policies
        seed_policies()
    except Exception as e:
        logger.warning("RAG seeding skipped: %s", e)

    yield   # application runs here

    # ── Shutdown (add cleanup here if needed) ─────────────────────────────────
    logger.info("Application shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered HR management system.",
    docs_url="/docs",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/", tags=["Health"])
def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


# ── Routers ───────────────────────────────────────────────────────────────────
from app.api.auth        import router as auth_router
from app.api.employees   import router as employee_router
from app.api.departments import router as department_router
from app.api.roles       import router as role_router
from app.api.leave       import router as leave_router

app.include_router(auth_router,       prefix="/api/auth",        tags=["Authentication"])
app.include_router(employee_router,   prefix="/api/employees",   tags=["Employees"])
app.include_router(department_router, prefix="/api/departments", tags=["Departments"])
app.include_router(role_router,       prefix="/api/roles",       tags=["Roles"])
app.include_router(leave_router,      prefix="/api/leave",       tags=["Leave Management"])

from app.api.attendance import router as attendance_router
app.include_router(attendance_router, prefix="/api/attendance", tags=["Attendance"])

from app.api.performance import router as performance_router
app.include_router(performance_router, prefix="/api/performance", tags=["Performance"])

from app.api.chat import router as chat_router
app.include_router(chat_router, prefix="/api/chat", tags=["AI Chat"])

from app.api.reports import router as reports_router
app.include_router(reports_router, prefix="/api/reports", tags=["Reports & Analytics"])

from app.api.notifications import router as notifications_router
app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])

from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

from app.api.recruitment import router as recruitment_router
app.include_router(recruitment_router, prefix="/api/recruitment", tags=["Recruitment"])

# ── Static files & Chat UI ────────────────────────────────────────────────────
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
_uploads_dir = _os.path.join(_os.path.dirname(__file__), "..", "uploads")
_os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/chat", tags=["AI Chat"], include_in_schema=False)
def chat_ui():
    """Serves the AI Chat web interface."""
    return FileResponse(_os.path.join(_static_dir, "chat.html"))
