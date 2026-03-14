"""api/middleware.py — CORS + request logging middleware."""
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
import time, uuid

def setup_middleware(app, allowed_origins):
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = allowed_origins,
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        rid   = str(uuid.uuid4())[:8]
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000)
        print(f"[{rid}] {request.method} {request.url.path} → {response.status_code} ({duration}ms)")
        return response
