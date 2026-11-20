"""Deterministic screening scores; never auto-reject candidates.

Scores are a review aid, not a hiring decision. Weights are explicit and
must be evaluated on a labeled sample set before production use.
"""

from math import isfinite, sqrt

from pydantic import BaseModel, Field

DIMENSIONS = 384


class ScreeningScore(BaseModel):
    semantic_score: float = Field(ge=0, le=1)
    skill_score: float = Field(ge=0, le=1)
    combined_score: float = Field(ge=0, le=1)
    matched_skills: list[str]
    missing_skills: list[str]


def cosine_score(left: list[float], right: list[float]) -> float:
    if len(left) != DIMENSIONS or len(right) != DIMENSIONS:
        raise ValueError(f"Both embeddings must contain {DIMENSIONS} dimensions")
    if not all(isfinite(x) for x in left + right):
        raise ValueError("Embeddings must contain finite numbers")
    norm_left = sqrt(sum(x * x for x in left))
    norm_right = sqrt(sum(x * x for x in right))
    if not norm_left or not norm_right:
        raise ValueError("Zero-length embedding cannot be compared")
    similarity = sum(x * y for x, y in zip(left, right)) / (norm_left * norm_right)
    return max(0.0, min(1.0, similarity))


def score_candidate(
    resume_embedding: list[float],
    job_embedding: list[float],
    candidate_skills: list[str],
    required_skills: list[str],
    *,
    semantic_weight: float = 0.7,
) -> ScreeningScore:
    if not 0 <= semantic_weight <= 1:
        raise ValueError("semantic_weight must be between 0 and 1")
    required = {s.strip().casefold() for s in required_skills if s.strip()}
    candidate = {s.strip().casefold() for s in candidate_skills if s.strip()}
    matched = sorted(required & candidate)
    missing = sorted(required - candidate)
    semantic = cosine_score(resume_embedding, job_embedding)
    # No specified skills means skill scoring is not applicable.
    skill = len(matched) / len(required) if required else 1.0
    weight = semantic_weight if required else 1.0
    combined = weight * semantic + (1 - weight) * skill
    return ScreeningScore(
        semantic_score=round(semantic, 4),
        skill_score=round(skill, 4),
        combined_score=round(combined, 4),
        matched_skills=matched,
        missing_skills=missing,
    )
