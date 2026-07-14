"""Unit tests for OpenAPI merge (no live services)."""

from app.openapi_aggregate import merge_openapi_specs


def test_merge_openapi_specs_prefixes_schemas_and_tags():
    identity = {
        "openapi": "3.1.0",
        "paths": {
            "/api/v1/auth/otp/request": {
                "post": {
                    "tags": ["auth"],
                    "summary": "Request OTP",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/OtpOut"}
                                }
                            }
                        }
                    },
                }
            },
            "/health/live": {"get": {"responses": {"200": {}}}},
        },
        "components": {
            "schemas": {
                "OtpOut": {
                    "type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                }
            }
        },
    }
    catalog = {
        "openapi": "3.1.0",
        "paths": {
            "/api/v1/kitchens/{kitchen_id}/menu": {
                "get": {
                    "tags": ["menu"],
                    "summary": "Get menu",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {"schemas": {}},
    }

    merged = merge_openapi_specs([("identity", identity), ("catalog", catalog)])

    assert "/api/v1/auth/otp/request" in merged["paths"]
    assert "/api/v1/kitchens/{kitchen_id}/menu" in merged["paths"]
    assert "/health/live" not in merged["paths"]
    assert "identity_OtpOut" in merged["components"]["schemas"]
    ref = (
        merged["paths"]["/api/v1/auth/otp/request"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
    )
    assert ref == "#/components/schemas/identity_OtpOut"
    assert merged["paths"]["/api/v1/auth/otp/request"]["post"]["tags"] == [
        "Identity: auth"
    ]
    assert merged["info"]["title"] == "kitchCU Public API"
    assert "HTTPBearer" in merged["components"]["securitySchemes"]
