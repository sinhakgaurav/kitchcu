"""Seed WhatsApp app secret + Facebook OAuth Control key rows."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_extra_platform_api_keys"
down_revision: Union[str, None] = "009_platform_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EXTRA_KEYS = [
    ("whatsapp_app_secret", "notification", "Meta WhatsApp app secret (webhook X-Hub-Signature-256)", True),
    ("oauth_facebook_client_id", "identity", "Facebook OAuth client ID (customer login)", False),
    ("oauth_facebook_client_secret", "identity", "Facebook OAuth client secret", True),
]


def upgrade() -> None:
    conn = op.get_bind()
    for key, category, description, is_secret in EXTRA_KEYS:
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM ckac_identity.platform_api_keys WHERE key = :key LIMIT 1"
            ),
            {"key": key},
        ).scalar()
        if exists:
            continue
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
    for key, *_ in EXTRA_KEYS:
        conn.execute(
            sa.text("DELETE FROM ckac_identity.platform_api_keys WHERE key = :key"),
            {"key": key},
        )
