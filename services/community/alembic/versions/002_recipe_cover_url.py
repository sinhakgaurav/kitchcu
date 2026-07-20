"""Add cover_url to shared community recipes.

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shared_recipes",
        sa.Column("cover_url", sa.String(2000), nullable=True),
        schema="ckac_community",
    )


def downgrade() -> None:
    op.drop_column("shared_recipes", "cover_url", schema="ckac_community")
