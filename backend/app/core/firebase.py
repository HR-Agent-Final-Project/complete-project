"""
Firebase Admin SDK — verifies Google ID tokens from frontend.
"""

import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings
import os

_firebase_app = None


def get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if not os.path.exists(cred_path):
        print(f"Firebase credentials not found: {cred_path}")
        return None

    try:
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized.")
        return _firebase_app
    except Exception as e:
        print(f"Firebase init failed: {e}")
        return None


def verify_firebase_token(id_token: str) -> dict:
    """Verify Firebase ID token and return user data."""
    app = get_firebase_app()
    if app is None:
        raise Exception("Firebase not configured.")
    try:
        return auth.verify_id_token(id_token)
    except auth.ExpiredIdTokenError:
        raise Exception("Google session expired. Please sign in again.")
    except auth.InvalidIdTokenError:
        raise Exception("Invalid Google token.")
    except Exception as e:
        raise Exception(f"Token verification failed: {str(e)}")