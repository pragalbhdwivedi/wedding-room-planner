"""Private invitation context and local celebration times."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_wedding_details"
down_revision = "0003_age_bands"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("wedding_details", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("data", postgresql.JSONB(), nullable=False))
    op.add_column("function_events", sa.Column("start_time", sa.String(5), nullable=True))
    op.add_column("function_events", sa.Column("venue", sa.String(150), nullable=False, server_default=""))
    op.add_column("function_events", sa.Column("source_url", sa.String(250), nullable=False, server_default=""))
    op.create_check_constraint("event_local_time", "function_events", "start_time IS NULL OR start_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON wedding_details TO planner_app")


def downgrade():
    op.drop_constraint("event_local_time", "function_events")
    for name in ["source_url", "venue", "start_time"]: op.drop_column("function_events", name)
    op.drop_table("wedding_details")
