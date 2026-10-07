from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CommunityUserOut(BaseModel):
    """What other students can see. No email, no password."""
    id: int
    name: str
    college: str
    career_role: Optional[str] = None
    skill_level: Optional[str] = None
    study_year: Optional[int] = None
    relation: Optional[str] = None  # senior | junior | peer (relative to the viewer)
    bio: Optional[str] = None
    interests: List[str] = []


class PostCreate(BaseModel):
    type: Literal["question", "resource", "project_idea", "discussion"]
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=3000)
    role_tag: Optional[str] = Field(default=None, max_length=80)

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("must be at least 3 characters")
        return v


class PostOut(BaseModel):
    id: int
    author_id: int
    author_name: str
    author_role: Optional[str] = None
    college: str
    type: str
    title: str
    body: str
    role_tag: Optional[str] = None
    created_at: Optional[datetime] = None
    is_mine: bool = False
