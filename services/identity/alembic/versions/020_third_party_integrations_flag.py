"""Master kill-switch for outbound third-party APIs (Meta, Porter, OpenAI, OAuth).

Revision ID: 020
Revises: 019
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAG_KEY = "third_party_integrations"


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM ckac_identity.feature_flags WHERE key = :k LIMIT 1"),
        {"k": FLAG_KEY},
    ).scalar()
    if not exists:
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.feature_flags (key, enabled, scope, description)
                VALUES (
                    :k,
                    false,
                    'platform',
                    'Outbound third-party APIs (Meta WhatsApp, Porter, OpenAI, OAuth IdP). '
                    'OFF = simulate success / mock fees; super-admin enables when keys are ready.'
                )
                """
            ),
            {"k": FLAG_KEY},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ckac_identity.feature_flags WHERE key = :k"),
        {"k": FLAG_KEY},
    )
