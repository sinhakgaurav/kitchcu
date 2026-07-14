"""GST domain — profiles, tax invoices, monthly audit, balance sheet."""

from __future__ import annotations

import re
import uuid
from calendar import monthrange
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GstMonthlyAudit, GstTaxInvoice, KitchenGstProfile
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
DEFAULT_FOOD_TAX_RATE = 5.0


class GstProfileUpsertRequest(BaseModel):
    """Register or update a kitchen's GST registration — required before GST invoice sync/reports.

    Kitchens under India's GST threshold may skip this entirely; the GST subsystem only
    activates once a profile with `is_active=true` exists.
    """

    gstin: str = Field(
        min_length=15,
        max_length=15,
        description="15-character GSTIN. Validated against the standard GSTIN format; normalized to uppercase.",
        examples=["27AAAPL1234C1Z5"],
    )
    legal_name: str = Field(min_length=2, max_length=255, description="Legal business name as per GST registration.")
    trade_name: str | None = Field(default=None, max_length=255, description="Trade/brand name, if different from legal name.")
    registered_address: str = Field(min_length=5, max_length=2000, description="Registered business address for GST filings.")
    default_tax_rate: float = Field(
        default=DEFAULT_FOOD_TAX_RATE,
        ge=0,
        le=28,
        description="Default GST rate (%) applied to invoices, unless overridden per-invoice.",
    )
    is_active: bool = Field(default=True, description="Whether GST invoicing/sync is active for this kitchen.")
    invoice_prefix: str | None = Field(
        default=None,
        max_length=20,
        description="Prefix for generated invoice numbers (defaults to the kitchen code).",
    )

    @field_validator("gstin")
    @classmethod
    def normalize_gstin(cls, value: str) -> str:
        gstin = value.strip().upper()
        if not GSTIN_RE.match(gstin):
            raise ValueError("Invalid GSTIN format")
        return gstin


class GstProfileResponse(BaseModel):
    """A kitchen's GST registration profile."""

    id: uuid.UUID = Field(..., description="Profile ID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen (tenant scope).")
    gstin: str = Field(..., description="15-character GSTIN.")
    legal_name: str = Field(..., description="Legal business name.")
    trade_name: str | None = Field(default=None, description="Trade/brand name.")
    state_code: str = Field(..., description="2-digit GST state code, derived from the GSTIN.")
    registered_address: str = Field(..., description="Registered business address.")
    default_tax_rate: float = Field(..., description="Default GST rate (%) applied to invoices.")
    is_active: bool = Field(..., description="Whether GST invoicing/sync is active.")
    invoice_prefix: str | None = Field(default=None, description="Invoice number prefix.")
    created_at: datetime = Field(..., description="Profile creation timestamp.")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp.")

    model_config = {"from_attributes": True}


class GstTaxInvoiceResponse(BaseModel):
    """A tax invoice generated for a delivered order (CGST+SGST for intra-state supply, IGST for inter-state)."""

    id: uuid.UUID = Field(..., description="Invoice ID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen (tenant scope).")
    order_id: uuid.UUID = Field(..., description="Delivered order this invoice covers.")
    invoice_number: str = Field(..., description="Sequential invoice number.", examples=["CKPNQ001-GST-202607-0001"])
    invoice_date: datetime = Field(..., description="Invoice date (order delivery timestamp).")
    order_code: str = Field(..., description="Human-readable order code.")
    customer_name: str | None = Field(default=None, description="Customer name on the invoice.")
    place_of_supply_state_code: str = Field(..., description="2-digit GST state code for place of supply.")
    supply_type: str = Field(..., description="Supply type.", examples=["intra_state", "inter_state"])
    taxable_value: float = Field(..., description="Order value excluding tax.")
    cgst_amount: float = Field(..., description="Central GST amount (intra-state only).")
    sgst_amount: float = Field(..., description="State GST amount (intra-state only).")
    igst_amount: float = Field(..., description="Integrated GST amount (inter-state only).")
    tax_rate: float = Field(..., description="GST rate (%) applied.")
    gross_total: float = Field(..., description="Total invoice value including tax.")

    model_config = {"from_attributes": True}


class GstMonthlyReportResponse(BaseModel):
    """Monthly GST summary — invoice totals for a filing period, refreshed from the live audit."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen this report covers.")
    period_year: int = Field(..., description="Report year.", examples=[2026])
    period_month: int = Field(..., description="Report month (1-12).", examples=[7])
    gstin: str = Field(..., description="Kitchen's GSTIN.")
    legal_name: str = Field(..., description="Kitchen's legal business name.")
    invoice_count: int = Field(..., description="Number of tax invoices in the period.")
    total_taxable: float = Field(..., description="Sum of taxable values across invoices.")
    total_cgst: float = Field(..., description="Sum of CGST across invoices.")
    total_sgst: float = Field(..., description="Sum of SGST across invoices.")
    total_igst: float = Field(..., description="Sum of IGST across invoices.")
    total_tax: float = Field(..., description="Total tax (CGST+SGST+IGST) across invoices.")
    total_gross_sales: float = Field(..., description="Total gross sales (taxable + tax) across invoices.")
    audit_status: str = Field(..., description="Monthly audit status.", examples=["open", "closed"])
    invoices: list[GstTaxInvoiceResponse] = Field(..., description="Invoices included in this report.")


class GstBalanceSheetLine(BaseModel):
    """A single labeled line item on the balance sheet (asset, liability, or equity)."""

    label: str = Field(..., description="Human-readable line item label.")
    amount: float = Field(..., description="Line item amount in INR.")


class GstBalanceSheetResponse(BaseModel):
    """Simplified monthly balance sheet — cash/settlements as assets, GST payable as liability, retained earnings as equity."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen this balance sheet covers.")
    period_year: int = Field(..., description="Period year.")
    period_month: int = Field(..., description="Period month (1-12).")
    assets: list[GstBalanceSheetLine] = Field(..., description="Asset line items (cash & bank from settlements/COD).")
    liabilities: list[GstBalanceSheetLine] = Field(..., description="Liability line items (GST payable, accrued platform fees).")
    equity: list[GstBalanceSheetLine] = Field(..., description="Equity line items (retained earnings).")
    total_assets: float = Field(..., description="Sum of all asset lines.")
    total_liabilities: float = Field(..., description="Sum of all liability lines.")
    total_equity: float = Field(..., description="Sum of all equity lines (assets − liabilities).")


class GstAuditResponse(BaseModel):
    """A kitchen's monthly GST audit — running totals until closed; immutable once closed."""

    id: uuid.UUID = Field(..., description="Audit record ID.")
    kitchen_id: uuid.UUID = Field(..., description="Kitchen this audit covers.")
    period_year: int = Field(..., description="Period year.")
    period_month: int = Field(..., description="Period month (1-12).")
    status: str = Field(..., description="Audit status.", examples=["open", "closed"])
    invoice_count: int = Field(..., description="Number of invoices in the period.")
    total_taxable: float = Field(..., description="Sum of taxable values.")
    total_cgst: float = Field(..., description="Sum of CGST.")
    total_sgst: float = Field(..., description="Sum of SGST.")
    total_igst: float = Field(..., description="Sum of IGST.")
    total_tax: float = Field(..., description="Total tax across invoices.")
    total_gross_sales: float = Field(..., description="Total gross sales across invoices.")
    closed_at: datetime | None = Field(default=None, description="Timestamp the audit was closed (immutable after).")
    balance_sheet: GstBalanceSheetResponse | None = Field(
        default=None, description="Snapshot balance sheet for this period (frozen once closed)."
    )
    invoices: list[GstTaxInvoiceResponse] = Field(..., description="Invoices included in this audit period.")


class GstSyncResponse(BaseModel):
    """Result of syncing delivered orders into GST tax invoices."""

    synced_count: int = Field(..., description="Number of new invoices created in this sync run.")
    invoices: list[GstTaxInvoiceResponse] = Field(..., description="Newly created invoices.")


def _money(value: float) -> float:
    return round(float(value), 2)


def split_tax_inclusive(amount: float, rate_pct: float, *, intra_state: bool) -> dict[str, float]:
    if amount <= 0:
        return {
            "taxable_value": 0.0,
            "cgst_amount": 0.0,
            "sgst_amount": 0.0,
            "igst_amount": 0.0,
            "total_tax": 0.0,
        }
    taxable = _money(amount / (1 + rate_pct / 100))
    tax = _money(amount - taxable)
    if intra_state:
        half = _money(tax / 2)
        remainder = _money(tax - half)
        return {
            "taxable_value": taxable,
            "cgst_amount": half,
            "sgst_amount": remainder,
            "igst_amount": 0.0,
            "total_tax": tax,
        }
    return {
        "taxable_value": taxable,
        "cgst_amount": 0.0,
        "sgst_amount": 0.0,
        "igst_amount": tax,
        "total_tax": tax,
    }


def _period_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=UTC)
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=UTC)
    return start, end


async def _load_kitchen_code(session: AsyncSession, kitchen_id: uuid.UUID) -> str:
    result = await session.execute(
        text("SELECT code FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
        {"kid": kitchen_id},
    )
    code = result.scalar_one_or_none()
    if not code:
        raise ValueError("Kitchen not found")
    return code


def profile_to_response(profile: KitchenGstProfile) -> GstProfileResponse:
    return GstProfileResponse(
        id=profile.id,
        kitchen_id=profile.kitchen_id,
        gstin=profile.gstin,
        legal_name=profile.legal_name,
        trade_name=profile.trade_name,
        state_code=profile.state_code,
        registered_address=profile.registered_address,
        default_tax_rate=float(profile.default_tax_rate),
        is_active=profile.is_active,
        invoice_prefix=profile.invoice_prefix,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def invoice_to_response(invoice: GstTaxInvoice) -> GstTaxInvoiceResponse:
    return GstTaxInvoiceResponse(
        id=invoice.id,
        kitchen_id=invoice.kitchen_id,
        order_id=invoice.order_id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        order_code=invoice.order_code,
        customer_name=invoice.customer_name,
        place_of_supply_state_code=invoice.place_of_supply_state_code,
        supply_type=invoice.supply_type,
        taxable_value=float(invoice.taxable_value),
        cgst_amount=float(invoice.cgst_amount),
        sgst_amount=float(invoice.sgst_amount),
        igst_amount=float(invoice.igst_amount),
        tax_rate=float(invoice.tax_rate),
        gross_total=float(invoice.gross_total),
    )


async def get_gst_profile(session: AsyncSession, kitchen_id: uuid.UUID) -> KitchenGstProfile | None:
    result = await session.execute(
        select(KitchenGstProfile).where(KitchenGstProfile.kitchen_id == kitchen_id)
    )
    return result.scalar_one_or_none()


async def upsert_gst_profile(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    body: GstProfileUpsertRequest,
    publisher: EventPublisher,
) -> KitchenGstProfile:
    state_code = body.gstin[:2]
    prefix = body.invoice_prefix
    if not prefix:
        prefix = await _load_kitchen_code(session, kitchen_id)

    existing = await get_gst_profile(session, kitchen_id)
    now = datetime.now(UTC)
    if existing:
        existing.gstin = body.gstin
        existing.legal_name = body.legal_name
        existing.trade_name = body.trade_name
        existing.state_code = state_code
        existing.registered_address = body.registered_address
        existing.default_tax_rate = body.default_tax_rate
        existing.is_active = body.is_active
        existing.invoice_prefix = prefix
        existing.updated_at = now
        profile = existing
        event_type = "gst.profile.updated"
    else:
        profile = KitchenGstProfile(
            kitchen_id=kitchen_id,
            gstin=body.gstin,
            legal_name=body.legal_name,
            trade_name=body.trade_name,
            state_code=state_code,
            registered_address=body.registered_address,
            default_tax_rate=body.default_tax_rate,
            is_active=body.is_active,
            invoice_prefix=prefix,
        )
        session.add(profile)
        event_type = "gst.profile.created"

    await session.flush()
    event = EventPublisher.build(
        event_type=event_type,
        aggregate_type="gst_profile",
        aggregate_id=str(profile.id),
        producer="billing-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "gstin": profile.gstin,
            "is_active": profile.is_active,
        },
    )
    await publisher.publish(stream_key("billing", "gst"), event, session=session)
    return profile


async def _next_invoice_number(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    prefix: str,
    invoice_date: datetime,
) -> str:
    period = invoice_date.strftime("%Y%m")
    pattern = f"{prefix}-GST-{period}-%"
    result = await session.execute(
        select(func.count())
        .select_from(GstTaxInvoice)
        .where(
            GstTaxInvoice.kitchen_id == kitchen_id,
            GstTaxInvoice.invoice_number.like(pattern),
        )
    )
    seq = int(result.scalar_one()) + 1
    return f"{prefix}-GST-{period}-{seq:04d}"


async def sync_gst_invoices(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    publisher: EventPublisher,
    *,
    year: int | None = None,
    month: int | None = None,
) -> list[GstTaxInvoice]:
    profile = await get_gst_profile(session, kitchen_id)
    if not profile or not profile.is_active:
        raise ValueError("GST profile not active for this kitchen")

    params: dict[str, Any] = {"kid": kitchen_id}
    date_filter = ""
    if year is not None and month is not None:
        start, end = _period_bounds(year, month)
        params["start"] = start
        params["end"] = end
        date_filter = "AND o.updated_at >= :start AND o.updated_at <= :end"

    result = await session.execute(
        text(
            f"""
            SELECT o.id, o.order_code, o.subtotal, o.delivery_fee, o.total,
                   o.customer_name, o.updated_at
            FROM ckac_orders.orders o
            WHERE o.kitchen_id = :kid
              AND o.status = 'delivered'
              AND NOT EXISTS (
                SELECT 1 FROM ckac_billing.gst_tax_invoices gi
                WHERE gi.order_id = o.id
              )
              {date_filter}
            ORDER BY o.updated_at ASC
            """
        ),
        params,
    )
    rows = result.mappings().all()
    created: list[GstTaxInvoice] = []
    prefix = profile.invoice_prefix or await _load_kitchen_code(session, kitchen_id)
    rate = float(profile.default_tax_rate)

    for row in rows:
        gross = float(row["subtotal"]) + float(row["delivery_fee"] or 0)
        tax_parts = split_tax_inclusive(gross, rate, intra_state=True)
        invoice_date = row["updated_at"] or datetime.now(UTC)
        invoice_number = await _next_invoice_number(session, kitchen_id, prefix, invoice_date)
        invoice = GstTaxInvoice(
            kitchen_id=kitchen_id,
            order_id=row["id"],
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            order_code=row["order_code"],
            customer_name=row["customer_name"],
            place_of_supply_state_code=profile.state_code,
            supply_type="intra_state",
            taxable_value=tax_parts["taxable_value"],
            cgst_amount=tax_parts["cgst_amount"],
            sgst_amount=tax_parts["sgst_amount"],
            igst_amount=tax_parts["igst_amount"],
            tax_rate=rate,
            gross_total=gross,
        )
        session.add(invoice)
        await session.flush()
        event = EventPublisher.build(
            event_type="gst.invoice.created",
            aggregate_type="gst_invoice",
            aggregate_id=str(invoice.id),
            producer="billing-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "order_id": str(row["id"]),
                "invoice_number": invoice_number,
                "gross_total": gross,
            },
        )
        await publisher.publish(stream_key("billing", "gst"), event, session=session)
        created.append(invoice)

    return created


async def _load_invoices_for_period(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    year: int,
    month: int,
) -> list[GstTaxInvoice]:
    start, end = _period_bounds(year, month)
    result = await session.execute(
        select(GstTaxInvoice)
        .where(
            GstTaxInvoice.kitchen_id == kitchen_id,
            GstTaxInvoice.invoice_date >= start,
            GstTaxInvoice.invoice_date <= end,
        )
        .order_by(GstTaxInvoice.invoice_date.asc())
    )
    return list(result.scalars().all())


async def _get_or_create_audit(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    year: int,
    month: int,
) -> GstMonthlyAudit:
    result = await session.execute(
        select(GstMonthlyAudit).where(
            GstMonthlyAudit.kitchen_id == kitchen_id,
            GstMonthlyAudit.period_year == year,
            GstMonthlyAudit.period_month == month,
        )
    )
    audit = result.scalar_one_or_none()
    if audit:
        return audit
    audit = GstMonthlyAudit(
        kitchen_id=kitchen_id,
        period_year=year,
        period_month=month,
        status="open",
    )
    session.add(audit)
    await session.flush()
    return audit


def _summarize_invoices(invoices: list[GstTaxInvoice]) -> dict[str, float | int]:
    return {
        "invoice_count": len(invoices),
        "total_taxable": _money(sum(float(i.taxable_value) for i in invoices)),
        "total_cgst": _money(sum(float(i.cgst_amount) for i in invoices)),
        "total_sgst": _money(sum(float(i.sgst_amount) for i in invoices)),
        "total_igst": _money(sum(float(i.igst_amount) for i in invoices)),
        "total_tax": _money(
            sum(float(i.cgst_amount) + float(i.sgst_amount) + float(i.igst_amount) for i in invoices)
        ),
        "total_gross_sales": _money(sum(float(i.gross_total) for i in invoices)),
    }


async def _refresh_audit_totals(
    session: AsyncSession,
    audit: GstMonthlyAudit,
    invoices: list[GstTaxInvoice],
) -> GstMonthlyAudit:
    if audit.status == "closed":
        return audit
    summary = _summarize_invoices(invoices)
    audit.invoice_count = int(summary["invoice_count"])
    audit.total_taxable = float(summary["total_taxable"])
    audit.total_cgst = float(summary["total_cgst"])
    audit.total_sgst = float(summary["total_sgst"])
    audit.total_igst = float(summary["total_igst"])
    audit.total_tax = float(summary["total_tax"])
    audit.total_gross_sales = float(summary["total_gross_sales"])
    audit.updated_at = datetime.now(UTC)
    await session.flush()
    return audit


async def build_balance_sheet(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    year: int,
    month: int,
    *,
    gst_payable: float,
    gross_sales: float,
) -> GstBalanceSheetResponse:
    start, end = _period_bounds(year, month)

    payment_result = await session.execute(
        text(
            """
            SELECT COALESCE(SUM(p.amount), 0) AS captured
            FROM ckac_billing.payments p
            JOIN ckac_orders.orders o ON o.id = p.order_id
            WHERE o.kitchen_id = :kid
              AND p.status = 'captured'
              AND p.updated_at >= :start
              AND p.updated_at <= :end
            """
        ),
        {"kid": kitchen_id, "start": start, "end": end},
    )
    captured = _money(float(payment_result.scalar_one()))

    cod_result = await session.execute(
        text(
            """
            SELECT COALESCE(SUM(o.total), 0) AS cod_total
            FROM ckac_orders.orders o
            WHERE o.kitchen_id = :kid
              AND o.status = 'delivered'
              AND o.payment_method = 'cod'
              AND o.updated_at >= :start
              AND o.updated_at <= :end
            """
        ),
        {"kid": kitchen_id, "start": start, "end": end},
    )
    cod_collected = _money(float(cod_result.scalar_one()))

    settlement_result = await session.execute(
        text(
            """
            SELECT
              COALESCE(SUM(s.platform_fee), 0) AS platform_fees,
              COALESCE(SUM(s.net_to_owner), 0) AS net_to_owner
            FROM ckac_billing.settlements s
            WHERE s.kitchen_id = :kid
              AND s.created_at >= :start
              AND s.created_at <= :end
            """
        ),
        {"kid": kitchen_id, "start": start, "end": end},
    )
    settlement_row = settlement_result.mappings().one()
    platform_fees = _money(float(settlement_row["platform_fees"]))
    net_to_owner = _money(float(settlement_row["net_to_owner"]))

    cash_and_bank = _money(captured + cod_collected if net_to_owner == 0 else net_to_owner + cod_collected)
    if cash_and_bank == 0 and gross_sales > 0:
        cash_and_bank = _money(gross_sales - gst_payable)

    assets = [
        GstBalanceSheetLine(label="Cash & bank (settlements + COD)", amount=cash_and_bank),
    ]
    liabilities = [
        GstBalanceSheetLine(label="GST payable (output tax)", amount=gst_payable),
    ]
    if platform_fees > 0:
        liabilities.append(
            GstBalanceSheetLine(label="Platform fees accrued", amount=platform_fees),
        )

    total_assets = _money(sum(line.amount for line in assets))
    total_liabilities = _money(sum(line.amount for line in liabilities))
    retained = _money(total_assets - total_liabilities)
    equity = [GstBalanceSheetLine(label="Retained earnings", amount=retained)]

    return GstBalanceSheetResponse(
        kitchen_id=kitchen_id,
        period_year=year,
        period_month=month,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=retained,
    )


async def get_monthly_gst_report(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    year: int,
    month: int,
) -> GstMonthlyReportResponse:
    profile = await get_gst_profile(session, kitchen_id)
    if not profile or not profile.is_active:
        raise ValueError("GST profile not active for this kitchen")

    invoices = await _load_invoices_for_period(session, kitchen_id, year, month)
    audit = await _get_or_create_audit(session, kitchen_id, year, month)
    audit = await _refresh_audit_totals(session, audit, invoices)
    summary = _summarize_invoices(invoices)

    return GstMonthlyReportResponse(
        kitchen_id=kitchen_id,
        period_year=year,
        period_month=month,
        gstin=profile.gstin,
        legal_name=profile.legal_name,
        invoice_count=int(summary["invoice_count"]),
        total_taxable=float(summary["total_taxable"]),
        total_cgst=float(summary["total_cgst"]),
        total_sgst=float(summary["total_sgst"]),
        total_igst=float(summary["total_igst"]),
        total_tax=float(summary["total_tax"]),
        total_gross_sales=float(summary["total_gross_sales"]),
        audit_status=audit.status,
        invoices=[invoice_to_response(i) for i in invoices],
    )


async def get_monthly_audit(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    year: int,
    month: int,
) -> GstAuditResponse:
    profile = await get_gst_profile(session, kitchen_id)
    if not profile or not profile.is_active:
        raise ValueError("GST profile not active for this kitchen")

    invoices = await _load_invoices_for_period(session, kitchen_id, year, month)
    audit = await _get_or_create_audit(session, kitchen_id, year, month)
    audit = await _refresh_audit_totals(session, audit, invoices)

    balance_sheet: GstBalanceSheetResponse | None = None
    if audit.balance_sheet_snapshot:
        balance_sheet = GstBalanceSheetResponse.model_validate(audit.balance_sheet_snapshot)
    elif audit.status == "open":
        balance_sheet = await build_balance_sheet(
            session,
            kitchen_id,
            year,
            month,
            gst_payable=float(audit.total_tax),
            gross_sales=float(audit.total_gross_sales),
        )

    return GstAuditResponse(
        id=audit.id,
        kitchen_id=kitchen_id,
        period_year=year,
        period_month=month,
        status=audit.status,
        invoice_count=audit.invoice_count,
        total_taxable=float(audit.total_taxable),
        total_cgst=float(audit.total_cgst),
        total_sgst=float(audit.total_sgst),
        total_igst=float(audit.total_igst),
        total_tax=float(audit.total_tax),
        total_gross_sales=float(audit.total_gross_sales),
        closed_at=audit.closed_at,
        balance_sheet=balance_sheet,
        invoices=[invoice_to_response(i) for i in invoices],
    )


async def close_monthly_audit(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    owner_id: uuid.UUID,
    year: int,
    month: int,
    publisher: EventPublisher,
) -> GstAuditResponse:
    profile = await get_gst_profile(session, kitchen_id)
    if not profile or not profile.is_active:
        raise ValueError("GST profile not active for this kitchen")

    invoices = await _load_invoices_for_period(session, kitchen_id, year, month)
    audit = await _get_or_create_audit(session, kitchen_id, year, month)
    if audit.status == "closed":
        raise ValueError("Monthly audit already closed")

    audit = await _refresh_audit_totals(session, audit, invoices)
    balance_sheet = await build_balance_sheet(
        session,
        kitchen_id,
        year,
        month,
        gst_payable=float(audit.total_tax),
        gross_sales=float(audit.total_gross_sales),
    )
    audit.status = "closed"
    audit.closed_at = datetime.now(UTC)
    audit.closed_by_owner_id = owner_id
    audit.balance_sheet_snapshot = balance_sheet.model_dump(mode="json")
    audit.updated_at = datetime.now(UTC)
    await session.flush()

    event = EventPublisher.build(
        event_type="gst.audit.closed",
        aggregate_type="gst_audit",
        aggregate_id=str(audit.id),
        producer="billing-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "period_year": year,
            "period_month": month,
            "total_tax": float(audit.total_tax),
            "invoice_count": audit.invoice_count,
        },
    )
    await publisher.publish(stream_key("billing", "gst"), event, session=session)
    return await get_monthly_audit(session, kitchen_id, year, month)
