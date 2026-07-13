"""GST tax split unit tests."""

from app.gst import split_tax_inclusive


def test_split_tax_inclusive_intra_state():
    parts = split_tax_inclusive(105.0, 5.0, intra_state=True)
    assert parts["taxable_value"] == 100.0
    assert parts["cgst_amount"] == 2.5
    assert parts["sgst_amount"] == 2.5
    assert parts["igst_amount"] == 0.0
    assert parts["total_tax"] == 5.0


def test_split_tax_inclusive_inter_state():
    parts = split_tax_inclusive(105.0, 5.0, intra_state=False)
    assert parts["taxable_value"] == 100.0
    assert parts["igst_amount"] == 5.0
    assert parts["cgst_amount"] == 0.0
    assert parts["sgst_amount"] == 0.0


def test_split_tax_inclusive_zero_amount():
    parts = split_tax_inclusive(0.0, 5.0, intra_state=True)
    assert parts["taxable_value"] == 0.0
    assert parts["total_tax"] == 0.0
