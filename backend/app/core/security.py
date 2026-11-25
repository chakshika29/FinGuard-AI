"""Authentication, password hashing, RBAC, and sensitive data masking."""

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import get_db

ROLE_ADMIN = "Administrator"
ROLE_STEWARD = "Data Steward"
ROLE_ANALYST = "Risk Analyst"
ALL_ROLES = [ROLE_ADMIN, ROLE_STEWARD, ROLE_ANALYST]

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, role: str, user_id: int, expires_minutes: int | None = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    expire_delta = timedelta(minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "uid": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """FastAPI dependency returning the authenticated active user."""
    from backend.app.models.metadata import User

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
        )
    payload = decode_access_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found.")
    return user


def require_roles(*allowed_roles: str) -> Callable:
    """Dependency factory enforcing RBAC role membership."""

    def _checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' lacks permission. Required: {', '.join(allowed_roles)}.",
            )
        return current_user

    return _checker


def mask_card_token(token: str | None) -> str:
    """Mask synthetic card token while preserving last 4 characters."""
    if not token:
        return "****"
    s = str(token)
    if len(s) <= 4:
        return "****"
    return f"{'*' * max(4, len(s) - 4)}{s[-4:]}"


def mask_identifier(value: str | None, keep_prefix: int = 4, keep_suffix: int = 2) -> str:
    """Mask sensitive identifier for non-privileged views."""
    if not value:
        return "***"
    s = str(value)
    if len(s) <= keep_prefix + keep_suffix:
        return "*" * len(s)
    return f"{s[:keep_prefix]}***{s[-keep_suffix:]}"
