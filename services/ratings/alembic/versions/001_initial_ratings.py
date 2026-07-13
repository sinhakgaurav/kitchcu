"""Initial ratings schema — Sprint 11 (F16–F18)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_ratings")

    op.create_table(
        "dish_ratings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("home_taste_score", sa.SmallInteger(), nullable=False),
        sa.Column("quality_score", sa.SmallInteger(), nullable=False),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("media_type", sa.String(10), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_verified_purchase", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("moderation_status", sa.String(20), server_default="approved", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "home_taste_score BETWEEN 1 AND 5",
            name="ck_dish_ratings_home_taste",
        ),
        sa.CheckConstraint(
            "quality_score BETWEEN 1 AND 5",
            name="ck_dish_ratings_quality",
        ),
        sa.UniqueConstraint(
            "order_id",
            "dish_id",
            "customer_id",
            name="uq_rating_order_dish_customer",
        ),
        schema="ckac_ratings",
    )
    op.create_index("ix_dish_ratings_dish", "dish_ratings", ["dish_id"], schema="ckac_ratings")
    op.create_index("ix_dish_ratings_kitchen", "dish_ratings", ["kitchen_id"], schema="ckac_ratings")

    op.create_table(
        "dish_rating_aggregates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("rating_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("avg_home_taste", sa.Numeric(4, 2), server_default="0", nullable=False),
        sa.Column("avg_quality", sa.Numeric(4, 2), server_default="0", nullable=False),
        sa.Column("overall_rating", sa.Numeric(4, 2), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dish_id", name="uq_aggregate_dish"),
        schema="ckac_ratings",
    )
    op.create_index(
        "ix_dish_rating_aggregates_kitchen",
        "dish_rating_aggregates",
        ["kitchen_id"],
        schema="ckac_ratings",
    )

    op.create_table(
        "dish_suggestions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("suggestion_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("owner_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_ratings",
    )
    op.create_index(
        "ix_dish_suggestions_kitchen",
        "dish_suggestions",
        ["kitchen_id"],
        schema="ckac_ratings",
    )


def downgrade() -> None:
    op.drop_table("dish_suggestions", schema="ckac_ratings")
    op.drop_table("dish_rating_aggregates", schema="ckac_ratings")
    op.drop_table("dish_ratings", schema="ckac_ratings")
