"""
Start the HRAgent backend server.
Run from the backend/ directory:

    python run.py

Or with uvicorn directly:

    uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level="debug" if settings.DEBUG else "info",
    )
