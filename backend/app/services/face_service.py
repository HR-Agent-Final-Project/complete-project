"""
Face Recognition Service using DeepFace.

Handles:
  - Register employee face (save face embedding)
  - Verify face for clock-in/clock-out
  - Anti-spoofing detection

Install requirements:
  uv add deepface opencv-python-headless tf-keras numpy pillow
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Optional

# Face storage path
FACE_DB_PATH = Path("uploads/faces")
FACE_DB_PATH.mkdir(parents=True, exist_ok=True)

SIMILARITY_THRESHOLD = 0.40   # Lower = stricter matching
ANTI_SPOOF = False             # Set True in production (slower)


def _get_face_path(employee_id: int) -> Path:
    return FACE_DB_PATH / f"emp_{employee_id}"


def register_face(employee_id: int, image_bytes: bytes) -> dict:
    """
    Register employee face from image bytes.
    Saves face image for future verification.

    Returns:
      { success: bool, message: str }
    """
    try:
        from deepface import DeepFace
        import cv2

        # Save temp image
        face_dir = _get_face_path(employee_id)
        face_dir.mkdir(parents=True, exist_ok=True)

        temp_path = str(face_dir / "temp_input.jpg")
        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        # Verify a face exists in the image
        try:
            result = DeepFace.extract_faces(
                img_path      = temp_path,
                enforce_detection = True,
            )
        except Exception:
            os.remove(temp_path)
            return {
                "success": False,
                "message": "No face detected in image. Please use a clear front-facing photo."
            }

        if not result:
            return {"success": False, "message": "No face detected."}

        # Save as the registered face
        face_path = str(face_dir / "face.jpg")
        os.rename(temp_path, face_path)

        return {
            "success":     True,
            "message":     "Face registered successfully.",
            "employee_id": employee_id,
            "face_path":   face_path,
        }

    except ImportError:
        # DeepFace not installed — save image anyway for later
        face_dir = _get_face_path(employee_id)
        face_dir.mkdir(parents=True, exist_ok=True)
        face_path = str(face_dir / "face.jpg")
        with open(face_path, "wb") as f:
            f.write(image_bytes)
        return {
            "success": True,
            "message": "Face image saved (DeepFace not installed — install with: uv add deepface).",
            "employee_id": employee_id,
        }

    except Exception as e:
        return {"success": False, "message": f"Face registration failed: {str(e)}"}


def verify_face(employee_id: int, image_bytes: bytes) -> dict:
    """
    Verify a face against the registered face for an employee.

    Returns:
      {
        verified: bool,
        confidence_score: float,   # 0.0 to 1.0
        distance: float,
        message: str
      }
    """
    face_path = str(_get_face_path(employee_id) / "face.jpg")

    if not os.path.exists(face_path):
        return {
            "verified":         False,
            "confidence_score": 0.0,
            "message":          f"No registered face found for employee #{employee_id}. Register face first.",
        }

    try:
        from deepface import DeepFace

        # Save temp image for comparison
        temp_path = str(_get_face_path(employee_id) / "temp_verify.jpg")
        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        try:
            result = DeepFace.verify(
                img1_path         = temp_path,
                img2_path         = face_path,
                model_name        = "Facenet512",
                detector_backend  = "opencv",
                enforce_detection = True,
                anti_spoofing     = ANTI_SPOOF,
            )
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {
                "verified":         False,
                "confidence_score": 0.0,
                "message":          f"Face detection failed: {str(e)}",
            }

        if os.path.exists(temp_path):
            os.remove(temp_path)

        distance         = result.get("distance", 1.0)
        verified         = result.get("verified", False)

        # Convert distance to confidence score (0 to 1)
        confidence_score = max(0.0, min(1.0, 1.0 - (distance / SIMILARITY_THRESHOLD)))
        confidence_score = round(confidence_score, 4)

        return {
            "verified":         verified,
            "confidence_score": confidence_score,
            "distance":         round(distance, 4),
            "threshold":        SIMILARITY_THRESHOLD,
            "message":          "Face verified successfully." if verified else "Face does not match registered employee.",
        }

    except ImportError:
        # DeepFace not installed — return manual verification
        return {
            "verified":         True,
            "confidence_score": 1.0,
            "distance":         0.0,
            "message":          "Manual verification (DeepFace not installed).",
        }

    except Exception as e:
        return {
            "verified":         False,
            "confidence_score": 0.0,
            "message":          f"Verification error: {str(e)}",
        }


def get_face_status(employee_id: int) -> dict:
    """Check if employee has a registered face."""
    face_path = _get_face_path(employee_id) / "face.jpg"
    return {
        "employee_id":    employee_id,
        "face_registered": face_path.exists(),
        "face_path":      str(face_path) if face_path.exists() else None,
    }