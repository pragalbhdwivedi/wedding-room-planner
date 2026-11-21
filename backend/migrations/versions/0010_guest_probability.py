"""Reversible guest archive probability; existing placements remain unchanged."""
from alembic import op
import sqlalchemy as sa

revision = "0010_guest_probability"
down_revision = "0009_guest_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("guests", sa.Column("probability", sa.Integer(), server_default="100", nullable=False))
    op.create_check_constraint("guest_probability_range", "guests", "probability BETWEEN 0 AND 100")


def downgrade():
    op.drop_constraint("guest_probability_range", "guests", type_="check")
    op.drop_column("guests", "probability")
