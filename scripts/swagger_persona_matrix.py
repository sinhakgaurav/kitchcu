#!/usr/bin/env python3
"""Exercise every gateway OpenAPI operation as owner, customer, and admin.

Mirrors Swagger Authorize (POST /api/v1/auth/token) then Try it out for each
persona. Safe methods use the seeded kitchen. Mutating calls use a non-existent
UUID / empty JSON so a missing auth gate is reported instead of writing demo data.

Usage:
  python scripts/swagger_persona_matrix.py
  CKAC_GATEWAY_URL=https://api.kitchcu.com python scripts/swagger_persona_matrix.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_data import DEMO_ADMIN, DEMO_OTP, DEMO_OWNER  # noqa: E402

GATEWAY = os.environ.get("CKAC_GATEWAY_URL", "http://localhost:18000").rstrip("/")
SAFE = frozenset({"GET", "HEAD", "OPTIONS"})
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
ABSENT_UUID = "00000000-0000-4000-8000-000000000000"
CUSTOMER_PHONE = os.environ.get("CKAC_CUSTOMER_PHONE", "9123456789")
def _admin_candidates() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    hint_status, hint = _call("GET", "/api/v1/admin/auth/login-hint")
    if hint_status == 200 and isinstance(hint, dict) and hint.get("revealed"):
        email = str(hint.get("email") or "").strip()
        password = str(hint.get("password") or "")
        if email and password:
            found.append((email, password))
    found.append(
        (
            os.environ.get("CKAC_ADMIN_EMAIL", DEMO_ADMIN["email"]),
            os.environ.get("CKAC_ADMIN_PASSWORD", DEMO_ADMIN["password"]),
        )
    )
    found.append(("admin@kitchcu.com", os.environ.get("CKAC_ADMIN_PASSWORD", DEMO_ADMIN["password"])))
    # Preserve order, drop dup emails keeping first password (hint wins).
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for email, password in found:
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((email, password))
    return unique


@dataclass
class Tokens:
    owner: str | None = None
    customer: str | None = None
    admin: str | None = None
    kitchen_id: str | None = None
    notes: list[str] = field(default_factory=list)


def _call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json_body: dict | None = None,
    form: dict[str, str] | None = None,
    timeout: float = 40,
) -> tuple[int, object]:
    headers = {"Accept": "application/json"}
    data: bytes | None = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{GATEWAY}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", "replace")
            try:
                return resp.status, json.loads(text or "null")
            except json.JSONDecodeError:
                return resp.status, text[:200]
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        text = raw.decode("utf-8", "replace")
        try:
            return exc.code, json.loads(text or "null")
        except json.JSONDecodeError:
            return exc.code, text[:200]
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(exc)


def swagger_token(username: str, password: str) -> str:
    status, body = _call(
        "POST",
        "/api/v1/auth/token",
        form={"username": username, "password": password, "grant_type": "password"},
    )
    if status != 200 or not isinstance(body, dict) or not body.get("access_token"):
        raise RuntimeError(f"Authorize failed for {username!r}: {status} {body}")
    return str(body["access_token"])


def collect_tokens() -> Tokens:
    tokens = Tokens()
    try:
        tokens.owner = swagger_token(DEMO_OWNER["phone"], DEMO_OTP)
    except RuntimeError as exc:
        tokens.notes.append(str(exc))
    try:
        tokens.customer = swagger_token(CUSTOMER_PHONE, DEMO_OTP)
    except RuntimeError as exc:
        tokens.notes.append(str(exc))
    last_admin_err = "no admin candidate tried"
    for email, password in _admin_candidates():
        try:
            tokens.admin = swagger_token(email, password)
            tokens.notes.append(f"admin swagger login as {email}")
            break
        except RuntimeError as exc:
            last_admin_err = str(exc)
    if not tokens.admin:
        tokens.notes.append(last_admin_err)
    if tokens.owner:
        status, body = _call("GET", "/api/v1/kitchens/me", token=tokens.owner)
        if status == 200 and isinstance(body, list) and body:
            tokens.kitchen_id = body[0].get("id")
        else:
            tokens.notes.append(f"kitchen lookup {status} {body}")
    return tokens


def _dummy(schema: dict, name: str) -> str:
    fmt = str(schema.get("format") or "")
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), "string")
    if schema.get("enum"):
        return str(schema["enum"][0])
    if fmt == "uuid" or name.endswith("_id"):
        return ABSENT_UUID
    if kind in ("integer", "number"):
        lo = schema.get("minimum")
        return str(lo if isinstance(lo, (int, float)) else 1)
    if kind == "boolean":
        return "false"
    lowered = name.lower()
    if "lat" in lowered:
        return "18.5362"
    if "lng" in lowered or "lon" in lowered:
        return "73.8958"
    if lowered in ("code", "kitchen_code"):
        return "CKPNQ001"
    if lowered == "provider":
        return "google"
    return "probe"


def build_url(path: str, operation: dict, shared: dict, kitchen_id: str | None, *, real_ids: bool) -> str:
    params = list(shared.get("parameters") or []) + list(operation.get("parameters") or [])
    query: dict[str, str] = {}
    resolved = path
    for param in params:
        if not isinstance(param, dict):
            continue
        name = param.get("name")
        if not name:
            continue
        schema = param.get("schema") or {}
        value = _dummy(schema, name)
        if real_ids and name == "kitchen_id" and kitchen_id:
            value = kitchen_id
        if param.get("in") == "path":
            resolved = resolved.replace("{" + name + "}", urllib.parse.quote(str(value)))
        elif param.get("in") == "query" and param.get("required"):
            query[name] = value
    while "{" in resolved and "}" in resolved:
        start = resolved.index("{")
        end = resolved.index("}", start)
        resolved = resolved[:start] + ABSENT_UUID + resolved[end + 1 :]
    if query:
        resolved += "?" + urllib.parse.urlencode(query)
    return resolved


def classify(path: str, operation: dict) -> str:
    if "/internal/" in path:
        return "internal"
    if "/webhooks/" in path:
        return "webhook"
    security = operation.get("security")
    if not security:
        return "public"
    if any(not req for req in security):
        return "optional"
    tags = [t.lower() for t in (operation.get("tags") or [])]
    if path.startswith("/api/v1/admin") or any("admin" in t for t in tags):
        return "admin"
    if (
        "/customers/me" in path
        or "/customer/me" in path
        or "/auth/customer" in path
        or "/payments/customer" in path
        or "/orders/customer" in path
        or ("/dishes/" in path and path.endswith("/suggestions"))
        or path.endswith("/subscribe")
        or path.endswith("/appreciate")
        or path.endswith("/coupons/validate")
        or path.endswith("/viewer-token")
    ):
        return "customer"
    return "owner"


def expected_accept(audience: str, persona: str) -> bool | None:
    """None = do not judge (public/optional/webhook)."""
    if audience in ("public", "optional", "webhook"):
        return None
    if audience == "internal":
        return False
    return persona == audience


def judge(audience: str, persona: str, status: int) -> str:
    """Auth-oriented verdict. 403/404/422 after a JWT means the gate ran."""
    if status == 0 or status >= 500:
        return "FAIL"
    if audience == "internal":
        return "PASS" if status in (401, 403, 404) else "FAIL"
    want = expected_accept(audience, persona)
    if want is None:
        if audience == "public" and status in (401, 403) and persona == "anon":
            return "FAIL"
        return "PASS"
    authed = status != 401
    if want:
        return "PASS" if authed else "FAIL"
    if status == 401 or status == 403:
        return "PASS"
    if persona == "admin" and audience in ("owner", "customer"):
        return "INFO"
    return "FAIL"


def iter_ops(spec: dict):
    for path, item in sorted((spec.get("paths") or {}).items()):
        if not isinstance(item, dict):
            continue
        for method_key, operation in item.items():
            if method_key not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            yield path, method_key.upper(), operation, item


def run_matrix(spec: dict, tokens: Tokens, *, delay: float) -> list[dict]:
    rows: list[dict] = []
    personas: list[tuple[str, str | None]] = [
        ("anon", None),
        ("owner", tokens.owner),
        ("customer", tokens.customer),
        ("admin", tokens.admin),
    ]
    for path, method, operation, shared in iter_ops(spec):
        audience = classify(path, operation)
        url = build_url(
            path, operation, shared, tokens.kitchen_id, real_ids=method in SAFE
        )
        body = None if method in SAFE else {}
        statuses: dict[str, int] = {}
        verdicts: dict[str, str] = {}
        for name, token in personas:
            if name != "anon" and not token:
                statuses[name] = -1
                verdicts[name] = "SKIP"
                continue
            status, _body = _call(method, url, token=token, json_body=body)
            statuses[name] = status
            verdicts[name] = judge(audience, name, status)
            if delay:
                time.sleep(delay)
        row_verdict = "FAIL" if "FAIL" in verdicts.values() else (
            "SKIP" if all(v == "SKIP" for k, v in verdicts.items() if k != "anon") else "PASS"
        )
        if "FAIL" not in verdicts.values() and "INFO" in verdicts.values():
            row_verdict = "INFO" if row_verdict == "PASS" else row_verdict
        rows.append(
            {
                "method": method,
                "path": path,
                "audience": audience,
                "url": url,
                "statuses": statuses,
                "verdicts": verdicts,
                "verdict": row_verdict,
            }
        )
    return rows


def print_report(rows: list[dict], tokens: Tokens) -> int:
    counts = Counter(r["verdict"] for r in rows)
    audiences = Counter(r["audience"] for r in rows)
    print(f"kitchCU Swagger persona matrix  gateway={GATEWAY}")
    print(f"operations={len(rows)}  " + " ".join(f"{k}={v}" for k, v in sorted(audiences.items())))
    print(f"PASS={counts['PASS']}  FAIL={counts['FAIL']}  INFO={counts['INFO']}  SKIP={counts['SKIP']}")
    print(
        f"tokens: owner={'yes' if tokens.owner else 'NO'}  "
        f"customer={'yes' if tokens.customer else 'NO'}  "
        f"admin={'yes' if tokens.admin else 'NO'}  "
        f"kitchen={tokens.kitchen_id or 'none'}"
    )
    for note in tokens.notes:
        print(f"  note: {note}")
    failures = [r for r in rows if r["verdict"] == "FAIL"]
    if failures:
        print()
        print(f"FAILURES ({len(failures)})")
        for r in failures:
            st = r["statuses"]
            print(
                f"  {r['method']:6} {r['path']}"
                f"  [{r['audience']}]"
                f"  anon={st.get('anon')} owner={st.get('owner')} "
                f"customer={st.get('customer')} admin={st.get('admin')}"
            )
    print()
    print("Sample accepted reads (status < 400) by persona:")
    for persona in ("owner", "customer", "admin"):
        hits = [
            r
            for r in rows
            if r["method"] == "GET" and 200 <= (r["statuses"].get(persona) or 0) < 400
        ]
        print(f"  {persona}: {len(hits)} GET 2xx/3xx")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", metavar="PATH", help="write full matrix as JSON")
    parser.add_argument("--delay", type=float, default=0.12, help="seconds between calls")
    args = parser.parse_args()

    status, spec = _call("GET", "/openapi.json", timeout=90)
    if status != 200 or not isinstance(spec, dict):
        print(f"Cannot load {GATEWAY}/openapi.json ({status} {spec})", file=sys.stderr)
        return 2
    tokens = collect_tokens()
    rows = run_matrix(spec, tokens, delay=args.delay)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")
    return print_report(rows, tokens)


if __name__ == "__main__":
    raise SystemExit(main())
