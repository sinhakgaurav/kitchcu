"""Honesty gates — mock Razorpay ids / free capture only in development/test."""

from ckac_common.platform_config import (
    is_dev_provider_id,
    require_dev_payment_mocks,
    verify_meta_signature,
)
import hashlib
import hmac
import os

import pytest


def test_is_dev_provider_id():
    assert is_dev_provider_id("pay_dev_abc") is True
    assert is_dev_provider_id("pay_real_xyz") is False
    assert is_dev_provider_id(None) is True


def test_require_dev_payment_mocks_allows_test_env():
    # conftest sets APP_ENV=test
    require_dev_payment_mocks("Payment capture")


def test_require_dev_payment_mocks_blocks_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    from ckac_common.config import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="live Razorpay"):
            require_dev_payment_mocks("Payment capture")
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()


def test_verify_meta_signature():
    secret = "app_secret_xyz"
    body = b'{"object":"whatsapp_business_account"}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_meta_signature(body, f"sha256={digest}", secret) is True
    assert verify_meta_signature(body, "sha256=deadbeef", secret) is False
    assert verify_meta_signature(body, None, secret) is False
