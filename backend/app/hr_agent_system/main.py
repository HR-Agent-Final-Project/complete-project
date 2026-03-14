"""
main.py
────────
FastAPI application entry point.

Start: uv run uvicorn main:app --reload --port 8001
Docs:  http://localhost:8001/docs
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config.settings import settings
from api.middleware import setup_middleware
from api.routes.chat       import router as chat_router
from api.routes.attendance import router as attendance_router
from api.routes.leave      import router as leave_router
from api.routes.reports    import router as reports_router


# ── Lifespan: startup & shutdown ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ───────────────────────────────────────────────────────────────
    print("=" * 60)
    print("🚀 AI HR Management System — Starting Up")
    print("=" * 60)

    # 1. Create AI-specific tables (existing Neon tables are NOT touched)
    try:
        from models.database import init_new_tables
        init_new_tables()
        print("✅ Database tables ready")
    except Exception as e:
        print(f"⚠️  DB init failed: {e}")

    # 2. Seed ChromaDB with HR policy documents
    try:
        from rag.knowledge_base import seed_all_policies
        seed_all_policies()
    except Exception as e:
        print(f"⚠️  RAG seeding failed: {e}")

    # 3. Pre-warm the master graph (imports + compiles all sub-graphs)
    try:
        from core.graph import get_hr_graph
        get_hr_graph()
    except Exception as e:
        print(f"⚠️  Graph build failed: {e}")

    print("=" * 60)
    print(f"🌐 API ready at http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"📚 Docs at http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print("=" * 60)

    yield

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    print("👋 Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "AI HR Management System",
    description = (
        "Multi-agent LangGraph HR system with 7 specialized AI agents. "
        "B.Tech Final Year Project — UoVT Sri Lanka."
    ),
    version  = "1.0.0",
    lifespan = lifespan,
)

setup_middleware(app, settings.ALLOWED_ORIGINS)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(chat_router,       prefix="/api", tags=["Chat"])
app.include_router(attendance_router, prefix="/api", tags=["Attendance"])
app.include_router(leave_router,      prefix="/api", tags=["Leave"])
app.include_router(reports_router,    prefix="/api", tags=["Reports"])


# ── Health & Utility Endpoints ────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/graph/visualize", tags=["System"])
async def visualize_graph():
    """Returns Mermaid diagram of the complete LangGraph."""
    try:
        from core.graph import get_hr_graph
        mermaid = get_hr_graph().get_graph().draw_mermaid()
        return {"mermaid": mermaid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/performance/{employee_id}", tags=["Performance"])
async def performance_review(employee_id: str):
    from core.state import blank_state
    from core.graph import get_hr_graph
    import uuid
    graph  = get_hr_graph()
    state  = blank_state(employee_id, "Performance review", "hr_manager",
                         intent="performance_review")
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(state, config)
    return result.get("structured_output", {})


@app.post("/api/recruitment/interview", tags=["Recruitment"])
async def recruitment_interview(body: dict):
    from core.state import blank_state
    from core.graph import get_hr_graph
    import uuid
    graph  = get_hr_graph()
    state  = blank_state(
        user_input = f"Screen {body.get('candidate_name', 'candidate')} for {body.get('position', 'role')}",
        role       = "hr_manager",
        intent     = "recruitment",
        task_data  = body,
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(state, config)
    return result.get("structured_output", {})


@app.post("/api/security/detect", tags=["Security"])
async def security_detect(body: dict):
    from core.state import blank_state
    from core.graph import get_hr_graph
    import uuid
    graph  = get_hr_graph()
    state  = blank_state(
        user_input = "Security detection event",
        intent     = "security_alert",
        task_data  = body,
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(state, config)
    return result.get("structured_output", {})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host   = settings.API_HOST,
        port   = settings.API_PORT,
        reload = True,
    )
