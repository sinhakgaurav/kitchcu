"""Seed Meta WhatsApp Cloud API access token platform key slot."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KEY = (
    "whatsapp_access_token",
    "notification",
    "Meta WhatsApp Cloud API permanent access token (outbound messages)",
    True,
)


def upgrade() -> None:
    conn = op.get_bind()
    key, category, description, is_secret = KEY
    exists = conn.execute(
        sa.text("SELECT 1 FROM ckac_identity.platform_api_keys WHERE key = :key LIMIT 1"),
        {"key": key},
    ).scalar()
    if exists:
        return
    conn.execute(
        sa.text(
            """
            INSERT INTO ckac_identity.platform_api_keys
                (key, category, description, is_secret)
            VALUES (:key, :category, :description, :is_secret)
            """
        ),
        {
            "key": key,
            "category": category,
            "description": description,
            "is_secret": is_secret,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ckac_identity.platform_api_keys WHERE key = :key"),
        {"key": KEY[0]},
    )
