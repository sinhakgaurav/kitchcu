"""Platform API keys configurable from super-admin Control."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_platform_api_keys"
down_revision: Union[str, None] = "008_feature_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_KEYS = [
    ("razorpay_key_id", "billing", "Razorpay Key ID (platform SaaS / fallback)", False),
    ("razorpay_key_secret", "billing", "Razorpay Key Secret (platform SaaS / fallback)", True),
    ("razorpay_webhook_secret", "billing", "Razorpay webhook signing secret", True),
    ("livekit_url", "streaming", "LiveKit WebSocket URL", False),
    ("livekit_api_key", "streaming", "LiveKit API key", False),
    ("livekit_api_secret", "streaming", "LiveKit API secret", True),
    ("support_ai_api_key", "notification", "OpenAI-compatible key for AI support chat", True),
    ("whatsapp_verify_token", "notification", "Meta WhatsApp webhook verify token", True),
    ("google_maps_api_key", "platform", "Google Maps embed / places (browser or server)", False),
    ("oauth_google_client_id", "identity", "Google OAuth client ID (customer login)", False),
    ("oauth_google_client_secret", "identity", "Google OAuth client secret", True),
]


def upgrade() -> None:
    op.create_table(
        "platform_api_keys",
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), server_default="platform", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("value_enc", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("key"),
        schema="ckac_identity",
    )
    keys = sa.table(
        "platform_api_keys",
        sa.column("key", sa.String),
        sa.column("category", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_secret", sa.Boolean),
        schema="ckac_identity",
    )
    op.bulk_insert(
        keys,
        [
            {
                "key": k,
                "category": cat,
                "description": desc,
                "is_secret": secret,
            }
            for k, cat, desc, secret in DEFAULT_KEYS
        ],
    )


def downgrade() -> None:
    op.drop_table("platform_api_keys", schema="ckac_identity")
