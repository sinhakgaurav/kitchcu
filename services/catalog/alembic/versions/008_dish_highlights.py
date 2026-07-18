"""dish highlight flags: featured, chef's special, unique recipe

Revision ID: 008_dish_highlights
Revises: 007_dish_max_time
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_dish_highlights"
down_revision: Union[str, None] = "007_dish_max_time"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dishes",
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema="ckac_catalog",
    )
    op.add_column(
        "dishes",
        sa.Column("is_chefs_special", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema="ckac_catalog",
    )
    op.add_column(
        "dishes",
        sa.Column("is_unique_recipe", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema="ckac_catalog",
    )
    op.create_index(
        "ix_dishes_kitchen_featured",
        "dishes",
        ["kitchen_id", "is_featured"],
        unique=False,
        schema="ckac_catalog",
    )
    op.create_index(
        "ix_dishes_kitchen_chefs_special",
        "dishes",
        ["kitchen_id", "is_chefs_special"],
        unique=False,
        schema="ckac_catalog",
    )
    op.create_index(
        "ix_dishes_kitchen_unique_recipe",
        "dishes",
        ["kitchen_id", "is_unique_recipe"],
        unique=False,
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_index("ix_dishes_kitchen_unique_recipe", table_name="dishes", schema="ckac_catalog")
    op.drop_index("ix_dishes_kitchen_chefs_special", table_name="dishes", schema="ckac_catalog")
    op.drop_index("ix_dishes_kitchen_featured", table_name="dishes", schema="ckac_catalog")
    op.drop_column("dishes", "is_unique_recipe", schema="ckac_catalog")
    op.drop_column("dishes", "is_chefs_special", schema="ckac_catalog")
    op.drop_column("dishes", "is_featured", schema="ckac_catalog")
