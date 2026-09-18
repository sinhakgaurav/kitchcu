"""Every kitchen and every diner must have a planned row in every module.

The bulk seeder used to decorate only CKPNQ001 and five demo phones. These
tests pin the volume plan so a second kitchen or a Mumbai login is not an
empty CRM / empty address book / empty tiffin inbox.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from feature_volume import (  # noqa: E402
    CUSTOMER_SURFACES,
    DEFAULT_PLAN,
    KITCHEN_SURFACES,
    diner_referral_phone,
    diner_ticket_subjects,
    extra_address_specs,
    kitchen_coupon_specs,
    kitchen_template_specs,
    kitchens_for_diner,
)


def test_every_owner_module_is_on_the_kitchen_checklist() -> None:
    required = {
        "menu",
        "pantry",
        "recipes",
        "orders",
        "coupons",
        "promotions",
        "templates",
        "tiffin_plans",
        "tiffin_subscribers",
        "prep_batches",
        "crm",
        "whatsapp",
        "payments",
        "gst",
        "refunds",
        "branded_page",
        "streaming",
        "learning",
        "community",
        "growth_suggestions",
        "daily_menu",
    }
    assert required <= set(KITCHEN_SURFACES)


def test_every_diner_module_is_on_the_customer_checklist() -> None:
    required = {
        "addresses",
        "pwa_orders",
        "ratings",
        "tickets",
        "tiffin_subscription",
        "referrals",
        "notification_prefs",
    }
    assert required <= set(CUSTOMER_SURFACES)


def test_volume_is_huge_enough_to_fill_lists_not_empty_states() -> None:
    plan = DEFAULT_PLAN
    assert plan.coupons_per_kitchen >= 4
    assert plan.templates_per_kitchen >= 4
    assert plan.tiffin_subscribers_per_kitchen >= 2
    assert plan.gst_sync_months >= 6
    assert plan.addresses_per_customer >= 3
    assert plan.pwa_orders_per_customer >= 4
    assert plan.ratings_per_customer >= 3
    assert plan.tickets_per_customer >= 2


def test_coupon_codes_are_unique_per_kitchen() -> None:
    a = [c["code"] for c in kitchen_coupon_specs("CKPNQ001")]
    b = [c["code"] for c in kitchen_coupon_specs("CKBOM001")]
    assert len(a) == len(set(a)) == DEFAULT_PLAN.coupons_per_kitchen
    assert set(a).isdisjoint(set(b))
    assert all(code.startswith("CKPNQ001") or code.startswith("CKPNQ") for code in a)
    types = {c["discount_type"] for c in kitchen_coupon_specs("CKPNQ001")}
    assert types <= {"percent", "fixed"}
    assert "fixed" in types


def test_templates_cover_whatsapp_and_email() -> None:
    specs = kitchen_template_specs("Sharma Home Kitchen")
    channels = {s["channel"] for s in specs}
    assert channels == {"whatsapp", "email"}
    assert all(s.get("subject") for s in specs if s["channel"] == "email")


def test_extra_addresses_are_work_and_family_in_the_same_city() -> None:
    diner = {
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400050",
        "phone_e164": "+916201000001",
        "address_line": "Bandra West",
        "latitude": 19.05,
        "longitude": 72.83,
    }
    extras = extra_address_specs(diner)
    assert {a["label"] for a in extras} == {"Work", "Family"}
    assert all(a["city"] == "Mumbai" for a in extras)
    assert all(a["is_default"] is False for a in extras)
    assert 1 + len(extras) >= DEFAULT_PLAN.addresses_per_customer


def test_diners_prefer_kitchens_in_their_city() -> None:
    kitchens = [
        {"id": "pune", "city": "Pune", "code": "CKPNQ001"},
        {"id": "bom", "city": "Mumbai", "code": "CKBOM001"},
    ]
    picked = kitchens_for_diner({"city": "Mumbai"}, kitchens)
    assert [k["id"] for k in picked] == ["bom"]
    assert kitchens_for_diner({"city": "Goa"}, kitchens) == kitchens


def test_referral_phones_stay_off_demo_and_weekly_prefixes() -> None:
    phone = diner_referral_phone({"phone": "6201000001"}, 0)
    assert len(phone) == 10
    assert phone.startswith("60")
    assert diner_referral_phone({"phone": "6201000001"}, 0) == phone
    assert diner_referral_phone({"phone": "6201000001"}, 1) != phone


def test_ticket_subjects_are_stable_per_diner_and_kitchen() -> None:
    subjects = diner_ticket_subjects({"phone": "6201000001"}, "CKBOM001")
    assert len(subjects) >= DEFAULT_PLAN.tickets_per_customer
    assert all("CKBOM001" in s for s in subjects)
    assert subjects == diner_ticket_subjects({"phone": "6201000001"}, "CKBOM001")


def test_bulk_seeder_runs_feature_volume() -> None:
    text = (SCRIPTS / "seed-bulk-data.py").read_text(encoding="utf-8")
    assert "seed_feature_volume" in text
    assert "CKAC_FEATURE_VOLUME" in text
    assert "harvest_secondary_demo_kitchens" in text
    assert "kitchen_ctxs" in text
