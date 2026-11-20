"""Transactional persistence for one embedding per resume and model.

This module does not re-encode existing resumes; the caller supplies the
already-computed vector. Call from a worker after parsing and extraction.
"""

from math import isfinite

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.embeddings.provider import DIMENSIONS, MODEL_NAME
from backend.models.screening_embedding import ResumeEmbedding


def save_embedding(
    session: Session,
    *,
    resume_id: int,
    embedding: list[float],
    model_name: str = MODEL_NAME,
) -> ResumeEmbedding:
    if resume_id <= 0:
        raise ValueError("resume_id must be positive")
    if len(embedding) != DIMENSIONS or not all(isfinite(x) for x in embedding):
        raise ValueError(f"Embedding must contain {DIMENSIONS} finite values")
    if model_name != MODEL_NAME:
        raise ValueError("This database is configured for the MiniLM embedding model")

    existing = session.scalar(
        select(ResumeEmbedding).where(
            ResumeEmbedding.resume_id == resume_id,
            ResumeEmbedding.model_name == model_name,
        )
    )
    if existing is not None:
        return existing

    record = ResumeEmbedding(
        resume_id=resume_id, model_name=model_name, embedding=embedding
    )
    session.add(record)
    session.flush()
    return record
