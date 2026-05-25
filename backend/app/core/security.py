"""
JWT security utilities and route dependencies.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Separate signing secrets per token purpose — tokens signed for one purpose
# cannot be decoded or reused for any other purpose.
_RESET_SECRET    = settings.SECRET_KEY + "_password_reset"
_APPROVAL_SECRET = settings.SECRET_KEY + "_registration_approval"

# Pre-computed at startup — used as the hash to verify against when no account
# is found for a given identifier.  Running bcrypt even on a miss keeps the
# response time indistinguishable from a wrong-password failure, preventing
# timing-based account enumeration.
_DUMMY_HASH: str = pwd_context.hash("__dummy_sentinel_not_a_real_password__")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access", "jti": str(uuid.uuid4())})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_approval_token(data: dict, expires_hours: int = 24) -> str:
    """Create a token for email approval links.

    Signed with a separate secret so it cannot be decoded by decode_token()
    and cannot be used as a bearer token on any protected route.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=expires_hours)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, _APPROVAL_SECRET, algorithm=settings.ALGORITHM
    )


def decode_approval_token(token: str) -> dict:
    """Decode a registration-approval token.  Raises a plain dict error (not
    HTTPException) so the caller can return an HTML error page instead."""
    try:
        payload = jwt.decode(token, _APPROVAL_SECRET, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise ValueError("Invalid or expired approval token.")
    if payload.get("type") != "registration_approval":
        raise ValueError("Token is not a registration approval token.")
    return payload


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_password_reset_token(employee_id: int) -> str:
    """Create a short-lived token exclusively for password resets.

    Uses a separate signing secret so the token cannot be used as a bearer
    token on any protected route, even if an attacker intercepts it.
    """
    expire = datetime.utcnow() + timedelta(minutes=30)
    payload = {
        "sub":  str(employee_id),
        "type": "password_reset",
        "exp":  expire,
    }
    return jwt.encode(payload, _RESET_SECRET, algorithm=settings.ALGORITHM)


def decode_password_reset_token(token: str) -> dict:
    """Decode a password-reset token.  Raises 400 if invalid, expired, or
    the token was signed with the regular access-token secret."""
    try:
        payload = jwt.decode(token, _RESET_SECRET, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )
    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token.",
        )
    return payload


_BLACKLIST_PREFIX = "blacklist:"


def blacklist_token(jti: str, exp: int) -> None:
    """Add a token's JTI to the Redis blacklist until it naturally expires.

    TTL is set to the token's remaining lifetime so the key self-cleans.
    If Redis is unavailable the failure is logged but does not raise — the
    token is time-limited anyway and the frontend will discard it on logout.
    """
    from app.core.redis_client import get_redis
    r = get_redis()
    if r is None:
        import logging
        logging.getLogger(__name__).warning(
            "Token blacklist: Redis unavailable — JTI %s could not be revoked.", jti
        )
        return
    try:
        remaining = int(exp - datetime.utcnow().timestamp())
        if remaining > 0:
            r.setex(f"{_BLACKLIST_PREFIX}{jti}", remaining, "1")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Token blacklist: failed to store JTI %s: %s", jti, exc
        )


def is_token_blacklisted(jti: Optional[str]) -> bool:
    """Return True if this JTI has been revoked.

    Fails open (returns False) on Redis errors — a logged warning is raised
    instead of rejecting all requests during an outage.
    """
    if not jti:
        return False
    from app.core.redis_client import get_redis
    r = get_redis()
    if r is None:
        return False
    try:
        return r.exists(f"{_BLACKLIST_PREFIX}{jti}") > 0
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Token blacklist: Redis check failed for JTI %s: %s", jti, exc
        )
        return False


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_employee(  # noqa: C901
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Inject current employee into any protected route."""
    from app.models.employee import Employee

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type."
        )

    if is_token_blacklisted(payload.get("jti")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    employee_id = payload.get("sub")
    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject."
        )

    employee = db.query(Employee).filter(
        Employee.id == int(employee_id),
        Employee.is_active == True
    ).first()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee not found or deactivated."
        )
    return employee


def require_role(min_level: int):
    """
    Role checker dependency.
    Usage: Depends(require_role(3)) = HR Manager and above only
    """
    def checker(current_user=Depends(get_current_employee)):
        user_level = current_user.role.access_level if current_user.role else 1
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Need level {min_level}, you have level {user_level}."
            )
        return current_user
    return checker


# ── Shortcut dependencies ─────────────────────────────────────────────────────
def get_hr_staff(u=Depends(require_role(2))):
    return u

def get_hr_manager(u=Depends(require_role(3))):
    return u

def get_admin(u=Depends(require_role(4))):
    return u