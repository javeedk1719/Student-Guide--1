"""All settings are read from .env here, once. Nothing else touches os.environ."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Required: the app will not start without these
    DATABASE_URL: str
    SECRET_KEY: str

    # External API keys (empty default so the app still boots without them;
    # the features that need a key return a clear error instead)
    GROQ_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    # Fixed configuration (not secrets)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    COOKIE_SECURE: bool = False
    TIMEZONE: str = "Asia/Kolkata"
    NEWS_REFRESH_HOURS: int = 3

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_must_be_real(cls, v: str) -> str:
        if len(v) < 16 or v == "your_secret_key":
            raise ValueError(
                "SECRET_KEY is too short or still the placeholder. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return v


settings = Settings()
