from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserOut(BaseModel):
    """Safe public view of a user. Never contains password_hash."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    college: str
    career_role: Optional[str] = None
    skill_level: Optional[str] = None
    created_at: Optional[datetime] = None


class ProfileOut(BaseModel):
    id: int
    name: str
    email: str
    college: str
    career_role: Optional[str] = None
    skill_level: Optional[str] = None
    skills: List[str] = []
    learning_goals: Optional[str] = None
    available_time: Optional[str] = None
    study_year: Optional[int] = None
    bio: Optional[str] = None
    interests: List[str] = []


def _clean_list(values: Optional[List[str]], max_items: int, max_len: int) -> Optional[List[str]]:
    if values is None:
        return None
    cleaned = []
    for v in values:
        v = str(v).strip()[:max_len]
        if v and v.lower() not in [c.lower() for c in cleaned]:
            cleaned.append(v)
    return cleaned[:max_items]


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    college: Optional[str] = Field(default=None, min_length=2, max_length=150)
    career_role: Optional[str] = Field(default=None, max_length=80)
    skill_level: Optional[Literal["Beginner", "Intermediate", "Advanced"]] = None
    skills: Optional[List[str]] = None
    learning_goals: Optional[str] = Field(default=None, max_length=1000)
    available_time: Optional[str] = Field(default=None, max_length=60)
    study_year: Optional[int] = Field(default=None, ge=1, le=6)
    bio: Optional[str] = Field(default=None, max_length=500)
    interests: Optional[List[str]] = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v):
        return _clean_list(v, 30, 40)

    @field_validator("interests")
    @classmethod
    def clean_interests(cls, v):
        return _clean_list(v, 15, 40)
