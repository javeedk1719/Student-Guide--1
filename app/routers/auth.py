from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import COOKIE_NAME, get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import settings
from app.database.database import get_db
from app.database.models import CommunityProfile, User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Used to make "unknown email" take as long as "wrong password"
_DUMMY_HASH = hash_password("not-a-real-password")


def _set_login_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_token(user_id),
        httponly=True,                      # JavaScript cannot read it (protects against XSS theft)
        samesite="lax",                     # not sent on cross-site POSTs (CSRF protection)
        secure=settings.COOKIE_SECURE,      # True on HTTPS deployments
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(name=data.name, email=email, password_hash=hash_password(data.password),
                college=data.college, career_role=data.career_role or None, skills=[])
    db.add(user)
    try:
        db.flush()
        db.add(CommunityProfile(user_id=user.id, interests=[]))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from None
    db.refresh(user)
    _set_login_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserOut)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if user is None:
        verify_password(data.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    _set_login_cookie(response, user.id)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
