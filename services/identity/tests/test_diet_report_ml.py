"""Unit tests for checkup ML parse + dish compatibility (no DB)."""

from __future__ import annotations

from app.diet_report import (
    DISCLAIMER,
    dish_is_compatible,
    extract_lab_values,
    extract_pdf_text,
    extract_report_text,
    parse_report_to_profile,
)


def _pdf(text: str) -> bytes:
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET".encode("latin-1", errors="replace")
    objs = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n",
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n",
        b"4 0 obj<< /Length "
        + str(len(stream)).encode()
        + b" >>stream\n"
        + stream
        + b"\nendstream\nendobj\n",
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
    ]
    body = b"".join(objs)
    xref_positions = []
    offset = len(b"%PDF-1.1\n")
    chunks = [b"%PDF-1.1\n"]
    for obj in objs:
        xref_positions.append(offset)
        chunks.append(obj)
        offset += len(obj)
    xref_start = offset
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for pos in xref_positions:
        xref.append(f"{pos:010d} 00000 n \n".encode())
    trailer = (
        b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_start).encode()
        + b"\n%%EOF\n"
    )
    return b"".join(chunks + xref) + trailer


def test_hba1c_report_flags_diabetes_and_excludes_sweets():
    profile = parse_report_to_profile(
        "Laboratory report. HbA1c 8.2%. Type 2 Diabetes Mellitus. Fasting glucose 168 mg/dl."
    )
    assert "diabetes" in profile.conditions
    assert "desserts" in profile.avoid_categories
    assert DISCLAIMER in profile.disclaimer
    assert dish_is_compatible(
        name="Gulab Jamun",
        category_slug="desserts",
        ingredient_blob="khoya sugar",
        profile=profile,
    ) is False
    assert dish_is_compatible(
        name="Dal Tadka",
        category_slug="veg",
        ingredient_blob="toor dal turmeric",
        profile=profile,
    ) is True


def test_normal_labs_do_not_invent_diabetes():
    profile = parse_report_to_profile(
        "Complete blood count within normal limits. Hb 13.2. Annual wellness visit."
    )
    assert "diabetes" not in profile.conditions
    assert dish_is_compatible(
        name="Gulab Jamun",
        category_slug="desserts",
        ingredient_blob="sugar",
        profile=profile,
    ) is True


def test_hypertension_and_gout_keywords():
    bp = parse_report_to_profile("Blood pressure 168/102 mmHg essential hypertension")
    assert "hypertension" in bp.conditions
    gout = parse_report_to_profile("Uric acid 9.1 mg/dl acute gout flare")
    assert "gout" in gout.conditions
    assert dish_is_compatible(
        name="Mutton Rogan Josh",
        category_slug="non_veg",
        ingredient_blob="mutton",
        profile=gout,
    ) is False


def test_extract_lab_values():
    labs = extract_lab_values("HbA1c 7.1% LDL 190 mg/dl TSH 12.5")
    assert labs["hba1c"] == 7.1
    assert labs["ldl"] == 190
    assert labs["tsh"] == 12.5


def test_pdf_text_roundtrip():
    data = _pdf("HbA1c 8.2% Type 2 Diabetes Mellitus")
    assert "Diabetes" in extract_pdf_text(data)
    combined = extract_report_text(data=data, notes="optional note")
    assert "Diabetes" in combined
    assert "optional note" in combined


def test_image_bytes_need_notes():
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01"
        b"\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    assert extract_report_text(data=png, notes="") == ""
    assert "diabetes" in extract_report_text(data=png, notes="Known diabetes mellitus").lower()
