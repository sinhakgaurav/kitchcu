"""Shared HTTP helpers for CKAC seed scripts."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

GATEWAY = os.environ.get("CKAC_GATEWAY_URL", "http://localhost:18000").rstrip("/")
# GCP VM alembic on e2-small can take several minutes after compose up.
MAX_WAIT_SEC = int(os.environ.get("CKAC_SEED_WAIT_SEC", "600"))
REQUIRED_SERVICES = ("identity", "catalog", "order", "billing")


def resolve_postgres_container() -> str:
    """Return the running Postgres container name (local `ckac-postgres-1` or GCP `gcp-vm-postgres-1`)."""
    override = os.environ.get("CKAC_POSTGRES_CONTAINER", "").strip()
    if override:
        return override
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}"],
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "ckac-postgres-1"
    names = [line.strip() for line in out.splitlines() if line.strip()]
    for name in names:
        if name.endswith("-postgres-1") or name.endswith("_postgres_1"):
            return name
    for name in names:
        if "postgres" in name.lower():
            return name
    return "ckac-postgres-1"


class ApiError(Exception):
    pass


def _retry_after_seconds(exc: urllib.error.HTTPError, detail: str) -> float:
    """Parse Retry-After header or ``try again in Ns`` detail for 429 backoff."""
    raw = exc.headers.get("Retry-After") if exc.headers else None
    if raw:
        try:
            return max(1.0, float(raw))
        except ValueError:
            pass
    # e.g. "Too many requests — try again in 2s"
    marker = "try again in "
    lower = detail.lower()
    if marker in lower:
        tail = lower.split(marker, 1)[1]
        digits = ""
        for ch in tail:
            if ch.isdigit() or ch == ".":
                digits += ch
            else:
                break
        if digits:
            try:
                return max(1.0, float(digits))
            except ValueError:
                pass
    return 3.0


_RETRYABLE_HTTP = frozenset({429, 502, 503, 504})


def request(
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
    timeout: int = 60,
    *,
    max_retries: int = 10,
) -> dict | list:
    url = f"{GATEWAY}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_msg = ""
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()
            try:
                parsed = json.loads(detail)
                msg = parsed.get("detail", detail)
            except json.JSONDecodeError:
                msg = detail or exc.reason
            last_msg = f"{method} {path} -> {exc.code}: {msg}"
            if exc.code in _RETRYABLE_HTTP and attempt < max_retries:
                if exc.code == 429:
                    wait = _retry_after_seconds(exc, str(msg))
                    print(f"  … rate limited, retry in {wait:.0f}s ({attempt + 1}/{max_retries})")
                else:
                    wait = min(30.0, 2.0 * (attempt + 1))
                    print(
                        f"  … HTTP {exc.code}, backoff {wait:.0f}s "
                        f"({attempt + 1}/{max_retries})"
                    )
                time.sleep(wait)
                continue
            raise ApiError(last_msg) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_msg = f"{method} {path} -> transport: {exc}"
            if attempt < max_retries:
                wait = min(30.0, 2.0 * (attempt + 1))
                print(f"  … transport error, retry in {wait:.0f}s ({attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            raise ApiError(last_msg) from exc
    raise ApiError(last_msg or f"{method} {path} -> failed")


def _ready_payload() -> dict | None:
    url = f"{GATEWAY}/health/ready"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        ConnectionError,  # includes http.client.RemoteDisconnected during gateway restart
        OSError,
        json.JSONDecodeError,
    ):
        return None


def wait_for_gateway() -> None:
    """Block until gateway /health/ready is status=ok (identity + core services up).

    Do not seed on /health/live alone — that only proves the gateway process is up.
    """
    print(f"Waiting for stack ready at {GATEWAY}/health/ready (need identity) ...")
    deadline = time.time() + MAX_WAIT_SEC
    last_note = ""
    while time.time() < deadline:
        body = _ready_payload()
        if body:
            services = body.get("services") or {}
            missing = [s for s in REQUIRED_SERVICES if not services.get(s)]
            if body.get("status") == "ok" and not missing:
                # Re-check once — identity can flap during alembic restart loops.
                time.sleep(5)
                body2 = _ready_payload() or {}
                services2 = body2.get("services") or {}
                missing2 = [s for s in REQUIRED_SERVICES if not services2.get(s)]
                if body2.get("status") == "ok" and not missing2:
                    print(
                        "Stack ready: "
                        + ", ".join(f"{k}={v}" for k, v in sorted(services2.items()))
                    )
                    return
            note = f"status={body.get('status')} missing={missing or 'none'} services={services}"
            if note != last_note:
                print(f"  … {note}")
                last_note = note
        else:
            if last_note != "unreachable":
                print("  … gateway /health/ready unreachable")
                last_note = "unreachable"
        time.sleep(5)
    raise SystemExit(
        f"Stack not ready after {MAX_WAIT_SEC}s — identity (and core services) must be up. "
        "On GCP: docker compose -f infra/gcp-vm/docker-compose.prod.yml logs --tail=80 identity"
    )


def login_owner(phone_e164: str, otp: str) -> str:
    request("POST", "/api/v1/auth/otp/request", {"phone": phone_e164})
    token_resp = request("POST", "/api/v1/auth/otp/verify", {"phone": phone_e164, "otp": otp})
    return token_resp["access_token"]


def login_customer(phone_e164: str, otp: str) -> str:
    request("POST", "/api/v1/auth/customer/whatsapp/request", {"phone": phone_e164})
    token_resp = request(
        "POST",
        "/api/v1/auth/customer/whatsapp/verify",
        {"phone": phone_e164, "otp": otp},
    )
    return token_resp["access_token"]


def login_admin(email: str, password: str) -> str:
    token_resp = request(
        "POST",
        "/api/v1/admin/auth/login",
        {"email": email, "password": password},
    )
    return token_resp["access_token"]


def log(msg: str) -> None:
    print(msg, flush=True)


def cuisine_map(token: str, kitchen_id: str) -> dict[str, str]:
    cuisines = request("GET", f"/api/v1/kitchens/{kitchen_id}/cuisines", token=token)
    return {c["slug"]: c["id"] for c in cuisines}


def ensure_ingredients(token: str, kitchen_id: str, pantry: list[dict]) -> dict[str, str]:
    """Create pantry items; return name -> ingredient id."""
    existing = request("GET", f"/api/v1/kitchens/{kitchen_id}/ingredients", token=token)
    by_name = {i["name"]: i["id"] for i in existing.get("ingredients", [])}
    created = 0
    for item in pantry:
        if item["name"] in by_name:
            continue
        resp = request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/ingredients",
            item,
            token=token,
        )
        by_name[item["name"]] = resp["id"]
        created += 1
    if created:
        print(f"  Added {created} ingredients to kitchen {kitchen_id[:8]}...")
    return by_name


def ensure_dish_recipes(
    token: str,
    kitchen_id: str,
    dish_ids: dict[str, str],
    recipes: dict[str, list],
    ingredient_ids: dict[str, str],
    prep_steps: dict[str, list[dict]] | None = None,
) -> int:
    """Set recipe lines + optional prep steps for dishes that have mappings."""
    set_count = 0
    for dish_name, lines in recipes.items():
        dish_id = dish_ids.get(dish_name)
        if not dish_id:
            continue
        payload_lines = []
        for index, entry in enumerate(lines):
            if len(entry) == 4:
                ing_name, qty, unit, photo = entry
            else:
                ing_name, qty, unit = entry
                photo = None
            ing_id = ingredient_ids.get(ing_name)
            if not ing_id:
                continue
            line = {
                "ingredient_id": ing_id,
                "quantity": qty,
                "unit": unit,
                "sort_order": index,
            }
            if photo:
                line["photo_url"] = photo
            payload_lines.append(line)
        if not payload_lines:
            continue
        body: dict = {"lines": payload_lines}
        if prep_steps and dish_name in prep_steps:
            body["prep_steps"] = prep_steps[dish_name]
        request(
            "PUT",
            f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
            body,
            token=token,
        )
        set_count += 1
    if set_count:
        print(f"  Set recipes on {set_count} dishes.")
    return set_count


def dish_create_payload(
    dish: dict,
    *,
    category_ids: dict[str, str],
    cuisine_ids: dict[str, str],
    captured_at: str,
) -> dict:
    from demo_data import infer_cuisine_slug, normalize_category_slug

    diet_slug = normalize_category_slug(dish)
    cuisine_slug = infer_cuisine_slug(dish)
    category_id = category_ids.get(diet_slug)
    cuisine_id = cuisine_ids.get(cuisine_slug) or cuisine_ids.get("home_style")
    if not category_id or not cuisine_id:
        raise ApiError(f"Missing cuisine/category for dish {dish['name']}: {cuisine_slug}/{diet_slug}")

    return {
        "name": dish["name"],
        "price": dish["price"],
        "prep_time_min": dish["prep_time_min"],
        "description": dish.get("description", f"{dish['name']} — house special."),
        "ingredients_description": dish.get("ingredients_description", "Fresh ingredients"),
        "cuisine_id": cuisine_id,
        "category_id": category_id,
        "media": {
            "url": dish["media_url"],
            "is_hero": True,
            "is_live_capture": True,
            "captured_at": captured_at,
        },
    }
