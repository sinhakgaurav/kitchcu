#!/usr/bin/env python3
"""Check that the gateway enforces the auth its Swagger schema advertises.

Swagger is a promise. This walks every operation in the gateway's aggregated
OpenAPI document and probes the live edge to see whether the promise holds:

* an operation that declares ``security`` must reject an anonymous caller
* an operation that declares none must serve an anonymous caller
* a valid JWT must actually get a declared-protected read past the gate
* ``/internal/*`` is service-to-service and must not be reachable from the edge

Required query parameters are filled with dummy values first, so a 422 can never
be mistaken for an auth rejection. Token probes only touch safe methods, and
anonymous probes of mutating routes use non-existent ids so that a missing gate
is reported rather than acted on.

Usage:
  python scripts/audit-api-auth.py
  python scripts/audit-api-auth.py --json report.json
  CKAC_GATEWAY_URL=https://api.kitchcu.com python scripts/audit-api-auth.py
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_data import DEMO_OTP, DEMO_OWNER  # noqa: E402
from seed_common import GATEWAY, ApiError, login_admin, login_customer, login_owner, request  # noqa: E402

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
REJECTED = frozenset({401, 403})

# A syntactically valid UUID that owns nothing, so an unguarded mutating route
# 404s on its tenant lookup instead of writing.
ABSENT_UUID = "00000000-0000-4000-8000-000000000000"

ADMIN_EMAIL = "admin@kitchcu.dev"
ADMIN_PASSWORD = "admin123456"
DEMO_CUSTOMER_PHONE = "+919123456789"


class Verdict:
    PASS = "PASS"
    FAIL = "FAIL"
    INFO = "INFO"


@dataclass
class Probe:
    method: str
    path: str
    audience: str  # public | owner | customer | admin | internal | webhook
    anon_status: int | None = None
    token_status: int | None = None
    verdict: str = Verdict.INFO
    note: str = ""


@dataclass
class Tokens:
    owner: str | None = None
    customer: str | None = None
    admin: str | None = None
    kitchen_id: str | None = None
    failures: list[str] = field(default_factory=list)


def fetch_spec() -> dict:
    url = f"{GATEWAY}/openapi.json"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode())


def raw_call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict | None = None,
) -> int:
    """Return the HTTP status, treating every response as data rather than error."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{GATEWAY}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def _dummy_for(schema: dict, name: str) -> str:
    """A value that will pass validation, so only auth can reject the request."""
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
    return "audit"


def build_url(
    path: str,
    operation: dict,
    shared: dict,
    tokens: Tokens,
    *,
    real_ids: bool,
) -> str:
    """Substitute path params and supply every required query param.

    ``real_ids`` is only ever set for safe methods. A mutating probe always
    addresses a non-existent tenant, so a route that turns out to have no auth
    gate is reported rather than executed against the demo kitchen.
    """
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
        value = _dummy_for(schema, name)
        # A 404 proves nothing about a route that is supposed to check ownership
        # before answering, so reads use the seeded kitchen.
        if real_ids and name == "kitchen_id" and tokens.kitchen_id:
            value = tokens.kitchen_id
        where = param.get("in")
        if where == "path":
            resolved = resolved.replace("{" + name + "}", urllib.parse.quote(str(value)))
        elif where == "query" and param.get("required"):
            query[name] = value
    # Anything the spec did not describe still has to be filled or the URL breaks.
    while "{" in resolved and "}" in resolved:
        start = resolved.index("{")
        end = resolved.index("}", start)
        resolved = resolved[:start] + ABSENT_UUID + resolved[end + 1 :]
    if query:
        resolved += "?" + urllib.parse.urlencode(query)
    return resolved


def declared_optional_auth(operation: dict) -> bool:
    """True when the schema says a token is accepted but not required.

    OpenAPI spells this as an empty requirement object alongside the scheme:
    ``security: [{}, {"HTTPBearer": []}]``.
    """
    return any(not requirement for requirement in (operation.get("security") or []))


def classify(path: str, operation: dict) -> str:
    """Best guess at the intended audience — used for reporting, not for verdicts.

    Protected routes are verified by offering every token in turn, so a wrong
    guess here cannot produce a false failure.
    """
    if "/internal/" in path:
        return "internal"
    if "/webhooks/" in path:
        return "webhook"
    if not operation.get("security"):
        return "public"
    if declared_optional_auth(operation):
        return "optional"
    tags = [t.lower() for t in (operation.get("tags") or [])]
    if path.startswith("/api/v1/admin") or any("admin" in t for t in tags):
        return "admin"
    if "/customer/me" in path or "/customers/me" in path or "/customers/" in path:
        return "customer"
    return "owner"


def collect_tokens() -> Tokens:
    tokens = Tokens()
    try:
        tokens.owner = login_owner(DEMO_OWNER["phone_e164"], DEMO_OTP)
    except (ApiError, KeyError) as exc:
        tokens.failures.append(f"owner login: {exc}")
    try:
        tokens.customer = login_customer(DEMO_CUSTOMER_PHONE, DEMO_OTP)
    except (ApiError, KeyError) as exc:
        tokens.failures.append(f"customer login: {exc}")
    try:
        tokens.admin = login_admin(ADMIN_EMAIL, ADMIN_PASSWORD)
    except (ApiError, KeyError) as exc:
        tokens.failures.append(f"admin login: {exc}")
    if tokens.owner:
        try:
            kitchens = request("GET", "/api/v1/kitchens/me", token=tokens.owner)
            if isinstance(kitchens, list) and kitchens:
                tokens.kitchen_id = kitchens[0]["id"]
        except (ApiError, KeyError, IndexError) as exc:
            tokens.failures.append(f"kitchen lookup: {exc}")
    return tokens


def candidate_tokens(audience: str, tokens: Tokens) -> list[tuple[str, str]]:
    """Every token worth offering, best guess first."""
    available = [
        (name, tok)
        for name, tok in (
            ("owner", tokens.owner),
            ("customer", tokens.customer),
            ("admin", tokens.admin),
        )
        if tok
    ]
    available.sort(key=lambda pair: pair[0] != audience)
    return available


def audit(spec: dict, tokens: Tokens) -> list[Probe]:
    probes: list[Probe] = []
    for path, item in sorted(spec.get("paths", {}).items()):
        for method_key, operation in item.items():
            if method_key not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            method = method_key.upper()
            audience = classify(path, operation)
            url = build_url(
                path, operation, item, tokens, real_ids=method in SAFE_METHODS
            )
            probe = Probe(method=method, path=path, audience=audience)

            body = None if method in SAFE_METHODS else {}
            probe.anon_status = raw_call(method, url, body=body)

            if probe.anon_status == 0:
                probe.verdict = Verdict.FAIL
                probe.note = "gateway unreachable"
                probes.append(probe)
                continue

            if audience in ("public", "optional"):
                if probe.anon_status in REJECTED:
                    probe.verdict = Verdict.FAIL
                    probe.note = (
                        f"declared {audience} but rejected anonymous ({probe.anon_status})"
                    )
                else:
                    probe.verdict = Verdict.PASS
                    probe.note = f"anonymous reachable ({probe.anon_status})"

            elif audience == "internal":
                # Service-to-service. Reachable from the public edge is the finding,
                # whichever status it answers with.
                if probe.anon_status in REJECTED or probe.anon_status == 404:
                    probe.verdict = Verdict.PASS
                    probe.note = f"not usable from edge ({probe.anon_status})"
                else:
                    probe.verdict = Verdict.FAIL
                    probe.note = (
                        f"internal route answered {probe.anon_status} without X-Internal-Key"
                    )

            elif audience == "webhook":
                # External callers cannot present a JWT, so these are guarded by
                # provider signatures instead. Whether an unsigned call is
                # refused depends on the configured secret, which this probe
                # cannot see, so the status is reported rather than judged.
                probe.verdict = Verdict.INFO
                probe.note = (
                    f"provider-signature endpoint, anonymous got {probe.anon_status} "
                    "(verify the signing secret is configured per environment)"
                )

            else:
                if probe.anon_status not in REJECTED:
                    probe.verdict = Verdict.FAIL
                    probe.note = (
                        f"declares security but anonymous got {probe.anon_status}"
                    )
                elif method in SAFE_METHODS:
                    # Offer each token until one is let through, so the audit
                    # reports the audience the route really serves rather than
                    # trusting a path heuristic.
                    accepted: str | None = None
                    for name, tok in candidate_tokens(audience, tokens):
                        status = raw_call(method, url, token=tok)
                        if probe.token_status is None or name == audience:
                            probe.token_status = status
                        if status not in REJECTED:
                            accepted = name
                            probe.token_status = status
                            break
                    if accepted:
                        probe.verdict = Verdict.PASS
                        probe.note = (
                            f"anon {probe.anon_status}, {accepted} token "
                            f"{probe.token_status}"
                        )
                    elif not any(tok for _, tok in candidate_tokens(audience, tokens)):
                        probe.verdict = Verdict.INFO
                        probe.note = (
                            f"anonymous rejected ({probe.anon_status}); no token to verify with"
                        )
                    else:
                        probe.verdict = Verdict.FAIL
                        probe.note = (
                            f"anonymous rejected ({probe.anon_status}) but no valid "
                            "token was accepted either"
                        )
                else:
                    probe.verdict = Verdict.PASS
                    probe.note = f"anonymous rejected ({probe.anon_status})"
            probes.append(probe)
    return probes


def report(probes: list[Probe], tokens: Tokens) -> int:
    by_audience: Counter[str] = Counter(p.audience for p in probes)
    by_verdict: Counter[str] = Counter(p.verdict for p in probes)

    print("kitchCU API auth audit")
    print("=" * 78)
    print(f"Gateway: {GATEWAY}")
    print(f"Operations probed: {len(probes)}")
    print(
        "  " + "  ".join(f"{k}={v}" for k, v in sorted(by_audience.items()))
    )
    print(
        f"  PASS={by_verdict[Verdict.PASS]}  "
        f"FAIL={by_verdict[Verdict.FAIL]}  INFO={by_verdict[Verdict.INFO]}"
    )
    if tokens.failures:
        print()
        print("Token setup problems (protected routes could not be positively verified):")
        for note in tokens.failures:
            print(f"  ! {note}")

    failures = [p for p in probes if p.verdict == Verdict.FAIL]
    if failures:
        print()
        print(f"FAILURES ({len(failures)})")
        print("-" * 78)
        for p in failures:
            print(f"  {p.method:6} {p.path}")
            print(f"         [{p.audience}] {p.note}")

    infos = [p for p in probes if p.verdict == Verdict.INFO]
    if infos:
        print()
        print(f"INFORMATIONAL ({len(infos)})")
        print("-" * 78)
        for p in infos:
            print(f"  {p.method:6} {p.path} — {p.note}")

    print()
    if failures:
        print(f"RESULT: FAIL — {len(failures)} operation(s) do not enforce declared auth")
    else:
        print("RESULT: PASS — enforced auth matches the published schema")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", metavar="PATH", help="write the full probe table as JSON")
    args = parser.parse_args()

    spec = fetch_spec()
    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    print("Security schemes in the published schema:")
    for name, scheme in schemes.items():
        print(
            f"  {name}: type={scheme.get('type')} scheme={scheme.get('scheme')} "
            f"format={scheme.get('bearerFormat')}"
        )
    if not schemes:
        print("  ! none — Swagger will not offer an Authorize button")
    print(f"Global security: {spec.get('security') or 'none (declared per operation)'}")
    print()

    tokens = collect_tokens()
    probes = audit(spec, tokens)

    if args.json:
        Path(args.json).write_text(
            json.dumps([p.__dict__ for p in probes], indent=2), encoding="utf-8"
        )
        print(f"Wrote {args.json}")

    return report(probes, tokens)


if __name__ == "__main__":
    raise SystemExit(main())
