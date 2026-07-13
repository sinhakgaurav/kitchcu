"""Shared HTTP helpers for CKAC seed scripts."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

GATEWAY = os.environ.get("CKAC_GATEWAY_URL", "http://localhost:18000").rstrip("/")
MAX_WAIT_SEC = int(os.environ.get("CKAC_SEED_WAIT_SEC", "120"))


class ApiError(Exception):
    pass


def request(
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
    timeout: int = 30,
) -> dict | list:
    url = f"{GATEWAY}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
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
        raise ApiError(f"{method} {path} -> {exc.code}: {msg}") from exc


def wait_for_gateway() -> None:
    print(f"Waiting for gateway at {GATEWAY} ...")
    deadline = time.time() + MAX_WAIT_SEC
    while time.time() < deadline:
        try:
            request("GET", "/health/live")
            print("Gateway live.")
            return
        except (ApiError, urllib.error.URLError, TimeoutError):
            time.sleep(2)
    raise SystemExit(f"Gateway not ready after {MAX_WAIT_SEC}s")


def login_owner(phone_e164: str, otp: str) -> str:
    request("POST", "/api/v1/auth/otp/request", {"phone": phone_e164})
    token_resp = request("POST", "/api/v1/auth/otp/verify", {"phone": phone_e164, "otp": otp})
    return token_resp["access_token"]


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
