"""Customer accounts and OAuth identity links."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "004_customers_oauth"
down_revision = "003_platform_admins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=15), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_ckac_identity_customers_email",
        "customers",
        ["email"],
        schema="ckac_identity",
    )
    op.create_index(
        "ix_ckac_identity_customers_phone",
        "customers",
        ["phone"],
        schema="ckac_identity",
    )

    op.create_table(
        "customer_oauth_identities",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("profile", JSONB, server_default="{}", nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["customer_id"], ["ckac_identity.customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_customer_oauth_provider_user"),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_ckac_identity_customer_oauth_customer_id",
        "customer_oauth_identities",
        ["customer_id"],
        schema="ckac_identity",
    )


def downgrade() -> None:
    op.drop_table("customer_oauth_identities", schema="ckac_identity")
    op.drop_table("customers", schema="ckac_identity")
