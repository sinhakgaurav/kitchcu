"""Build receipt context and render PDF bills."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MasterOrder, Order


def _ascii_safe(text: str) -> str:
    if not text:
        return text
    replacements = {
        "\u20b9": "Rs ",
        "\u2014": " - ",
        "\u2013": "-",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("ascii", "replace").decode("ascii")


@dataclass
class ReceiptLine:
    name: str
    quantity: int
    unit_price: float
    line_total: float


@dataclass
class ReceiptPayment:
    method: str
    status: str
    amount: float | None
    reference: str | None


@dataclass
class OrderReceipt:
    bill_id: str
    order_code: str
    kitchen_name: str
    kitchen_code: str
    kitchen_city: str | None
    customer_name: str | None
    customer_phone: str | None
    status: str
    delivery_type: str
    payment_method: str
    subtotal: float
    delivery_fee: float
    total: float
    created_at: datetime
    lines: list[ReceiptLine]
    payment: ReceiptPayment | None = None
    master_order_code: str | None = None


@dataclass
class MasterReceipt:
    master_order_code: str
    payment_method: str
    subtotal: float
    delivery_fee: float
    total: float
    created_at: datetime
    orders: list[OrderReceipt]


async def _load_kitchen_meta(session: AsyncSession, kitchen_id: uuid.UUID) -> tuple[str, str, str | None]:
    result = await session.execute(
        text(
            "SELECT name, code, city FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"
        ),
        {"kid": kitchen_id},
    )
    row = result.one_or_none()
    if not row:
        raise ValueError("Kitchen not found")
    return row[0], row[1], row[2]


async def _load_payment(session: AsyncSession, order_id: uuid.UUID) -> ReceiptPayment | None:
    result = await session.execute(
        text(
            """
            SELECT method, status, amount, razorpay_payment_id
            FROM ckac_billing.payments
            WHERE order_id = :oid
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"oid": order_id},
    )
    row = result.one_or_none()
    if not row:
        return None
    return ReceiptPayment(
        method=row[0],
        status=row[1],
        amount=float(row[2]) if row[2] is not None else None,
        reference=row[3],
    )


async def build_order_receipt(session: AsyncSession, order: Order) -> OrderReceipt:
    kitchen_name, kitchen_code, kitchen_city = await _load_kitchen_meta(session, order.kitchen_id)
    items = (
        await session.execute(
            text(
                """
                SELECT dish_name, quantity, unit_price
                FROM ckac_orders.order_items
                WHERE order_id = :oid
                ORDER BY id
                """
            ),
            {"oid": order.id},
        )
    ).all()
    lines = [
        ReceiptLine(
            name=row[0],
            quantity=int(row[1]),
            unit_price=float(row[2]),
            line_total=float(row[2]) * int(row[1]),
        )
        for row in items
    ]
    payment = await _load_payment(session, order.id)
    master_code = None
    if order.master_order_id:
        master = await session.get(MasterOrder, order.master_order_id)
        if master:
            master_code = master.master_order_code

    return OrderReceipt(
        bill_id=order.bill_id,
        order_code=order.order_code,
        kitchen_name=kitchen_name,
        kitchen_code=kitchen_code,
        kitchen_city=kitchen_city,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        status=order.status,
        delivery_type=order.delivery_type,
        payment_method=order.payment_method,
        subtotal=float(order.subtotal),
        delivery_fee=float(order.delivery_fee),
        total=float(order.total),
        created_at=order.created_at,
        lines=lines,
        payment=payment,
        master_order_code=master_code,
    )


async def build_master_receipt(session: AsyncSession, master: MasterOrder) -> MasterReceipt:
    from sqlalchemy import select

    orders = (
        await session.execute(
            select(Order).where(Order.master_order_id == master.id).order_by(Order.created_at)
        )
    ).scalars().all()
    order_receipts = [await build_order_receipt(session, o) for o in orders]
    return MasterReceipt(
        master_order_code=master.master_order_code,
        payment_method=master.payment_method,
        subtotal=float(master.subtotal),
        delivery_fee=float(master.delivery_fee),
        total=float(master.total),
        created_at=master.created_at,
        orders=order_receipts,
    )


def render_order_bill_pdf(receipt: OrderReceipt) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _ascii_safe("kitchCU Bill / Receipt"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _ascii_safe(f"Bill ID: {receipt.bill_id}"), ln=True)
    pdf.cell(0, 6, _ascii_safe(f"Order: {receipt.order_code}"), ln=True)
    if receipt.master_order_code:
        pdf.cell(0, 6, _ascii_safe(f"Master order: {receipt.master_order_code}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, _ascii_safe(receipt.kitchen_name), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        6,
        _ascii_safe(f"{receipt.kitchen_code}" + (f" · {receipt.kitchen_city}" if receipt.kitchen_city else "")),
        ln=True,
    )
    pdf.ln(2)

    created = receipt.created_at.strftime("%d %b %Y, %H:%M UTC")
    pdf.cell(0, 6, _ascii_safe(f"Date: {created}"), ln=True)
    pdf.cell(0, 6, _ascii_safe(f"Status: {receipt.status}"), ln=True)
    pdf.cell(0, 6, _ascii_safe(f"Delivery: {receipt.delivery_type}"), ln=True)
    if receipt.customer_name or receipt.customer_phone:
        pdf.cell(
            0,
            6,
            _ascii_safe(
                f"Customer: {receipt.customer_name or '-'} · {receipt.customer_phone or '-'}"
            ),
            ln=True,
        )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 7, "Item", border=1)
    pdf.cell(25, 7, "Qty", border=1, align="C")
    pdf.cell(35, 7, "Rate (Rs)", border=1, align="R")
    pdf.cell(40, 7, "Amount (Rs)", border=1, align="R", ln=True)
    pdf.set_font("Helvetica", "", 10)

    for line in receipt.lines:
        pdf.cell(90, 7, _ascii_safe(line.name[:40]), border=1)
        pdf.cell(25, 7, str(line.quantity), border=1, align="C")
        pdf.cell(35, 7, f"{line.unit_price:.0f}", border=1, align="R")
        pdf.cell(40, 7, f"{line.line_total:.0f}", border=1, align="R", ln=True)

    pdf.ln(4)
    pdf.cell(150, 6, "Subtotal", align="R")
    pdf.cell(40, 6, f"Rs {receipt.subtotal:.0f}", align="R", ln=True)
    if receipt.delivery_fee > 0:
        pdf.cell(150, 6, "Delivery fee", align="R")
        pdf.cell(40, 6, f"Rs {receipt.delivery_fee:.0f}", align="R", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(150, 8, "Total", align="R")
    pdf.cell(40, 8, f"Rs {receipt.total:.0f}", align="R", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(4)

    method = receipt.payment.method if receipt.payment else receipt.payment_method
    pdf.cell(0, 6, _ascii_safe(f"Payment method: {method.upper()}"), ln=True)
    if receipt.payment:
        pdf.cell(0, 6, _ascii_safe(f"Payment status: {receipt.payment.status}"), ln=True)
        if receipt.payment.reference:
            pdf.cell(0, 6, _ascii_safe(f"Payment ref: {receipt.payment.reference}"), ln=True)

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        _ascii_safe(
            "This is a food order receipt from kitchCU. "
            "No per-order food commission — owner subscription SaaS only."
        ),
    )
    return pdf.output()


def render_master_bill_pdf(receipt: MasterReceipt) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _ascii_safe("kitchCU Master Receipt"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _ascii_safe(f"Master order: {receipt.master_order_code}"), ln=True)
    pdf.cell(
        0,
        6,
        _ascii_safe(f"Date: {receipt.created_at.strftime('%d %b %Y, %H:%M UTC')}"),
        ln=True,
    )
    pdf.cell(0, 6, _ascii_safe(f"Payment: {receipt.payment_method.upper()}"), ln=True)
    pdf.ln(6)

    for idx, order in enumerate(receipt.orders, start=1):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _ascii_safe(f"{idx}. {order.kitchen_name} ({order.order_code})"), ln=True)
        pdf.set_font("Helvetica", "", 10)
        for line in order.lines:
            pdf.cell(
                0,
                6,
                _ascii_safe(
                    f"   {line.quantity} x {line.name} — Rs {line.line_total:.0f}"
                ),
                ln=True,
            )
        pdf.cell(0, 6, _ascii_safe(f"   Kitchen total: Rs {order.total:.0f}"), ln=True)
        pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(150, 8, "Grand total", align="R")
    pdf.cell(40, 8, f"Rs {receipt.total:.0f}", align="R", ln=True)
    return pdf.output()


def bill_pdf_filename(order_code: str) -> str:
    safe = order_code.replace("/", "-").replace("\\", "-")
    return f"{safe}.pdf"
