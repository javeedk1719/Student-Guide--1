from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TaskOut(BaseModel):
    id: int
    task_date: date
    title: str
    description: str = ""
    difficulty: str = "easy"
    step_topic: Optional[str] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
