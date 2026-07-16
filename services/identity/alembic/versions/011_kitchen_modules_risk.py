"""Per-kitchen module kill-switches + configurable Phase-2 risk flags."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_kitchen_modules_risk"
down_revision: Union[str, None] = "010_extra_platform_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RISK_FLAGS = [
    ("order_parser_llm", False, "order", "gpt-4o-mini WhatsApp order parser (falls back to rules)"),
    ("courier_porter_dunzo", False, "delivery", "Porter/Dunzo courier quote integration"),
    ("payments_stripe_multi_region", False, "billing", "Stripe AE/DE multi-region checkout"),
    ("messaging_wallet_deduct", True, "billing", "Deduct Meta/Twilio fees from kitchen messaging wallet"),
    ("kitchen_module_overrides", True, "platform", "Per-kitchen module kill-switches in Admin Control"),
]

MODULE_KEYS = (
    "whatsapp",
    "livekit",
    "razorpay",
    "refunds",
    "marketing_broadcast",
    "customer_checkout",
    "streaming",
)


def upgrade() -> None:
    op.create_table(
        "kitchen_module_flags",
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("module_key", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("kitchen_id", "module_key"),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_kitchen_module_flags_kitchen",
        "kitchen_module_flags",
        ["kitchen_id"],
        unique=False,
        schema="ckac_identity",
    )

    flags = sa.table(
        "feature_flags",
        sa.column("key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("scope", sa.String),
        sa.column("description", sa.Text),
        schema="ckac_identity",
    )
    conn = op.get_bind()
    for key, enabled, scope, desc in RISK_FLAGS:
        exists = conn.execute(
            sa.text(
                "SELECT 1 FROM ckac_identity.feature_flags WHERE key = :k LIMIT 1"
            ),
            {"k": key},
        ).scalar()
        if not exists:
            op.execute(
                flags.insert().values(
                    key=key, enabled=enabled, scope=scope, description=desc
                )
            )


def downgrade() -> None:
    op.drop_index(
        "ix_kitchen_module_flags_kitchen",
        table_name="kitchen_module_flags",
        schema="ckac_identity",
    )
    op.drop_table("kitchen_module_flags", schema="ckac_identity")
    conn = op.get_bind()
    for key, _, _, _ in RISK_FLAGS:
        conn.execute(
            sa.text("DELETE FROM ckac_identity.feature_flags WHERE key = :k"),
            {"k": key},
        )
