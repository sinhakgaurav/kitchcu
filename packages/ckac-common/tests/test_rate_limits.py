from ckac_common.rate_limits import (
    DEFAULT_RULES,
    TEST_PHASE_RULES,
    merge_rules,
    normalize_payload,
)
from ckac_common.rate_limits import test_phase_payload as build_test_phase_payload


def test_merge_rules_partial_override():
    merged = merge_rules({"otp_request": {"limit": 50, "window_seconds": 60}})
    assert merged["otp_request"]["limit"] == 50
    assert merged["otp_request"]["window_seconds"] == 60
    assert merged["default"] == DEFAULT_RULES["default"]


def test_merge_rules_ignores_invalid_and_unknown():
    merged = merge_rules(
        {
            "otp_request": {"limit": -1, "window_seconds": 60},
            "nope": {"limit": 1, "window_seconds": 1},
        }
    )
    assert merged["otp_request"]["limit"] == DEFAULT_RULES["otp_request"]["limit"]
    assert "nope" not in merged


def test_test_phase_preset_is_generous():
    payload = build_test_phase_payload()
    assert payload["enabled"] is True
    assert payload["rules"]["otp_request"]["limit"] >= TEST_PHASE_RULES["otp_request"]["limit"]
    assert payload["rules"]["otp_request"]["limit"] > DEFAULT_RULES["otp_request"]["limit"]


def test_normalize_can_disable():
    assert normalize_payload({"enabled": False})["enabled"] is False
