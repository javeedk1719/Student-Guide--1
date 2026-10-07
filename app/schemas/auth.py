from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    college: str = Field(min_length=2, max_length=150)
    career_role: Optional[str] = Field(default=None, max_length=80)

    @field_validator("name", "college")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("must be at least 2 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)
