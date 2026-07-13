"""Initial order schema — Sprint 3."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_orders")

    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("bill_id", sa.String(32), nullable=False),
        sa.Column("order_code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), server_default="received", nullable=False),
        sa.Column("source", sa.String(32), server_default="manual", nullable=False),
        sa.Column("delivery_type", sa.String(16), server_default="pickup", nullable=False),
        sa.Column("payment_method", sa.String(16), server_default="cod", nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(10, 2), server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("estimated_prep_min", sa.Integer(), nullable=True),
        sa.Column("estimated_ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_code", name="uq_orders_order_code"),
        schema="ckac_orders",
    )
    op.create_index(
        "ix_orders_kitchen_created",
        "orders",
        ["kitchen_id", sa.text("created_at DESC")],
        schema="ckac_orders",
    )
    op.create_index("ix_orders_kitchen_status", "orders", ["kitchen_id", "status"], schema="ckac_orders")

    op.create_table(
        "order_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("dish_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("prep_time_min", sa.Integer(), server_default="30"),
        sa.ForeignKeyConstraint(["order_id"], ["ckac_orders.orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_orders",
    )
    op.create_index("ix_order_items_order", "order_items", ["order_id"], schema="ckac_orders")

    op.create_table(
        "order_status_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["ckac_orders.orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_orders",
    )
    op.create_index(
        "ix_order_status_events_order",
        "order_status_events",
        ["order_id", sa.text("created_at DESC")],
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_table("order_status_events", schema="ckac_orders")
    op.drop_table("order_items", schema="ckac_orders")
    op.drop_table("orders", schema="ckac_orders")
