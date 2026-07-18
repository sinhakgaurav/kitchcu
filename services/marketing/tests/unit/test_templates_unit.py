"""Marketing template helpers — unit (no DB)."""

import pytest
from pydantic import ValidationError

from app.templates import TemplateCreateRequest, _extract_variables, _render_template


def test_extract_variables_from_body_and_subject():
    vars_ = _extract_variables(
        "Hi {{ customer_name }}, order {{ order_code }} ready!",
        "Update for {{ customer_name }}",
    )
    assert vars_ == ["customer_name", "order_code"]


def test_extract_variables_empty():
    assert _extract_variables("Plain text with no vars", None) == []


def test_render_template_replaces_spaced_and_tight_vars():
    out = _render_template(
        "Hi {{ customer_name }} — {{kitchen_name}} specials",
        {"customer_name": "Asha", "kitchen_name": "Spice Box"},
    )
    assert out == "Hi Asha — Spice Box specials"


def test_create_request_rejects_bad_channel():
    with pytest.raises(ValidationError):
        TemplateCreateRequest(channel="sms", name="x", body="Hello world message")


def test_create_request_normalizes_channel():
    req = TemplateCreateRequest(
        channel="WhatsApp",
        name="Daily menu",
        body="Today: {{ dish_name }} — order now",
    )
    assert req.channel == "whatsapp"
