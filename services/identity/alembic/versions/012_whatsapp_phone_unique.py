"""Unique WhatsApp phone_number_id per kitchen (Meta Cloud API routing)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_whatsapp_phone_unique"
down_revision: Union[str, None] = "011_kitchen_modules_risk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_kitchens_whatsapp_phone_id",
        "kitchens",
        ["whatsapp_phone_id"],
        unique=True,
        schema="ckac_identity",
        postgresql_where=sa.text("whatsapp_phone_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_kitchens_whatsapp_phone_id",
        table_name="kitchens",
        schema="ckac_identity",
    )
