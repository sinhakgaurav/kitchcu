"""Platform feature flags for super-admin kill-switches and module control."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_feature_flags"
down_revision: Union[str, None] = "007_customer_addresses_password"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_FLAGS = [
    ("refunds_gateway", True, "billing", "Allow full gateway (Razorpay) refunds"),
    ("refunds_direct", True, "billing", "Allow direct UPI/bank refunds with evidence"),
    ("customer_dashboard", True, "customer", "Customer dashboard at /dashboard"),
    ("customer_savings_health", True, "customer", "Savings + health charts on dashboard"),
    ("customer_complaints", True, "customer", "Customer complaint raise/inbox"),
    ("customer_addresses", True, "customer", "Customer address book with map pins"),
    ("customer_payout_profile", True, "customer", "Customer UPI/bank payout profile"),
    ("multi_kitchen_checkout", True, "customer", "F06 multi-kitchen cart checkout"),
    ("live_streaming", True, "platform", "LiveKit prep streaming features"),
    ("owner_registrations", True, "kitchen", "Allow new owner kitchen registration"),
]


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("scope", sa.String(32), server_default="platform", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("key"),
        schema="ckac_identity",
    )
    flags = sa.table(
        "feature_flags",
        sa.column("key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("scope", sa.String),
        sa.column("description", sa.Text),
        schema="ckac_identity",
    )
    op.bulk_insert(
        flags,
        [
            {"key": k, "enabled": en, "scope": scope, "description": desc}
            for k, en, scope, desc in DEFAULT_FLAGS
        ],
    )


def downgrade() -> None:
    op.drop_table("feature_flags", schema="ckac_identity")
