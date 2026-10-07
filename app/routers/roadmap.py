from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import User
from app.schemas.resource import ResourceOut
from app.schemas.roadmap import GenerateRoadmapRequest, RoadmapOut, StepOut
from app.services import roadmap_service, youtube_service

router = APIRouter(prefix="/api/roadmap", tags=["Roadmap"])


@router.post("/generate", response_model=RoadmapOut, status_code=201)
def generate(req: GenerateRoadmapRequest, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return roadmap_service.generate_roadmap(db, user, req)


@router.get("", response_model=Optional[RoadmapOut])
def get_my_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The user's active roadmap, or null if they have not generated one yet."""
    roadmap = roadmap_service.get_active_roadmap(db, user.id)
    return roadmap_service.serialize_roadmap(db, roadmap) if roadmap else None


@router.post("/steps/{step_id}/complete", response_model=RoadmapOut)
def complete_step(step_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return roadmap_service.complete_step(db, user, step_id)


@router.get("/steps/{step_id}/resources", response_model=List[ResourceOut])
def step_resources(step_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """YouTube videos for one step. Searched on first request, then saved and reused."""
    step = roadmap_service.get_owned_step(db, user, step_id)
    if not step.resources:
        step.resources = youtube_service.search_resources(db, step.search_query or f"{step.topic} tutorial")
        db.commit()
    return youtube_service.serialize_resources(db, user.id, list(step.resources))


@router.get("/{roadmap_id}", response_model=RoadmapOut)
def get_roadmap(roadmap_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roadmap = roadmap_service.get_owned_roadmap(db, user, roadmap_id)
    return roadmap_service.serialize_roadmap(db, roadmap)


@router.get("/{roadmap_id}/steps", response_model=List[StepOut])
def get_steps(roadmap_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roadmap = roadmap_service.get_owned_roadmap(db, user, roadmap_id)
    return roadmap_service.serialize_roadmap(db, roadmap).steps
