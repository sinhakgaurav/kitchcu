"""Golden recipe pins for standout performance days."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "golden_recipe_pins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("dish_id", sa.UUID(), nullable=False),
        sa.Column("suggestion_id", sa.UUID(), nullable=True),
        sa.Column("performance_date", sa.Date(), nullable=False),
        sa.Column("dish_name", sa.String(255), nullable=False),
        sa.Column("recipe_snapshot", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("metrics", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "kitchen_id",
            "dish_id",
            "performance_date",
            name="uq_golden_pin_kitchen_dish_day",
        ),
        schema="ckac_growth",
    )
    op.create_index(
        "ix_golden_recipe_pins_kitchen",
        "golden_recipe_pins",
        ["kitchen_id"],
        schema="ckac_growth",
    )
    op.create_index(
        "ix_golden_recipe_pins_dish",
        "golden_recipe_pins",
        ["kitchen_id", "dish_id"],
        schema="ckac_growth",
    )


def downgrade() -> None:
    op.drop_index("ix_golden_recipe_pins_dish", table_name="golden_recipe_pins", schema="ckac_growth")
    op.drop_index("ix_golden_recipe_pins_kitchen", table_name="golden_recipe_pins", schema="ckac_growth")
    op.drop_table("golden_recipe_pins", schema="ckac_growth")
