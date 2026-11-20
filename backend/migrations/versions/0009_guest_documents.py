"""Authenticated guest ID images and Reception PDF access."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_guest_documents"
down_revision = "0008_fixed_wyndham_inventory"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("guest_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guest_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("guests.id", ondelete="CASCADE"), nullable=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("octet_length(content) BETWEEN 1 AND 5242880", name="guest_document_size"))
    op.create_index("ix_guest_documents_guest_id", "guest_documents", ["guest_id"])
    op.create_index("guest_document_source", "guest_documents", ["guest_id", "source_hash"], unique=True)
    op.create_index("unmatched_document_source", "guest_documents", ["source_hash"], unique=True, postgresql_where=sa.text("guest_id IS NULL"))
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON guest_documents TO planner_app")


def downgrade():
    op.drop_table("guest_documents")
