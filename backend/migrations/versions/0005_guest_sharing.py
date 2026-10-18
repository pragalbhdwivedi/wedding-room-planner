"""Explicit gender and friend-sharing preference; no inferred genders."""
from alembic import op
import sqlalchemy as sa

revision = "0005_guest_sharing"
down_revision = "0004_wedding_details"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("guests",sa.Column("gender",sa.String(16),nullable=False,server_default="unspecified"))
    op.add_column("guests",sa.Column("sharing_mode",sa.String(8),nullable=False,server_default="family"))
    op.create_check_constraint("guest_gender","guests","gender IN ('unspecified','male','female')")
    op.create_check_constraint("guest_sharing_mode","guests","sharing_mode IN ('family','friends')")
    # Preserve the explicit friend classification already supplied on imports.
    op.execute("UPDATE guests SET sharing_mode='friends' WHERE category='guest' AND (tags ? 'role_friend' OR tags ? 'friends')")


def downgrade():
    op.drop_constraint("guest_sharing_mode","guests")
    op.drop_constraint("guest_gender","guests")
    op.drop_column("guests","sharing_mode")
    op.drop_column("guests","gender")
