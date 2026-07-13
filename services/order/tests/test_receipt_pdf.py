"""Unit tests for PDF bill rendering (no database)."""

from datetime import UTC, datetime

from app.receipts import (
    OrderReceipt,
    ReceiptLine,
    ReceiptPayment,
    bill_pdf_filename,
    render_order_bill_pdf,
)


def test_render_order_bill_pdf_bytes():
    receipt = OrderReceipt(
        bill_id="BILL-20260713-0001",
        order_code="CKPNQ001-BILL-20260713-0001",
        kitchen_name="Raj Home Kitchen",
        kitchen_code="CKPNQ001",
        kitchen_city="Pune",
        customer_name="Asha",
        customer_phone="+919876543210",
        status="delivered",
        delivery_type="pickup",
        payment_method="upi",
        subtotal=398.0,
        delivery_fee=0.0,
        total=398.0,
        created_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        lines=[
            ReceiptLine(name="Paneer Tikka", quantity=2, unit_price=199.0, line_total=398.0),
        ],
        payment=ReceiptPayment(method="upi", status="captured", amount=398.0, reference="pay_dev_1"),
    )
    pdf = render_order_bill_pdf(receipt)
    assert isinstance(pdf, (bytes, bytearray))
    assert bytes(pdf)[:4] == b"%PDF"


def test_bill_pdf_filename_sanitizes():
    assert bill_pdf_filename("CKPNQ001-BILL-20260713-0001") == "CKPNQ001-BILL-20260713-0001.pdf"
