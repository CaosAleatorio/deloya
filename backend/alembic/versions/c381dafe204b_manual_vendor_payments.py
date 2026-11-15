"""Snapshot seller wallets and record reviewed direct transfers per suborder.

Revision ID: c381dafe204b
Revises: b249cce103a2
"""
from alembic import op
import sqlalchemy as sa


revision = "c381dafe204b"
down_revision = "b249cce103a2"
branch_labels = None
depends_on = None


def upgrade():
    for provider in ("mpesa", "emola"):
        op.add_column("stores", sa.Column(f"{provider}_phone", sa.String(13), nullable=True))
        op.add_column("stores", sa.Column(f"{provider}_account_name", sa.String(160), nullable=True))
    op.add_column("orders", sa.Column("payment_mode", sa.String(20), server_default="demo", nullable=False))
    op.drop_constraint("ck_order_status", "orders", type_="check")
    op.create_check_constraint("ck_order_status", "orders",
        "status IN ('pendente_pagamento','parcialmente_paga','paga','em_preparacao','pronta','entregue','cancelada')")
    op.add_column("vendor_orders", sa.Column("payment_destinations", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("payment_attempts", sa.Column("vendor_order_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_payment_vendor_order", "payment_attempts", "vendor_orders", ["vendor_order_id"], ["id"])
    op.create_index("ix_payment_attempts_vendor_order_id", "payment_attempts", ["vendor_order_id"])
    for name, size in [("transfer_reference", 120), ("destination_phone", 13),
                       ("destination_account_name", 160), ("notes", 1000), ("review_notes", 1000)]:
        op.add_column("payment_attempts", sa.Column(name, sa.String(size), nullable=True))
    op.add_column("payment_attempts", sa.Column("reviewed_by", sa.Uuid(), nullable=True))
    op.add_column("payment_attempts", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_payment_reviewer", "payment_attempts", "users", ["reviewed_by"], ["id"])
    active = sa.text("vendor_order_id IS NOT NULL AND status IN ('pending','success')")
    op.create_index("uq_manual_payment_active", "payment_attempts", ["vendor_order_id"], unique=True, postgresql_where=active)
    op.create_index("uq_manual_transfer_reference", "payment_attempts",
                    ["provider", "destination_phone", "transfer_reference"], unique=True, postgresql_where=active)


def downgrade():
    # Refuse to silently discard a partial financial state on rollback.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM payment_attempts WHERE vendor_order_id IS NOT NULL)")):
        raise RuntimeError("Preserve os registos de pagamentos manuais antes de reverter esta migração")
    op.drop_index("uq_manual_transfer_reference", table_name="payment_attempts")
    op.drop_index("uq_manual_payment_active", table_name="payment_attempts")
    op.drop_constraint("fk_payment_reviewer", "payment_attempts", type_="foreignkey")
    op.drop_constraint("fk_payment_vendor_order", "payment_attempts", type_="foreignkey")
    op.drop_index("ix_payment_attempts_vendor_order_id", table_name="payment_attempts")
    for name in ("vendor_order_id", "transfer_reference", "destination_phone", "destination_account_name",
                 "notes", "review_notes", "reviewed_by", "reviewed_at"):
        op.drop_column("payment_attempts", name)
    op.drop_column("vendor_orders", "payment_destinations")
    op.drop_constraint("ck_order_status", "orders", type_="check")
    op.create_check_constraint("ck_order_status", "orders",
        "status IN ('pendente_pagamento','paga','em_preparacao','pronta','entregue','cancelada')")
    op.drop_column("orders", "payment_mode")
    for provider in ("mpesa", "emola"):
        op.drop_column("stores", f"{provider}_account_name")
        op.drop_column("stores", f"{provider}_phone")
