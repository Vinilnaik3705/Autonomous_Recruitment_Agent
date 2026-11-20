"""Validated output for the resume-screening extraction step."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ResumeFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: EmailStr | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
