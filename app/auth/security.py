"""Password hashing (bcrypt) and JWT creation / verification."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import settings


def _prep(password: str) -> bytes:
    # bcrypt only looks at the first 72 bytes
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prep(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prep(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """Return the user id inside a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
