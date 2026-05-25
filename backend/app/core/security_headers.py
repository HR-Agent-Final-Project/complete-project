"""
Security headers middleware.

Injects defence-in-depth HTTP security headers into every response.
These headers instruct browsers to apply additional protections
even when application code has a vulnerability.

Header                     Purpose
─────────────────────────  ──────────────────────────────────────────────────
Content-Security-Policy    Restricts resource origins — primary XSS mitigation
X-Frame-Options            Prevents clickjacking via iframe embedding
X-Content-Type-Options     Prevents MIME-type sniffing attacks
Strict-Transport-Security  Forces HTTPS for 1 year (production only)
Referrer-Policy            Limits referrer data sent in cross-origin requests
Permissions-Policy         Disables browser APIs the application never uses
X-XSS-Protection           Set to 0 — the legacy IE filter introduced its own
                           vulnerabilities; modern browsers ignore it anyway
Cache-Control              Prevents intermediaries caching sensitive API data
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply security headers to every HTTP response."""

    def __init__(self, app, *, debug: bool = False) -> None:
        super().__init__(app)
        self._debug = debug

        # Build CSP once at startup — it never changes per-request.
        # DEBUG mode adds CDN sources required by Swagger UI (FastAPI docs).
        # Production mode is strict: only same-origin resources permitted.
        if debug:
            self._csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
                "img-src 'self' data: cdn.jsdelivr.net; "
                "font-src 'self' fonts.gstatic.com; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        else:
            # Pure API — no external resources needed.
            # 'unsafe-inline' is permitted for the static chat UI inline styles only.
            self._csp = (
                "default-src 'none'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # ── Content-Security-Policy ───────────────────────────────────────────
        response.headers["Content-Security-Policy"] = self._csp

        # ── Clickjacking protection ───────────────────────────────────────────
        response.headers["X-Frame-Options"] = "DENY"

        # ── MIME-type sniffing protection ─────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── HTTPS enforcement (production only) ───────────────────────────────
        # Never send HSTS over plain HTTP — it permanently breaks dev tooling.
        if not self._debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # ── Referrer policy ───────────────────────────────────────────────────
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Permissions policy ────────────────────────────────────────────────
        # Explicitly disable every sensitive browser API this app never needs.
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), bluetooth=()"
        )

        # ── Legacy XSS filter ─────────────────────────────────────────────────
        # Set to 0 to disable the IE/old-Chrome XSS auditor, which itself had
        # exploitable behaviour. Modern browsers ignore this header entirely.
        response.headers["X-XSS-Protection"] = "0"

        # ── API response caching ──────────────────────────────────────────────
        # Prevent reverse proxies and CDNs from caching authenticated API
        # responses. Static assets under /static/ can still be cached normally.
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"

        return response
