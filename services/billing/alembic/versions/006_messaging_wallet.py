"""Enterprise subscription ledger + per-kitchen messaging wallet."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_messaging_wallet"
down_revision: Union[str, None] = "005_kitchen_payment_gateway"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kitchen_messaging_wallets",
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("balance_inr", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("low_balance_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("kitchen_id"),
        schema="ckac_billing",
    )
    op.create_table(
        "subscription_ledger_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=True),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("platform_revenue_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("wallet_credit_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_subscription_ledger_subscription_id",
        "subscription_ledger_entries",
        ["subscription_id"],
        unique=False,
        schema="ckac_billing",
    )
    op.create_index(
        "ix_subscription_ledger_kitchen_id",
        "subscription_ledger_entries",
        ["kitchen_id"],
        unique=False,
        schema="ckac_billing",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscription_ledger_kitchen_id",
        table_name="subscription_ledger_entries",
        schema="ckac_billing",
    )
    op.drop_index(
        "ix_subscription_ledger_subscription_id",
        table_name="subscription_ledger_entries",
        schema="ckac_billing",
    )
    op.drop_table("subscription_ledger_entries", schema="ckac_billing")
    op.drop_table("kitchen_messaging_wallets", schema="ckac_billing")
