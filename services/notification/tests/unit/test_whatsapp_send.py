"""WhatsApp Cloud API outbound client — unit (no network / no DB)."""

import asyncio

from app.whatsapp_send import send_text_message


def test_dev_without_token_simulates_success(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("THIRD_PARTY_INTEGRATIONS", "1")
    result = asyncio.run(
        send_text_message(
            phone_number_id="",
            to_phone="+919876543210",
            text="Hello",
            access_token="",
        )
    )
    assert result.ok is True
    assert result.simulated is True


def test_simulate_flag_bypasses_graph(monkeypatch):
    monkeypatch.setenv("THIRD_PARTY_INTEGRATIONS", "1")
    monkeypatch.setenv("WHATSAPP_SIMULATE_SEND", "true")
    result = asyncio.run(
        send_text_message(
            phone_number_id="123",
            to_phone="+919876543210",
            text="Hello",
            access_token="token",
        )
    )
    assert result.ok is True
    assert result.simulated is True


def test_third_party_flag_off_simulates_without_meta(monkeypatch):
    monkeypatch.setenv("THIRD_PARTY_INTEGRATIONS", "0")
    monkeypatch.setenv("APP_ENV", "production")
    result = asyncio.run(
        send_text_message(
            phone_number_id="123",
            to_phone="+919876543210",
            text="Hello",
            access_token="real-token",
        )
    )
    assert result.ok is True
    assert result.simulated is True
