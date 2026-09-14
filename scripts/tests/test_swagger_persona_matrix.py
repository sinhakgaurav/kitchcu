import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import swagger_persona_matrix as matrix


def test_classify_admin_and_customer_and_public():
    assert matrix.classify("/api/v1/admin/kitchens", {"security": [{"HTTPBearer": []}]}) == "admin"
    assert (
        matrix.classify("/api/v1/customers/me", {"security": [{"HTTPBearer": []}]}) == "customer"
    )
    assert matrix.classify("/api/v1/billing/payments/customer", {"security": [{"HTTPBearer": []}]}) == "customer"
    assert (
        matrix.classify(
            "/api/v1/kitchens/{kitchen_id}/growth/suggestions",
            {"security": [{"HTTPBearer": []}]},
        )
        == "owner"
    )
    assert (
        matrix.classify(
            "/api/v1/kitchens/{kitchen_id}/orders/customer",
            {"security": [{"HTTPBearer": []}]},
        )
        == "customer"
    )
    assert matrix.classify("/api/v1/auth/otp/request", {"security": []}) == "public"


def test_judge_wrong_persona_is_fail_unless_admin_override():
    assert matrix.judge("owner", "owner", 200) == "PASS"
    assert matrix.judge("owner", "owner", 403) == "PASS"
    assert matrix.judge("owner", "customer", 401) == "PASS"
    assert matrix.judge("owner", "customer", 200) == "FAIL"
    assert matrix.judge("owner", "admin", 200) == "INFO"
    assert matrix.judge("owner", "owner", 500) == "FAIL"
    assert matrix.judge("public", "anon", 202) == "PASS"
    assert matrix.judge("internal", "anon", 404) == "PASS"
