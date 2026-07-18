"""Extended platform seed — every persona, CRM, ratings, recipes, subscriptions,
WhatsApp/payments/GST/refunds, delivery, support, growth, community, streaming, learning."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone

from demo_data import DEMO_ADMIN, DEMO_CUSTOMERS, DEMO_OTP
from seed_common import (
    ApiError,
    login_admin,
    login_customer,
    login_owner,
    log,
    request,
    resolve_postgres_container,
)

MIN_TRIAL_INVITES = 5

# Mirrors the CURATED_SEED fixture in services/learning/alembic/versions/001_initial_learning.py.
# Re-inserted here only as a safety net when the (reference-data) table has been emptied by a
# test run's TRUNCATE cleanup — the migration itself is the source of truth.
CURATED_RECIPE_FALLBACK_SEED = [
    (
        "paneer-butter-masala",
        "Paneer Butter Masala",
        "north_indian",
        "north_indian",
        "Creamy tomato gravy with soft paneer cubes — a cloud-kitchen staple.",
        ["paneer", "tomato", "butter", "cream", "kasuri methi"],
        ["Blend tomato base", "Simmer with spices", "Add paneer and cream"],
        "https://images.unsplash.com/photo-1631452180519-f014710f6fea?w=800&q=85&auto=format&fit=crop",
        "kitchCU Curated",
    ),
    (
        "masala-dosa",
        "Masala Dosa",
        "south_indian",
        "south_indian",
        "Crisp fermented crepe with spiced potato filling.",
        ["rice batter", "urad dal", "potato", "mustard seeds", "curry leaves"],
        ["Ferment batter overnight", "Spread on hot tawa", "Fill with masala"],
        "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=800&q=85&auto=format&fit=crop",
        "kitchCU Curated",
    ),
]


def ensure_curated_recipes_present() -> bool:
    """Self-heal the learning portal's reference data if it was emptied (e.g. by a test
    suite's TRUNCATE cleanup running against the same dev database). Returns True if at
    least one curated recipe is available afterwards."""
    try:
        existing = request("GET", "/api/v1/learning/recipes")
        recipe_list = existing.get("recipes") if isinstance(existing, dict) else existing
        if recipe_list:
            return True
    except ApiError as exc:
        log(f"  ! curated recipes check: {exc}")
        return False

    log("  Curated recipes table empty — reseeding reference data (F21 fixture)")
    values_sql = ",\n".join(
        "(gen_random_uuid(), %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, true, now())" % (
            _sql_str(slug), _sql_str(title), _sql_str(category), _sql_str(cuisine),
            _sql_str(description), _sql_json(ingredients), _sql_json(prep_steps),
            _sql_str(image_url), _sql_str(source_name),
        )
        for slug, title, category, cuisine, description, ingredients, prep_steps, image_url, source_name
        in CURATED_RECIPE_FALLBACK_SEED
    )
    sql = (
        "INSERT INTO ckac_learning.curated_recipes "
        "(id, slug, title, category, cuisine, description, ingredients, prep_steps, "
        "image_url, source_name, is_active, created_at) VALUES\n"
        f"{values_sql}\nON CONFLICT (slug) DO NOTHING;"
    )
    try:
        proc = subprocess.run(
            [
                "docker",
                "exec",
                resolve_postgres_container(),
                "psql",
                "-U",
                "ckac",
                "-d",
                "ckac",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                sql,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            log(f"  ! curated recipes reseed failed: {proc.stderr.strip() or proc.stdout.strip()}")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        log(f"  ! curated recipes reseed skipped ({exc})")
        return False

    try:
        recheck = request("GET", "/api/v1/learning/recipes")
        recipe_list = recheck.get("recipes") if isinstance(recheck, dict) else recheck
        return bool(recipe_list)
    except ApiError:
        return False


def _sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_json(value: list[str]) -> str:
    import json

    return _sql_str(json.dumps(value))


def ensure_admin_session() -> str:
    """Login with GCP/prod ADMIN_* env when set; fall back to local DEMO_ADMIN."""
    email = os.environ.get("ADMIN_EMAIL", DEMO_ADMIN["email"]).strip() or DEMO_ADMIN["email"]
    password = os.environ.get("ADMIN_PASSWORD", DEMO_ADMIN["password"]).strip() or DEMO_ADMIN["password"]
    token = login_admin(email, password)
    log(f"  Admin login OK ({email})")
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
    for idx, cust in enumerate(customers):
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
                rating: dict = {
                    "dish_id": dish_id,
                    "home_taste_score": 5,
                    "quality_score": 4,
                }
                if idx == 0 and count == 0:
                    # A/V review coverage (F16-F18) — one anonymous video review.
                    rating["media_url"] = "https://cdn.kitchcu.dev/demo/reviews/sample-review.mp4"
                    rating["media_type"] = "video"
                    rating["is_anonymous"] = True
                request(
                    "POST",
                    f"/api/v1/customers/me/orders/{order['id']}/ratings",
                    {"ratings": [rating]},
                    token=cust["token"],
                )
                count += 1
        except ApiError as exc:
            log(f"  ! rating for {cust['name']}: {exc}")
    log(f"  Ratings submitted: {count}")
    return count


def ensure_marketing(owner_token: str, kitchen_id: str, dish_id: str) -> None:
    now = datetime.now(timezone.utc)
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


def ensure_community_recipe(owner_token: str, kitchen_id: str, dish_id: str) -> dict | None:
    try:
        existing = request("GET", f"/api/v1/community/recipes?kitchen_id={kitchen_id}", token=owner_token)
        rows = existing.get("recipes") if isinstance(existing, dict) else existing
        if rows:
            log("  Community recipe already published — reusing")
            return rows[0]
        recipe = request(
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
        return recipe
    except ApiError as exc:
        log(f"  ! community recipe: {exc}")
        return None


def ensure_community_extras(customers: list[dict], owner_token: str, kitchen_id: str, recipe: dict | None) -> None:
    """Customer appreciation (+points) and chef-ranking leaderboard compute (F23-F24)."""
    if recipe and recipe.get("id") and customers:
        try:
            request(
                "POST",
                f"/api/v1/community/recipes/{recipe['id']}/appreciate",
                token=customers[0]["token"],
            )
            log("  Community recipe appreciated by a customer")
        except ApiError as exc:
            if "already appreciated" in str(exc).lower():
                log("  Community recipe already appreciated — skipped")
            else:
                log(f"  ! community appreciate: {exc}")

    try:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/community/rankings/compute?scope=city&region_key=Pune",
            token=owner_token,
        )
        log("  Chef leaderboard recomputed (city: Pune)")
    except ApiError as exc:
        log(f"  ! community rankings compute: {exc}")

    try:
        rewards = request("GET", f"/api/v1/kitchens/{kitchen_id}/community/rewards", token=owner_token)
        balance = rewards.get("points_balance", 0)
        log(f"  Community reward balance: {balance} pts")
        if balance >= 500:
            request(
                "POST",
                f"/api/v1/kitchens/{kitchen_id}/community/rewards/redeem",
                {"redemption_type": "featured_listing"},
                token=owner_token,
            )
            log("  Community reward points redeemed (featured listing)")
    except ApiError as exc:
        log(f"  ! community reward redeem: {exc}")


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


def ensure_growth_suggestions(owner_token: str, kitchen_id: str) -> None:
    """Persist growth suggestions from order-history mining (F11)."""
    try:
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/growth/suggestions/generate",
            token=owner_token,
        )
        log("  Growth suggestions generated (combos/patterns mining)")
    except ApiError as exc:
        log(f"  ! growth suggestions: {exc}")


def ensure_whatsapp_integration(owner_token: str, kitchen_id: str) -> None:
    """Connect a dummy Meta WhatsApp Business phone to the kitchen (owner integrations)."""
    try:
        current = request(
            "GET", f"/api/v1/kitchens/{kitchen_id}/whatsapp-integration", token=owner_token
        )
        if current.get("connected"):
            log("  WhatsApp integration already connected — skipped")
            return
        request(
            "PUT",
            f"/api/v1/kitchens/{kitchen_id}/whatsapp-integration",
            {
                "whatsapp_phone_id": f"demo-wa-{kitchen_id[:8]}",
                "whatsapp_display_phone": "+919876543210",
            },
            token=owner_token,
        )
        log("  WhatsApp Business number connected (demo phone id)")
    except ApiError as exc:
        log(f"  ! whatsapp integration: {exc}")


def ensure_payment_gateway(owner_token: str, kitchen_id: str) -> None:
    """Save dummy Razorpay test credentials so the owner integrations page shows a live config."""
    try:
        request(
            "PUT",
            f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
            {
                "key_id": "rzp_test_demo0000000001",
                "key_secret": "demo_test_secret_do_not_use",
                "webhook_secret": "demo_test_webhook_secret",
                "is_active": True,
            },
            token=owner_token,
        )
        log("  Payment gateway config saved (Razorpay test keys)")
    except ApiError as exc:
        log(f"  ! payment gateway: {exc}")


def ensure_gst(
    owner_token: str,
    kitchen_id: str,
    kitchen_name: str,
    *,
    gstin: str | None = None,
    kitchen_code: str | None = None,
) -> None:
    """Register a GST profile and sync invoices from delivered orders."""
    now = datetime.now(timezone.utc)
    if gstin is None:
        gstin = "27AAAPL1234C1Z5"
    # Invoice numbers are unique per kitchen; still use a distinct prefix so seeded
    # invoices are readable in admin tooling (kitchen code or short kitchen_id).
    prefix = (kitchen_code or f"K{kitchen_id.replace('-', '')[:6]}").upper()[:20]
    try:
        request(
            "PUT",
            f"/api/v1/kitchens/{kitchen_id}/gst/profile",
            {
                "gstin": gstin,
                "legal_name": kitchen_name,
                "trade_name": kitchen_name,
                "registered_address": "Koregaon Park, Lane 7, Pune, Maharashtra 411001",
                "default_tax_rate": 5,
                "invoice_prefix": prefix,
                "is_active": True,
            },
            token=owner_token,
        )
        for months_ago in (0, 1):
            period = now - timedelta(days=30 * months_ago)
            try:
                request(
                    "POST",
                    f"/api/v1/kitchens/{kitchen_id}/gst/sync?year={period.year}&month={period.month}",
                    token=owner_token,
                )
            except ApiError as exc:
                log(f"  ! gst sync {period.year}-{period.month:02d}: {exc}")
        log("  GST profile registered + invoices synced")
    except ApiError as exc:
        log(f"  ! gst profile: {exc}")


def ensure_refund(owner_token: str, kitchen_id: str) -> None:
    """Create + capture a payment on a delivered order, then a partial direct-transfer refund."""
    try:
        existing = request("GET", "/api/v1/billing/refunds", token=owner_token)
        if isinstance(existing, list) and existing:
            log("  Refund already exists — skipped")
            return

        orders = request("GET", f"/api/v1/kitchens/{kitchen_id}/orders?status=delivered", token=owner_token)
        candidates = [o for o in orders.get("orders", []) if o.get("payment_method") != "cod"]
        if not candidates:
            log("  ! refund: no eligible (non-COD, delivered) order found — skipped")
            return
        order = candidates[0]

        payment = request(
            "POST",
            "/api/v1/billing/payments",
            {"order_id": order["id"], "method": "upi"},
            token=owner_token,
        )
        request("POST", f"/api/v1/billing/payments/{payment['id']}/capture", token=owner_token)

        refund_amount = round(float(order["total"]) * 0.3, 2)
        request(
            "POST",
            "/api/v1/billing/refunds",
            {
                "order_id": order["id"],
                "kind": "partial",
                "amount": refund_amount,
                "destination_type": "upi",
                "destination_upi": "demo.customer@upi",
                "reason": "Missing item — owner-approved partial refund",
            },
            token=owner_token,
        )
        log(f"  Refund created: order {order['order_code']} — Rs {refund_amount}")
    except ApiError as exc:
        log(f"  ! refund: {exc}")


def ensure_delivery_quote(kitchen_id: str) -> None:
    """Exercise the public delivery fee-quote endpoint (F27-F28, F31)."""
    try:
        quote = request(
            "POST",
            "/api/v1/delivery/quote",
            {"kitchen_id": kitchen_id, "latitude": 18.5550, "longitude": 73.9020, "subtotal": 350.0},
        )
        log(f"  Delivery quote: {quote.get('distance_km', '?')} km — fee options computed")
    except ApiError as exc:
        log(f"  ! delivery quote: {exc}")


def ensure_support_tickets(customers: list[dict]) -> None:
    """Public + customer-JWT support ticket creation (notification service)."""
    try:
        request(
            "POST",
            "/api/v1/support/tickets",
            {
                "audience": "customer",
                "category": "delivery",
                "subject": "Order delayed beyond estimate",
                "description": "My order took much longer than the estimated delivery window — please check with the kitchen.",
                "customer_name": "Guest Diner",
                "source": "web_form",
            },
        )
        log("  Public support ticket created")
    except ApiError as exc:
        log(f"  ! public ticket: {exc}")

    if customers:
        try:
            request(
                "POST",
                "/api/v1/customers/me/tickets",
                {
                    "audience": "customer",
                    "category": "quality",
                    "subject": "Dish was cold on arrival",
                    "description": "The curry arrived cold — requesting a partial refund or replacement.",
                    "source": "web_form",
                },
                token=customers[0]["token"],
            )
            log("  Customer support ticket created")
        except ApiError as exc:
            log(f"  ! customer ticket: {exc}")


def ensure_branded_page(owner_token: str, kitchen_id: str, kitchen_name: str) -> None:
    """Publish the customer branded storefront at /k/{code}."""
    try:
        request(
            "PATCH",
            f"/api/v1/kitchens/{kitchen_id}/branded-page",
            {
                "enabled": True,
                "tagline": f"Home-taste from {kitchen_name}",
                "accent_color": "#0F766E",
            },
            token=owner_token,
        )
        log("  Branded storefront published")
    except ApiError as exc:
        log(f"  ! branded page: {exc}")


def ensure_streaming(
    owner_token: str, kitchen_id: str, dish_id: str | None = None
) -> None:
    """Opt in to live streaming and run a completed go-live with dish showcase (F46–F48)."""
    try:
        request(
            "PATCH",
            f"/api/v1/kitchens/{kitchen_id}/stream/settings",
            {"live_sharing_enabled": True, "q_and_a_enabled": True},
            token=owner_token,
        )
        session = request(
            "GET", f"/api/v1/kitchens/{kitchen_id}/stream/session", token=owner_token
        )
        if session and session.get("status") == "live":
            log("  Streaming session already live — skipped go-live")
            return
        body: dict = {"title": "Live: Weekend prep at the kitchen"}
        if dish_id:
            body["dish_id"] = dish_id
            body["showcase_phase"] = "ingredients"
        live = request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/stream/go-live",
            body,
            token=owner_token,
        )
        if dish_id and live.get("id"):
            try:
                request(
                    "PATCH",
                    f"/api/v1/kitchens/{kitchen_id}/stream/showcase",
                    {"showcase_phase": "prep", "active_prep_step_order": 1},
                    token=owner_token,
                )
                request(
                    "PATCH",
                    f"/api/v1/kitchens/{kitchen_id}/stream/showcase",
                    {"showcase_phase": "prepared"},
                    token=owner_token,
                )
            except ApiError as phase_exc:
                log(f"  ! stream showcase phases: {phase_exc}")
        request("POST", f"/api/v1/kitchens/{kitchen_id}/stream/end", token=owner_token)
        if dish_id:
            log("  Streaming go-live with dish showcase (ingredients→prep→prepared) recorded")
        else:
            log("  Streaming go-live opt-in + one completed session recorded")
    except ApiError as exc:
        log(f"  ! streaming: {exc}")


def ensure_learning_trial(owner_token: str, kitchen_id: str) -> None:
    """Curated recipe -> dish trial -> CRM invites -> ratings -> promote (F21-F22)."""
    try:
        if not ensure_curated_recipes_present():
            log("  ! learning trial: no curated recipes available — skipped")
            return
        recipes = request("GET", "/api/v1/learning/recipes")
        recipe_list = recipes.get("recipes") if isinstance(recipes, dict) else recipes

        trials = request("GET", f"/api/v1/kitchens/{kitchen_id}/learning/trials", token=owner_token)
        trial_list = trials.get("trials") if isinstance(trials, dict) else trials
        if trial_list:
            trial = trial_list[0]
            log("  Dish trial already exists — reusing")
        else:
            recipe = recipe_list[0]
            trial = request(
                "POST",
                f"/api/v1/kitchens/{kitchen_id}/learning/learn",
                {"recipe_id": recipe["id"]},
                token=owner_token,
            )
            log(f"  Started dish trial from curated recipe '{recipe['title']}'")

        if trial.get("status") == "promoted":
            log("  Dish trial already promoted — skipped")
            return

        crm = request("GET", f"/api/v1/kitchens/{kitchen_id}/crm/customers", token=owner_token)
        candidate_ids = [c["customer_id"] for c in crm.get("customers", []) if c.get("customer_id")]
        if len(candidate_ids) < MIN_TRIAL_INVITES:
            log(
                f"  ! learning trial: only {len(candidate_ids)} CRM customers with linked accounts "
                f"(need {MIN_TRIAL_INVITES}) — skipped invites/promote"
            )
            return

        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/learning/trials/{trial['id']}/invites",
            {"customer_ids": candidate_ids[:MIN_TRIAL_INVITES], "promo_type": "free"},
            token=owner_token,
        )
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/learning/trials/{trial['id']}/send-samples",
            token=owner_token,
        )
        detail = request(
            "GET", f"/api/v1/kitchens/{kitchen_id}/learning/trials/{trial['id']}", token=owner_token
        )
        for invite in detail.get("invites", []):
            if invite.get("status") == "rated":
                continue
            try:
                request(
                    "POST",
                    f"/api/v1/kitchens/{kitchen_id}/learning/trials/{trial['id']}/ratings",
                    {"invite_id": invite["id"], "home_taste_score": 5, "quality_score": 4},
                    token=owner_token,
                )
            except ApiError as exc:
                log(f"  ! trial rating: {exc}")
        request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/learning/trials/{trial['id']}/promote?force=true",
            token=owner_token,
        )
        log(f"  Dish trial promoted to live menu: {trial.get('dish_name', trial['id'])}")
    except ApiError as exc:
        log(f"  ! learning trial: {exc}")


def ensure_crm_and_coupon_extras(owner_token: str, kitchen_id: str, customers: list[dict]) -> None:
    """CRM tag update + coupon validation + active-promotion read (F36-F38 polish)."""
    try:
        crm = request("GET", f"/api/v1/kitchens/{kitchen_id}/crm/customers", token=owner_token)
        top_customer = next(iter(crm.get("customers", [])), None)
        if top_customer:
            request(
                "PATCH",
                f"/api/v1/kitchens/{kitchen_id}/crm/customers/{top_customer['id']}",
                {"tags": ["vip", "repeat-buyer"]},
                token=owner_token,
            )
            log("  CRM tags set on top customer (vip)")
    except ApiError as exc:
        log(f"  ! crm tags: {exc}")

    if customers:
        try:
            request(
                "POST",
                "/api/v1/marketing/coupons/validate",
                {"kitchen_id": kitchen_id, "code": "WELCOME10", "subtotal": 250},
                token=customers[0]["token"],
            )
            log("  Coupon validated at checkout (WELCOME10)")
        except ApiError as exc:
            log(f"  ! coupon validate: {exc}")

    try:
        request("GET", f"/api/v1/kitchens/{kitchen_id}/promotions/active")
        log("  Active promotions read (customer-facing)")
    except ApiError as exc:
        log(f"  ! promotions active: {exc}")


def demo_gstin_for_kitchen(kitchen_id: str) -> str:
    """Deterministic fake GSTIN per kitchen (global uq_kitchen_gst_profiles_gstin).

    Must match GSTIN_RE in services/billing/app/gst.py:
    2 digits (state) + 5 letters (PAN) + 4 digits (PAN) + 1 letter (PAN) + 1 alnum (entity) + "Z" + 1 alnum (checksum) = 15 chars.
    """
    digest = int(kitchen_id.replace("-", "")[:10], 16) % 10_000
    return f"27AAAAA{digest:04d}C1Z5"


def seed_kitchen_integrations(
    owner_token: str,
    kitchen_id: str,
    kitchen_name: str,
    *,
    kitchen_code: str | None = None,
    dish_id: str | None = None,
) -> None:
    """Per-kitchen owner integrations (safe to run for every kitchen in bulk seed)."""
    ensure_whatsapp_integration(owner_token, kitchen_id)
    ensure_payment_gateway(owner_token, kitchen_id)
    ensure_gst(
        owner_token,
        kitchen_id,
        kitchen_name,
        gstin=demo_gstin_for_kitchen(kitchen_id),
        kitchen_code=kitchen_code,
    )
    ensure_delivery_quote(kitchen_id)
    ensure_branded_page(owner_token, kitchen_id, kitchen_name)
    ensure_streaming(owner_token, kitchen_id, dish_id=dish_id)


def seed_kitchen_modules(owner_token: str, kitchen_id: str, dish_ids: dict[str, str]) -> None:
    """Per-kitchen marketing + growth modules (tenant-scoped, idempotent)."""
    if not dish_ids:
        return
    first_dish = next(iter(dish_ids.values()))
    ensure_marketing(owner_token, kitchen_id, first_dish)
    ensure_growth_suggestions(owner_token, kitchen_id)


def seed_platform_extras(
    *,
    owner_token: str,
    kitchen_id: str,
    dish_ids: dict[str, str],
    owner_phone_e164: str = "+919876543210",
    kitchen_name: str = "Sharma Home Kitchen",
) -> None:
    """Seed every persona + module: admin, customers, ratings, marketing, subscription,
    community, growth, WhatsApp, payments/GST/refunds, delivery, support, streaming, learning."""
    if os.environ.get("CKAC_SEED_EXTRAS", "1").strip().lower() in ("0", "false", "no"):
        log("Platform extras disabled (CKAC_SEED_EXTRAS=0)")
        return

    log("")
    log("Platform extras (all user types + all modules)")
    log("-" * 50)
    ensure_admin_session()
    customers = ensure_customer_sessions()
    if dish_ids:
        ensure_customer_orders(customers, kitchen_id, dish_ids, owner_token)
        ensure_ratings(customers, kitchen_id)
        first_dish = next(iter(dish_ids.values()))
        ensure_marketing(owner_token, kitchen_id, first_dish)
        ensure_enterprise_subscription(owner_token)
        recipe = ensure_community_recipe(owner_token, kitchen_id, first_dish)
        ensure_community_extras(customers, owner_token, kitchen_id, recipe)
        ensure_growth_blast(owner_token, kitchen_id, list(dish_ids.values())[:5])
        ensure_growth_suggestions(owner_token, kitchen_id)
        ensure_crm_and_coupon_extras(owner_token, kitchen_id, customers)

    log("")
    log("Owner integrations (WhatsApp, payments, GST, refunds, delivery, streaming, learning)")
    log("-" * 50)
    ensure_whatsapp_integration(owner_token, kitchen_id)
    ensure_payment_gateway(owner_token, kitchen_id)
    ensure_gst(
        owner_token,
        kitchen_id,
        kitchen_name,
        gstin=demo_gstin_for_kitchen(kitchen_id),
        kitchen_code="CKPNQ001",
    )
    ensure_refund(owner_token, kitchen_id)
    ensure_delivery_quote(kitchen_id)
    ensure_support_tickets(customers)
    ensure_branded_page(owner_token, kitchen_id, kitchen_name)
    first_dish = next(iter(dish_ids.values()), None) if dish_ids else None
    ensure_streaming(owner_token, kitchen_id, dish_id=first_dish)
    if dish_ids:
        ensure_learning_trial(owner_token, kitchen_id)

    log("Platform extras complete.")
