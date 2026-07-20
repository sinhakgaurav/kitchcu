"""Monthly GST calculation exports — Excel (.xlsx) and PDF for accountant handoff."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from zipfile import ZIP_DEFLATED, ZipFile

from app.gst import GstBalanceSheetResponse, GstMonthlyReportResponse

MONTH_NAMES = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


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


def _money(n: float) -> str:
    return f"{float(n):.2f}"


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _cell(ref: str, value: str | float | int, *, number: bool = False) -> str:
    if number:
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{_xml_escape(str(value))}</t></is></c>'


def _col_letter(idx: int) -> str:
    """1-based column index → Excel letter (A..Z, AA..)."""
    letters = ""
    n = idx
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def render_monthly_gst_excel(
    report: GstMonthlyReportResponse,
    balance_sheet: GstBalanceSheetResponse | None = None,
) -> bytes:
    """Build a real .xlsx (OOXML) workbook Excel can open — no third-party required."""
    period = f"{MONTH_NAMES[report.period_month]} {report.period_year}"
    rows: list[list[str | float | int]] = [
        ["kitchCU Monthly GST Calculation"],
        ["Period", period],
        ["GSTIN", report.gstin],
        ["Legal name", report.legal_name],
        ["Audit status", report.audit_status],
        [],
        ["Summary"],
        ["Invoice count", report.invoice_count],
        ["Total taxable", report.total_taxable],
        ["Total CGST", report.total_cgst],
        ["Total SGST", report.total_sgst],
        ["Total IGST", report.total_igst],
        ["Total tax", report.total_tax],
        ["Total gross sales", report.total_gross_sales],
        [],
        [
            "Invoice number",
            "Order code",
            "Invoice date",
            "Customer",
            "Supply type",
            "Taxable",
            "CGST",
            "SGST",
            "IGST",
            "Tax rate %",
            "Gross total",
        ],
    ]
    for inv in report.invoices:
        rows.append(
            [
                inv.invoice_number,
                inv.order_code,
                inv.invoice_date.strftime("%Y-%m-%d"),
                inv.customer_name or "",
                inv.supply_type,
                float(inv.taxable_value),
                float(inv.cgst_amount),
                float(inv.sgst_amount),
                float(inv.igst_amount),
                float(inv.tax_rate),
                float(inv.gross_total),
            ]
        )

    if balance_sheet:
        rows.extend(
            [
                [],
                ["Balance sheet"],
                ["Section", "Label", "Amount"],
            ]
        )
        for line in balance_sheet.assets:
            rows.append(["Asset", line.label, float(line.amount)])
        for line in balance_sheet.liabilities:
            rows.append(["Liability", line.label, float(line.amount)])
        for line in balance_sheet.equity:
            rows.append(["Equity", line.label, float(line.amount)])
        rows.append(["", "Total assets", float(balance_sheet.total_assets)])
        rows.append(["", "Total liabilities", float(balance_sheet.total_liabilities)])
        rows.append(["", "Total equity", float(balance_sheet.total_equity)])

    sheet_rows_xml: list[str] = []
    for r_idx, row in enumerate(rows, start=1):
        cells: list[str] = []
        for c_idx, value in enumerate(row, start=1):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(_cell(ref, value, number=True))
            else:
                cells.append(_cell(ref, value if value is not None else ""))
        sheet_rows_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows_xml)}</sheetData>"
        "</worksheet>"
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="GST Monthly" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    buf = io.BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def render_monthly_gst_pdf(
    report: GstMonthlyReportResponse,
    balance_sheet: GstBalanceSheetResponse | None = None,
) -> bytes:
    from fpdf import FPDF

    period = f"{MONTH_NAMES[report.period_month]} {report.period_year}"
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, _ascii_safe("kitchCU Monthly GST Calculation"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _ascii_safe(f"Period: {period}"), ln=True)
    pdf.cell(0, 6, _ascii_safe(f"GSTIN: {report.gstin}"), ln=True)
    pdf.cell(0, 6, _ascii_safe(f"Legal name: {report.legal_name}"), ln=True)
    pdf.cell(0, 6, _ascii_safe(f"Audit status: {report.audit_status}"), ln=True)
    pdf.cell(
        0,
        6,
        _ascii_safe(f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"),
        ln=True,
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for label, value in (
        ("Invoice count", str(report.invoice_count)),
        ("Taxable value", f"Rs {_money(report.total_taxable)}"),
        ("CGST", f"Rs {_money(report.total_cgst)}"),
        ("SGST", f"Rs {_money(report.total_sgst)}"),
        ("IGST", f"Rs {_money(report.total_igst)}"),
        ("Total tax", f"Rs {_money(report.total_tax)}"),
        ("Gross sales", f"Rs {_money(report.total_gross_sales)}"),
    ):
        pdf.cell(70, 6, _ascii_safe(label))
        pdf.cell(0, 6, _ascii_safe(value), ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Tax invoices", ln=True)
    pdf.set_font("Helvetica", "B", 8)
    cols = [
        (38, "Invoice"),
        (32, "Order"),
        (22, "Date"),
        (24, "Taxable"),
        (18, "CGST"),
        (18, "SGST"),
        (24, "Gross"),
    ]
    for w, h in cols:
        pdf.cell(w, 6, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    if not report.invoices:
        pdf.cell(176, 6, "No invoices in this period", border=1, ln=True)
    else:
        for inv in report.invoices:
            pdf.cell(38, 5, _ascii_safe(inv.invoice_number[:22]), border=1)
            pdf.cell(32, 5, _ascii_safe(inv.order_code[:18]), border=1)
            pdf.cell(22, 5, inv.invoice_date.strftime("%Y-%m-%d"), border=1)
            pdf.cell(24, 5, _money(inv.taxable_value), border=1, align="R")
            pdf.cell(18, 5, _money(inv.cgst_amount), border=1, align="R")
            pdf.cell(18, 5, _money(inv.sgst_amount), border=1, align="R")
            pdf.cell(24, 5, _money(inv.gross_total), border=1, align="R", ln=True)

    if balance_sheet:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Balance sheet", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for section, lines in (
            ("Assets", balance_sheet.assets),
            ("Liabilities", balance_sheet.liabilities),
            ("Equity", balance_sheet.equity),
        ):
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, section, ln=True)
            pdf.set_font("Helvetica", "", 9)
            for line in lines:
                pdf.cell(100, 5, _ascii_safe(line.label))
                pdf.cell(0, 5, f"Rs {_money(line.amount)}", ln=True, align="R")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(100, 5, "Total assets")
        pdf.cell(0, 5, f"Rs {_money(balance_sheet.total_assets)}", ln=True, align="R")
        pdf.cell(100, 5, "Total liabilities")
        pdf.cell(0, 5, f"Rs {_money(balance_sheet.total_liabilities)}", ln=True, align="R")
        pdf.cell(100, 5, "Total equity")
        pdf.cell(0, 5, f"Rs {_money(balance_sheet.total_equity)}", ln=True, align="R")

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0,
        4,
        _ascii_safe(
            "Accountant handoff export from kitchCU. Output tax from delivered-order invoices. "
            "No per-order food commission — owner subscription SaaS only."
        ),
    )
    return bytes(pdf.output())


def export_filename(kitchen_code: str | None, year: int, month: int, ext: str) -> str:
    code = (kitchen_code or "kitchen").replace(" ", "_")
    return f"kitchcu-gst-{code}-{year}-{month:02d}.{ext}"
