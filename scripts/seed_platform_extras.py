"""Extended platform seed — every persona, CRM, ratings, recipes, subscriptions."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from demo_data import DEMO_ADMIN, DEMO_CUSTOMERS, DEMO_OTP
from seed_common import ApiError, login_admin, login_customer, login_owner, log, request


def ensure_admin_session() -> str:
    token = login_admin(DEMO_ADMIN["email"], DEMO_ADMIN["password"])
    log("  Admin login OK")
    return token


def ensure_customer_sessions() -> list[dict]:
    sessions: list[dict] = []
    for customer in DEMO_CUSTOMERS:
        try:
            token = login_customer(customer["phone_e164"], DEMO_OTP)
            sessions.append({**customer, "token": token})
            log(f"  Customer login: {customer['name']} ({customer['phone']})")
        except ApiError as exc:
            log(f"  ! Customer {customer['phone']}: {exc}")
    return sessions


def ensure_customer_orders(
    customers: list[dict],
    kitchen_id: str,
    dish_ids: dict[str, str],
    owner_token: str,
    *,
    per_customer: int = 2,
) -> int:
    if not dish_ids:
        return 0
    names = list(dish_ids.keys())[:6]
    created = 0
    for cust in customers:
        token = cust["token"]
        for _ in range(per_customer):
            dish_name = names[created % len(names)]
            payload = {
                "items": [{"dish_id": dish_ids[dish_name], "quantity": 1}],
                "delivery_type": "pickup",
                "payment_method": "cod",
            }
            try:
                order = request(
                    "POST",
                    f"/api/v1/kitchens/{kitchen_id}/orders/customer",
                    payload,
                    token=token,
                )
                for status in ("accepted", "preparing", "ready", "delivered"):
                    request(
                        "PATCH",
                        f"/api/v1/orders/{order['id']}/status",
                        {"status": status},
                        token=owner_token,
                    )
                created += 1
            except ApiError as exc:
                log(f"  ! customer order: {exc}")
    log(f"  Customer PWA orders created: {created}")
    return created


def ensure_ratings(customers: list[dict], kitchen_id: str) -> int:
    count = 0
    for cust in customers:
        try:
            orders = request("GET", "/api/v1/customers/me/orders", token=cust["token"])
            for order in orders.get("orders", [])[:2]:
                if order.get("status") != "delivered":
                    continue
                items = order.get("items") or []
                if not items:
                    continue
                dish_id = items[0].get("dish_id")
                if not dish_id:
                    continue
                request(
                    "POST",
                    f"/api/v1/customers/me/orders/{order['id']}/ratings",
                    {
                        "ratings": [
                            {
                                "dish_id": dish_id,
                                "home_taste_score": 5,
                                "quality_score": 4,
                            }
                        ]
                    },
                    token=cust["token"],
                )
                count += 1
        except ApiError as exc:
            log(f"  ! rating for {cust['name']}: {exc}")
    log(f"  Ratings submitted: {count}")
    return count


def ensure_marketing(owner_token: str, kitchen_id: str, dish_id: str) -> None:
    now = datetime.now(UTC)
    try:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/coupons",
            {
                "code": "WELCOME10",
                "discount_type": "percent",
                "discount_value": 10,
                "min_order_amount": 199,
                "max_uses": 500,
            },
            token=owner_token,
        )
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/promotions",
            {
                "name": "Weekend special",
                "dish_id": dish_id,
                "special_price": 129,
                "segment": "all",
                "starts_at": (now - timedelta(days=1)).isoformat(),
                "ends_at": (now + timedelta(days=14)).isoformat(),
            },
            token=owner_token,
        )
        request(
            "GET",
            f"/api/v1/kitchens/{kitchen_id}/crm/customers?refresh=true",
            token=owner_token,
        )
        log("  Marketing: coupon + promotion + CRM sync")
    except ApiError as exc:
        if "409" in str(exc) or "already" in str(exc).lower():
            log("  Marketing assets already exist — skipped")
        else:
            log(f"  ! marketing: {exc}")


def ensure_enterprise_subscription(owner_token: str) -> None:
    try:
        create = request(
            "POST",
            "/api/v1/billing/subscriptions",
            {"plan_tier": "enterprise", "billing_cycle": "monthly"},
            token=owner_token,
        )
        request(
            "POST",
            f"/api/v1/billing/subscriptions/{create['id']}/activate",
            token=owner_token,
        )
        log("  Enterprise subscription activated (Rs 1799 bifurcation)")
    except ApiError as exc:
        if "already" in str(exc).lower() or "409" in str(exc):
            log("  Enterprise subscription already active — skipped")
        else:
            log(f"  ! subscription: {exc}")


def ensure_community_recipe(owner_token: str, kitchen_id: str, dish_id: str) -> None:
    try:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/community/recipes",
            {
                "title": "Grandma's Dal Tadka",
                "summary": "Home-style tempering technique",
                "recipe_html": "<p>Soak dal, pressure cook, temper with ghee and spices.</p>",
                "dish_id": dish_id,
            },
            token=owner_token,
        )
        log("  Community recipe published")
    except ApiError as exc:
        log(f"  ! community recipe: {exc}")


def ensure_growth_blast(owner_token: str, kitchen_id: str, dish_ids: list[str]) -> None:
    if not dish_ids:
        return
    try:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/growth/daily-menu/push",
            {"dish_ids": dish_ids[:3]},
            token=owner_token,
        )
        log("  Growth daily-menu blast queued (wallet deduct if enabled)")
    except ApiError as exc:
        log(f"  ! growth blast: {exc}")


def seed_platform_extras(
    *,
    owner_token: str,
    kitchen_id: str,
    dish_ids: dict[str, str],
    owner_phone_e164: str = "+919876543210",
) -> None:
    """Seed admin, customers, ratings, marketing, subscription, community, growth."""
    if os.environ.get("CKAC_SEED_EXTRAS", "1").strip().lower() in ("0", "false", "no"):
        log("Platform extras disabled (CKAC_SEED_EXTRAS=0)")
        return

    log("")
    log("Platform extras (all user types)")
    log("-" * 50)
    ensure_admin_session()
    customers = ensure_customer_sessions()
    if dish_ids:
        ensure_customer_orders(customers, kitchen_id, dish_ids, owner_token)
        ensure_ratings(customers, kitchen_id)
        first_dish = next(iter(dish_ids.values()))
        ensure_marketing(owner_token, kitchen_id, first_dish)
        ensure_enterprise_subscription(owner_token)
        ensure_community_recipe(owner_token, kitchen_id, first_dish)
        ensure_growth_blast(owner_token, kitchen_id, list(dish_ids.values())[:5])
    log("Platform extras complete.")
