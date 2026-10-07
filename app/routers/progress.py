from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import DailyTask, ResourceCompletion, TaskCompletion, User
from app.schemas.progress import (CurrentStep, ProfileSummary, ProgressOut, RoadmapSummary, TaskStats)
from app.services import roadmap_service
from app.services.task_service import today_local

router = APIRouter(prefix="/api/progress", tags=["Progress"])


def _streak(db: Session, user_id: int) -> int:
    """Consecutive days (ending today or yesterday) with a completed daily task."""
    dates = {d for (d,) in db.query(DailyTask.task_date).join(
        TaskCompletion, TaskCompletion.task_id == DailyTask.id).filter(TaskCompletion.user_id == user_id)}
    day = today_local()
    if day not in dates:
        day -= timedelta(days=1)
    streak = 0
    while day in dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


@router.get("", response_model=ProgressOut)
def get_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roadmap_summary = None
    roadmap = roadmap_service.get_active_roadmap(db, user.id)
    if roadmap:
        rm = roadmap_service.serialize_roadmap(db, roadmap)
        pending = [s for s in rm.steps if s.status != "completed"]
        roadmap_summary = RoadmapSummary(
            id=rm.id, role=rm.role, total_steps=rm.total_steps, completed_steps=rm.completed_steps,
            percent=rm.percent,
            current_step=CurrentStep(id=pending[0].id, topic=pending[0].topic,
                                     order_index=pending[0].order_index) if pending else None,
            remaining_topics=[s.topic for s in pending])

    total_tasks = db.query(func.count(DailyTask.id)).filter(DailyTask.user_id == user.id).scalar() or 0
    done_tasks = db.query(func.count(TaskCompletion.id)).filter(TaskCompletion.user_id == user.id).scalar() or 0
    done_resources = db.query(func.count(ResourceCompletion.id)).filter(
        ResourceCompletion.user_id == user.id).scalar() or 0

    return ProgressOut(
        profile=ProfileSummary(name=user.name, college=user.college, career_role=user.career_role,
                               skill_level=user.skill_level),
        roadmap=roadmap_summary,
        tasks=TaskStats(completed=done_tasks, pending=max(total_tasks - done_tasks, 0), total=total_tasks),
        resources_completed=done_resources,
        streak=_streak(db, user.id))
