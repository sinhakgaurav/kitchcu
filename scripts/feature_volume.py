"""Deterministic plan: every kitchen and every diner gets real data in every module.

The existing bulk seeder already lays six months of orders and a live-capture
menu. Platform extras then decorate *one* kitchen and five demo diners. QA and
owner walkthroughs fall over the moment they open a second kitchen or a city
login — CRM empty, no coupons, no tiffin subscriber, no ticket, one address.

This module decides the volume *without* calling the API so the checklist can
be asserted in ``scripts/tests/test_feature_volume.py``. ``seed_feature_volume``
executes the plan against every kitchen/customer the bulk seeder already minted.
"""

from __future__ import annotations

from dataclasses import dataclass

# Kitchen-scoped surfaces an owner opens on kitchen.kitchcu.in.
KITCHEN_SURFACES = (
    "menu",
    "pantry",
    "recipes",
    "orders",
    "drafts",
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
    "delivery_quote",
)

# Customer-scoped surfaces a diner opens on customer.kitchcu.in.
CUSTOMER_SURFACES = (
    "addresses",
    "pwa_orders",
    "ratings",
    "tickets",
    "tiffin_subscription",
    "referrals",
    "notification_prefs",
)


@dataclass(frozen=True)
class FeatureVolumePlan:
    coupons_per_kitchen: int = 4
    promotions_per_kitchen: int = 2
    templates_per_kitchen: int = 4
    tiffin_subscribers_per_kitchen: int = 2
    prep_batches_per_kitchen: int = 1
    refunds_per_kitchen: int = 1
    gst_sync_months: int = 6
    community_recipes_per_kitchen: int = 1
    learning_trials_per_kitchen: int = 1
    addresses_per_customer: int = 3
    pwa_orders_per_customer: int = 4
    ratings_per_customer: int = 3
    tickets_per_customer: int = 2
    referrals_per_customer: int = 1


DEFAULT_PLAN = FeatureVolumePlan()

# Coupon codes stay unique per kitchen (marketing uniqueness is tenant-scoped,
# but a shared WELCOME10 on 30 kitchens is how re-seeds 409 and testers cannot
# tell which kitchen they are exercising).
_COUPON_SPECS = (
    ("WELCOME", "percent", 10, 199),
    ("LOYAL", "percent", 15, 299),
    ("LUNCH", "fixed", 50, 249),
    ("TIFFIN", "percent", 8, 499),
)

_TEMPLATE_SPECS = (
    ("whatsapp", "Daily menu", "Today at {kitchen}: {dish} is live. Reply 1 to order."),
    ("whatsapp", "Order out for delivery", "Hi {name}, {order_code} is on the way. Track: {link}"),
    ("email", "Weekend thali", "This weekend's thali from {kitchen} — book by Friday noon."),
    ("email", "Win-back", "We miss you at {kitchen}. Here's {code} for 15% off your next order."),
)


def kitchen_coupon_specs(kitchen_code: str, count: int | None = None) -> list[dict]:
    code = (kitchen_code or "CKXXX").upper().replace("-", "")[:8]
    n = DEFAULT_PLAN.coupons_per_kitchen if count is None else count
    out: list[dict] = []
    for suffix, discount_type, discount_value, min_order in _COUPON_SPECS[:n]:
        out.append(
            {
                "code": f"{code}{suffix}"[:20],
                "discount_type": discount_type,
                "discount_value": discount_value,
                "min_order_amount": min_order,
                "max_uses": 500,
            }
        )
    return out


def kitchen_template_specs(kitchen_name: str, count: int | None = None) -> list[dict]:
    n = DEFAULT_PLAN.templates_per_kitchen if count is None else count
    out: list[dict] = []
    for channel, name, body in _TEMPLATE_SPECS[:n]:
        spec: dict = {
            "channel": channel,
            "name": f"{name} · {kitchen_name}"[:120],
            "body": body,
            "is_active": True,
        }
        if channel == "email":
            spec["subject"] = f"{kitchen_name}: {name}"[:255]
        out.append(spec)
    return out


def extra_address_specs(diner: dict) -> list[dict]:
    """Work + family pins in the same city so the address book is not a single Home."""
    city = str(diner.get("city") or "Pune")
    state = str(diner.get("state") or "Maharashtra")
    pincode = str(diner.get("pincode") or "411001")
    phone = str(diner.get("phone_e164") or diner.get("phone") or "")
    lat = float(diner.get("latitude") or 18.5362)
    lng = float(diner.get("longitude") or 73.8958)
    line = str(diner.get("address_line") or city)
    return [
        {
            "label": "Work",
            "address_line": f"Office park near {line}",
            "city": city,
            "state": state,
            "pincode": pincode,
            "phone": phone,
            "latitude": round(lat + 0.012, 6),
            "longitude": round(lng + 0.008, 6),
            "is_default": False,
        },
        {
            "label": "Family",
            "address_line": f"Parents' house, {line}",
            "city": city,
            "state": state,
            "pincode": pincode,
            "phone": phone,
            "latitude": round(lat - 0.009, 6),
            "longitude": round(lng - 0.006, 6),
            "is_default": False,
        },
    ]


def kitchens_for_diner(diner: dict, kitchens: list[dict]) -> list[dict]:
    """Prefer same-city kitchens so discovery, delivery quotes and CRM stay coherent."""
    city = str(diner.get("city") or "")
    same = [k for k in kitchens if str(k.get("city") or "") == city]
    return same or list(kitchens)


def diner_ticket_subjects(diner: dict, kitchen_code: str) -> list[str]:
    phone = str(diner.get("phone") or diner.get("phone_e164") or "diner")[-4:]
    tag = f"{kitchen_code or 'CK'}-{phone}"
    return [
        f"Volume seed — late delivery {tag}",
        f"Volume seed — packaging {tag}",
    ]


def diner_referral_phone(diner: dict, slot: int) -> str:
    """Unused 10-digit mobile that cannot collide with demo / weekly / city logins."""
    digits = "".join(ch for ch in str(diner.get("phone") or diner.get("phone_e164") or "6200000000") if ch.isdigit())
    tail = int(digits[-8:] or "1")
    # 60… prefix is reserved for volume-seed referral leads (not 62 city / 7–8 weekly / 91 demo).
    return f"60{(tail + slot) % 10_000_000:08d}"
