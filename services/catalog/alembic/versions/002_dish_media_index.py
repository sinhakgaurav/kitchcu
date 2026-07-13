"""Add index on dish_media.dish_id for menu enrichment queries."""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_dish_media_dish_id",
        "dish_media",
        ["dish_id"],
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_index("ix_dish_media_dish_id", table_name="dish_media", schema="ckac_catalog")
