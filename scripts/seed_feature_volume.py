"""Fill every kitchen and every diner across every module.

Called from ``seed-bulk-data.py`` after kitchens, menus and the 6-month order
history exist. Idempotent: codes, ticket subjects and address labels are stable,
so a re-run tops up instead of duplicating.

Host Python on the GCP VM is 3.10 — do not import ``datetime.UTC``.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from feature_volume import (
    DEFAULT_PLAN,
    FeatureVolumePlan,
    diner_referral_phone,
    diner_ticket_subjects,
    extra_address_specs,
    kitchen_coupon_specs,
    kitchen_template_specs,
    kitchens_for_diner,
)
from seed_common import ApiError, ensure_customer_addresses, log, request
from seed_platform_extras import (
    ensure_community_extras,
    ensure_community_recipe,
    ensure_enterprise_subscription,
    ensure_growth_blast,
    ensure_growth_suggestions,
    ensure_learning_trial,
    ensure_ratings,
    ensure_tiffin_plans,
)

UTC = timezone.utc


def _enabled() -> bool:
    return os.environ.get("CKAC_FEATURE_VOLUME", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _skippable(exc: ApiError) -> bool:
    text = str(exc)
    return any(code in text for code in (" 402", " 403", "409", "already", "Already"))


def _list(payload: object, key: str) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        rows = payload.get(key)
        if isinstance(rows, list):
            return rows
    return []


def _fill_coupons(kitchen: dict, plan: FeatureVolumePlan) -> int:
    token, kid, code = kitchen["token"], kitchen["id"], kitchen.get("code") or "CKXXX"
    try:
        listed = request("GET", f"/api/v1/kitchens/{kid}/coupons", token=token)
    except ApiError as exc:
        log(f"    ! coupons list {code}: {exc}")
        return 0
    have = {str(row.get("code") or "").upper() for row in _list(listed, "coupons")}
    created = 0
    for spec in kitchen_coupon_specs(str(code), plan.coupons_per_kitchen):
        if spec["code"].upper() in have:
            continue
        try:
            request("POST", f"/api/v1/kitchens/{kid}/coupons", spec, token=token)
            created += 1
        except ApiError as exc:
            if not _skippable(exc):
                log(f"    ! coupon {spec['code']}: {exc}")
    return created


def _fill_promotions(kitchen: dict, plan: FeatureVolumePlan) -> int:
    token, kid = kitchen["token"], kitchen["id"]
    dish_ids = list((kitchen.get("dish_ids") or {}).values())
    if not dish_ids:
        return 0
    now = datetime.now(UTC)
    names = ("Lunch special", "Dinner spotlight")[: plan.promotions_per_kitchen]
    created = 0
    try:
        listed = request("GET", f"/api/v1/kitchens/{kid}/promotions", token=token)
        have = {str(row.get("name") or "") for row in _list(listed, "promotions")}
    except ApiError:
        have = set()
    for idx, name in enumerate(names):
        if name in have:
            continue
        try:
            request(
                "POST",
                f"/api/v1/kitchens/{kid}/promotions",
                {
                    "name": name,
                    "dish_id": dish_ids[idx % len(dish_ids)],
                    "special_price": 129 + idx * 20,
                    "segment": "all",
                    "starts_at": (now - timedelta(days=1)).isoformat(),
                    "ends_at": (now + timedelta(days=21)).isoformat(),
                },
                token=token,
            )
            created += 1
        except ApiError as exc:
            if not _skippable(exc):
                log(f"    ! promotion {name}: {exc}")
    return created


def _fill_templates(kitchen: dict, plan: FeatureVolumePlan) -> int:
    token, kid = kitchen["token"], kitchen["id"]
    try:
        listed = request("GET", f"/api/v1/kitchens/{kid}/templates", token=token)
        have = {str(row.get("name") or "") for row in _list(listed, "templates")}
    except ApiError:
        have = set()
    created = 0
    for spec in kitchen_template_specs(str(kitchen.get("name") or "Kitchen"), plan.templates_per_kitchen):
        if spec["name"] in have:
            continue
        try:
            request("POST", f"/api/v1/kitchens/{kid}/templates", spec, token=token)
            created += 1
        except ApiError as exc:
            if not _skippable(exc):
                log(f"    ! template {spec['name']}: {exc}")
    return created


def _fill_gst_months(kitchen: dict, plan: FeatureVolumePlan) -> int:
    token, kid = kitchen["token"], kitchen["id"]
    now = datetime.now(UTC)
    synced = 0
    for months_ago in range(plan.gst_sync_months):
        period = now - timedelta(days=30 * months_ago)
        try:
            request(
                "POST",
                f"/api/v1/kitchens/{kid}/gst/sync?year={period.year}&month={period.month}",
                token=token,
            )
            synced += 1
        except ApiError as exc:
            if not _skippable(exc):
                log(f"    ! gst sync {kitchen.get('code')}: {exc}")
    return synced


def _fill_refund(kitchen: dict) -> int:
    token, kid = kitchen["token"], kitchen["id"]
    try:
        existing = request("GET", "/api/v1/billing/refunds", token=token)
        refunded = {str(row.get("order_id") or "") for row in _list(existing, "refunds") or (existing if isinstance(existing, list) else [])}
    except ApiError:
        refunded = set()
    try:
        orders = request(
            "GET",
            f"/api/v1/kitchens/{kid}/orders?status=delivered&limit=50",
            token=token,
        )
    except ApiError as exc:
        log(f"    ! refund orders {kitchen.get('code')}: {exc}")
        return 0
    candidates = [
        o
        for o in _list(orders, "orders")
        if o.get("id") and str(o["id"]) not in refunded
    ]
    preferred = [o for o in candidates if (o.get("payment_method") or "").lower() not in ("", "cod")]
    if not preferred:
        return 0
    order = preferred[0]
    try:
        payment = request(
            "POST",
            "/api/v1/billing/payments",
            {"order_id": order["id"], "method": "upi"},
            token=token,
        )
        request("POST", f"/api/v1/billing/payments/{payment['id']}/capture", token=token)
        amount = round(max(20.0, float(order.get("total") or 100) * 0.25), 2)
        request(
            "POST",
            "/api/v1/billing/refunds",
            {
                "order_id": order["id"],
                "kind": "partial",
                "amount": amount,
                "destination_type": "upi",
                "destination_upi": "volume.diner@upi",
                "reason": f"Volume seed refund — {kitchen.get('code')}",
            },
            token=token,
        )
        return 1
    except ApiError as exc:
        if not _skippable(exc):
            log(f"    ! refund {kitchen.get('code')}: {exc}")
        return 0


def _fill_prep_batch(kitchen: dict) -> int:
    token, kid = kitchen["token"], kitchen["id"]
    dish_ids = list((kitchen.get("dish_ids") or {}).values())[:2]
    if len(dish_ids) < 1:
        return 0
    name = f"Volume morning batch · {kitchen.get('code')}"
    try:
        listed = request("GET", f"/api/v1/kitchens/{kid}/prep-batches", token=token)
        if any(str(row.get("name") or "") == name for row in _list(listed, "batches") or _list(listed, "prep_batches")):
            return 0
        dishes = [{"dish_id": did, "quantity_per_portion": 1} for did in dish_ids]
        batch = request(
            "POST",
            f"/api/v1/kitchens/{kid}/prep-batches",
            {"name": name, "batch_type": "combo" if len(dishes) > 1 else "single_dish", "portions": 12, "dishes": dishes},
            token=token,
        )
        if batch.get("id"):
            try:
                request(
                    "POST",
                    f"/api/v1/kitchens/{kid}/prep-batches/{batch['id']}/mark-prepared",
                    token=token,
                )
            except ApiError:
                pass
        return 1
    except ApiError as exc:
        if not _skippable(exc):
            log(f"    ! prep batch {kitchen.get('code')}: {exc}")
        return 0


def _fill_tiffin_subscribers(kitchen: dict, diners: list[dict], plan: FeatureVolumePlan) -> int:
    token, kid = kitchen["token"], kitchen["id"]
    try:
        listed = request("GET", f"/api/v1/kitchens/{kid}/subscription-plans", token=token)
    except ApiError as exc:
        log(f"    ! tiffin list {kitchen.get('code')}: {exc}")
        return 0
    plans = [p for p in _list(listed, "plans") if p.get("id")]
    if not plans or not diners:
        return 0
    subscribed = 0
    for diner in diners[: plan.tiffin_subscribers_per_kitchen]:
        diner_token = diner.get("token")
        if not diner_token:
            continue
        try:
            request(
                "POST",
                f"/api/v1/kitchens/{kid}/subscription-plans/{plans[0]['id']}/subscribe",
                {"customer_name": diner.get("name"), "note": "Volume seed subscriber"},
                token=diner_token,
            )
            subscribed += 1
        except ApiError as exc:
            if "open subscription" in str(exc).lower() or _skippable(exc):
                subscribed += 1
            else:
                log(f"    ! subscribe {diner.get('phone')}: {exc}")
    return subscribed


def _fill_customer_addresses(diner: dict) -> int:
    token = diner.get("token")
    if not token:
        return 0
    return ensure_customer_addresses(token, extra_address_specs(diner))


def _fill_customer_orders(
    diner: dict,
    kitchens: list[dict],
    plan: FeatureVolumePlan,
) -> int:
    token = diner.get("token")
    if not token:
        return 0
    targets = kitchens_for_diner(diner, kitchens)
    if not targets:
        return 0
    try:
        existing = request("GET", "/api/v1/customers/me/orders?limit=50", token=token)
        have = len(_list(existing, "orders"))
    except ApiError:
        have = 0
    need = max(0, plan.pwa_orders_per_customer - have)
    created = 0
    for i in range(need):
        kitchen = targets[i % len(targets)]
        dish_ids = list((kitchen.get("dish_ids") or {}).values())
        owner_token = kitchen.get("token")
        if not dish_ids or not owner_token:
            continue
        try:
            order = request(
                "POST",
                f"/api/v1/kitchens/{kitchen['id']}/orders/customer",
                {
                    "items": [{"dish_id": dish_ids[i % len(dish_ids)], "quantity": 1}],
                    "delivery_type": "delivery" if i % 2 == 0 else "pickup",
                    "payment_method": "cod" if i % 3 else "upi",
                },
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
            if not _skippable(exc):
                log(f"    ! pwa order {diner.get('phone')} @ {kitchen.get('code')}: {exc}")
    return created


def _fill_customer_tickets(diner: dict, kitchen: dict | None, plan: FeatureVolumePlan) -> int:
    token = diner.get("token")
    if not token:
        return 0
    code = str((kitchen or {}).get("code") or "CK")
    try:
        listed = request("GET", "/api/v1/customers/me/tickets", token=token)
        have = {str(row.get("subject") or "") for row in _list(listed, "tickets")}
    except ApiError:
        have = set()
    created = 0
    for subject in diner_ticket_subjects(diner, code)[: plan.tickets_per_customer]:
        if subject in have:
            continue
        try:
            request(
                "POST",
                "/api/v1/customers/me/tickets",
                {
                    "audience": "customer",
                    "category": "quality" if created else "delivery",
                    "subject": subject,
                    "description": (
                        f"Volume-seed ticket so {diner.get('name')} has an open conversation "
                        f"against {code}."
                    ),
                    "source": "web_form",
                },
                token=token,
            )
            created += 1
        except ApiError as exc:
            if not _skippable(exc):
                log(f"    ! ticket {diner.get('phone')}: {exc}")
    return created


def _fill_customer_prefs(diner: dict) -> int:
    token = diner.get("token")
    if not token:
        return 0
    try:
        request(
            "PATCH",
            "/api/v1/customers/me/notifications",
            {
                "notify_order_updates": True,
                "notify_offers": True,
                "notify_channel": "whatsapp",
            },
            token=token,
        )
        return 1
    except ApiError as exc:
        if not _skippable(exc):
            log(f"    ! prefs {diner.get('phone')}: {exc}")
        return 0


def _fill_customer_referral(diner: dict, kitchen: dict | None) -> int:
    token = diner.get("token")
    if not token:
        return 0
    phone = diner_referral_phone(diner, 0)
    city = str(diner.get("city") or (kitchen or {}).get("city") or "Pune")
    try:
        request(
            "POST",
            "/api/v1/customers/me/referrals/kitchens",
            {
                "kitchen_name": f"{city} Home Kitchen Lead",
                "contact_name": diner.get("name"),
                "contact_phone": f"+91{phone}",
                "city": city,
                "notes": "Volume seed — customer referring a neighbourhood kitchen",
            },
            token=token,
        )
        return 1
    except ApiError as exc:
        if not _skippable(exc):
            log(f"    ! referral {diner.get('phone')}: {exc}")
        return 0


def _fill_owner_customer_lead(kitchen: dict, diner: dict, slot: int) -> int:
    token = kitchen.get("token")
    if not token:
        return 0
    phone = diner_referral_phone(diner, slot + 3)
    try:
        request(
            "POST",
            "/api/v1/owners/me/referrals/customers",
            {
                "kitchen_id": kitchen["id"],
                "contact_name": diner.get("name"),
                "contact_phone": f"+91{phone}",
                "city": diner.get("city") or kitchen.get("city"),
                "notes": "Volume seed — kitchen referring a diner",
            },
            token=token,
        )
        return 1
    except ApiError as exc:
        if not _skippable(exc):
            log(f"    ! owner referral {kitchen.get('code')}: {exc}")
        return 0


def seed_feature_volume(
    *,
    kitchens: list[dict],
    customers: list[dict],
    customers_by_city: dict[str, list[dict]] | None = None,
    plan: FeatureVolumePlan | None = None,
) -> dict[str, int]:
    """Decorate every kitchen and every diner. Returns per-surface counts."""
    plan = plan or DEFAULT_PLAN
    if not _enabled():
        log("Feature volume disabled (CKAC_FEATURE_VOLUME=0)")
        return {}
    if not kitchens:
        log("  ! feature volume: no kitchens")
        return {}

    log("")
    log("Feature volume — every kitchen + every customer")
    log("-" * 50)

    totals = {
        "kitchens": 0,
        "coupons": 0,
        "promotions": 0,
        "templates": 0,
        "gst_months": 0,
        "refunds": 0,
        "prep_batches": 0,
        "tiffin_subscribers": 0,
        "addresses": 0,
        "pwa_orders": 0,
        "tickets": 0,
        "prefs": 0,
        "referrals": 0,
        "ratings": 0,
    }

    seen_owners: set[str] = set()
    for kitchen in kitchens:
        token = kitchen.get("token")
        if token and token not in seen_owners:
            ensure_enterprise_subscription(token)
            seen_owners.add(token)

        kid = kitchen["id"]
        dish_ids = kitchen.get("dish_ids") or {}
        city = str(kitchen.get("city") or "")
        city_diners = list((customers_by_city or {}).get(city) or [])
        if not city_diners:
            city_diners = [c for c in customers if c.get("token")]

        log(f"  [{kitchen.get('code')}] {kitchen.get('name')} ({city})")
        if dish_ids:
            ensure_tiffin_plans(token, kid, dish_ids)
            first = next(iter(dish_ids.values()))
            recipe = ensure_community_recipe(token, kid, first)
            ensure_community_extras(city_diners[:3], token, kid, recipe)
            ensure_growth_blast(token, kid, list(dish_ids.values())[:5])
            ensure_growth_suggestions(token, kid)
            ensure_learning_trial(token, kid)

        totals["coupons"] += _fill_coupons(kitchen, plan)
        totals["promotions"] += _fill_promotions(kitchen, plan)
        totals["templates"] += _fill_templates(kitchen, plan)
        totals["gst_months"] += _fill_gst_months(kitchen, plan)
        totals["refunds"] += _fill_refund(kitchen)
        totals["prep_batches"] += _fill_prep_batch(kitchen)
        totals["tiffin_subscribers"] += _fill_tiffin_subscribers(kitchen, city_diners, plan)
        if city_diners:
            totals["referrals"] += _fill_owner_customer_lead(kitchen, city_diners[0], totals["kitchens"])
        totals["kitchens"] += 1

    for diner in customers:
        if not diner.get("token"):
            continue
        home = kitchens_for_diner(diner, kitchens)
        totals["addresses"] += _fill_customer_addresses(diner)
        totals["pwa_orders"] += _fill_customer_orders(diner, kitchens, plan)
        totals["tickets"] += _fill_customer_tickets(diner, home[0] if home else None, plan)
        totals["prefs"] += _fill_customer_prefs(diner)
        totals["referrals"] += _fill_customer_referral(diner, home[0] if home else None)

    try:
        totals["ratings"] = ensure_ratings(customers, kitchens[0]["id"])
    except Exception as exc:  # noqa: BLE001 — volume must not abort the bulk run
        log(f"  ! volume ratings: {exc}")

    log(
        f"  Volume: {totals['kitchens']} kitchens · {totals['coupons']} coupons · "
        f"{totals['templates']} templates · {totals['pwa_orders']} diner orders · "
        f"{totals['addresses']} extra addresses · {totals['tickets']} tickets · "
        f"{totals['tiffin_subscribers']} tiffin subscribers · {totals['ratings']} ratings"
    )
    return totals
