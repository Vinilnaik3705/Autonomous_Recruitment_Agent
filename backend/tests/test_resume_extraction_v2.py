"""Offline extraction tests using fake structured-output models."""

import pytest

from backend.schemas.resume import ResumeFields
from backend.services.resume_extraction import extract_resume_fields


class FakeChain:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class FakeModel:
    def __init__(self, responses):
        self.chain = FakeChain(responses)

    def with_structured_output(self, schema):
        assert schema is ResumeFields
        return self.chain


def test_valid_extraction():
    model = FakeModel([{"name": "Ada Lovelace", "email": "ada@example.org", "skills": ["Python"]}])
    result = extract_resume_fields("Ada Lovelace Python", model=model)
    assert result.name == "Ada Lovelace"
    assert result.skills == ["Python"]


def test_retry_after_invalid_output():
    model = FakeModel([{"email": "invalid"}, {"email": "ada@example.org"}])
    result = extract_resume_fields("Ada resume", model=model, sleep=lambda _: None)
    assert result.email == "ada@example.org"
    assert model.chain.calls == 2


def test_bounded_failure():
    model = FakeModel([TimeoutError("timeout"), TimeoutError("timeout")])
    with pytest.raises(RuntimeError, match="after 2 attempts"):
        extract_resume_fields("Resume", model=model, max_attempts=2, sleep=lambda _: None)


def test_empty_text_does_not_call_model():
    model = FakeModel([])
    with pytest.raises(ValueError, match="empty"):
        extract_resume_fields("  ", model=model)
    assert model.chain.calls == 0
