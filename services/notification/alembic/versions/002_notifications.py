"""Notification log + tracking reminders — Sprint 14 (F29/F45)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_notifications"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_notifications")

    op.create_table(
        "notification_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=True),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("recipient_phone", sa.String(20), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("template_id", sa.String(100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), server_default="{}"),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_notifications",
    )
    op.create_index(
        "ix_notification_log_order",
        "notification_log",
        ["order_id"],
        schema="ckac_notifications",
    )

    op.create_table(
        "tracking_reminders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("order_code", sa.String(64), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("tracking_token", sa.String(64), nullable=True),
        sa.Column("order_status", sa.String(32), nullable=False),
        sa.Column("interval_min", sa.Integer(), server_default="5", nullable=False),
        sa.Column("next_reminder_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_tracking_reminder_order"),
        schema="ckac_notifications",
    )
    op.create_index(
        "ix_tracking_reminders_active",
        "tracking_reminders",
        ["is_active", "next_reminder_at"],
        schema="ckac_notifications",
    )


def downgrade() -> None:
    op.drop_table("tracking_reminders", schema="ckac_notifications")
    op.drop_table("notification_log", schema="ckac_notifications")
