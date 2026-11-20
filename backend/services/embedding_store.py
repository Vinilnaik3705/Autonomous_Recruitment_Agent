"""Idempotent pgvector storage; concurrency-safe for duplicate worker retries."""

from math import isfinite

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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

    statement = (
        insert(ResumeEmbedding)
        .values(resume_id=resume_id, model_name=model_name, embedding=embedding)
        .on_conflict_do_nothing(constraint="screening_resume_embeddings_resume_id_model_name_key")
    )
    session.execute(statement)
    record = session.scalar(
        select(ResumeEmbedding).where(
            ResumeEmbedding.resume_id == resume_id,
            ResumeEmbedding.model_name == model_name,
        )
    )
    if record is None:
        raise RuntimeError("Embedding could not be retrieved after insert")
    return record
