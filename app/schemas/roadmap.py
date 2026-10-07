from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenerateRoadmapRequest(BaseModel):
    """Every field is optional: missing ones fall back to the user's profile."""
    role: Optional[str] = Field(default=None, max_length=80)
    skill_level: Optional[str] = Field(default=None, max_length=20)
    existing_skills: Optional[List[str]] = None
    goals: Optional[str] = Field(default=None, max_length=1000)


class StepOut(BaseModel):
    id: int
    order_index: int
    topic: str
    why: str = ""
    concepts: List[str] = []
    after_learning: str = ""
    project_idea: str = ""
    practice_task: str = ""
    expected_outcome: str = ""
    search_query: str = ""
    status: str = "not_started"
    completed_at: Optional[datetime] = None


class RoadmapOut(BaseModel):
    id: int
    role: str
    skill_level: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    total_steps: int
    completed_steps: int
    percent: int
    steps: List[StepOut]


# ---- Validation of what the Groq model returns ----
def _to_text(v) -> str:
    return "" if v is None else str(v).strip()


class GroqStep(BaseModel):
    model_config = ConfigDict(extra="ignore")

    topic: str
    why: str = ""
    concepts: List[str] = []
    after_learning: str = ""
    project_idea: str = ""
    practice_task: str = ""
    expected_outcome: str = ""
    search_query: str = ""

    @field_validator("topic", "why", "after_learning", "project_idea", "practice_task",
                     "expected_outcome", "search_query", mode="before")
    @classmethod
    def text(cls, v):
        return _to_text(v)

    @field_validator("concepts", mode="before")
    @classmethod
    def concepts_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            v = [p for p in v.replace("\n", ",").split(",")]
        return [str(c).strip() for c in v if str(c).strip()][:12]


class GroqRoadmap(BaseModel):
    model_config = ConfigDict(extra="ignore")

    steps: List[GroqStep] = Field(min_length=3, max_length=20)
