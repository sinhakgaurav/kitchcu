#!/usr/bin/env python3
"""Full application E2E — smoke test + F19 integration + S16–S18 modules."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from demo_data import DEMO_OTP, DEMO_OWNER  # noqa: E402
from seed_common import ApiError, login_owner, request, wait_for_gateway  # noqa: E402


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_s16_s18(token: str, kitchen_id: str, customer_token: str) -> None:
    print("\nLearning (S16)")
    recipes = request("GET", "/api/v1/learning/recipes?limit=5")
    assert_ok(isinstance(recipes, dict) and "recipes" in recipes, "Learning recipes list failed")

    if recipes["recipes"]:
        learned = request(
            "POST",
            f"/api/v1/kitchens/{kitchen_id}/learning/learn",
            {"recipe_id": recipes["recipes"][0]["id"]},
            token=token,
        )
        assert_ok("trial_id" in learned or "id" in learned, "Learn recipe failed")
        print("  Trial dish created from curated recipe")
    else:
        print("  Skipping learn — no curated recipes seeded")

    trials = request("GET", f"/api/v1/kitchens/{kitchen_id}/learning/trials", token=token)
    assert_ok("trials" in trials, "List trials failed")
    print(f"  Trials: {len(trials.get('trials', []))}")

    print("\nCommunity (S17)")
    shared = request(
        "POST",
        f"/api/v1/kitchens/{kitchen_id}/community/recipes",
        {
            "title": "E2E Community Recipe",
            "summary": "Automated test",
            "recipe_html": "<p>Marinate overnight.</p>",
        },
        token=token,
    )
    assert_ok("id" in shared, "Share community recipe failed")
    recipe_id = shared["id"]

    appreciated = request(
        "POST",
        f"/api/v1/community/recipes/{recipe_id}/appreciate",
        token=customer_token,
    )
    assert_ok(appreciated.get("appreciation_count", 0) >= 1, "Appreciate recipe failed")

    rewards = request("GET", f"/api/v1/kitchens/{kitchen_id}/community/rewards", token=token)
    assert_ok(rewards.get("points_balance", 0) >= 10, "Reward points not credited")
    print(f"  Reward balance: {rewards['points_balance']} pts")

    rankings = request("GET", "/api/v1/community/rankings?scope=city&region_key=Pune")
    assert_ok("rankings" in rankings, "Chef rankings list failed")
    print(f"  City rankings: {rankings.get('total', 0)}")

    print("\nStreaming (S18)")
    settings = request("GET", f"/api/v1/kitchens/{kitchen_id}/stream/settings", token=token)
    assert_ok("live_sharing_enabled" in settings, "Stream settings failed")

    updated = request(
        "PATCH",
        f"/api/v1/kitchens/{kitchen_id}/stream/settings",
        {"live_sharing_enabled": True},
        token=token,
    )
    assert_ok(updated.get("live_sharing_enabled") is True, "Enable live sharing failed")

    live = request(
        "POST",
        f"/api/v1/kitchens/{kitchen_id}/stream/go-live",
        {"title": "E2E live prep"},
        token=token,
    )
    assert_ok(live.get("status") == "live", "Go live failed")
    session_id = live["id"]
    print(f"  Live session: {live['room_name']}")

    listed = request("GET", "/api/v1/stream/live-kitchens")
    assert_ok(listed.get("total", 0) >= 1, "Live kitchens list empty")
    assert_ok(any(k["kitchen_id"] == kitchen_id for k in listed["kitchens"]), "Kitchen not in live list")

    viewer = request(
        "POST",
        f"/api/v1/stream/sessions/{session_id}/viewer-token",
        token=customer_token,
    )
    assert_ok(viewer.get("room_name") == live["room_name"], "Viewer token failed")

    nearby_live = request(
        "GET",
        "/api/v1/kitchens/public/nearby?latitude=18.5362&longitude=73.8958&live_only=true&limit=10",
    )
    assert_ok(nearby_live.get("total", 0) >= 1, "live_only nearby filter empty")
    assert_ok(
        any(k.get("is_live_now") for k in nearby_live.get("kitchens", [])),
        "Nearby kitchen missing is_live_now",
    )
    print(f"  live_only nearby: {nearby_live['total']} kitchen(s)")

    ended = request("POST", f"/api/v1/kitchens/{kitchen_id}/stream/end", token=token)
    assert_ok(ended.get("status") == "ended", "End live failed")
    print("  Stream ended")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    print("kitchCU full E2E test")
    print("=" * 50)

    print("\n[1/3] Smoke test (core flows)")
    smoke = subprocess.run([sys.executable, str(root / "scripts" / "smoke-test.py")], cwd=root)
    if smoke.returncode != 0:
        raise SystemExit("Smoke test failed")

    print("\n[2/3] F19 integration (ingredients + orders)")
    integration = subprocess.run([sys.executable, str(root / "scripts" / "test-e2e-integration.py")], cwd=root)
    if integration.returncode != 0:
        raise SystemExit("Integration test failed")

    print("\n[3/3] S16–S18 modules")
    wait_for_gateway()
    token = login_owner(DEMO_OWNER["phone_e164"], DEMO_OTP)
    kitchens = request("GET", "/api/v1/kitchens/me", token=token)
    assert_ok(len(kitchens) > 0, "No kitchens for S16–S18")
    kitchen_id = kitchens[0]["id"]

    request("POST", "/api/v1/auth/customer/whatsapp/request", {"phone": "+919876543299"})
    cust = request(
        "POST",
        "/api/v1/auth/customer/whatsapp/verify",
        {"phone": "+919876543299", "otp": DEMO_OTP},
    )
    customer_token = cust["access_token"]

    run_s16_s18(token, kitchen_id, customer_token)

    print("\n" + "=" * 50)
    print("Full E2E test PASSED")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ApiError, SystemExit) as exc:
        print(f"\nFull E2E FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
