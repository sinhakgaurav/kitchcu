#!/usr/bin/env python3
"""End-to-end smoke test against the live CKAC gateway + frontends.

Verifies: portals serve HTML, gateway health, owner auth, cuisine-grouped menu,
nearby kitchens, and admin panel APIs. Exit non-zero on any failure.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

GATEWAY = os.environ.get("CKAC_GATEWAY_URL", "http://localhost:18000").rstrip("/")
FRONTENDS = {
    "portal": "http://localhost:13000/",
    "customer": "http://localhost:13001/",
    "kitchen": "http://localhost:13002/",
    "admin": "http://localhost:13003/",
}
DEMO_PHONE = "+919876543210"
DEMO_OTP = "123456"
ADMIN_EMAIL = "admin@kitchcu.dev"
ADMIN_PASSWORD = "admin123456"

passed = 0
failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} {detail}")


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | list]:
    url = f"{GATEWAY}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:
            return exc.code, {}


def get_html(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            resp.read()
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError:
        return 0


def main() -> None:
    print("kitchCU smoke test")
    print("=" * 50)

    print("\nFrontends")
    for name, url in FRONTENDS.items():
        check(f"{name} serves HTML", get_html(url) == 200)

    print("\nSupport AI chat")
    status, chat = api("POST", "/api/v1/support/chat", {"audience": "owner", "message": "pricing plans"})
    check("owner support chat", status == 200 and "499" in chat.get("reply", ""))
    status, chat = api("POST", "/api/v1/support/chat", {"audience": "customer", "message": "find kitchen"})
    check("customer support chat", status == 200 and len(chat.get("reply", "")) > 20)

    print("\nGateway")
    status, _ = api("GET", "/health/ready")
    check("gateway health ready", status == 200)

    print("\nOwner auth + cuisine menu")
    api("POST", "/api/v1/auth/otp/request", {"phone": DEMO_PHONE})
    status, tok = api("POST", "/api/v1/auth/otp/verify", {"phone": DEMO_PHONE, "otp": DEMO_OTP})
    token = tok.get("access_token") if isinstance(tok, dict) else None
    check("owner OTP login", status == 200 and bool(token))

    kitchens = []
    if token:
        status, kitchens = api("GET", "/api/v1/kitchens/me", token=token)
        check("list owner kitchens", status == 200 and len(kitchens) >= 1)

    if kitchens:
        kid = kitchens[0]["id"]
        status, cuisines = api("GET", f"/api/v1/kitchens/{kid}/cuisines")
        check("kitchen cuisines list", status == 200 and len(cuisines) >= 1)

        status, menu = api("GET", f"/api/v1/kitchens/{kid}/menu")
        grouped = menu.get("grouped", []) if isinstance(menu, dict) else []
        check("menu has cuisine groups", status == 200 and len(grouped) >= 1)

        has_diet = any(
            g.get("diets") and any(d.get("diet", {}).get("slug") in ("veg", "non_veg") for d in g["diets"])
            for g in grouped
        )
        check("menu groups by veg/non-veg diet", has_diet)

    if kitchens and token:
        kid = kitchens[0]["id"]
        print("\nOwner growth analytics")

        status, unauth = api("GET", f"/api/v1/kitchens/{kid}/analytics/summary")
        check("analytics requires auth", status == 401)

        status, summary = api("GET", f"/api/v1/kitchens/{kid}/analytics/summary?days=30", token=token)
        ok = status == 200 and summary.get("total_orders", 0) >= 1 and summary.get("gross_revenue", 0) > 0
        check("analytics revenue summary", ok, str(summary) if not ok else "")

        status, ts = api(
            "GET", f"/api/v1/kitchens/{kid}/analytics/revenue-timeseries?days=30", token=token
        )
        check("analytics revenue timeseries", status == 200 and len(ts.get("points", [])) == 30)

        status, dishes = api(
            "GET", f"/api/v1/kitchens/{kid}/analytics/top-dishes?days=30&limit=5", token=token
        )
        check("analytics top dishes", status == 200 and len(dishes.get("dishes", [])) >= 1)

        status, peak = api(
            "GET", f"/api/v1/kitchens/{kid}/analytics/peak-hours?days=30", token=token
        )
        check("analytics peak hours (24 buckets)", status == 200 and len(peak.get("hours", [])) == 24)

        status, cust = api(
            "GET", f"/api/v1/kitchens/{kid}/analytics/customers?days=90&limit=5", token=token
        )
        check("analytics customer segments", status == 200 and "top_customers" in cust)

    if token:
        print("\nBilling (Sprint 6)")
        status, plans = api("GET", "/api/v1/billing/subscriptions/plans")
        check("billing subscription plans", status == 200 and len(plans.get("plans", [])) >= 3)

        status, unauth_sub = api("GET", "/api/v1/billing/subscriptions/me")
        check("billing subscription me requires auth", status == 401)

        status, sub = api(
            "POST",
            "/api/v1/billing/subscriptions",
            {"plan_tier": "starter", "billing_cycle": "monthly"},
            token=token,
        )
        sub_id = sub.get("id") if isinstance(sub, dict) else None
        check("billing create subscription", status == 201 and bool(sub_id))

        if sub_id:
            status, activated = api(
                "POST",
                f"/api/v1/billing/subscriptions/{sub_id}/activate",
                token=token,
            )
            check(
                "billing activate subscription",
                status == 200 and activated.get("status") == "active",
            )

        if kitchens:
            kid = kitchens[0]["id"]
            status, orders = api("GET", f"/api/v1/kitchens/{kid}/orders", token=token)
            upi_order = next(
                (
                    o
                    for o in (orders if isinstance(orders, list) else orders.get("orders", []))
                    if o.get("payment_method") == "upi"
                    and o.get("status") not in ("delivered", "cancelled")
                ),
                None,
            )
            if upi_order:
                status, intent = api(
                    "POST",
                    "/api/v1/billing/payments/upi-intent",
                    {"order_id": upi_order["id"]},
                    token=token,
                )
                check(
                    "billing UPI intent",
                    status == 201 and intent.get("upi_uri", "").startswith("upi://"),
                )
                pay_id = intent.get("payment_id")
                if pay_id:
                    status, captured = api(
                        "POST",
                        f"/api/v1/billing/payments/{pay_id}/capture",
                        token=token,
                    )
                    check(
                        "billing capture UPI payment",
                        status == 200 and captured.get("status") == "captured",
                    )
            else:
                check("billing UPI intent (no open upi order)", True, "skipped")

    print("\nCustomer checkout (Sprint 5)")
    status, cust_providers = api("GET", "/api/v1/auth/customer/oauth/providers")
    check("customer oauth providers", status == 200 and len(cust_providers.get("providers", [])) >= 1)

    api("POST", "/api/v1/auth/customer/whatsapp/request", {"phone": "+919876543299"})
    status, cust_tok = api(
        "POST",
        "/api/v1/auth/customer/whatsapp/verify",
        {"phone": "+919876543299", "otp": DEMO_OTP},
    )
    cust_token = cust_tok.get("access_token") if isinstance(cust_tok, dict) else None
    check("customer WhatsApp OTP login", status == 200 and bool(cust_token))

    if cust_token and kitchens:
        kid = kitchens[0]["id"]
        status, menu = api("GET", f"/api/v1/kitchens/{kid}/menu")
        dish_id = None
        if isinstance(menu, dict) and menu.get("dishes"):
            dish_id = menu["dishes"][0]["id"]
        if dish_id:
            status, order = api(
                "POST",
                f"/api/v1/kitchens/{kid}/orders/customer",
                {
                    "items": [{"dish_id": dish_id, "quantity": 1}],
                    "delivery_type": "pickup",
                    "payment_method": "cod",
                },
                token=cust_token,
            )
            check(
                "customer checkout place order",
                status == 201 and order.get("source") == "customer_pwa",
            )
            status, my_orders = api("GET", "/api/v1/customers/me/orders", token=cust_token)
            check("customer order history", status == 200 and my_orders.get("total", 0) >= 1)
        else:
            check("customer checkout (no dishes)", True, "skipped")

    print("\nNearby kitchens (distance sort)")
    status, nearby = api(
        "GET",
        "/api/v1/kitchens/public/nearby?latitude=18.5362&longitude=73.8958&limit=20&max_km=50",
    )
    kitchens_n = nearby.get("kitchens", []) if isinstance(nearby, dict) else []
    check("nearby returns kitchens", status == 200 and len(kitchens_n) >= 1)
    distances = [k.get("distance_km", 0) for k in kitchens_n]
    check("nearby sorted ascending by distance", distances == sorted(distances))

    print("\nAdmin panel")
    status, atok = api("POST", "/api/v1/admin/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    admin_token = atok.get("access_token") if isinstance(atok, dict) else None
    check("admin login", status == 200 and bool(admin_token))

    if admin_token:
        status, stats = api("GET", "/api/v1/admin/stats", token=admin_token)
        ok = status == 200 and stats.get("kitchens", 0) >= 1 and stats.get("orders", 0) >= 1
        check("admin platform stats", ok, str(stats) if not ok else "")

        status, a_kitchens = api("GET", "/api/v1/admin/kitchens", token=admin_token)
        check("admin lists kitchens", status == 200 and len(a_kitchens) >= 1)

        status, a_owners = api("GET", "/api/v1/admin/owners", token=admin_token)
        check("admin lists owners", status == 200 and len(a_owners) >= 1)

        status, a_orders = api("GET", "/api/v1/admin/orders", token=admin_token)
        check("admin lists orders", status == 200 and len(a_orders) >= 1)

    print("\n" + "=" * 50)
    print(f"Result: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
