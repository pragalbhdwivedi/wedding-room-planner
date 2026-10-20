"""Optional Superior or Premium room requirement for a family."""
from alembic import op
import sqlalchemy as sa

revision = "0007_family_room_type"
down_revision = "0006_editors_child_beds"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("families", sa.Column("required_room_type", sa.String(8), nullable=True))
    op.create_check_constraint("family_required_room_type", "families", "required_room_type IS NULL OR required_room_type IN ('superior','premium')")


def downgrade():
    op.drop_constraint("family_required_room_type", "families")
    op.drop_column("families", "required_room_type")
