"""Full editor accounts and explicit separate beds for young children."""
from alembic import op
import sqlalchemy as sa

revision = "0006_editors_child_beds"
down_revision = "0005_guest_sharing"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("user_role", "users")
    op.create_check_constraint("user_role", "users", "role IN ('owner','editor','family','reception')")
    op.add_column("assignments", sa.Column("separate_bed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("assignments", "separate_bed")
    op.drop_constraint("user_role", "users")
    op.create_check_constraint("user_role", "users", "role IN ('owner','family','reception')")
