from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import DailyTask, TaskCompletion, User
from app.schemas.task import TaskOut
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["Daily Tasks"])


@router.get("/today", response_model=TaskOut)
def today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = task_service.get_or_create_today(db, user)
    return task_service.serialize_task(db, task)


@router.get("", response_model=List[TaskOut])
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = (db.query(DailyTask).filter(DailyTask.user_id == user.id)
             .order_by(DailyTask.task_date.desc()).limit(60).all())
    return [task_service.serialize_task(db, t) for t in tasks]


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(DailyTask, task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found.")
    exists = db.query(TaskCompletion).filter(TaskCompletion.task_id == task.id,
                                             TaskCompletion.user_id == user.id).first()
    if not exists:
        db.add(TaskCompletion(task_id=task.id, user_id=user.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return task_service.serialize_task(db, task)
