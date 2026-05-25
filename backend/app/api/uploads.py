"""
Protected file-serving endpoint for the uploads directory.

Replaces the unauthenticated StaticFiles mount.  All files require a valid
JWT.  Biometric face images additionally require HR Manager level (3+).
Attendance scan images require HR Staff level (2+).

Path-traversal protection is enforced by resolving both the base directory
and the requested path and confirming the latter is strictly inside the former.
"""

import mimetypes
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.security import get_current_employee

router = APIRouter()

# Resolve once at import time — the canonical absolute path of the uploads dir
_UPLOADS_BASE = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
)


def _safe_path(file_path: str) -> str:
    """
    Resolve `file_path` relative to the uploads base directory.

    Raises 403 if the resolved path escapes the base (path-traversal attack).
    Raises 404 if the file does not exist.
    """
    # Resolve symlinks and normalise separators
    full_path = os.path.realpath(os.path.join(_UPLOADS_BASE, file_path))

    # Must be strictly inside _UPLOADS_BASE (trailing sep prevents prefix attack)
    if not full_path.startswith(_UPLOADS_BASE + os.sep):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    if not os.path.isfile(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    return full_path


@router.get(
    "/{file_path:path}",
    include_in_schema=False,
    summary="Serve an uploaded file — requires authentication",
)
def serve_upload(
    file_path: str,
    current_user=Depends(get_current_employee),
):
    """
    Serve a file from the uploads directory with role-based access control.

    Access levels:
      - faces/*        → HR Manager+ (level 3) — biometric data
      - scans/*        → HR Staff+   (level 2) — attendance records
      - profile_photos/* → any authenticated employee (level 1+)
    """
    # Normalise to forward slashes for consistent prefix checks
    normalised = file_path.replace("\\", "/").lstrip("/")

    # ── Biometric face images — HR Manager+ only ──────────────────────────────
    if normalised.startswith("faces/"):
        access_level = current_user.role.access_level if current_user.role else 1
        if access_level < 3:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR Manager access required to view face images.",
            )

    # ── Attendance scan images — HR Staff+ only ───────────────────────────────
    elif normalised.startswith("scans/"):
        access_level = current_user.role.access_level if current_user.role else 1
        if access_level < 2:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HR Staff access required to view scan images.",
            )

    # ── Profile photos — any authenticated employee ───────────────────────────
    # (falls through — authentication is already enforced by Depends above)

    full_path = _safe_path(normalised)

    # Every legitimate upload in this system is an image.
    # Reject anything else so a misconfigured write cannot leak non-image data.
    media_type, _ = mimetypes.guess_type(full_path)
    if not media_type or not media_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    return FileResponse(full_path, media_type=media_type)
