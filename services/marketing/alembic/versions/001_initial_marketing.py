"""Initial marketing schema — Sprint 10 (F36–F38)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_marketing")

    op.create_table(
        "kitchen_customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("customer_name", sa.String(120), nullable=True),
        sa.Column("total_spend", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("monthly_spend", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("order_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("favorite_dishes", sa.dialects.postgresql.JSONB(), server_default="[]"),
        sa.Column("order_patterns", sa.dialects.postgresql.JSONB(), server_default="{}"),
        sa.Column("tags", sa.dialects.postgresql.JSONB(), server_default="[]"),
        sa.Column("last_order_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", "customer_phone", name="uq_kitchen_customer_phone"),
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_kitchen_customers_kitchen",
        "kitchen_customers",
        ["kitchen_id"],
        schema="ckac_marketing",
    )

    op.create_table(
        "coupons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("discount_type", sa.String(10), nullable=False),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", "code", name="uq_coupon_kitchen_code"),
        schema="ckac_marketing",
    )
    op.create_index("ix_coupons_kitchen", "coupons", ["kitchen_id"], schema="ckac_marketing")

    op.create_table(
        "promotions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("dish_name", sa.String(200), nullable=False),
        sa.Column("special_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("segment", sa.String(20), server_default="all", nullable=False),
        sa.Column("segment_limit", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_marketing",
    )
    op.create_index("ix_promotions_kitchen", "promotions", ["kitchen_id"], schema="ckac_marketing")


def downgrade() -> None:
    op.drop_table("promotions", schema="ckac_marketing")
    op.drop_table("coupons", schema="ckac_marketing")
    op.drop_table("kitchen_customers", schema="ckac_marketing")
