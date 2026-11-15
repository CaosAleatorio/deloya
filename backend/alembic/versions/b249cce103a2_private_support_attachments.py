"""Add private support attachments without changing existing marketplace records.

Revision ID: b249cce103a2
Revises: a1786739467f
"""
from alembic import op
import sqlalchemy as sa


revision = "b249cce103a2"
down_revision = "a1786739467f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "private_attachments",
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("pathname", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(180), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.UniqueConstraint("pathname"),
        sa.CheckConstraint("size_bytes > 0 AND size_bytes <= 3145728", name="ck_private_attachment_size"),
        sa.CheckConstraint("content_type IN ('image/jpeg','image/png','image/webp','application/pdf')",
                           name="ck_private_attachment_type"),
    )
    op.create_index("ix_private_attachments_ticket_id", "private_attachments", ["ticket_id"])
    op.create_index("ix_private_attachments_uploaded_by", "private_attachments", ["uploaded_by"])


def downgrade():
    op.drop_index("ix_private_attachments_uploaded_by", table_name="private_attachments")
    op.drop_index("ix_private_attachments_ticket_id", table_name="private_attachments")
    op.drop_table("private_attachments")
