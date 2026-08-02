"""Gateway rate-limit settings (super-admin configurable).

Revision ID: 022
Revises: 021
Create Date: 2026-08-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gateway_rate_limit_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "rules",
            JSONB(),
            nullable=False,
            server_default=sa.text(
                "'{\"otp_request\": {\"limit\": 5, \"window_seconds\": 600}}'::jsonb"
            ),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        schema="ckac_identity",
    )
    op.execute(
        sa.text(
            """
            INSERT INTO ckac_identity.gateway_rate_limit_settings (id, enabled, rules)
            VALUES (
              1,
              true,
              '{"otp_request": {"limit": 5, "window_seconds": 600},
                "otp_verify": {"limit": 10, "window_seconds": 600},
                "owner_register": {"limit": 10, "window_seconds": 3600},
                "checkout": {"limit": 30, "window_seconds": 60},
                "default": {"limit": 600, "window_seconds": 60}}'::jsonb
            )
            ON CONFLICT (id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_table("gateway_rate_limit_settings", schema="ckac_identity")
