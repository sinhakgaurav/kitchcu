"""Customer authentication routes — social OAuth + WhatsApp OTP."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_schemas import (
    CustomerAuthResponse,
    CustomerPhoneRequest,
    CustomerPhoneVerifyRequest,
    CustomerResponse,
    OAuthCompleteRequest,
    OAuthStartResponse,
    clear_customer_otp_store,
    customer_auth_response,
    load_oauth_state,
    save_oauth_state,
    store_customer_otp,
    upsert_customer_from_oauth,
    upsert_customer_from_phone,
    validate_oauth_provider,
    verify_customer_otp,
)
from app.models import Customer
from app.oauth import exchange_oauth_code, start_oauth
from ckac_common.auth import stream_key
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_401, RESP_422

router = APIRouter()
security = HTTPBearer(auto_error=False)
settings = get_settings()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


def get_redis():
    from app.main import redis_client

    return redis_client


async def get_current_customer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Customer:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "customer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        customer_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    customer = await session.get(Customer, customer_id)
    if not customer or customer.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer not found")
    return customer


@router.get(
    "/auth/customer/oauth/providers",
    summary="List supported customer login providers",
    description=(
        "Returns the social OAuth providers and the WhatsApp OTP option available for "
        "customer login, for rendering the login screen.\n\n"
        "**Auth:** none — public endpoint."
    ),
    tags=["Customer Auth"],
)
async def list_oauth_providers() -> dict:
    return {
        "providers": [
            {"id": "google", "label": "Google"},
            {"id": "facebook", "label": "Facebook"},
            {"id": "instagram", "label": "Instagram"},
            {"id": "twitter", "label": "Twitter / X"},
            {"id": "whatsapp", "label": "WhatsApp", "method": "otp"},
        ]
    }


@router.get(
    "/auth/customer/oauth/{provider}/start",
    response_model=OAuthStartResponse,
    summary="Start a customer social OAuth login",
    description=(
        "Begins a social login flow for `provider` (google, facebook, instagram, twitter). "
        "Generates and stores CSRF `state` in Redis (10 min TTL) and returns the provider "
        "authorization URL to redirect the customer to.\n\n"
        "**Auth:** none — public endpoint.\n\n"
        "**400:** unsupported provider, or `provider` is `whatsapp` (use the WhatsApp OTP endpoints instead)."
    ),
    responses={400: RESP_400, 422: RESP_422},
    tags=["Customer Auth"],
)
async def oauth_start(
    provider: str,
    redirect_uri: str = Query(..., min_length=8, description="Where the provider should redirect after consent; must match the value sent in `/complete`.", examples=["https://customer.kitchcu.in/oauth/callback"]),
) -> OAuthStartResponse:
    try:
        normalized = validate_oauth_provider(provider)
        if normalized == "whatsapp":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use /auth/customer/whatsapp/request for WhatsApp login",
            )
        result = start_oauth(normalized, redirect_uri=redirect_uri)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    redis_client = get_redis()
    if redis_client:
        await save_oauth_state(
            redis_client,
            state=result.state,
            provider=normalized,
            redirect_uri=redirect_uri,
            code_verifier=result.code_verifier,
        )

    return OAuthStartResponse(
        provider=normalized,
        state=result.state,
        authorization_url=result.authorization_url,
        dev_mode=result.dev_mode,
    )


@router.post(
    "/auth/customer/oauth/{provider}/complete",
    response_model=CustomerAuthResponse,
    summary="Complete a customer social OAuth login",
    description=(
        "Exchanges the provider authorization `code` for a profile, validates the CSRF "
        "`state` + `redirect_uri` against what was stored in `/start`, then creates or "
        "updates the customer and links the OAuth identity.\n\n"
        "**Auth:** none — public endpoint (state token proves flow continuity).\n\n"
        "**Body:** code, state, redirect_uri (must match `/start`).\n\n"
        "**Response 200:** customer JWT (type=customer) + profile. Publishes `customer.created` "
        "on `ckac:identity:customer` for first-time sign-ups.\n\n"
        "**400:** unsupported/whatsapp provider, expired/invalid state, or redirect_uri mismatch."
    ),
    responses={400: RESP_400, 422: RESP_422},
    tags=["Customer Auth"],
)
async def oauth_complete(
    provider: str,
    body: OAuthCompleteRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> CustomerAuthResponse:
    try:
        normalized = validate_oauth_provider(provider)
        if normalized == "whatsapp":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use WhatsApp OTP endpoints")

        redis_client = get_redis()
        state_data = await load_oauth_state(redis_client, body.state) if redis_client else None
        if not state_data or state_data.get("provider") != normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
        if state_data.get("redirect_uri") != body.redirect_uri:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri mismatch")

        profile = await exchange_oauth_code(
            normalized,
            code=body.code,
            redirect_uri=body.redirect_uri,
            code_verifier=state_data.get("code_verifier"),
        )
        customer, created = await upsert_customer_from_oauth(session, normalized, profile)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if created:
        event = EventPublisher.build(
            event_type="customer.created",
            aggregate_type="customer",
            aggregate_id=str(customer.id),
            producer="identity-service",
            payload={
                "customer_id": str(customer.id),
                "provider": normalized,
                "email": customer.email,
            },
        )
        await publisher.publish(stream_key("identity", "customer"), event, session=session)

    return customer_auth_response(customer)


@router.post(
    "/auth/customer/whatsapp/request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request customer WhatsApp login OTP",
    description=(
        "Sends a one-time password to the customer's WhatsApp number to start login.\n\n"
        "**Body:** phone (10-digit India mobile or E.164).\n\n"
        "**Response 202:** confirmation message. In dev/staging the OTP is always `123456` "
        "— no real WhatsApp message is sent.\n\n"
        "Follow up with `POST /auth/customer/whatsapp/verify`."
    ),
    responses={422: RESP_422},
    tags=["Customer Auth"],
)
async def customer_whatsapp_request(body: CustomerPhoneRequest) -> dict[str, str]:
    store_customer_otp(body.phone)
    return {"message": "OTP sent via WhatsApp", "dev_hint": "Use 123456 in development"}


@router.post(
    "/auth/customer/whatsapp/verify",
    response_model=CustomerAuthResponse,
    summary="Verify customer WhatsApp OTP and issue JWT",
    description=(
        "Exchanges a WhatsApp OTP for a customer Bearer JWT. Creates the customer on "
        "first login (upsert-by-phone).\n\n"
        "**Body:** phone + otp (dev OTP is always 123456).\n\n"
        "**Response 200:** access_token (JWT type=customer), token_type=bearer, expires_in, "
        "and the customer profile. Publishes `customer.created` on `ckac:identity:customer` "
        "for first-time sign-ups.\n\n"
        "Use `Authorization: Bearer <access_token>` on subsequent customer APIs."
    ),
    responses={401: RESP_401, 422: RESP_422},
    tags=["Customer Auth"],
)
async def customer_whatsapp_verify(
    body: CustomerPhoneVerifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> CustomerAuthResponse:
    if not verify_customer_otp(body.phone, body.otp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    customer, created = await upsert_customer_from_phone(session, body.phone)
    if created:
        event = EventPublisher.build(
            event_type="customer.created",
            aggregate_type="customer",
            aggregate_id=str(customer.id),
            producer="identity-service",
            payload={"customer_id": str(customer.id), "provider": "whatsapp", "phone": body.phone},
        )
        await publisher.publish(stream_key("identity", "customer"), event, session=session)

    return customer_auth_response(customer)


@router.get(
    "/customers/me",
    response_model=CustomerResponse,
    summary="Get the authenticated customer's profile",
    description=(
        "Returns the profile of the customer identified by the Bearer JWT.\n\n"
        "**Auth:** customer JWT (`Authorization: Bearer <access_token>`, `type=customer`) required.\n\n"
        "**Response 200:** customer profile."
    ),
    responses={401: RESP_401, 422: RESP_422},
    tags=["Customer Auth"],
)
async def customer_me(customer: Annotated[Customer, Depends(get_current_customer)]) -> Customer:
    return customer
