"""Ingredient kcal + dish calories note.

Revision ID: 011_dish_ingredient_calories
Revises: 010_ingredient_brand_pack
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_dish_ingredient_calories"
down_revision: Union[str, None] = "010_ingredient_brand_pack"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingredients",
        sa.Column("kcal_per_100", sa.Numeric(8, 2), nullable=True),
        schema="ckac_catalog",
    )
    op.add_column(
        "dishes",
        sa.Column("calories_description", sa.Text(), nullable=True),
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_column("dishes", "calories_description", schema="ckac_catalog")
    op.drop_column("ingredients", "kcal_per_100", schema="ckac_catalog")
