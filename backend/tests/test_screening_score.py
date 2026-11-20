"""Pure offline matching tests; no model download or database required."""

import pytest

from backend.services.screening_score import cosine_score, score_candidate

A = [1.0] + [0.0] * 383
B = [0.0, 1.0] + [0.0] * 382


def test_identical_embeddings():
    assert cosine_score(A, A) == pytest.approx(1.0)


def test_orthogonal_embeddings():
    assert cosine_score(A, B) == pytest.approx(0.0)


def test_skill_overlap():
    result = score_candidate(A, A, ["Python", "SQL"], ["python", "docker"])
    assert result.matched_skills == ["python"]
    assert result.missing_skills == ["docker"]
    assert result.skill_score == 0.5
    assert result.combined_score == 0.85


def test_no_required_skills_uses_semantic_only():
    assert score_candidate(A, B, [], []).combined_score == 0.0


def test_invalid_dimension():
    with pytest.raises(ValueError, match="384"):
        cosine_score([1.0], A)


def test_zero_vector_rejected():
    with pytest.raises(ValueError, match="Zero-length"):
        cosine_score([0.0] * 384, A)


def test_weight_validation():
    with pytest.raises(ValueError, match="semantic_weight"):
        score_candidate(A, A, [], [], semantic_weight=1.5)
