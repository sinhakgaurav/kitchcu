#!/usr/bin/env python3
"""Validation & negative-path probe against live gateway.

Checks auth gates, Pydantic validation (422), bad OTP, bad kitchen codes,
tenant-ish protection, and OpenAPI availability. Exit non-zero on failures.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# Windows consoles (cp1252) choke on arrows/dashes in probe names.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GATEWAY = os.environ.get("CKAC_GATEWAY_URL", "http://localhost:18000").rstrip("/")
DEMO_PHONE = "+919876543210"
DEMO_OTP = "123456"

passed = 0
failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    name = name.replace("\u2192", "->").replace("\u2014", "-").replace("\u2013", "-")
    detail = detail.replace("\u2192", "->").replace("\u2014", "-").replace("\u2013", "-")
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} {detail}")


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | list | str]:
    url = f"{GATEWAY}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, (json.loads(raw) if raw else {})
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return exc.code, raw
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(exc)


def main() -> None:
    print("kitchCU validation / negative-path probe")
    print("=" * 50)

    print("\nOpenAPI / docs")
    status, doc = api("GET", "/openapi.json")
    check("openapi.json available", status == 200 and isinstance(doc, dict) and "paths" in doc)
    if isinstance(doc, dict):
        check("openapi has paths", len(doc.get("paths", {})) >= 20, f"paths={len(doc.get('paths', {}))}")
    status, _ = api("GET", "/docs")
    check("swagger /docs serves", status == 200)

    print("\nAuth validation")
    status, body = api("POST", "/api/v1/auth/otp/request", {})
    check("OTP request missing phone -> 422", status == 422)

    status, body = api("POST", "/api/v1/auth/otp/request", {"phone": "not-a-phone"})
    # Known gap if this passes: phone schema accepts non-E.164 strings
    check("OTP request invalid phone -> 422", status == 422, f"got {status}")

    status, body = api("POST", "/api/v1/auth/otp/verify", {"phone": DEMO_PHONE, "otp": "000000"})
    check("OTP verify wrong code rejected", status in (400, 401, 403))

    status, body = api(
        "POST",
        "/api/v1/admin/auth/login",
        {"email": "admin@kitchcu.dev", "password": "wrongpassword"},
    )
    check("admin bad password rejected", status in (400, 401, 403), f"got {status}")

    status, body = api("POST", "/api/v1/admin/auth/login", {"email": "not-an-email", "password": "x"})
    check("admin invalid email -> 422", status == 422)

    print("\nAuthz gates")
    status, _ = api("GET", "/api/v1/kitchens/me")
    check("owner kitchens require JWT", status == 401)

    status, _ = api("GET", "/api/v1/admin/stats")
    check("admin stats require JWT", status == 401)

    status, _ = api("GET", "/api/v1/customers/me/orders")
    check("customer orders require JWT", status == 401)

    status, _ = api("GET", "/api/v1/billing/subscriptions/me")
    check("billing me requires JWT", status == 401)

    # Owner token for positive + more negatives
    api("POST", "/api/v1/auth/otp/request", {"phone": DEMO_PHONE})
    status, tok = api("POST", "/api/v1/auth/otp/verify", {"phone": DEMO_PHONE, "otp": DEMO_OTP})
    token = tok.get("access_token") if isinstance(tok, dict) else None
    check("demo owner login for probes", bool(token))

    kitchens = []
    if token:
        status, kitchens = api("GET", "/api/v1/kitchens/me", token=token)
        check("owner kitchens list", status == 200 and isinstance(kitchens, list) and len(kitchens) >= 1)

    print("\nOrder / menu validation")
    if token and kitchens:
        kid = kitchens[0]["id"]
        status, body = api(
            "POST",
            f"/api/v1/kitchens/{kid}/orders/manual",
            {"items": [], "delivery_type": "pickup", "payment_method": "cod"},
            token=token,
        )
        check("manual order empty items rejected", status in (400, 422), f"got {status}")

        status, body = api(
            "POST",
            f"/api/v1/kitchens/{kid}/orders/manual",
            {
                "items": [{"dish_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}],
                "delivery_type": "pickup",
                "payment_method": "cod",
            },
            token=token,
        )
        check("manual order unknown dish rejected", status in (400, 404, 422), f"got {status}")

        status, body = api(
            "POST",
            f"/api/v1/kitchens/{kid}/orders/customer",
            {
                "items": [{"dish_id": "not-a-uuid", "quantity": 0}],
                "delivery_type": "pickup",
                "payment_method": "cod",
            },
            token=token,
        )
        # Owner JWT on customer checkout must be rejected
        check("customer checkout rejects owner JWT", status in (401, 403), f"got {status}")

        api("POST", "/api/v1/auth/customer/whatsapp/request", {"phone": "+919123456789"})
        status, cust = api(
            "POST",
            "/api/v1/auth/customer/whatsapp/verify",
            {"phone": "+919123456789", "otp": DEMO_OTP},
        )
        cust_token = cust.get("access_token") if isinstance(cust, dict) else None
        if cust_token:
            status, body = api(
                "POST",
                f"/api/v1/kitchens/{kid}/orders/customer",
                {
                    "items": [{"dish_id": "not-a-uuid", "quantity": 0}],
                    "delivery_type": "pickup",
                    "payment_method": "cod",
                },
                token=cust_token,
            )
            check("customer order invalid payload -> 422", status == 422, f"got {status}")

    print("\nPublic lookup validation")
    status, body = api("GET", "/api/v1/kitchens/public/nearby?latitude=999&longitude=73.85")
    check("nearby invalid latitude rejected", status in (400, 422), f"got {status}")

    status, body = api("GET", "/api/v1/kitchens/public/by-code/DOESNOTEXIST")
    check("unknown kitchen code -> 404", status == 404)

    status, body = api("GET", "/api/v1/kitchens/00000000-0000-0000-0000-000000000099/menu")
    check("unknown kitchen menu -> 404", status == 404, f"got {status}")

    print("\nCoupon / GST style validation (if reachable)")
    if token and kitchens:
        kid = kitchens[0]["id"]
        status, body = api(
            "POST",
            f"/api/v1/kitchens/{kid}/coupons",
            {"code": "", "discount_type": "percent", "discount_value": -5},
            token=token,
        )
        check("coupon invalid payload rejected", status in (400, 404, 422))

        status, body = api(
            "PUT",
            f"/api/v1/kitchens/{kid}/gst/profile",
            {"gstin": "BAD", "legal_name": "X"},
            token=token,
        )
        check("GST bad GSTIN rejected or not found", status in (400, 404, 422))

    print("\n" + "=" * 50)
    print(f"Result: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
