from typing import Optional

from pydantic import BaseModel, ConfigDict


class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    youtube_video_id: str
    title: str
    url: str
    thumbnail: Optional[str] = None
    channel: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[str] = None
    topic: Optional[str] = None
    completed: bool = False
