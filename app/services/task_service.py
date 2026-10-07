"""Daily tasks: one task per user per day, generated once and then reused."""
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DailyTask, Progress, RoadmapStep, TaskCompletion, User
from app.schemas.task import TaskOut
from app.services import groq_service
from app.services.errors import ExternalServiceError
from app.services.roadmap_service import get_active_roadmap


def today_local() -> date:
    try:
        return datetime.now(ZoneInfo(settings.TIMEZONE)).date()
    except Exception:
        return datetime.utcnow().date()


def _current_step(db: Session, user: User) -> Optional[RoadmapStep]:
    roadmap = get_active_roadmap(db, user.id)
    if roadmap is None:
        return None
    done = {p.step_id for p in db.query(Progress).filter(
        Progress.user_id == user.id, Progress.status == "completed")}
    for step in roadmap.steps:
        if step.id not in done:
            return step
    return roadmap.steps[-1] if roadmap.steps else None


def _generate(user: User, step: Optional[RoadmapStep], recent_titles: list) -> dict:
    topic = step.topic if step else ""
    system = "You create small daily practice tasks for college students. Respond with valid JSON only."
    prompt = (
        f"Student role: {user.career_role}. Skill level: {user.skill_level or 'Beginner'}.\n"
        f"Current learning topic: {topic or 'general fundamentals for the role'}.\n"
        f"Recent task titles (do NOT repeat): {recent_titles or 'none'}.\n"
        "Create ONE task that takes 20-40 minutes. Examples: solve a problem, write a SQL query, build a "
        "small endpoint, fix a small bug, explain a concept in your own words, practice yesterday's topic.\n"
        'Return JSON: {"title": "short title", "description": "2-3 clear sentences", '
        '"difficulty": "easy" or "medium"}'
    )
    data = groq_service.chat_json(system, prompt, temperature=0.8, max_tokens=500)
    title = str(data.get("title") or "").strip()[:200]
    if not title:
        raise ExternalServiceError("Empty task from AI.")
    difficulty = str(data.get("difficulty") or "easy").lower()
    return {"title": title, "description": str(data.get("description") or "").strip()[:1500],
            "difficulty": difficulty if difficulty in ("easy", "medium", "hard") else "easy"}


def _fallback(user: User, step: Optional[RoadmapStep]) -> dict:
    """Used when the AI is unavailable. Built from the student's own roadmap data."""
    if step and step.practice_task:
        return {"title": f"Practice: {step.topic}", "description": step.practice_task, "difficulty": "easy"}
    if step:
        return {"title": f"Review: {step.topic}",
                "description": f"Spend 30 minutes revising {step.topic} and write 5 bullet points that "
                               "explain it in your own words.", "difficulty": "easy"}
    return {"title": f"Explore the {user.career_role} path",
            "description": f"Read one beginner article about what a {user.career_role} does and note "
                           "three tools or skills you want to learn first.", "difficulty": "easy"}


def get_or_create_today(db: Session, user: User) -> DailyTask:
    if not user.career_role:
        raise HTTPException(status_code=400, detail="Choose a career role in your profile to get daily tasks.")
    today = today_local()
    task = db.query(DailyTask).filter(DailyTask.user_id == user.id, DailyTask.task_date == today).first()
    if task:
        return task

    step = _current_step(db, user)
    recent = [t for (t,) in db.query(DailyTask.title).filter(DailyTask.user_id == user.id)
              .order_by(DailyTask.id.desc()).limit(7)]
    try:
        content = _generate(user, step, recent)
    except ExternalServiceError:
        content = _fallback(user, step)

    task = DailyTask(user_id=user.id, step_id=step.id if step else None, task_date=today, **content)
    db.add(task)
    try:
        db.commit()
    except IntegrityError:  # two tabs asked at once: use the one that won
        db.rollback()
        task = db.query(DailyTask).filter(DailyTask.user_id == user.id, DailyTask.task_date == today).first()
    return task


def serialize_task(db: Session, task: DailyTask) -> TaskOut:
    comp = db.query(TaskCompletion).filter(TaskCompletion.task_id == task.id,
                                           TaskCompletion.user_id == task.user_id).first()
    return TaskOut(id=task.id, task_date=task.task_date, title=task.title,
                   description=task.description or "", difficulty=task.difficulty or "easy",
                   step_topic=task.step.topic if task.step else None,
                   completed=comp is not None, completed_at=comp.completed_at if comp else None)
