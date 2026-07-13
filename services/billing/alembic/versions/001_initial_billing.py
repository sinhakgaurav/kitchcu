"""Initial billing schema — Sprint 6."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_billing")

    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("master_order_id", sa.UUID(), nullable=True),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("kitchen_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("razorpay_order_id", sa.String(100), nullable=True),
        sa.Column("razorpay_payment_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="created", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "method", name="uq_payment_order_method"),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_payments_order",
        "payments",
        ["order_id"],
        schema="ckac_billing",
    )
    op.create_index(
        "ix_payments_owner",
        "payments",
        ["owner_id"],
        schema="ckac_billing",
    )

    op.create_table(
        "owner_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("plan_tier", sa.String(20), nullable=False),
        sa.Column("billing_cycle", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("razorpay_subscription_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="trial", nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_owner_subscriptions_owner",
        "owner_subscriptions",
        ["owner_id"],
        schema="ckac_billing",
    )


def downgrade() -> None:
    op.drop_table("owner_subscriptions", schema="ckac_billing")
    op.drop_table("payments", schema="ckac_billing")
