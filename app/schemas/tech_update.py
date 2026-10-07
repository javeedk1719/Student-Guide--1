from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class TechUpdateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    url: str
    published_at: Optional[datetime] = None
    category: Optional[str] = None
    why_it_matters: Optional[str] = None
    relevant_roles: List[str] = []
