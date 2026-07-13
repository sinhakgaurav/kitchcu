"""GST profiles, tax invoices, and monthly audits for registered owners."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kitchen_gst_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("gstin", sa.String(15), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("trade_name", sa.String(255), nullable=True),
        sa.Column("state_code", sa.String(2), nullable=False),
        sa.Column("registered_address", sa.Text(), nullable=False),
        sa.Column("default_tax_rate", sa.Numeric(5, 2), server_default="5.00", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("invoice_prefix", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", name="uq_kitchen_gst_profiles_kitchen"),
        sa.UniqueConstraint("gstin", name="uq_kitchen_gst_profiles_gstin"),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_kitchen_gst_profiles_kitchen",
        "kitchen_gst_profiles",
        ["kitchen_id"],
        schema="ckac_billing",
    )

    op.create_table(
        "gst_tax_invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("invoice_number", sa.String(64), nullable=False),
        sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_code", sa.String(64), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("place_of_supply_state_code", sa.String(2), nullable=False),
        sa.Column("supply_type", sa.String(16), server_default="intra_state", nullable=False),
        sa.Column("taxable_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("sgst_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("igst_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("gross_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_gst_tax_invoices_order"),
        sa.UniqueConstraint("invoice_number", name="uq_gst_tax_invoices_number"),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_gst_tax_invoices_kitchen_date",
        "gst_tax_invoices",
        ["kitchen_id", "invoice_date"],
        schema="ckac_billing",
    )

    op.create_table(
        "gst_monthly_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.Column("invoice_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_taxable", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_cgst", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_sgst", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_igst", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_tax", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_gross_sales", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_owner_id", sa.UUID(), nullable=True),
        sa.Column("balance_sheet_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "kitchen_id",
            "period_year",
            "period_month",
            name="uq_gst_monthly_audits_period",
        ),
        schema="ckac_billing",
    )
    op.create_index(
        "ix_gst_monthly_audits_kitchen",
        "gst_monthly_audits",
        ["kitchen_id"],
        schema="ckac_billing",
    )


def downgrade() -> None:
    op.drop_table("gst_monthly_audits", schema="ckac_billing")
    op.drop_table("gst_tax_invoices", schema="ckac_billing")
    op.drop_table("kitchen_gst_profiles", schema="ckac_billing")
