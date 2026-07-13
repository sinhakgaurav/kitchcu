"""F44 split settlements for multi-kitchen payments."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "settlements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("master_order_id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_fee_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("platform_fee", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("net_to_owner", sa.Numeric(12, 2), nullable=False),
        sa.Column("razorpay_transfer_id", sa.String(100), nullable=True),
        sa.Column("settlement_status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["ckac_billing.payments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_settlements_order_id"),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_settlements_master_order",
        "settlements",
        ["master_order_id"],
        schema="ckac_billing",
    )
    op.create_index(
        "ix_settlements_kitchen",
        "settlements",
        ["kitchen_id"],
        schema="ckac_billing",
    )
    op.create_index(
        "ix_payments_master_order",
        "payments",
        ["master_order_id"],
        schema="ckac_billing",
    )
    op.create_index(
        "uq_payments_master_method",
        "payments",
        ["master_order_id", "method"],
        unique=True,
        schema="ckac_billing",
        postgresql_where=sa.text("master_order_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_payments_master_method",
        table_name="payments",
        schema="ckac_billing",
    )
    op.drop_index("ix_payments_master_order", table_name="payments", schema="ckac_billing")
    op.drop_index("ix_settlements_kitchen", table_name="settlements", schema="ckac_billing")
    op.drop_index("ix_settlements_master_order", table_name="settlements", schema="ckac_billing")
    op.drop_table("settlements", schema="ckac_billing")
