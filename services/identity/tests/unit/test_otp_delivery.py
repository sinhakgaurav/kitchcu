"""OTP helpers (no DB)."""

from app.otp_delivery import generate_otp_code


def test_generate_otp_six_digits():
    code = generate_otp_code()
    assert len(code) == 6
    assert code.isdigit()
