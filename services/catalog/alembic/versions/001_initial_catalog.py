"""Initial catalog schema."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_catalog")

    op.create_table(
        "categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", "slug", name="uq_category_kitchen_slug"),
        schema="ckac_catalog",
    )
    op.create_index("ix_categories_kitchen", "categories", ["kitchen_id"], schema="ckac_catalog")

    op.create_table(
        "dishes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("prep_time_min", sa.Integer(), server_default="30"),
        sa.Column("ingredients_description", sa.Text(), nullable=True),
        sa.Column("quality_measures", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["category_id"], ["ckac_catalog.categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_catalog",
    )
    op.create_index("ix_dishes_kitchen", "dishes", ["kitchen_id"], schema="ckac_catalog")
    op.create_index(
        "ix_dishes_kitchen_active",
        "dishes",
        ["kitchen_id", "is_active"],
        schema="ckac_catalog",
    )

    op.create_table(
        "dish_media",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("is_hero", sa.Boolean(), server_default="false"),
        sa.Column("is_live_capture", sa.Boolean(), server_default="false"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["dish_id"], ["ckac_catalog.dishes.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_table("dish_media", schema="ckac_catalog")
    op.drop_table("dishes", schema="ckac_catalog")
    op.drop_table("categories", schema="ckac_catalog")
