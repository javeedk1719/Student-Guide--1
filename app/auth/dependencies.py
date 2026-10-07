"""Dependencies that turn a request into a logged-in User."""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database.database import get_db
from app.database.models import User

COOKIE_NAME = "access_token"


def _token_from_request(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Returns the user or None. Never raises. Used for HTML page redirects."""
    token = _token_from_request(request)
    if not token:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        return None
    return db.get(User, user_id)


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    """Use on every private API endpoint."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated or session expired. Please log in again.",
        )
    return user
