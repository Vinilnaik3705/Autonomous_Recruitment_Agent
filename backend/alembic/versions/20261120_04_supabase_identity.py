"""Link hosted identities to stable local user IDs, independent of email."""
from alembic import op

revision = "20261120_04"
down_revision = "20261120_03"
branch_labels = depends_on = None


def upgrade():
    op.execute("""CREATE TABLE recruitment_identities (
        issuer text NOT NULL, subject uuid NOT NULL, user_id integer NOT NULL UNIQUE,
        PRIMARY KEY (issuer,subject))""")


def downgrade():
    op.drop_table("recruitment_identities")
