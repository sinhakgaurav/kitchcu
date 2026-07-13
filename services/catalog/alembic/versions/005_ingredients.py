"""Ingredients + dish recipes — Sprint 15 (F19)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_ingredients"
down_revision: Union[str, None] = "004_delivery_time"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingredients",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("current_stock", sa.Numeric(12, 3), server_default="0", nullable=False),
        sa.Column("low_stock_threshold", sa.Numeric(12, 3), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", "name", name="uq_ingredient_kitchen_name"),
        schema="ckac_catalog",
    )
    op.create_index(
        "ix_ingredients_kitchen",
        "ingredients",
        ["kitchen_id"],
        schema="ckac_catalog",
    )

    op.create_table(
        "dish_ingredients",
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("ingredient_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["dish_id"], ["ckac_catalog.dishes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ckac_catalog.ingredients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("dish_id", "ingredient_id"),
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_table("dish_ingredients", schema="ckac_catalog")
    op.drop_table("ingredients", schema="ckac_catalog")
