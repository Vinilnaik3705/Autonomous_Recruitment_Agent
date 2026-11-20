"""Explicit, conservative candidate stage transitions.

Rejection and offers require HR approval. No stage changes are performed here;
this module validates requests before a transactional database update.
"""

from enum import Enum


class CandidateStatus(str, Enum):
    APPLIED = "applied"
    SCREENED = "screened"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    FEEDBACK_RECEIVED = "feedback_received"
    SELECTED = "selected"
    REJECTED = "rejected"
    HOLD = "hold"
    OFFER_SENT = "offer_sent"
    ONBOARDING = "onboarding"
    COMPLETE = "complete"


ALLOWED = {
    CandidateStatus.APPLIED: {CandidateStatus.SCREENED},
    CandidateStatus.SCREENED: {CandidateStatus.SHORTLISTED, CandidateStatus.HOLD},
    CandidateStatus.SHORTLISTED: {CandidateStatus.INTERVIEW_SCHEDULED, CandidateStatus.HOLD},
    CandidateStatus.INTERVIEW_SCHEDULED: {CandidateStatus.INTERVIEWED, CandidateStatus.HOLD},
    CandidateStatus.INTERVIEWED: {CandidateStatus.FEEDBACK_RECEIVED},
    CandidateStatus.FEEDBACK_RECEIVED: {CandidateStatus.SELECTED, CandidateStatus.REJECTED, CandidateStatus.HOLD},
    CandidateStatus.SELECTED: {CandidateStatus.OFFER_SENT},
    CandidateStatus.HOLD: {CandidateStatus.SHORTLISTED, CandidateStatus.REJECTED},
    CandidateStatus.OFFER_SENT: {CandidateStatus.ONBOARDING},
    CandidateStatus.ONBOARDING: {CandidateStatus.COMPLETE},
    CandidateStatus.REJECTED: set(),
    CandidateStatus.COMPLETE: set(),
}

APPROVAL_REQUIRED = {
    CandidateStatus.REJECTED,
    CandidateStatus.OFFER_SENT,
}


def validate_transition(current: CandidateStatus, target: CandidateStatus, *, hr_approved: bool = False):
    if target not in ALLOWED[current]:
        raise ValueError(f"Invalid candidate transition: {current.value} -> {target.value}")
    if target in APPROVAL_REQUIRED and not hr_approved:
        raise PermissionError(f"HR approval required before {target.value}")
