"""Order refunds — gateway reverse + direct UPI/bank with evidence."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refunds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("status", sa.String(20), server_default="requested", nullable=False),
        sa.Column("destination_type", sa.String(32), nullable=False),
        sa.Column("destination_upi", sa.String(100), nullable=True),
        sa.Column("destination_bank_account", sa.String(34), nullable=True),
        sa.Column("destination_bank_ifsc", sa.String(11), nullable=True),
        sa.Column("destination_account_name", sa.String(255), nullable=True),
        sa.Column("transfer_remark", sa.String(128), nullable=False),
        sa.Column("razorpay_refund_id", sa.String(100), nullable=True),
        sa.Column("evidence_url", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_billing",
    )
    op.create_index("ix_refunds_order_id", "refunds", ["order_id"], schema="ckac_billing")
    op.create_index("ix_refunds_kitchen_id", "refunds", ["kitchen_id"], schema="ckac_billing")
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"], schema="ckac_billing")


def downgrade() -> None:
    op.drop_index("ix_refunds_payment_id", table_name="refunds", schema="ckac_billing")
    op.drop_index("ix_refunds_kitchen_id", table_name="refunds", schema="ckac_billing")
    op.drop_index("ix_refunds_order_id", table_name="refunds", schema="ckac_billing")
    op.drop_table("refunds", schema="ckac_billing")
