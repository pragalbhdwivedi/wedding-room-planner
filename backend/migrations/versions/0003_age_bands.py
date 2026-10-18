"""Explicit adult/child counts without inventing exact ages."""
from alembic import op
import sqlalchemy as sa

revision = "0003_age_bands"
down_revision = "0002_planning"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("guests", sa.Column("age_band", sa.String(8), nullable=False, server_default="unknown"))
    op.create_check_constraint("guest_age_band", "guests", "age_band IN ('adult','child','unknown')")
    op.create_check_constraint("guest_age_band_consistent", "guests", "age IS NULL OR age_band='unknown' OR (age<=10 AND age_band='child') OR (age>10 AND age_band='adult')")


def downgrade():
    op.drop_constraint("guest_age_band_consistent", "guests")
    op.drop_constraint("guest_age_band", "guests")
    op.drop_column("guests", "age_band")
