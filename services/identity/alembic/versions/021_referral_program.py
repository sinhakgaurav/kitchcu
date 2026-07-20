"""Referral program: settings, leads, credits, ledger.

Revision ID: 021
Revises: 020
Create Date: 2026-07-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referral_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "customer_to_kitchen_reward_inr",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="10.00",
        ),
        sa.Column(
            "kitchen_to_customer_reward_inr",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="10.00",
        ),
        sa.Column(
            "kitchen_reward_trigger",
            sa.String(32),
            nullable=False,
            server_default="first_order_or_onboard",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        schema="ckac_identity",
    )
    op.execute(
        """
        INSERT INTO ckac_identity.referral_settings (id)
        VALUES (1)
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.create_table(
        "referral_leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("direction", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("referrer_customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("referrer_kitchen_id", UUID(as_uuid=True), nullable=True),
        sa.Column("referrer_owner_id", UUID(as_uuid=True), nullable=True),
        sa.Column("kitchen_name", sa.String(200), nullable=True),
        sa.Column("contact_name", sa.String(120), nullable=True),
        sa.Column("contact_phone", sa.String(20), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("matched_kitchen_id", UUID(as_uuid=True), nullable=True),
        sa.Column("matched_customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reward_inr", sa.Numeric(10, 2), nullable=True),
        sa.Column("credit_id", UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_referral_leads_direction_status",
        "referral_leads",
        ["direction", "status"],
        schema="ckac_identity",
    )
    op.create_index(
        "ix_referral_leads_contact_phone",
        "referral_leads",
        ["contact_phone"],
        schema="ckac_identity",
    )
    op.create_index(
        "ix_referral_leads_referrer_customer",
        "referral_leads",
        ["referrer_customer_id"],
        schema="ckac_identity",
    )
    op.create_index(
        "ix_referral_leads_referrer_kitchen",
        "referral_leads",
        ["referrer_kitchen_id"],
        schema="ckac_identity",
    )

    op.create_table(
        "referral_credits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("beneficiary_type", sa.String(16), nullable=False),
        sa.Column("beneficiary_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "balance_inr",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "lifetime_earned_inr",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "lifetime_applied_inr",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "beneficiary_type",
            "beneficiary_id",
            name="uq_referral_credits_beneficiary",
        ),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_referral_credits_beneficiary",
        "referral_credits",
        ["beneficiary_type", "beneficiary_id"],
        schema="ckac_identity",
    )

    op.create_table(
        "referral_credit_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "credit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ckac_identity.referral_credits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("amount_inr", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after_inr", sa.Numeric(12, 2), nullable=False),
        sa.Column("lead_id", UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_referral_credit_ledger_credit",
        "referral_credit_ledger",
        ["credit_id", "created_at"],
        schema="ckac_identity",
    )
    upgrade_rbac()


def upgrade_rbac() -> None:
    conn = op.get_bind()
    for code, desc in (
        ("referrals:read", "View referral settings and leads"),
        ("referrals:write", "Configure referral rewards and manage leads"),
    ):
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.admin_permissions (code, description)
                VALUES (:c, :d)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"c": code, "d": desc},
        )
    for role, perm in (("ops", "referrals:read"), ("finance", "referrals:read")):
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
                VALUES (:r, :p)
                ON CONFLICT DO NOTHING
                """
            ),
            {"r": role, "p": perm},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM ckac_identity.admin_role_permissions "
            "WHERE permission_code IN ('referrals:read', 'referrals:write')"
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM ckac_identity.admin_permissions "
            "WHERE code IN ('referrals:read', 'referrals:write')"
        )
    )
    op.drop_table("referral_credit_ledger", schema="ckac_identity")
    op.drop_table("referral_credits", schema="ckac_identity")
    op.drop_table("referral_leads", schema="ckac_identity")
    op.drop_table("referral_settings", schema="ckac_identity")
