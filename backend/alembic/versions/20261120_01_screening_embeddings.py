"""Add isolated resume embeddings table using pgvector.

Revision ID: 20261120_01
Revises:
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "20261120_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "screening_resume_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resume_id", "model_name"),
    )
    op.create_index(
        "ix_screening_resume_embeddings_resume_id",
        "screening_resume_embeddings",
        ["resume_id"],
    )


def downgrade():
    op.drop_index(
        "ix_screening_resume_embeddings_resume_id",
        table_name="screening_resume_embeddings",
    )
    op.drop_table("screening_resume_embeddings")
    # Do not drop vector extension; other tables may depend on it.
