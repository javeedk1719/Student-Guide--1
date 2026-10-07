from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.constants import ROLES, SKILL_LEVELS
from app.database.database import get_db
from app.database.models import CommunityProfile, User
from app.schemas.user import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/api", tags=["Profile"])

USER_FIELDS = {"name", "college", "career_role", "skill_level", "skills", "learning_goals", "available_time"}
COMMUNITY_FIELDS = {"study_year", "bio", "interests"}


def build_profile(user: User) -> ProfileOut:
    cp = user.community_profile
    return ProfileOut(
        id=user.id, name=user.name, email=user.email, college=user.college,
        career_role=user.career_role, skill_level=user.skill_level, skills=user.skills or [],
        learning_goals=user.learning_goals, available_time=user.available_time,
        study_year=cp.study_year if cp else None, bio=cp.bio if cp else None,
        interests=(cp.interests or []) if cp else [])


@router.get("/roles")
def list_roles():
    """Public: the fixed lists used by the registration and profile forms."""
    return {"roles": ROLES, "skill_levels": SKILL_LEVELS}


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    return build_profile(user)


@router.put("/profile", response_model=ProfileOut)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field in USER_FIELDS and value is not None:
            setattr(user, field, value)
        elif field in USER_FIELDS and field in ("career_role", "learning_goals", "available_time"):
            setattr(user, field, None)  # explicit null clears optional text fields

    community_changes = {k: v for k, v in changes.items() if k in COMMUNITY_FIELDS}
    if community_changes:
        cp = user.community_profile
        if cp is None:
            cp = CommunityProfile(user_id=user.id, interests=[])
            db.add(cp)
        for field, value in community_changes.items():
            setattr(cp, field, value)
    db.commit()
    db.refresh(user)
    return build_profile(user)
