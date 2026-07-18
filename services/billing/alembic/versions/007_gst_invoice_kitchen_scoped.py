"""Scope GST invoice_number uniqueness to kitchen_id (per-GSTIN uniqueness).

Previously invoice_number was globally unique, so bulk-seeding many kitchens with
the same invoice_prefix collided on SHK-GST-YYYYMM-0001 and returned HTTP 500.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_gst_invoice_kitchen_scoped"
down_revision: Union[str, None] = "006_messaging_wallet"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_gst_tax_invoices_number",
        "gst_tax_invoices",
        schema="ckac_billing",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_gst_tax_invoices_kitchen_number",
        "gst_tax_invoices",
        ["kitchen_id", "invoice_number"],
        schema="ckac_billing",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_gst_tax_invoices_kitchen_number",
        "gst_tax_invoices",
        schema="ckac_billing",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_gst_tax_invoices_number",
        "gst_tax_invoices",
        ["invoice_number"],
        schema="ckac_billing",
    )
