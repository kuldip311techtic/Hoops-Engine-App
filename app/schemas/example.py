"""Example request validation schema from project setup ticket."""

from pydantic import BaseModel, EmailStr, Field


class ExampleUser(BaseModel):
    """Example schema demonstrating Pydantic request validation."""

    username: str = Field(
        ...,
        description="Unique username for the account.",
        examples=["coach_jane"],
        min_length=1,
        max_length=64,
    )
    email: EmailStr = Field(
        ...,
        description="User email address.",
        examples=["coach@example.com"],
    )
