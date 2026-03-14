"""
tools/face_recognition_tools.py
────────────────────────────────
DeepFace + OpenCV tools for the Attendance and Detection agents.
Each tool returns JSON — no decisions, just raw match/liveness data.
"""

import json
import base64
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from langchain.tools import tool
from config.settings import settings


def _decode_image(image_base64: str) -> str:
    """Decode base64 image to a temp file, return file path."""
    img_data   = base64.b64decode(image_base64)
    tmp        = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.write(img_data)
    tmp.close()
    return tmp.name


@tool
def check_liveness(image_base64: str) -> str:
    """
    Anti-spoofing liveness detection using DeepFace.
    Rejects printed photos and screen captures.
    Returns liveness score and pass/fail result.
    """
    try:
        from deepface import DeepFace
        img_path = _decode_image(image_base64)
        result   = DeepFace.extract_faces(
            img_path          = img_path,
            enforce_detection = True,
            anti_spoofing     = True,
        )
        os.unlink(img_path)
        if not result:
            return json.dumps({"passed": False, "message": "No face detected."})
        face       = result[0]
        is_real    = face.get("is_real", True)
        confidence = face.get("antispoof_score", 1.0)
        return json.dumps({
            "passed":     is_real,
            "score":      round(float(confidence), 4),
            "message":    "Live face confirmed." if is_real else "Spoofing detected.",
        })
    except ImportError:
        # DeepFace not installed — mock for development
        return json.dumps({"passed": True, "score": 0.95, "message": "Mock liveness passed."})
    except Exception as e:
        return json.dumps({"passed": False, "message": str(e)})


@tool
def match_employee_face(image_base64: str, employee_id: str) -> str:
    """
    Verify that the face in the image matches the stored face for a given employee.
    Uses DeepFace.verify() with Facenet512 model.
    Returns: matched, confidence score, distance.
    """
    stored_path = Path(settings.FACE_UPLOADS_DIR) / f"emp_{employee_id}" / "face.jpg"
    if not stored_path.exists():
        return json.dumps({
            "matched":   False,
            "message":   f"No stored face found for {employee_id}. Please register face first.",
        })
    try:
        from deepface import DeepFace
        img_path = _decode_image(image_base64)
        result   = DeepFace.verify(
            img1_path    = img_path,
            img2_path    = str(stored_path),
            model_name   = settings.FACE_MODEL,
            enforce_detection = True,
        )
        os.unlink(img_path)
        confidence = 1.0 - result.get("distance", 1.0)
        return json.dumps({
            "matched":    result.get("verified", False),
            "confidence": round(float(confidence), 4),
            "distance":   round(float(result.get("distance", 1.0)), 4),
            "model":      settings.FACE_MODEL,
        })
    except ImportError:
        return json.dumps({"matched": True, "confidence": 0.92, "distance": 0.08, "model": "mock"})
    except Exception as e:
        return json.dumps({"matched": False, "confidence": 0.0, "message": str(e)})


@tool
def identify_unknown_face(image_base64: str) -> str:
    """
    Scan all registered employee faces to identify an unknown person.
    Used by Detection Agent when employee_id is not known.
    Returns: best match employee_id and confidence, or 'unregistered'.
    """
    faces_dir = Path(settings.FACE_UPLOADS_DIR)
    if not faces_dir.exists():
        return json.dumps({"identified": False, "message": "Face library not set up."})

    best_match      = None
    best_confidence = 0.0

    try:
        from deepface import DeepFace
        img_path = _decode_image(image_base64)

        for emp_dir in faces_dir.iterdir():
            face_path = emp_dir / "face.jpg"
            if not face_path.exists():
                continue
            try:
                result     = DeepFace.verify(img_path, str(face_path),
                                             model_name=settings.FACE_MODEL,
                                             enforce_detection=False)
                confidence = 1.0 - result.get("distance", 1.0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match      = emp_dir.name.replace("emp_", "")
            except Exception:
                continue

        os.unlink(img_path)

        threshold = settings.FACE_CONFIDENCE_THRESHOLD
        return json.dumps({
            "identified":  best_match is not None and best_confidence >= threshold,
            "employee_id": best_match if best_confidence >= threshold else None,
            "confidence":  round(best_confidence, 4),
            "is_registered": best_confidence >= threshold,
        })
    except ImportError:
        return json.dumps({"identified": False, "is_registered": False,
                           "message": "DeepFace not installed — mock mode."})
    except Exception as e:
        return json.dumps({"identified": False, "message": str(e)})


@tool
def save_employee_face(employee_id: str, image_base64: str) -> str:
    """
    Register / update a face photo for an employee.
    Saves to uploads/faces/emp_{id}/face.jpg
    """
    save_dir = Path(settings.FACE_UPLOADS_DIR) / f"emp_{employee_id}"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / "face.jpg"
    try:
        img_data = base64.b64decode(image_base64)
        with open(save_path, "wb") as f:
            f.write(img_data)
        return json.dumps({"success": True, "path": str(save_path)})
    except Exception as e:
        return json.dumps({"success": False, "message": str(e)})
