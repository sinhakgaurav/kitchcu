"""F34/F35 kitchen subscription plans + customer enrollments.

Revision ID: 003
Revises: 002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("plan_type", sa.String(32), nullable=False, server_default="tiffin"),
        sa.Column("dishes_config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("price_monthly", sa.Numeric(10, 2), nullable=False),
        sa.Column("billing_cycle", sa.String(16), nullable=False, server_default="monthly"),
        sa.Column("delivery_included", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_subscribers", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_subscription_plans_kitchen",
        "subscription_plans",
        ["kitchen_id"],
        unique=False,
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_subscription_plans_kitchen_active",
        "subscription_plans",
        ["kitchen_id", "is_active"],
        unique=False,
        schema="ckac_marketing",
    )

    op.create_table(
        "customer_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("billing_status", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("owner_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["ckac_marketing.subscription_plans.id"],
            ondelete="CASCADE",
        ),
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_customer_subscriptions_kitchen",
        "customer_subscriptions",
        ["kitchen_id"],
        unique=False,
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_customer_subscriptions_kitchen_status",
        "customer_subscriptions",
        ["kitchen_id", "status"],
        unique=False,
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_customer_subscriptions_customer",
        "customer_subscriptions",
        ["customer_id"],
        unique=False,
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_customer_subscriptions_plan",
        "customer_subscriptions",
        ["plan_id"],
        unique=False,
        schema="ckac_marketing",
    )


def downgrade() -> None:
    op.drop_table("customer_subscriptions", schema="ckac_marketing")
    op.drop_table("subscription_plans", schema="ckac_marketing")
