"""Offline unit tests for options-first support resolver (no DB)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    name = "ckac_ai_context_load_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / "load.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_owner_pricing():
    mod = _load()
    t = mod.resolve_support_turn("owner", "What are your pricing plans?")
    assert t.answer_id == "owner.pricing.plans"
    assert "499" in t.reply
    assert t.options


def test_owner_refunds():
    mod = _load()
    t = mod.resolve_support_turn("owner", "How do customer refunds work?")
    assert t.answer_id == "owner.billing.refunds"


def test_customer_checkout_not_stale():
    mod = _load()
    t = mod.resolve_support_turn("customer", "Can I checkout and pay with UPI?")
    assert t.answer_id == "customer.order.checkout"
    assert "coming in the next release" not in t.reply.lower()


def test_customer_track():
    mod = _load()
    t = mod.resolve_support_turn("customer", "Track my order status")
    assert t.answer_id == "customer.order.track"


def test_greeting_menu():
    mod = _load()
    t = mod.resolve_support_turn("owner", "hi")
    assert t.answer_id == "support.main_menu"
    assert len(t.options) >= 5


def test_menu_option_number():
    mod = _load()
    t = mod.resolve_support_turn("owner", "1", selected_option_id="1")
    assert t.answer_id == "owner.pricing.plans"
