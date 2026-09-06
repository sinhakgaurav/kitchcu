"""Replay the QA issue tracker's API bugs against a running gateway.

Each check mirrors one row of the "API Bug Report" sheet in the tracker: same
endpoint, same payload, same expectation the QA team wrote down. Run it after
`docker compose up -d` to confirm a fix actually holds at the HTTP edge rather
than only in unit tests.

    python scripts/validate_issue_tracker.py [--base-url http://localhost:18000]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

DEFAULT_BASE_URL = "http://localhost:18000"


@dataclass
class Result:
    bug_id: str
    title: str
    passed: bool
    detail: str


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)

    def add(self, bug_id: str, title: str, passed: bool, detail: str) -> None:
        self.results.append(Result(bug_id, title, passed, detail))
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {bug_id} — {detail}")

    @property
    def failed(self) -> list[Result]:
        return [r for r in self.results if not r.passed]


def call(base_url: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return exc.code, {"detail": raw}


def unique_phone() -> str:
    """A valid, unused 10-digit India mobile so 'accepted' never means 'duplicate'."""
    return "9" + str(uuid.uuid4().int)[:9]


def check_bug_01(base: str, report: Report) -> None:
    """OTP request must reject phone numbers that are not 10 national digits."""
    for phone in ("987654321011", "98765", "abcdefghij", "98765 4321!"):
        status, body = call(base, "POST", "/api/v1/auth/otp/request", {"phone": phone})
        ok = status == 422
        report.add(
            "BUG_01",
            "OTP request rejects malformed phone",
            ok,
            f"phone={phone!r} -> {status} (want 422) {str(body)[:90]}",
        )
    # +91 prefixed E.164 is a legitimate spelling of a 10-digit number: accept it.
    status, _ = call(base, "POST", "/api/v1/auth/otp/request", {"phone": "+919876543210"})
    report.add(
        "BUG_01",
        "OTP request accepts +91 E.164",
        status in (200, 202),
        f"phone='+919876543210' -> {status} (want 202, E.164 is valid input)",
    )


def check_bug_02(base: str, report: Report) -> None:
    """Owner registration must reject an over-long phone number."""
    for phone in ("987654321011", "12345"):
        status, body = call(
            base,
            "POST",
            "/api/v1/owners/register",
            {"name": "Valid Name", "phone": phone, "email": f"qa.{uuid.uuid4().hex[:8]}@qa.kitchcu.in"},
        )
        report.add(
            "BUG_02",
            "Owner register rejects malformed phone",
            status == 422,
            f"phone={phone!r} -> {status} (want 422) {str(body)[:90]}",
        )


def check_bug_03(base: str, report: Report) -> None:
    """Owner registration must normalise the email to lowercase before storing."""
    local = f"QA.{uuid.uuid4().hex[:8]}"
    email = f"{local}@GMAIL.COM"
    status, body = call(
        base,
        "POST",
        "/api/v1/owners/register",
        {"name": "Case Test", "phone": unique_phone(), "email": email},
    )
    if status not in (200, 201):
        report.add("BUG_03", "Owner register lowercases email", False, f"setup failed -> {status} {str(body)[:120]}")
        return
    returned = str(body.get("email", ""))
    report.add(
        "BUG_03",
        "Owner register lowercases email",
        returned == email.lower(),
        f"sent {email!r} -> stored {returned!r} (want {email.lower()!r})",
    )


def check_bug_04(base: str, report: Report) -> None:
    """Owner registration must reject numeric / symbol-only names."""
    for name in ("123456", "125@", "Pooja123", "John@123", "   ", "<script>x</script>"):
        status, body = call(
            base,
            "POST",
            "/api/v1/owners/register",
            {"name": name, "phone": unique_phone(), "email": f"qa.{uuid.uuid4().hex[:8]}@qa.kitchcu.in"},
        )
        report.add(
            "BUG_04",
            "Owner register rejects invalid name",
            status == 422,
            f"name={name!r} -> {status} (want 422) {str(body)[:80]}",
        )
    # A legitimate name with punctuation must still be accepted.
    status, _ = call(
        base,
        "POST",
        "/api/v1/owners/register",
        {"name": "D'Souza Rao-Patil", "phone": unique_phone(), "email": f"qa.{uuid.uuid4().hex[:8]}@qa.kitchcu.in"},
    )
    report.add(
        "BUG_04",
        "Owner register accepts real punctuated name",
        status in (200, 201),
        f"name=\"D'Souza Rao-Patil\" -> {status} (want 201)",
    )


def wait_for_gateway(base: str, attempts: int = 30) -> bool:
    for _ in range(attempts):
        try:
            status, _ = call(base, "GET", "/health/ready")
            if status == 200:
                return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    if not wait_for_gateway(base):
        print(f"Gateway not ready at {base} — start the stack first.", file=sys.stderr)
        return 2

    report = Report()
    print("Validating API bugs from the QA issue tracker\n")
    for label, fn in (
        ("BUG_01 OTP request phone validation", check_bug_01),
        ("BUG_02 Owner register phone validation", check_bug_02),
        ("BUG_03 Owner register email normalisation", check_bug_03),
        ("BUG_04 Owner register name validation", check_bug_04),
    ):
        print(f"{label}")
        fn(base, report)
        print()

    total = len(report.results)
    failed = report.failed
    print(f"{total - len(failed)}/{total} checks passed")
    if failed:
        print("\nStill broken:")
        for r in failed:
            print(f"  {r.bug_id}: {r.detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
