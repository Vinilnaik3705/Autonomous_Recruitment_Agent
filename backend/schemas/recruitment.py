from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field

from backend.orchestration.status import CandidateStatus


class JobInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    required_skills: list[str] = Field(default_factory=list, max_length=100)
    min_experience_years: float | None = Field(default=None, ge=0)
    location: str | None = None
    status: Literal["draft", "open", "closed"] = "open"


class ApplicationReceipt(BaseModel):
    id: int
    job_id: int
    status: CandidateStatus


class StageChange(BaseModel):
    target: CandidateStatus
    scheduled_start: AwareDatetime | None = None
    interviewer_id: int | None = None
    feedback_comments: str | None = Field(default=None, max_length=20000)
    feedback_scores: dict | None = None
    recommendation: Literal["select", "reject", "hold"] | None = None
    offer_text: str | None = Field(default=None, max_length=20000)
    checklist: list[str] = Field(default_factory=list, max_length=50)
    due_date: date | None = None


class Reconciliation(BaseModel):
    delivered: bool
    provider_id: str | None = None
    note: str = Field(min_length=1, max_length=2000)


class InterviewFeedback(BaseModel):
    comments: str = Field(min_length=1, max_length=20000)
    scores: dict[str, Annotated[int, Field(ge=1, le=5)]] = Field(default_factory=dict)
    recommendation: Literal["select", "reject", "hold"]
