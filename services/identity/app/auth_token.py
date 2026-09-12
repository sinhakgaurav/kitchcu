"""OAuth2 password token helper for Swagger Authorize."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Owner, PlatformAdmin
from app.schemas import OTPVerifyRequest, create_access_token
from ckac_common.database import get_db
from ckac_common.openapi import RESP_401, RESP_422
from ckac_common.platform_config import allows_fixed_dev_otp, get_demo_otp

router = APIRouter()


def _oauth_error(status_code: int, error: str, description: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "error_description": description, "detail": description},
    )


def _token_body(token: object) -> dict[str, object]:
    return {
        "access_token": getattr(token, "access_token"),
        "token_type": getattr(token, "token_type", "bearer"),
        "expires_in": getattr(token, "expires_in"),
    }


async def _admin_token(session: AsyncSession, email: str, password: str) -> JSONResponse:
    from app.admin_routes import create_admin_token, ensure_default_admin, verify_password

    await ensure_default_admin(session)
    await session.commit()
    result = await session.execute(
        select(PlatformAdmin).where(
            PlatformAdmin.email == email.lower(),
            PlatformAdmin.is_active.is_(True),
        )
    )
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(password, admin.password_hash):
        return _oauth_error(status.HTTP_401_UNAUTHORIZED, "invalid_grant", "Invalid credentials")
    issued = create_admin_token(admin.id, admin.email)
    return JSONResponse(_token_body(issued))


async def _owner_otp_ok(phone: str, otp: str) -> bool:
    if allows_fixed_dev_otp():
        from app.routes import _DEV_OTP

        expected = _DEV_OTP.get(phone)
        return bool(expected and expected == otp) or otp == get_demo_otp()
    from app.main import redis_client
    from app.otp_delivery import OWNER_OTP_PREFIX

    if not redis_client:
        return False
    key = f"{OWNER_OTP_PREFIX}{phone}"
    expected = await redis_client.get(key)
    if expected and expected == otp:
        await redis_client.delete(key)
        return True
    return False


async def _customer_otp_ok(phone: str, otp: str) -> bool:
    if allows_fixed_dev_otp():
        from app.customer_schemas import verify_customer_otp

        return verify_customer_otp(phone, otp) or otp == get_demo_otp()
    from app.main import redis_client
    from app.otp_delivery import CUSTOMER_OTP_PREFIX

    if not redis_client:
        return False
    key = f"{CUSTOMER_OTP_PREFIX}{phone}"
    expected = await redis_client.get(key)
    if expected and expected == otp:
        await redis_client.delete(key)
        return True
    return False


@router.post(
    "/auth/token",
    summary="OAuth2 password token (Swagger Authorize)",
    description=(
        "**Auth:** none — this is the Swagger / OAuth2 password token endpoint.\n\n"
        "Form fields: `username`, `password`, optional `grant_type`.\n"
        "- Admin: username is the admin email, password is `ADMIN_PASSWORD`.\n"
        "- Owner / customer: username is the phone, password is the OTP "
        "(local demo `123456`). Does not create a new customer.\n\n"
        "**Response 200:** `access_token`, `token_type=bearer`, `expires_in`."
    ),
    responses={401: RESP_401, 422: RESP_422},
    tags=["Auth"],
)
async def issue_oauth_password_token(
    session: Annotated[AsyncSession, Depends(get_db)],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    grant_type: Annotated[str, Form()] = "password",
    scope: Annotated[str, Form()] = "",
    client_id: Annotated[str, Form()] = "",
) -> JSONResponse:
    del grant_type, scope, client_id
    raw = (username or "").strip()
    secret = (password or "").strip()
    if not raw or not secret:
        return _oauth_error(status.HTTP_401_UNAUTHORIZED, "invalid_request", "username and password are required")

    if "@" in raw:
        return await _admin_token(session, raw, secret)

    try:
        body = OTPVerifyRequest(phone=raw, otp=secret)
    except ValidationError:
        return _oauth_error(status.HTTP_401_UNAUTHORIZED, "invalid_grant", "Invalid credentials")

    owner = (
        await session.execute(select(Owner).where(Owner.phone == body.phone))
    ).scalar_one_or_none()
    if owner:
        if not await _owner_otp_ok(body.phone, body.otp):
            return _oauth_error(status.HTTP_401_UNAUTHORIZED, "invalid_grant", "Invalid OTP")
        return JSONResponse(_token_body(create_access_token(owner.id, owner.phone)))

    customer = (
        await session.execute(select(Customer).where(Customer.phone == body.phone))
    ).scalar_one_or_none()
    if customer:
        if not await _customer_otp_ok(body.phone, body.otp):
            return _oauth_error(status.HTTP_401_UNAUTHORIZED, "invalid_grant", "Invalid OTP")
        from app.customer_schemas import create_customer_access_token

        token, expires_in = create_customer_access_token(customer.id)
        return JSONResponse(
            {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": expires_in,
            }
        )

    return _oauth_error(status.HTTP_401_UNAUTHORIZED, "invalid_grant", "Invalid credentials")
