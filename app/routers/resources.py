from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import Resource, ResourceCompletion, User
from app.schemas.resource import ResourceOut
from app.services import youtube_service

router = APIRouter(prefix="/api/resources", tags=["YouTube Resources"])


@router.get("/search", response_model=List[ResourceOut])
def search(query: str = Query(min_length=2, max_length=100), user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    resources = youtube_service.search_resources(db, query)
    return youtube_service.serialize_resources(db, user.id, resources)


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(resource_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return youtube_service.serialize_resources(db, user.id, [resource])[0]


@router.post("/{resource_id}/complete", response_model=ResourceOut)
def complete_resource(resource_id: int, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    exists = db.query(ResourceCompletion).filter(ResourceCompletion.user_id == user.id,
                                                 ResourceCompletion.resource_id == resource.id).first()
    if not exists:
        db.add(ResourceCompletion(user_id=user.id, resource_id=resource.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return youtube_service.serialize_resources(db, user.id, [resource])[0]
