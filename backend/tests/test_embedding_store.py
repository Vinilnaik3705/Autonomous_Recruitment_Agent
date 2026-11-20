"""Validation tests run without a database connection."""

import pytest

from backend.services.embedding_store import save_embedding


def test_rejects_invalid_resume_id():
    with pytest.raises(ValueError, match="positive"):
        save_embedding(None, resume_id=0, embedding=[0.1] * 384)


def test_rejects_wrong_dimension():
    with pytest.raises(ValueError, match="384"):
        save_embedding(None, resume_id=1, embedding=[0.1] * 3)


def test_rejects_non_finite_vector():
    with pytest.raises(ValueError, match="finite"):
        save_embedding(None, resume_id=1, embedding=[float("nan")] * 384)


def test_rejects_other_model():
    with pytest.raises(ValueError, match="MiniLM"):
        save_embedding(None, resume_id=1, embedding=[0.1] * 384, model_name="other")
