"""Record operator verification of ambiguous delivery."""

from alembic import op

revision = "20261120_03"
down_revision = "20261120_02"
branch_labels = depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE recruitment_actions ADD COLUMN reconciled_by integer, ADD COLUMN reconciliation_note text"
    )


def downgrade():
    op.execute(
        "ALTER TABLE recruitment_actions DROP COLUMN reconciliation_note, DROP COLUMN reconciled_by"
    )
