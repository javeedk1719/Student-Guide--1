from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _normalize(url: str) -> str:
    # Supabase sometimes shows postgres://, SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _normalize(settings.DATABASE_URL)
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: one DB session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
