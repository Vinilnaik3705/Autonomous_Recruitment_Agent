"""Stage-transition safety tests."""

import pytest

from backend.orchestration.status import CandidateStatus as S, validate_transition


def test_normal_progression():
    validate_transition(S.APPLIED, S.SCREENED)
    validate_transition(S.SELECTED, S.OFFER_SENT, hr_approved=True)


def test_rejection_requires_approval():
    with pytest.raises(PermissionError):
        validate_transition(S.FEEDBACK_RECEIVED, S.REJECTED)


def test_no_rejection_reversal():
    with pytest.raises(ValueError):
        validate_transition(S.REJECTED, S.ONBOARDING)


def test_offer_requires_approval():
    with pytest.raises(PermissionError):
        validate_transition(S.SELECTED, S.OFFER_SENT)
