"""Tests for shared OpenAPI helpers."""

from ckac_common.openapi import ErrorDetail, RESP_401, auth_errors, error_response


def test_error_detail_schema_has_description():
    schema = ErrorDetail.model_json_schema()
    assert "detail" in schema["properties"]
    assert schema["properties"]["detail"]["description"]


def test_error_response_includes_example():
    resp = error_response("Nope", example_detail="Invalid OTP")
    assert resp["description"] == "Nope"
    assert resp["content"]["application/json"]["example"] == {"detail": "Invalid OTP"}


def test_auth_errors_flags():
    basic = auth_errors()
    assert 401 in basic and 422 in basic
    assert 403 not in basic
    full = auth_errors(include_403=True, include_404=True)
    assert 403 in full and 404 in full
    assert RESP_401["description"].startswith("Unauthorized")
