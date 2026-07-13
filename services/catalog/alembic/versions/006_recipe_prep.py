"""Recipe prep steps + ingredient line photos — F19 enhancement."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_recipe_prep"
down_revision: Union[str, None] = "005_ingredients"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingredients",
        sa.Column("photo_url", sa.Text(), nullable=True),
        schema="ckac_catalog",
    )
    op.add_column(
        "dish_ingredients",
        sa.Column("photo_url", sa.Text(), nullable=True),
        schema="ckac_catalog",
    )
    op.add_column(
        "dish_ingredients",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        schema="ckac_catalog",
    )

    op.create_table(
        "dish_prep_steps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("duration_min", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["dish_id"], ["ckac_catalog.dishes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dish_id", "step_order", name="uq_dish_prep_step_order"),
        schema="ckac_catalog",
    )
    op.create_index(
        "ix_dish_prep_steps_dish",
        "dish_prep_steps",
        ["dish_id"],
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_table("dish_prep_steps", schema="ckac_catalog")
    op.drop_column("dish_ingredients", "sort_order", schema="ckac_catalog")
    op.drop_column("dish_ingredients", "photo_url", schema="ckac_catalog")
    op.drop_column("ingredients", "photo_url", schema="ckac_catalog")
