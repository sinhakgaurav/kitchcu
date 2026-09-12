"""Shared HTTP helpers for CKAC seed scripts."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime

GATEWAY = os.environ.get("CKAC_GATEWAY_URL", "http://localhost:18000").rstrip("/")
# GCP VM alembic on e2-small can take several minutes after compose up.
MAX_WAIT_SEC = int(os.environ.get("CKAC_SEED_WAIT_SEC", "600"))
REQUIRED_SERVICES = ("identity", "catalog", "order", "billing")


DEFAULT_POSTGRES_CONTAINER = "ckac-postgres-1"

# When more than one stack is up, `docker ps` order must not pick the database.
# The GCP parity dry-run (which the pre-push gate runs) leaves
# `ckac-gcp-dry-postgres-1` behind, and it sorted ahead of the dev container —
# so seed SQL silently updated rows in a database the gateway never reads.
_POSTGRES_PREFERENCE = (
    "ckac-postgres-1",  # docker-compose.yml — the stack the dev gateway uses
    "ckac_postgres_1",  # older underscore compose naming
    "gcp-vm-postgres-1",  # infra/gcp-vm/docker-compose.prod.yml on the VM
)


def _docker_container_names() -> list[str]:
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}"],
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def resolve_postgres_container() -> str:
    """Name the Postgres container that backs the gateway being seeded.

    Set ``CKAC_POSTGRES_CONTAINER`` to override; otherwise the dev stack wins
    over any parity or prod stack that happens to be running alongside it.
    """
    override = os.environ.get("CKAC_POSTGRES_CONTAINER", "").strip()
    if override:
        return override
    names = _docker_container_names()
    if not names:
        return DEFAULT_POSTGRES_CONTAINER
    running = set(names)
    for preferred in _POSTGRES_PREFERENCE:
        if preferred in running:
            return preferred
    candidates = [
        n for n in names if n.endswith(("-postgres-1", "_postgres_1"))
    ] or [n for n in names if "postgres" in n.lower()]
    if len(candidates) > 1:
        print(
            f"  ! Multiple Postgres containers running ({', '.join(candidates)}); "
            f"using {candidates[0]}. Set CKAC_POSTGRES_CONTAINER to choose."
        )
    return candidates[0] if candidates else DEFAULT_POSTGRES_CONTAINER


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


def ensure_customer_addresses(token: str, addresses: list[dict]) -> int:
    """Idempotent: add labelled pins the diner does not already have."""
    try:
        existing = request("GET", "/api/v1/customers/me/addresses", token=token) or []
    except ApiError as exc:
        log(f"  ! list addresses: {exc}")
        return 0
    have = {
        (str(row.get("label", "")).strip().lower(), str(row.get("city", "")).strip().lower())
        for row in existing
    }
    added = 0
    for spec in addresses:
        key = (str(spec.get("label", "")).strip().lower(), str(spec.get("city", "")).strip().lower())
        if key in have:
            continue
        try:
            request("POST", "/api/v1/customers/me/addresses", spec, token=token)
            added += 1
        except ApiError as exc:
            log(f"  ! address {spec.get('label')} {spec.get('city')}: {exc}")
    return added


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
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        # Windows consoles often default to cp1252; keep seed running.
        print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)


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

    payload = {
        "name": dish["name"],
        "price": dish["price"],
        "prep_time_min": dish["prep_time_min"],
        "description": dish.get("description", f"{dish['name']} — house special."),
        "ingredients_description": dish.get("ingredients_description", "Fresh ingredients"),
        "cuisine_id": cuisine_id,
        "category_id": category_id,
    }
    # Dishes with no honest asset (e.g. drinks) seed without a hero rather than
    # borrowing a photo of something else. Active dishes require a live-capture
    # hero, so those stay drafts until an owner captures one.
    if dish.get("media_url"):
        payload["media"] = {
            "url": dish["media_url"],
            "is_hero": True,
            "is_live_capture": True,
            "captured_at": captured_at,
        }
    else:
        payload["is_active"] = False
    return payload


# Rows that must move with their parent order when history is dated.
_ORDER_LINKED_TIMESTAMPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ckac_orders.order_status_events", ("created_at",)),
    ("ckac_billing.payments", ("created_at", "updated_at")),
    ("ckac_billing.refunds", ("created_at", "updated_at", "completed_at")),
    ("ckac_billing.settlements", ("created_at", "settled_at")),
    ("ckac_billing.gst_tax_invoices", ("created_at", "invoice_date")),
    ("ckac_ratings.dish_ratings", ("created_at",)),
)


def run_psql(sql: str, *, timeout: int = 300) -> tuple[bool, str]:
    """Pipe a script to psql inside the Postgres container the gateway uses."""
    try:
        proc = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                "-e",
                "PGCLIENTENCODING=UTF8",
                resolve_postgres_container(),
                "psql",
                "-U",
                "ckac",
                "-d",
                "ckac",
                "-v",
                "ON_ERROR_STOP=1",
                "-q",
                "-f",
                "-",
            ],
            input=sql,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or proc.stdout.strip())
    return True, ""


def apply_planned_order_times(
    kitchen_id: str,
    stamps: list[tuple[str, datetime]],
) -> tuple[bool, str]:
    """Shift each order (and linked payment/rating/GST rows) to ``stamps``.

    Used by the 6-month bulk seeder and the Saturday weekly fill. Returns
    ``(ok, error)`` so callers can log without raising.
    """
    if not stamps:
        return True, ""
    values = ",".join(
        f"('{order_id}'::uuid,'{when.isoformat()}'::timestamptz)"
        for order_id, when in stamps
    )
    cascade = ",".join(
        f"('{table}','{column}')"
        for table, columns in _ORDER_LINKED_TIMESTAMPS
        for column in columns
    )
    sql = f"""
BEGIN;
CREATE TEMP TABLE planned (order_id uuid PRIMARY KEY, placed_at timestamptz) ON COMMIT DROP;
INSERT INTO planned VALUES {values};

CREATE TEMP TABLE shifted (order_id uuid PRIMARY KEY, delta interval) ON COMMIT DROP;
INSERT INTO shifted
SELECT p.order_id, p.placed_at - o.created_at
FROM planned p
JOIN ckac_orders.orders o ON o.id = p.order_id
WHERE o.kitchen_id = '{kitchen_id}'::uuid;

DO $$
DECLARE matched int;
BEGIN
  SELECT count(*) INTO matched FROM shifted;
  IF matched <> {len(stamps)} THEN
    RAISE EXCEPTION
      'dating matched % of % orders for kitchen {kitchen_id} — wrong database?',
      matched, {len(stamps)};
  END IF;
END $$;

UPDATE ckac_orders.orders o
SET created_at = o.created_at + s.delta,
    updated_at = o.updated_at + s.delta
FROM shifted s
WHERE o.id = s.order_id;

DO $$
DECLARE v_tbl text; v_col text;
BEGIN
  FOR v_tbl, v_col IN SELECT * FROM (VALUES {cascade}) AS v(tbl, col) LOOP
    IF to_regclass(v_tbl) IS NULL THEN CONTINUE; END IF;
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema = split_part(v_tbl, '.', 1)
        AND c.table_name = split_part(v_tbl, '.', 2)
        AND c.column_name = v_col
    ) THEN CONTINUE; END IF;
    EXECUTE format(
      'UPDATE %s x SET %I = x.%I + s.delta FROM shifted s WHERE x.order_id = s.order_id',
      v_tbl, v_col, v_col
    );
  END LOOP;
END $$;

UPDATE ckac_billing.gst_tax_invoices g
SET invoice_number = left(g.invoice_number, 40) || '-t' || left(g.id::text, 8)
WHERE g.kitchen_id = '{kitchen_id}'::uuid
  AND EXISTS (SELECT 1 FROM shifted s WHERE s.order_id = g.order_id);

UPDATE ckac_billing.gst_tax_invoices g
SET invoice_number = n.fresh
FROM (
  SELECT
    g2.id,
    k.code || '-GST-' || to_char(g2.invoice_date AT TIME ZONE 'UTC', 'YYYYMM')
      || '-' || lpad(
        row_number() OVER (
          PARTITION BY g2.kitchen_id, to_char(g2.invoice_date AT TIME ZONE 'UTC', 'YYYYMM')
          ORDER BY g2.invoice_date, g2.id
        )::text,
        4, '0'
      ) AS fresh
  FROM ckac_billing.gst_tax_invoices g2
  JOIN ckac_identity.kitchens k ON k.id = g2.kitchen_id
  WHERE g2.kitchen_id = '{kitchen_id}'::uuid
    AND EXISTS (SELECT 1 FROM shifted s WHERE s.order_id = g2.order_id)
) n
WHERE g.id = n.id;

COMMIT;
"""
    return run_psql(sql)
