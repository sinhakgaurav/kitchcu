"""Shared OpenAPI helpers — standard error shapes and response docs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Standard FastAPI HTTPException body returned by all services."""

    detail: str = Field(
        ...,
        description="Human-readable error message (never include OTP, tokens, or full PII).",
        examples=["Invalid OTP", "Kitchen not found", "Not authenticated"],
    )


def error_response(description: str, *, example_detail: str | None = None) -> dict[str, Any]:
    """Build an OpenAPI response entry for FastAPI `responses=` maps."""
    content: dict[str, Any] = {"application/json": {"schema": ErrorDetail.model_json_schema()}}
    if example_detail is not None:
        content["application/json"]["example"] = {"detail": example_detail}
    return {"description": description, "content": content}


RESP_400 = error_response("Bad request — validation or business rule failure", example_detail="Invalid payload")
RESP_401 = error_response("Unauthorized — missing or invalid Bearer JWT / OTP", example_detail="Invalid token")
RESP_403 = error_response("Forbidden — caller does not own this kitchen/resource", example_detail="Not kitchen owner")
RESP_404 = error_response("Not found", example_detail="Kitchen not found")
RESP_409 = error_response("Conflict — duplicate or invalid state transition", example_detail="Owner with this phone already exists")
RESP_422 = error_response("Validation error — Pydantic rejected the body/query", example_detail="Field required")


def auth_errors(*, include_403: bool = False, include_404: bool = False) -> dict[int | str, dict[str, Any]]:
    """Common protected-route error responses."""
    out: dict[int | str, dict[str, Any]] = {401: RESP_401, 422: RESP_422}
    if include_403:
        out[403] = RESP_403
    if include_404:
        out[404] = RESP_404
    return out
