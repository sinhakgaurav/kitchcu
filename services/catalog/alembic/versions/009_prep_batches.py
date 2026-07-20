"""Bulk prep batches + kitchen stock deduct mode (F19b).

Revision ID: 009_prep_batches
Revises: 008_dish_highlights
Create Date: 2026-07-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_prep_batches"
down_revision: Union[str, None] = "008_dish_highlights"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kitchen_stock_settings",
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("deduct_mode", sa.String(32), server_default="order_ready", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("kitchen_id"),
        schema="ckac_catalog",
    )

    op.create_table(
        "prep_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("batch_type", sa.String(32), nullable=False),
        sa.Column("portions", sa.Numeric(12, 3), nullable=False),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_catalog",
    )
    op.create_index(
        "ix_prep_batches_kitchen_id",
        "prep_batches",
        ["kitchen_id"],
        schema="ckac_catalog",
    )
    op.create_index(
        "ix_prep_batches_kitchen_status",
        "prep_batches",
        ["kitchen_id", "status"],
        schema="ckac_catalog",
    )

    op.create_table(
        "prep_batch_dishes",
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("quantity_per_portion", sa.Numeric(12, 3), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["ckac_catalog.prep_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dish_id"],
            ["ckac_catalog.dishes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("batch_id", "dish_id"),
        schema="ckac_catalog",
    )

    op.create_table(
        "prep_batch_ingredients",
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("ingredient_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["ckac_catalog.prep_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"],
            ["ckac_catalog.ingredients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("batch_id", "ingredient_id"),
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_table("prep_batch_ingredients", schema="ckac_catalog")
    op.drop_table("prep_batch_dishes", schema="ckac_catalog")
    op.drop_index("ix_prep_batches_kitchen_status", table_name="prep_batches", schema="ckac_catalog")
    op.drop_index("ix_prep_batches_kitchen_id", table_name="prep_batches", schema="ckac_catalog")
    op.drop_table("prep_batches", schema="ckac_catalog")
    op.drop_table("kitchen_stock_settings", schema="ckac_catalog")
