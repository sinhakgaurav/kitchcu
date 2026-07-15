"""Customer addresses + optional password for account security."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_customer_addresses_password"
down_revision: Union[str, None] = "006_customer_payout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("password_hash", sa.String(255), nullable=True),
        schema="ckac_identity",
    )
    op.create_table(
        "customer_addresses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("address_line", sa.String(500), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("pincode", sa.String(12), nullable=True),
        sa.Column("landmark", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_customer_addresses_customer_id",
        "customer_addresses",
        ["customer_id"],
        schema="ckac_identity",
    )


def downgrade() -> None:
    op.drop_index("ix_customer_addresses_customer_id", table_name="customer_addresses", schema="ckac_identity")
    op.drop_table("customer_addresses", schema="ckac_identity")
    op.drop_column("customers", "password_hash", schema="ckac_identity")
