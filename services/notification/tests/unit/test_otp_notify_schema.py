"""OTP notify request schema (no DB)."""

from app.notification_domain import OtpNotifyRequest


def test_otp_notify_request_accepts_payload():
    body = OtpNotifyRequest(phone="+919876543210", code="482913", purpose="owner_login")
    assert body.code == "482913"
    assert body.purpose == "owner_login"
