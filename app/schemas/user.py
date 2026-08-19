"""Example user validation schemas."""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Example request body demonstrating input validation."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique username for the user.",
        examples=["coach_jane"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address.",
        examples=["coach@example.com"],
    )
