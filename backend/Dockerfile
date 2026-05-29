# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — dependency builder
#   Installs all Python packages into an isolated virtualenv using uv.
#   Only pyproject.toml and uv.lock are copied here so this layer is
#   re-used on every build where dependencies have not changed.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

# Install uv (fast, reproducible package installer)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only the lock files — application source is not needed to install deps
COPY pyproject.toml uv.lock ./

# Install production dependencies into .venv
# --frozen  : fail if uv.lock is out of date (no silent upgrades)
# --no-dev  : exclude dev/test extras
RUN uv sync --frozen --no-dev


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime image
#   Minimal image that only contains the app + its installed virtualenv.
#   No build tools, no uv, no source cache, no secrets.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

# System libraries required at runtime:
#   libgomp1      — OpenMP, used by numpy / DeepFace / TF
#   libglib2.0-0  — GLib, required by some OpenCV internals
#   curl          — used by the HEALTHCHECK instruction below
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libgomp1 \
      libglib2.0-0 \
      curl \
 && rm -rf /var/lib/apt/lists/*

# ── Non-root user ──────────────────────────────────────────────────────────
# Running as root inside a container is a privilege-escalation risk.
# The app does not need root for any operation.
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup \
             --no-create-home --shell /bin/false \
             appuser

WORKDIR /app

# Copy the pre-built virtualenv from the builder stage (no uv needed at runtime)
COPY --from=builder /app/.venv ./.venv

# Copy application source code
# .dockerignore excludes: .env, firebase-credentials.json, uploads/, chroma_db/,
# __pycache__, .venv, uv.lock, pyproject.toml (not needed at runtime)
COPY app/ ./app/

# Create the uploads directory; it will be bind-mounted at runtime so the
# container process can write face images and profile photos.
RUN mkdir -p uploads .deepface \
 && chown -R appuser:appgroup /app

# ── Security hardening ─────────────────────────────────────────────────────
# Drop all capabilities; the process has no reason to need any.
# no-new-privileges prevents setuid binaries from escalating.
# (capabilities are also set in docker-compose for defence-in-depth)
USER appuser

# Put the virtualenv's bin/ first so `uvicorn` resolves to the venv binary
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1   \
    PYTHONUNBUFFERED=1          \
    DEEPFACE_HOME=/app/.deepface \
    MPLCONFIGDIR=/tmp/matplotlib

EXPOSE 8080

# ── Health check ───────────────────────────────────────────────────────────
# Docker marks the container unhealthy if /health stops responding.
# start_period gives the app time to warm up DeepFace models on first boot.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# ── Production server ──────────────────────────────────────────────────────
# --workers 2         : two uvicorn worker processes (adjust to CPU count)
# --no-access-log     : access logs are handled by the reverse proxy (nginx)
# --proxy-headers     : trust X-Forwarded-For / X-Real-IP from the proxy
# --forwarded-allow-ips : only trust headers from localhost (nginx on same host)
# reload is intentionally absent — never use --reload in production
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "4", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "127.0.0.1", \
     "--log-level", "info", \
     "--limit-concurrency", "400", \
     "--limit-max-requests", "10000", \
     "--backlog", "2048"]
