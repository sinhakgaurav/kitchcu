"""Per-kitchen payment gateway credentials (owner-configurable Razorpay)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_kitchen_payment_gateway"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kitchen_payment_gateways",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(32), server_default="razorpay", nullable=False),
        sa.Column("key_id", sa.String(128), nullable=True),
        sa.Column("key_secret_enc", sa.Text(), nullable=True),
        sa.Column("webhook_secret_enc", sa.Text(), nullable=True),
        sa.Column("linked_account_id", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", "provider", name="uq_kitchen_payment_gateway_provider"),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_kitchen_payment_gateways_kitchen_id",
        "kitchen_payment_gateways",
        ["kitchen_id"],
        unique=False,
        schema="ckac_billing",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_kitchen_payment_gateways_kitchen_id",
        table_name="kitchen_payment_gateways",
        schema="ckac_billing",
    )
    op.drop_table("kitchen_payment_gateways", schema="ckac_billing")
