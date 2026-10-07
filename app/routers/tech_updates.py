from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import TechUpdate, User
from app.schemas.tech_update import TechUpdateOut
from app.services import news_service

router = APIRouter(prefix="/api/tech-updates", tags=["Tech Updates"])


@router.get("", response_model=List[TechUpdateOut])
def list_updates(role: Optional[str] = Query(default=None, max_length=80),
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return news_service.get_updates(db, role=role)


@router.get("/{update_id}", response_model=TechUpdateOut)
def get_update(update_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    update = db.get(TechUpdate, update_id)
    if update is None:
        raise HTTPException(status_code=404, detail="Update not found.")
    return update
