"""Initial community schema — Sprint 17 (F23–F24)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_community")

    op.create_table(
        "shared_recipes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("recipe_html", sa.Text(), nullable=False),
        sa.Column("dish_id", sa.UUID()),
        sa.Column("status", sa.String(20), server_default="published", nullable=False),
        sa.Column("appreciation_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("points_earned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_community",
    )
    op.create_index("ix_shared_recipes_kitchen", "shared_recipes", ["kitchen_id"], schema="ckac_community")

    op.create_table(
        "recipe_appreciations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recipe_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "customer_id", name="uq_recipe_appreciation_customer"),
        schema="ckac_community",
    )
    op.create_index(
        "ix_recipe_appreciations_recipe", "recipe_appreciations", ["recipe_id"], schema="ckac_community"
    )

    op.create_table(
        "kitchen_reward_balances",
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("points_balance", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("kitchen_id"),
        schema="ckac_community",
    )

    op.create_table(
        "reward_point_ledger",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("reference_id", sa.UUID()),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_community",
    )
    op.create_index("ix_reward_ledger_kitchen", "reward_point_ledger", ["kitchen_id"], schema="ckac_community")

    op.create_table(
        "reward_redemptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("redemption_type", sa.String(30), nullable=False),
        sa.Column("points_spent", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_community",
    )
    op.create_index("ix_reward_redemptions_kitchen", "reward_redemptions", ["kitchen_id"], schema="ckac_community")

    op.create_table(
        "chef_rankings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("region_key", sa.String(100), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("kitchen_code", sa.String(20), nullable=False),
        sa.Column("kitchen_name", sa.String(255), nullable=False),
        sa.Column("score", sa.Numeric(6, 3), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.dialects.postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period", "scope", "region_key", "kitchen_id", name="uq_chef_ranking_period"),
        schema="ckac_community",
    )
    op.create_index("ix_chef_rankings_period", "chef_rankings", ["period"], schema="ckac_community")


def downgrade() -> None:
    op.drop_table("chef_rankings", schema="ckac_community")
    op.drop_table("reward_redemptions", schema="ckac_community")
    op.drop_table("reward_point_ledger", schema="ckac_community")
    op.drop_table("kitchen_reward_balances", schema="ckac_community")
    op.drop_table("recipe_appreciations", schema="ckac_community")
    op.drop_table("shared_recipes", schema="ckac_community")
