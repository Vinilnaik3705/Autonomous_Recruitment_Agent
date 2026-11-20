"""Additive ORM model for Phase 2 embeddings.

The existing legacy resume tables are not modified here. Alembic must
create this table before any persistence code can use it.
"""

from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ScreeningBase(DeclarativeBase):
    pass


class ResumeEmbedding(ScreeningBase):
    __tablename__ = "screening_resume_embeddings"
    __table_args__ = (UniqueConstraint("resume_id", "model_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
