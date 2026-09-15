"""Ingredient brand + retail pack size (maps photos/weight to stock).

Revision ID: 010_ingredient_brand_pack
Revises: 009_prep_batches
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_ingredient_brand_pack"
down_revision: Union[str, None] = "009_prep_batches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingredients",
        sa.Column("brand", sa.String(120), nullable=True),
        schema="ckac_catalog",
    )
    op.add_column(
        "ingredients",
        sa.Column("pack_size", sa.Numeric(12, 3), nullable=True),
        schema="ckac_catalog",
    )
    op.add_column(
        "ingredients",
        sa.Column("pack_label", sa.String(80), nullable=True),
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_column("ingredients", "pack_label", schema="ckac_catalog")
    op.drop_column("ingredients", "pack_size", schema="ckac_catalog")
    op.drop_column("ingredients", "brand", schema="ckac_catalog")
