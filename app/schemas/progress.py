from typing import List, Optional

from pydantic import BaseModel


class ProfileSummary(BaseModel):
    name: str
    college: str
    career_role: Optional[str] = None
    skill_level: Optional[str] = None


class CurrentStep(BaseModel):
    id: int
    topic: str
    order_index: int


class RoadmapSummary(BaseModel):
    id: int
    role: str
    total_steps: int
    completed_steps: int
    percent: int
    current_step: Optional[CurrentStep] = None
    remaining_topics: List[str] = []


class TaskStats(BaseModel):
    completed: int
    pending: int
    total: int


class ProgressOut(BaseModel):
    profile: ProfileSummary
    roadmap: Optional[RoadmapSummary] = None
    tasks: TaskStats
    resources_completed: int
    streak: int
