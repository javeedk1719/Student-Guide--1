"""All database tables. Relationships are described at the bottom of each class."""
from datetime import datetime, timezone

from sqlalchemy import (JSON, Column, Date, DateTime, ForeignKey, Integer, String,
                        Table, Text, UniqueConstraint)
from sqlalchemy.orm import relationship

from app.database.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Many-to-many link: a roadmap step has several videos, a video can serve several steps
step_resources = Table(
    "step_resources",
    Base.metadata,
    Column("step_id", Integer, ForeignKey("roadmap_steps.id", ondelete="CASCADE"), primary_key=True),
    Column("resource_id", Integer, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    college = Column(String(150), nullable=False, default="")
    career_role = Column(String(80))
    skill_level = Column(String(20), default="Beginner")
    skills = Column(JSON, default=list)
    learning_goals = Column(Text)
    available_time = Column(String(60))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    roadmaps = relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    daily_tasks = relationship("DailyTask", back_populates="user", cascade="all, delete-orphan")
    task_completions = relationship("TaskCompletion", back_populates="user", cascade="all, delete-orphan")
    resource_completions = relationship("ResourceCompletion", back_populates="user", cascade="all, delete-orphan")
    community_profile = relationship("CommunityProfile", back_populates="user", uselist=False,
                                     cascade="all, delete-orphan")
    posts = relationship("CommunityPost", back_populates="author", cascade="all, delete-orphan")


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(80), nullable=False)
    skill_level = Column(String(20))
    status = Column(String(20), default="active", nullable=False)  # active | archived
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="roadmaps")
    steps = relationship("RoadmapStep", back_populates="roadmap", cascade="all, delete-orphan",
                         order_by="RoadmapStep.order_index")


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)
    topic = Column(String(150), nullable=False)
    why = Column(Text, default="")
    concepts = Column(JSON, default=list)
    after_learning = Column(Text, default="")
    project_idea = Column(Text, default="")
    practice_task = Column(Text, default="")
    expected_outcome = Column(Text, default="")
    search_query = Column(String(150), default="")

    roadmap = relationship("Roadmap", back_populates="steps")
    resources = relationship("Resource", secondary=step_resources)


class Resource(Base):
    """A cached YouTube video."""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    youtube_video_id = Column(String(30), unique=True, index=True, nullable=False)
    title = Column(String(300), nullable=False)
    url = Column(String(300), nullable=False)
    thumbnail = Column(String(300))
    channel = Column(String(200))
    description = Column(Text)
    published_at = Column(String(40))
    topic = Column(String(150))
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Progress(Base):
    """One row per (user, roadmap step)."""
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "step_id", name="uq_progress_user_step"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = Column(Integer, ForeignKey("roadmap_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="not_started", nullable=False)  # not_started | in_progress | completed
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="progress_records")
    step = relationship("RoadmapStep")


class ResourceCompletion(Base):
    __tablename__ = "resource_completions"
    __table_args__ = (UniqueConstraint("user_id", "resource_id", name="uq_resource_completion"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="resource_completions")


class DailyTask(Base):
    __tablename__ = "daily_tasks"
    __table_args__ = (UniqueConstraint("user_id", "task_date", name="uq_task_user_date"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = Column(Integer, ForeignKey("roadmap_steps.id", ondelete="SET NULL"))
    task_date = Column(Date, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    difficulty = Column(String(20), default="easy")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="daily_tasks")
    step = relationship("RoadmapStep")
    completions = relationship("TaskCompletion", back_populates="task", cascade="all, delete-orphan")


class TaskCompletion(Base):
    __tablename__ = "task_completions"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_completion_task_user"),)

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("daily_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), default=utcnow)

    task = relationship("DailyTask", back_populates="completions")
    user = relationship("User", back_populates="task_completions")


class TechUpdate(Base):
    """Shared cache of NewsAPI articles plus the AI explanation (same for every user)."""
    __tablename__ = "tech_updates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(400), nullable=False)
    description = Column(Text)
    source = Column(String(150))
    url = Column(String(600), unique=True, nullable=False)
    published_at = Column(DateTime(timezone=True), index=True)
    category = Column(String(60))
    why_it_matters = Column(Text)
    relevant_roles = Column(JSON, default=list)
    fetched_at = Column(DateTime(timezone=True), default=utcnow, index=True)


class CommunityProfile(Base):
    __tablename__ = "community_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    study_year = Column(Integer)  # 1..6, used to decide senior / junior / peer
    interests = Column(JSON, default=list)
    bio = Column(Text)

    user = relationship("User", back_populates="community_profile")


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    college = Column(String(150), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # question | resource | project_idea | discussion
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    role_tag = Column(String(80))
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    author = relationship("User", back_populates="posts")
