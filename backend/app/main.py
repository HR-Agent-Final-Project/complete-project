import logging
import os as _os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.security_headers import SecurityHeadersMiddleware

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

    # Seed default leave types + ensure all employees have balance records
    try:
        from datetime import date as _date
        from app.core.database import SessionLocal
        from app.models.leave import LeaveType, LeaveBalance
        from app.models.employee import Employee
        db = SessionLocal()
        try:
            if db.query(LeaveType).count() == 0:
                default_types = [
                    LeaveType(name="Annual Leave",    code="AL",  max_days_per_year=14, is_paid=True,  is_active=True, description="Paid annual vacation leave"),
                    LeaveType(name="Sick Leave",      code="SL",  max_days_per_year=10, is_paid=True,  is_active=True, description="Medical / health-related leave"),
                    LeaveType(name="Casual Leave",    code="CL",  max_days_per_year=7,  is_paid=True,  is_active=True, description="Short-notice personal leave"),
                    LeaveType(name="Maternity Leave", code="ML",  max_days_per_year=84, is_paid=True,  is_active=True, description="Maternity leave", gender_specific="female"),
                    LeaveType(name="Paternity Leave", code="PL",  max_days_per_year=3,  is_paid=True,  is_active=True, description="Paternity leave"),
                    LeaveType(name="No Pay Leave",    code="NPL", max_days_per_year=30, is_paid=False, is_active=True, description="Unpaid leave"),
                ]
                db.add_all(default_types)
                db.commit()
                logger.info("✅ Default leave types seeded.")

            # Ensure every active employee has a LeaveBalance row for every leave type this year
            current_year = _date.today().year
            employees    = db.query(Employee).filter(Employee.is_active == True).all()
            leave_types  = db.query(LeaveType).filter(LeaveType.is_active == True).all()

            # Single query to find all existing balances for this year
            existing = {
                (b.employee_id, b.leave_type_id)
                for b in db.query(LeaveBalance.employee_id, LeaveBalance.leave_type_id)
                           .filter(LeaveBalance.year == current_year)
                           .all()
            }
            new_balances = [
                LeaveBalance(
                    employee_id    = emp.id,
                    leave_type_id  = lt.id,
                    year           = current_year,
                    total_days     = lt.max_days_per_year,
                    used_days      = 0,
                    remaining_days = lt.max_days_per_year,
                )
                for emp in employees
                for lt in leave_types
                if (emp.id, lt.id) not in existing
            ]
            if new_balances:
                db.add_all(new_balances)
                db.commit()
                logger.info("✅ Created %d missing leave balance records.", len(new_balances))
        finally:
            db.close()
    except Exception as e:
        logger.warning("Leave type/balance seeding failed: %s", e)

    # Warm up DeepFace model so first scan is fast (loads Facenet512 into memory)
    try:
        import asyncio, numpy as np
        from deepface import DeepFace
        import tempfile, os
        from PIL import Image

        # Create a tiny blank image and run represent() to force model load
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            img = Image.new("RGB", (160, 160), color=(128, 128, 128))
            img.save(tmp.name)
            tmp_path = tmp.name
        try:
            DeepFace.represent(
                img_path          = tmp_path,
                model_name        = "Facenet512",
                detector_backend  = "opencv",
                enforce_detection = False,
            )
            logger.info("✅ DeepFace Facenet512 model warmed up.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.warning("DeepFace warm-up skipped: %s", e)

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
    # All API documentation endpoints are disabled in production (DEBUG=False).
    # openapi_url=None also kills /docs and /redoc even if set, so all three
    # are gated together to prevent partial exposure.
    openapi_url="/openapi.json" if settings.DEBUG else None,
    docs_url="/docs"            if settings.DEBUG else None,
    redoc_url="/redoc"          if settings.DEBUG else None,
    # persistAuthorization stores tokens in localStorage — dev convenience only.
    swagger_ui_parameters={"persistAuthorization": True} if settings.DEBUG else None,
    lifespan=lifespan,
    redirect_slashes=False,
)

# ── Middleware stack ──────────────────────────────────────────────────────────
# Starlette applies middleware in LIFO (last-added = outermost = runs first).
# Execution order for incoming requests:
#   TrustedHostMiddleware  →  SecurityHeadersMiddleware  →  CORSMiddleware  →  route

# 1. CORS — innermost; only reached after host + headers checks pass
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# 2. Security headers — applied to every response before it leaves the server
app.add_middleware(SecurityHeadersMiddleware, debug=settings.DEBUG)

# 3. Trusted host — outermost; rejects requests with invalid Host headers
#    before any business logic or auth runs (prevents DNS-rebinding attacks).
#    Set ALLOWED_HOSTS in .env for production, e.g. ALLOWED_HOSTS=["api.yourcompany.com"]
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)


@app.get("/", tags=["Health"])
def root():
    response = {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "running",
    }
    if settings.DEBUG:
        response["docs"] = "/docs"
    return response


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

# ── Protected uploads — replaces the unauthenticated StaticFiles mount ────────
from app.api.uploads import router as uploads_router
_uploads_dir = _os.path.join(_os.path.dirname(__file__), "..", "uploads")
_os.makedirs(_uploads_dir, exist_ok=True)
app.include_router(uploads_router, prefix="/uploads", tags=["Uploads"])

# ── Static files & Chat UI ────────────────────────────────────────────────────
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/chat", tags=["AI Chat"], include_in_schema=False)
def chat_ui():
    """Serves the AI Chat web interface."""
    return FileResponse(_os.path.join(_static_dir, "chat.html"))
