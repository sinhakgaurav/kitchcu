"""Platform admin API — full control over owners, kitchens, orders."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import bindparam, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    CustomerAddress,
    FeatureFlag,
    Kitchen,
    Owner,
    PlatformAdmin,
    PlatformApiKey,
)
from app.routes import get_publisher
from app.schemas import (
    KitchenDeliverySettingsUpdate,
    KitchenWhatsAppIntegrationResponse,
    KitchenWhatsAppIntegrationUpdate,
    kitchen_whatsapp_to_response,
    update_kitchen_delivery_settings,
    update_kitchen_whatsapp_integration,
)
from ckac_common.secret_box import decrypt_secret, encrypt_secret, mask_secret
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_401, RESP_422, auth_errors

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


async def _payment_gateway_kitchen_ids(
    session: AsyncSession,
    kitchen_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    """Cross-schema read — which kitchens have Razorpay kitchen credentials configured."""
    if not kitchen_ids:
        return set()
    stmt = text(
        """
        SELECT kitchen_id
        FROM ckac_billing.kitchen_payment_gateways
        WHERE kitchen_id IN :ids
          AND provider = 'razorpay'
          AND (
            NULLIF(TRIM(COALESCE(key_id, '')), '') IS NOT NULL
            OR key_secret_enc IS NOT NULL
            OR NULLIF(TRIM(COALESCE(linked_account_id, '')), '') IS NOT NULL
          )
        """
    ).bindparams(bindparam("ids", expanding=True))
    rows = (await session.execute(stmt, {"ids": list(kitchen_ids)})).scalars().all()
    return {uuid.UUID(str(r)) for r in rows}


def _mask_account(account: str | None) -> str | None:
    if not account:
        return None
    digits = "".join(c for c in account if c.isdigit())
    if len(digits) <= 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


class AdminLoginRequest(BaseModel):
    """Body for `POST /admin/auth/login` — platform admin login."""

    email: EmailStr = Field(..., description="Platform admin email.", examples=["admin@kitchcu.dev"])
    password: str = Field(..., min_length=6, description="Platform admin password.", examples=["admin123456"])


class AdminTokenResponse(BaseModel):
    """Bearer token issued after successful admin login.

    `access_token` is a JWT with `type: "admin"` and `sub` set to the admin UUID.
    """

    access_token: str = Field(
        ...,
        description='JWT bearer token, payload `{"sub": "<admin_id>", "email": "...", "type": "admin", "exp": ...}`.',
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(default="bearer", description="Always `bearer`.", examples=["bearer"])
    expires_in: int = Field(..., description="Token lifetime in seconds from issuance.", examples=[3600])


class AdminLoginHintResponse(BaseModel):
    """Public bootstrap hint for the admin login form.

    Password is only included when bring-up reveal is allowed
    (``APP_ENV`` development/test, or ``ADMIN_LOGIN_REVEAL_PASSWORD=1``).
    """

    email: str = Field(..., description="Expected admin login email from ADMIN_EMAIL.")
    password: str | None = Field(
        default=None,
        description="ADMIN_PASSWORD when reveal is enabled; otherwise null.",
    )
    revealed: bool = Field(
        ...,
        description="True when password is included in this response.",
    )
    source: str = Field(
        default="env",
        description="Where credentials come from (env / metadata via startup).",
    )


class AdminProfile(BaseModel):
    """Platform admin profile returned by `GET /admin/me`."""

    id: uuid.UUID = Field(..., description="Admin UUID primary key.")
    email: str = Field(..., description="Admin login email.", examples=["admin@kitchcu.dev"])
    name: str = Field(..., description="Admin display name.", examples=["kitchCU Platform Admin"])
    role: str = Field(..., description="Admin role.", examples=["superadmin"])
    permissions: list[str] = Field(
        default_factory=list,
        description="Permission codes for this role (`*` = superadmin).",
    )
    allowed_tabs: list[str] = Field(
        default_factory=list,
        description="Admin UI tabs this role may open.",
    )

    model_config = {"from_attributes": True}


class PlatformStats(BaseModel):
    """Aggregate platform counters returned by `GET /admin/stats`."""

    owners: int = Field(..., description="Total registered owners.", examples=[42])
    kitchens: int = Field(..., description="Total kitchens across all owners.", examples=[57])
    active_kitchens: int = Field(..., description="Kitchens with status=active.", examples=[49])
    orders: int = Field(..., description="Total orders placed platform-wide.", examples=[1830])
    dishes: int = Field(..., description="Total active dishes across all catalogs.", examples=[612])
    customers: int = Field(default=0, description="Registered customers.")
    refunds_open: int = Field(default=0, description="Refunds in requested/processing.")
    refunds_completed: int = Field(default=0, description="Completed refunds.")
    tickets_open: int = Field(default=0, description="Open support tickets.")
    payments_captured: int = Field(default=0, description="Captured payments.")


class AdminCustomerRow(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    email: str | None
    status: str
    has_password: bool
    has_payout: bool
    address_count: int
    created_at: datetime


class AdminCustomerDetail(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    email: str | None
    status: str
    has_password: bool
    upi_vpa: str | None
    upi_qr_url: str | None
    bank_account_number_masked: str | None
    bank_ifsc: str | None
    bank_account_name: str | None
    addresses: list[dict]
    created_at: datetime


class CustomerStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")


class OwnerSubscriptionUpdate(BaseModel):
    subscription_tier: str | None = Field(default=None, pattern="^(starter|growth|pro|trial)$")
    subscription_status: str | None = Field(
        default=None, pattern="^(trial|active|past_due|cancelled)$"
    )


class FeatureFlagRow(BaseModel):
    key: str
    enabled: bool
    scope: str
    description: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeatureFlagUpdate(BaseModel):
    enabled: bool


class PlatformApiKeyRow(BaseModel):
    key: str
    category: str
    description: str | None
    is_secret: bool
    configured: bool
    value_masked: str | None
    updated_at: datetime
    updated_by: str | None


class PlatformApiKeyUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=4000)


class JourneyMap(BaseModel):
    """Application data-journey control map for super admin."""

    stages: list[dict]


def _api_key_row(row: PlatformApiKey) -> PlatformApiKeyRow:
    plain = decrypt_secret(row.value_enc)
    configured = bool(plain)
    if not configured:
        masked = None
    elif row.is_secret:
        masked = mask_secret(plain)
    else:
        # Non-secret public-ish keys (Maps, OAuth client id) still masked lightly
        masked = plain if len(plain) <= 48 else mask_secret(plain, keep=8)
    return PlatformApiKeyRow(
        key=row.key,
        category=row.category,
        description=row.description,
        is_secret=row.is_secret,
        configured=configured,
        value_masked=masked,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


class AdminOwnerRow(BaseModel):
    """A single owner row in `GET /admin/owners`."""

    id: uuid.UUID = Field(..., description="Owner UUID primary key.")
    name: str = Field(..., description="Owner display name.", examples=["Priya Sharma"])
    phone: str = Field(..., description="Owner phone (E.164).", examples=["+919876543210"])
    email: str | None = Field(default=None, description="Owner email, if provided.")
    subscription_tier: str = Field(..., description="Subscription plan tier.", examples=["trial"])
    subscription_status: str = Field(..., description="Subscription lifecycle status.", examples=["trial", "active"])
    kitchen_count: int = Field(..., description="Number of kitchens owned by this owner.", examples=[1])


class AdminKitchenRow(BaseModel):
    """A single kitchen row in `GET /admin/kitchens`."""

    id: uuid.UUID = Field(..., description="Kitchen UUID primary key.")
    code: str = Field(..., description="Unique kitchen code.", examples=["CKPNQ001"])
    name: str = Field(..., description="Kitchen brand name.", examples=["Spice Route Kitchen"])
    city: str | None = Field(default=None, description="Kitchen city.", examples=["Pune"])
    status: str = Field(..., description="Kitchen lifecycle status.", examples=["active", "suspended", "pending_verification"])
    owner_name: str = Field(..., description="Name of the owning owner.", examples=["Priya Sharma"])
    owner_phone: str = Field(..., description="Phone of the owning owner.", examples=["+919876543210"])
    whatsapp_connected: bool = Field(
        default=False,
        description="True when this kitchen has a Meta WhatsApp phone_number_id linked.",
    )
    payment_gateway_configured: bool = Field(
        default=False,
        description="True when Razorpay kitchen credentials / linked account exist in billing.",
    )


class AdminKitchenDetail(AdminKitchenRow):
    """Kitchen workspace for super-admin ops — profile + WhatsApp travel with the kitchen."""

    owner_id: uuid.UUID = Field(..., description="Owning owner UUID.")
    address_line: str | None = Field(default=None, description="Street address, if set.")
    state: str | None = Field(default=None, description="State / region.")
    pincode: str | None = Field(default=None, description="PIN code.")
    whatsapp_phone_id: str | None = Field(default=None, description="Meta phone_number_id, if linked.")
    whatsapp_display_phone: str | None = Field(default=None, description="E.164 display number, if set.")
    porter_auto_book_enabled: bool = Field(
        default=True,
        description="When true (and module entitled), Porter is auto-booked after accept delay.",
    )
    porter_auto_book_delay_min: int = Field(
        default=15,
        description="Minutes after accept before first Porter auto-book attempt.",
    )
    platform_secrets_note: str = Field(
        default=(
            "Meta App Secret / Verify Token and platform Razorpay (SaaS) live under Super Admin → API Keys. "
            "Kitchen WhatsApp phone ID and kitchen Razorpay keys travel with this kitchen."
        ),
    )


def _admin_kitchen_row(
    kitchen: Kitchen,
    owner: Owner,
    *,
    payment_gateway_configured: bool = False,
) -> AdminKitchenRow:
    return AdminKitchenRow(
        id=kitchen.id,
        code=kitchen.code,
        name=kitchen.name,
        city=kitchen.city,
        status=kitchen.status,
        owner_name=owner.name,
        owner_phone=owner.phone,
        whatsapp_connected=bool(kitchen.whatsapp_phone_id),
        payment_gateway_configured=payment_gateway_configured,
    )


class AdminOrderRow(BaseModel):
    """A single order row in `GET /admin/orders`."""

    id: uuid.UUID = Field(..., description="Order UUID primary key.")
    order_code: str = Field(..., description="Human-readable order code.", examples=["CKPNQ001-BILL-20260712-0042"])
    kitchen_id: uuid.UUID = Field(..., description="UUID of the fulfilling kitchen.")
    kitchen_name: str = Field(..., description="Name of the fulfilling kitchen.", examples=["Spice Route Kitchen"])
    status: str = Field(..., description="Order lifecycle status.", examples=["delivered"])
    total: float = Field(..., description="Order total in INR.", examples=[349.0])
    customer_name: str | None = Field(default=None, description="Customer name captured on the order, if any.")
    created_at: datetime = Field(..., description="Order creation timestamp (UTC).")


class KitchenStatusUpdate(BaseModel):
    """Body for `PATCH /admin/kitchens/{kitchen_id}/status` — platform moderation action."""

    status: str = Field(
        ...,
        pattern="^(active|suspended|pending_verification)$",
        description="New kitchen lifecycle status.",
        examples=["suspended"],
    )


def create_admin_token(admin_id: uuid.UUID, email: str) -> AdminTokenResponse:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {"sub": str(admin_id), "email": email, "type": "admin", "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return AdminTokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformAdmin:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        admin_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    result = await session.execute(
        select(PlatformAdmin).where(PlatformAdmin.id == admin_id, PlatformAdmin.is_active.is_(True))
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin


async def ensure_default_admin(session: AsyncSession) -> None:
    """Bootstrap / sync the platform admin from ADMIN_EMAIL + ADMIN_PASSWORD.

    Password is kept aligned with env on every login bootstrap call so GCP metadata
    rotations and fresh resets do not leave a stale hash (common cause of
    'Invalid credentials' on admin.kitchcu.com).
    """
    email = settings.admin_email.lower().strip()
    result = await session.execute(select(PlatformAdmin).where(PlatformAdmin.email == email))
    admin = result.scalar_one_or_none()
    if admin is None:
        session.add(
            PlatformAdmin(
                email=email,
                password_hash=hash_password(settings.admin_password),
                name="kitchCU Platform Admin",
                role="superadmin",
                is_active=True,
            )
        )
        await session.flush()
        return

    admin.is_active = True
    if not verify_password(settings.admin_password, admin.password_hash):
        admin.password_hash = hash_password(settings.admin_password)
    await session.flush()


def _admin_login_reveal_allowed() -> bool:
    """Allow showing ADMIN_PASSWORD on the login form during bring-up only."""
    import os

    from ckac_common.platform_config import is_non_production

    raw = os.environ.get("ADMIN_LOGIN_REVEAL_PASSWORD", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    return is_non_production()


@router.get(
    "/auth/login-hint",
    response_model=AdminLoginHintResponse,
    summary="Admin login credential hint (bring-up)",
    description=(
        "Returns the expected admin email. Includes plaintext `ADMIN_PASSWORD` only when "
        "`APP_ENV` is development/test (GCP demo-mode / run-seed) or "
        "`ADMIN_LOGIN_REVEAL_PASSWORD=1`. Never enabled for hard production without that flag."
    ),
    tags=["Admin"],
)
async def admin_login_hint() -> AdminLoginHintResponse:
    email = settings.admin_email.lower().strip()
    if _admin_login_reveal_allowed():
        return AdminLoginHintResponse(
            email=email,
            password=settings.admin_password,
            revealed=True,
            source="ADMIN_EMAIL/ADMIN_PASSWORD",
        )
    return AdminLoginHintResponse(
        email=email,
        password=None,
        revealed=False,
        source="ADMIN_EMAIL/ADMIN_PASSWORD",
    )


@router.post(
    "/auth/login",
    response_model=AdminTokenResponse,
    summary="Platform admin login",
    description=(
        "Authenticates a platform admin by email/password and issues an admin Bearer JWT. "
        "Bootstraps the default admin account (from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars) "
        "on first call if it does not yet exist.\n\n"
        "**Auth:** none — this is the admin login entry point.\n\n"
        "**Response 200:** access_token (JWT type=admin), token_type=bearer, expires_in.\n\n"
        "Use `Authorization: Bearer <access_token>` on subsequent `/admin/*` APIs."
    ),
    responses={401: RESP_401, 422: RESP_422},
    tags=["Admin"],
)
async def admin_login(body: AdminLoginRequest, session: Annotated[AsyncSession, Depends(get_db)]) -> AdminTokenResponse:
    await ensure_default_admin(session)
    await session.commit()
    result = await session.execute(
        select(PlatformAdmin).where(
            PlatformAdmin.email == body.email.lower(),
            PlatformAdmin.is_active.is_(True),
        )
    )
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_admin_token(admin.id, admin.email)


@router.get(
    "/me",
    response_model=AdminProfile,
    summary="Get the authenticated admin's profile",
    description=(
        "Returns the profile of the platform admin identified by the Bearer JWT.\n\n"
        "**Auth:** admin JWT (`type=admin`) required — platform scope only, no owner/customer JWTs accepted."
    ),
    responses=auth_errors(),
    tags=["Admin"],
)
async def admin_me(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminProfile:
    from app.rbac import load_permissions_for_role, tabs_for_permissions

    grants = await load_permissions_for_role(session, admin.role)
    return AdminProfile(
        id=admin.id,
        email=admin.email,
        name=admin.name,
        role=admin.role,
        permissions=sorted(grants),
        allowed_tabs=tabs_for_permissions(grants),
    )


@router.get(
    "/audit-events",
    summary="List platform admin audit events",
    description="Append-only audit trail for high-value admin mutations. Requires `audit:read`.",
    responses=auth_errors(),
    tags=["Admin"],
)
async def admin_audit_events_list(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
    actor_email: str | None = None,
    resource_type: str | None = None,
    kitchen_id: uuid.UUID | None = None,
):
    from app.admin_audit import list_admin_audit_events
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="audit:read")
    return await list_admin_audit_events(
        session,
        limit=limit,
        offset=offset,
        actor_email=actor_email,
        resource_type=resource_type,
        kitchen_id=kitchen_id,
    )


@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Get platform-wide aggregate counters",
    description=(
        "Returns owner/kitchen/order/dish counts across the entire platform, for the admin "
        "overview dashboard.\n\n"
        "**Auth:** admin JWT required."
    ),
    responses=auth_errors(),
    tags=["Admin"],
)
async def admin_stats(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformStats:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:read")
    _ = admin
    owners = (await session.execute(select(func.count()).select_from(Owner))).scalar_one()
    kitchens = (await session.execute(select(func.count()).select_from(Kitchen))).scalar_one()
    active = (
        await session.execute(select(func.count()).select_from(Kitchen).where(Kitchen.status == "active"))
    ).scalar_one()
    orders = (
        await session.execute(text("SELECT COUNT(*) FROM ckac_orders.orders"))
    ).scalar_one()
    dishes = (
        await session.execute(text("SELECT COUNT(*) FROM ckac_catalog.dishes WHERE is_active = true"))
    ).scalar_one()
    customers = (await session.execute(select(func.count()).select_from(Customer))).scalar_one()
    extra = (
        await session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM ckac_billing.refunds WHERE status IN ('requested','processing')) AS refunds_open,
                  (SELECT COUNT(*) FROM ckac_billing.refunds WHERE status = 'completed') AS refunds_completed,
                  (SELECT COUNT(*) FROM ckac_support.support_tickets WHERE status IN ('open','in_progress','waiting_customer')) AS tickets_open,
                  (SELECT COUNT(*) FROM ckac_billing.payments WHERE status = 'captured') AS payments_captured
                """
            )
        )
    ).mappings().one()
    return PlatformStats(
        owners=owners,
        kitchens=kitchens,
        active_kitchens=active,
        orders=orders,
        dishes=dishes,
        customers=customers,
        refunds_open=int(extra["refunds_open"] or 0),
        refunds_completed=int(extra["refunds_completed"] or 0),
        tickets_open=int(extra["tickets_open"] or 0),
        payments_captured=int(extra["payments_captured"] or 0),
    )


@router.get(
    "/owners",
    response_model=list[AdminOwnerRow],
    summary="List owners (platform admin)",
    description=(
        "Returns up to 200 most-recently-created owners with their kitchen counts, for the "
        "admin owners table.\n\n"
        "**Auth:** admin JWT required."
    ),
    responses=auth_errors(),
    tags=["Admin"],
)
async def admin_owners(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminOwnerRow]:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="owners:write")
    _ = admin
    result = await session.execute(select(Owner).order_by(Owner.created_at.desc()).limit(200))
    owners = list(result.scalars().all())
    rows: list[AdminOwnerRow] = []
    for o in owners:
        kc = (
            await session.execute(select(func.count()).select_from(Kitchen).where(Kitchen.owner_id == o.id))
        ).scalar_one()
        rows.append(
            AdminOwnerRow(
                id=o.id,
                name=o.name,
                phone=o.phone,
                email=o.email,
                subscription_tier=o.subscription_tier,
                subscription_status=o.subscription_status,
                kitchen_count=kc,
            )
        )
    return rows


@router.get(
    "/kitchens",
    response_model=list[AdminKitchenRow],
    summary="List kitchens (platform admin)",
    description=(
        "Returns up to 300 most-recently-created kitchens with owner details, for the "
        "admin kitchens table.\n\n"
        "**Auth:** admin JWT required."
    ),
    responses=auth_errors(),
    tags=["Admin"],
)
async def admin_kitchens(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminKitchenRow]:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:read")
    _ = admin
    result = await session.execute(
        select(Kitchen, Owner)
        .join(Owner, Owner.id == Kitchen.owner_id)
        .order_by(Kitchen.created_at.desc())
        .limit(300)
    )
    pairs = list(result.all())
    gateway_ids = await _payment_gateway_kitchen_ids(session, [k.id for k, _ in pairs])
    return [
        _admin_kitchen_row(k, o, payment_gateway_configured=k.id in gateway_ids)
        for k, o in pairs
    ]


@router.get(
    "/kitchens/{kitchen_id}",
    response_model=AdminKitchenDetail,
    summary="Kitchen workspace detail (super admin)",
    description=(
        "Ops workspace for one kitchen — profile, WhatsApp linkage flags, and payment-gateway "
        "configured flag. Kitchen Razorpay CRUD is on billing "
        "`/admin/kitchens/{id}/payment-gateway`. Platform Meta/Razorpay SaaS secrets stay under "
        "`/admin/api-keys`.\n\n"
        "**Auth:** admin JWT required."
    ),
    responses=auth_errors(include_404=True),
    tags=["Admin"],
)
async def admin_kitchen_detail(
    kitchen_id: uuid.UUID,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminKitchenDetail:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:read")
    _ = admin
    result = await session.execute(
        select(Kitchen, Owner)
        .join(Owner, Owner.id == Kitchen.owner_id)
        .where(Kitchen.id == kitchen_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    kitchen, owner = row
    wa = kitchen_whatsapp_to_response(kitchen)
    gateway_ids = await _payment_gateway_kitchen_ids(session, [kitchen.id])
    base = _admin_kitchen_row(kitchen, owner, payment_gateway_configured=kitchen.id in gateway_ids)
    return AdminKitchenDetail(
        **base.model_dump(),
        owner_id=owner.id,
        address_line=kitchen.address_line,
        state=kitchen.state,
        pincode=kitchen.pincode,
        whatsapp_phone_id=wa.whatsapp_phone_id,
        whatsapp_display_phone=wa.whatsapp_display_phone,
        porter_auto_book_enabled=bool(getattr(kitchen, "porter_auto_book_enabled", True)),
        porter_auto_book_delay_min=int(getattr(kitchen, "porter_auto_book_delay_min", 15) or 15),
    )


@router.patch(
    "/kitchens/{kitchen_id}/delivery-settings",
    response_model=AdminKitchenDetail,
    summary="Update kitchen delivery / Porter auto-book settings (super admin)",
    responses=auth_errors(include_404=True),
    tags=["Admin"],
)
async def admin_kitchen_delivery_settings(
    kitchen_id: uuid.UUID,
    body: KitchenDeliverySettingsUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminKitchenDetail:
    from app.admin_audit import record_admin_audit
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:write")
    result = await session.execute(
        select(Kitchen, Owner)
        .join(Owner, Owner.id == Kitchen.owner_id)
        .where(Kitchen.id == kitchen_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    kitchen, owner = row
    try:
        kitchen = await update_kitchen_delivery_settings(session, kitchen, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await record_admin_audit(
        session,
        actor=admin,
        action="kitchen.delivery_settings.update",
        resource_type="kitchen",
        resource_id=str(kitchen_id),
        kitchen_id=kitchen_id,
        summary=f"{kitchen.code} delivery settings updated",
        after={
            "porter_auto_book_enabled": bool(getattr(kitchen, "porter_auto_book_enabled", True)),
            "porter_auto_book_delay_min": int(getattr(kitchen, "porter_auto_book_delay_min", 15) or 15),
        },
    )
    await session.commit()
    await session.refresh(kitchen)

    wa = kitchen_whatsapp_to_response(kitchen)
    gateway_ids = await _payment_gateway_kitchen_ids(session, [kitchen.id])
    base = _admin_kitchen_row(kitchen, owner, payment_gateway_configured=kitchen.id in gateway_ids)
    return AdminKitchenDetail(
        **base.model_dump(),
        owner_id=owner.id,
        address_line=kitchen.address_line,
        state=kitchen.state,
        pincode=kitchen.pincode,
        whatsapp_phone_id=wa.whatsapp_phone_id,
        whatsapp_display_phone=wa.whatsapp_display_phone,
        porter_auto_book_enabled=bool(getattr(kitchen, "porter_auto_book_enabled", True)),
        porter_auto_book_delay_min=int(getattr(kitchen, "porter_auto_book_delay_min", 15) or 15),
    )


@router.get(
    "/kitchens/{kitchen_id}/whatsapp-integration",
    response_model=KitchenWhatsAppIntegrationResponse,
    summary="Get kitchen WhatsApp Business linkage (super admin)",
    responses=auth_errors(include_404=True),
    tags=["Admin"],
)
async def admin_kitchen_whatsapp_get(
    kitchen_id: uuid.UUID,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenWhatsAppIntegrationResponse:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:read")
    _ = admin
    kitchen = await session.get(Kitchen, kitchen_id)
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    return kitchen_whatsapp_to_response(kitchen)


@router.put(
    "/kitchens/{kitchen_id}/whatsapp-integration",
    response_model=KitchenWhatsAppIntegrationResponse,
    summary="Upsert / clear kitchen WhatsApp Business linkage (super admin)",
    description=(
        "Connect or disconnect Meta `phone_number_id` for this kitchen (onboarding support). "
        "Does not store App Secret / Verify Token — those are platform API keys. "
        "Publishes `kitchen.whatsapp.updated`. Bypasses kitchen module kill-switch so ops can "
        "pre-configure before enabling the WhatsApp module."
    ),
    responses=auth_errors(include_404=True),
    tags=["Admin"],
)
async def admin_kitchen_whatsapp_put(
    kitchen_id: uuid.UUID,
    body: KitchenWhatsAppIntegrationUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> KitchenWhatsAppIntegrationResponse:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:write")
    kitchen = await session.get(Kitchen, kitchen_id)
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    try:
        result = await update_kitchen_whatsapp_integration(
            session,
            kitchen,
            body,
            publisher,
            enforce_module=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="kitchen.whatsapp.updated",
        resource_type="kitchen",
        resource_id=str(kitchen_id),
        kitchen_id=kitchen_id,
        summary=f"WhatsApp integration updated for {kitchen.code}",
        after={"configured": bool(result.connected)},
    )
    await session.commit()
    return result


@router.patch(
    "/kitchens/{kitchen_id}/status",
    response_model=AdminKitchenRow,
    summary="Update a kitchen's status (platform moderation)",
    description=(
        "Platform-level moderation action to set a kitchen's lifecycle status "
        "(`active`, `suspended`, `pending_verification`) — e.g. suspending a kitchen for "
        "policy violations.\n\n"
        "**Auth:** admin JWT required.\n\n"
        "**404:** kitchen does not exist."
    ),
    responses=auth_errors(include_404=True),
    tags=["Admin"],
)
async def admin_kitchen_status(
    kitchen_id: uuid.UUID,
    body: KitchenStatusUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminKitchenRow:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:write")
    result = await session.execute(
        select(Kitchen, Owner)
        .join(Owner, Owner.id == Kitchen.owner_id)
        .where(Kitchen.id == kitchen_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    kitchen, owner = row
    before_status = kitchen.status
    kitchen.status = body.status
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="kitchen.status.updated",
        resource_type="kitchen",
        resource_id=str(kitchen_id),
        kitchen_id=kitchen_id,
        summary=f"Kitchen {kitchen.code} status {before_status} → {body.status}",
        before={"status": before_status},
        after={"status": body.status},
    )
    await session.commit()
    gateway_ids = await _payment_gateway_kitchen_ids(session, [kitchen.id])
    return _admin_kitchen_row(
        kitchen, owner, payment_gateway_configured=kitchen.id in gateway_ids
    )


@router.get(
    "/orders",
    response_model=list[AdminOrderRow],
    summary="List orders (platform admin)",
    description=(
        "Returns the most recent orders across all kitchens (default 100, capped at 500), "
        "for the admin orders table.\n\n"
        "**Auth:** admin JWT required."
    ),
    responses=auth_errors(),
    tags=["Admin"],
)
async def admin_orders(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
) -> list[AdminOrderRow]:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:read")
    _ = admin
    result = await session.execute(
        text(
            """
            SELECT o.id, o.order_code, o.kitchen_id, o.status, o.total, o.customer_name, o.created_at,
                   k.name AS kitchen_name
            FROM ckac_orders.orders o
            JOIN ckac_identity.kitchens k ON k.id = o.kitchen_id
            ORDER BY o.created_at DESC
            LIMIT :lim
            """
        ),
        {"lim": min(limit, 500)},
    )
    return [
        AdminOrderRow(
            id=r.id,
            order_code=r.order_code,
            kitchen_id=r.kitchen_id,
            kitchen_name=r.kitchen_name,
            status=r.status,
            total=float(r.total),
            customer_name=r.customer_name,
            created_at=r.created_at,
        )
        for r in result.mappings().all()
    ]


@router.get("/customers", response_model=list[AdminCustomerRow], responses=auth_errors())
async def admin_customers(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = None,
    limit: int = 200,
) -> list[AdminCustomerRow]:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="customers:read")
    _ = admin
    stmt = select(Customer).order_by(Customer.created_at.desc()).limit(min(limit, 500))
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = (
            select(Customer)
            .where(
                (Customer.name.ilike(like))
                | (Customer.phone.ilike(like))
                | (Customer.email.ilike(like))
            )
            .order_by(Customer.created_at.desc())
            .limit(min(limit, 500))
        )
    customers = list((await session.execute(stmt)).scalars().all())
    rows: list[AdminCustomerRow] = []
    for c in customers:
        addr_count = (
            await session.execute(
                select(func.count()).select_from(CustomerAddress).where(CustomerAddress.customer_id == c.id)
            )
        ).scalar_one()
        rows.append(
            AdminCustomerRow(
                id=c.id,
                name=c.name,
                phone=c.phone,
                email=c.email,
                status=c.status,
                has_password=bool(c.password_hash),
                has_payout=bool(c.upi_vpa or c.bank_account_number),
                address_count=addr_count,
                created_at=c.created_at,
            )
        )
    return rows


@router.get("/customers/{customer_id}", response_model=AdminCustomerDetail, responses=auth_errors(include_404=True))
async def admin_customer_detail(
    customer_id: uuid.UUID,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCustomerDetail:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="customers:read")
    _ = admin
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    addresses = list(
        (
            await session.execute(
                select(CustomerAddress).where(CustomerAddress.customer_id == customer_id)
            )
        ).scalars().all()
    )
    return AdminCustomerDetail(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        status=customer.status,
        has_password=bool(customer.password_hash),
        upi_vpa=customer.upi_vpa,
        upi_qr_url=customer.upi_qr_url,
        bank_account_number_masked=_mask_account(customer.bank_account_number),
        bank_ifsc=customer.bank_ifsc,
        bank_account_name=customer.bank_account_name,
        addresses=[
            {
                "id": str(a.id),
                "label": a.label,
                "address_line": a.address_line,
                "city": a.city,
                "state": a.state,
                "pincode": a.pincode,
                "latitude": float(a.latitude) if a.latitude is not None else None,
                "longitude": float(a.longitude) if a.longitude is not None else None,
                "is_default": a.is_default,
            }
            for a in addresses
        ],
        created_at=customer.created_at,
    )


@router.patch(
    "/customers/{customer_id}/status",
    response_model=AdminCustomerRow,
    responses=auth_errors(include_404=True),
)
async def admin_customer_status(
    customer_id: uuid.UUID,
    body: CustomerStatusUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCustomerRow:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="customers:write")
    _ = admin
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.status = body.status
    await session.flush()
    addr_count = (
        await session.execute(
            select(func.count()).select_from(CustomerAddress).where(CustomerAddress.customer_id == customer.id)
        )
    ).scalar_one()
    return AdminCustomerRow(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        status=customer.status,
        has_password=bool(customer.password_hash),
        has_payout=bool(customer.upi_vpa or customer.bank_account_number),
        address_count=addr_count,
        created_at=customer.created_at,
    )


@router.post(
    "/customers/{customer_id}/clear-password",
    response_model=AdminCustomerDetail,
    responses=auth_errors(include_404=True),
)
async def admin_customer_clear_password(
    customer_id: uuid.UUID,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminCustomerDetail:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="customers:write")
    _ = admin
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.password_hash = None
    await session.flush()
    return await admin_customer_detail(customer_id, admin, session)


@router.patch(
    "/owners/{owner_id}/subscription",
    response_model=AdminOwnerRow,
    responses={**auth_errors(include_404=True), 400: RESP_400},
)
async def admin_owner_subscription(
    owner_id: uuid.UUID,
    body: OwnerSubscriptionUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminOwnerRow:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="owners:write")
    owner = await session.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    if body.subscription_tier is None and body.subscription_status is None:
        raise HTTPException(status_code=400, detail="Provide subscription_tier and/or subscription_status")
    before = {
        "subscription_tier": owner.subscription_tier,
        "subscription_status": owner.subscription_status,
    }
    if body.subscription_tier is not None:
        owner.subscription_tier = body.subscription_tier
    if body.subscription_status is not None:
        owner.subscription_status = body.subscription_status
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="owner.subscription.updated",
        resource_type="owner",
        resource_id=str(owner_id),
        summary=f"Owner subscription updated (**{str(owner.phone)[-4:]})",
        before=before,
        after={
            "subscription_tier": owner.subscription_tier,
            "subscription_status": owner.subscription_status,
        },
    )
    await session.flush()
    kc = (
        await session.execute(select(func.count()).select_from(Kitchen).where(Kitchen.owner_id == owner.id))
    ).scalar_one()
    return AdminOwnerRow(
        id=owner.id,
        name=owner.name,
        phone=owner.phone,
        email=owner.email,
        subscription_tier=owner.subscription_tier,
        subscription_status=owner.subscription_status,
        kitchen_count=kc,
    )


@router.get("/feature-flags", response_model=list[FeatureFlagRow], responses=auth_errors())
async def admin_feature_flags_list(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[FeatureFlagRow]:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="flags:read")
    _ = admin
    rows = list((await session.execute(select(FeatureFlag).order_by(FeatureFlag.scope, FeatureFlag.key))).scalars().all())
    return [FeatureFlagRow.model_validate(r) for r in rows]


@router.patch("/feature-flags/{key}", response_model=FeatureFlagRow, responses=auth_errors(include_404=True))
async def admin_feature_flag_update(
    key: str,
    body: FeatureFlagUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureFlagRow:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="flags:write")
    flag = await session.get(FeatureFlag, key)
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    before_enabled = bool(flag.enabled)
    flag.enabled = body.enabled
    flag.updated_at = datetime.now(UTC)
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="feature_flag.updated",
        resource_type="feature_flag",
        resource_id=key,
        summary=f"Feature flag {key} → {'on' if body.enabled else 'off'}",
        before={"enabled": before_enabled},
        after={"enabled": body.enabled},
    )
    await session.flush()
    return FeatureFlagRow.model_validate(flag)


class KitchenModuleFlagRow(BaseModel):
    module_key: str
    enabled: bool
    updated_at: datetime


class KitchenModuleFlagsResponse(BaseModel):
    kitchen_id: uuid.UUID
    kitchen_code: str
    modules: list[KitchenModuleFlagRow]


class KitchenModuleFlagUpdate(BaseModel):
    enabled: bool


@router.get(
    "/kitchens/{kitchen_id}/module-flags",
    response_model=KitchenModuleFlagsResponse,
    responses=auth_errors(include_404=True),
)
async def admin_kitchen_module_flags_list(
    kitchen_id: uuid.UUID,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenModuleFlagsResponse:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:read")
    _ = admin
    from app.models import KitchenModuleFlag
    from ckac_common.risk_config import KITCHEN_MODULE_KEYS

    kitchen = await session.get(Kitchen, kitchen_id)
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    rows = list(
        (
            await session.execute(
                select(KitchenModuleFlag).where(KitchenModuleFlag.kitchen_id == kitchen_id)
            )
        )
        .scalars()
        .all()
    )
    by_key = {r.module_key: r for r in rows}
    modules = []
    for key in KITCHEN_MODULE_KEYS:
        row = by_key.get(key)
        modules.append(
            KitchenModuleFlagRow(
                module_key=key,
                enabled=bool(row.enabled) if row else True,
                updated_at=row.updated_at if row else datetime.now(UTC),
            )
        )
    return KitchenModuleFlagsResponse(
        kitchen_id=kitchen_id,
        kitchen_code=kitchen.code,
        modules=modules,
    )


@router.patch(
    "/kitchens/{kitchen_id}/module-flags/{module_key}",
    response_model=KitchenModuleFlagRow,
    responses=auth_errors(include_404=True),
)
async def admin_kitchen_module_flag_update(
    kitchen_id: uuid.UUID,
    module_key: str,
    body: KitchenModuleFlagUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenModuleFlagRow:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="kitchens:write")
    from app.models import KitchenModuleFlag
    from ckac_common.risk_config import KITCHEN_MODULE_KEYS

    if module_key not in KITCHEN_MODULE_KEYS:
        raise HTTPException(status_code=404, detail="Unknown module key")
    kitchen = await session.get(Kitchen, kitchen_id)
    if not kitchen:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    row = await session.get(KitchenModuleFlag, (kitchen_id, module_key))
    before_enabled = bool(row.enabled) if row is not None else None
    if row is None:
        row = KitchenModuleFlag(kitchen_id=kitchen_id, module_key=module_key, enabled=body.enabled)
        session.add(row)
    else:
        row.enabled = body.enabled
    row.updated_at = datetime.now(UTC)
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="kitchen.module_flag.updated",
        resource_type="kitchen_module",
        resource_id=f"{kitchen_id}:{module_key}",
        kitchen_id=kitchen_id,
        summary=f"{kitchen.code} module {module_key} → {'on' if body.enabled else 'off'}",
        before={"enabled": before_enabled},
        after={"enabled": body.enabled, "module_key": module_key},
    )
    await session.flush()
    return KitchenModuleFlagRow(
        module_key=row.module_key,
        enabled=bool(row.enabled),
        updated_at=row.updated_at,
    )


@router.get("/api-keys", response_model=list[PlatformApiKeyRow], responses=auth_errors())
async def admin_api_keys_list(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlatformApiKeyRow]:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="api_keys:write")
    _ = admin
    rows = list(
        (
            await session.execute(
                select(PlatformApiKey).order_by(PlatformApiKey.category, PlatformApiKey.key)
            )
        )
        .scalars()
        .all()
    )
    return [_api_key_row(r) for r in rows]


@router.put("/api-keys/{key}", response_model=PlatformApiKeyRow, responses=auth_errors(include_404=True))
async def admin_api_key_upsert(
    key: str,
    body: PlatformApiKeyUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PlatformApiKeyRow:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="api_keys:write")
    row = await session.get(PlatformApiKey, key)
    if not row:
        raise HTTPException(status_code=404, detail="API key slot not found")
    row.value_enc = encrypt_secret(body.value.strip())
    row.updated_at = datetime.now(UTC)
    row.updated_by = admin.email
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="platform_api_key.updated",
        resource_type="api_key",
        resource_id=key,
        summary=f"API key slot {key} configured",
        after={"key": key, "category": row.category, "configured": True},
    )
    await session.flush()
    event = EventPublisher.build(
        event_type="platform_api_key.updated",
        aggregate_type="platform_api_key",
        aggregate_id=key,
        producer="identity-service",
        payload={"key": key, "category": row.category, "configured": True},
    )
    await publisher.publish("ckac:identity:platform", event, session=session)
    return _api_key_row(row)


@router.delete("/api-keys/{key}", response_model=PlatformApiKeyRow, responses=auth_errors(include_404=True))
async def admin_api_key_clear(
    key: str,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> PlatformApiKeyRow:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="api_keys:write")
    row = await session.get(PlatformApiKey, key)
    if not row:
        raise HTTPException(status_code=404, detail="API key slot not found")
    row.value_enc = None
    row.updated_at = datetime.now(UTC)
    row.updated_by = admin.email
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="platform_api_key.cleared",
        resource_type="api_key",
        resource_id=key,
        summary=f"API key slot {key} cleared",
        after={"key": key, "category": row.category, "configured": False},
    )
    await session.flush()
    event = EventPublisher.build(
        event_type="platform_api_key.cleared",
        aggregate_type="platform_api_key",
        aggregate_id=key,
        producer="identity-service",
        payload={"key": key, "category": row.category, "configured": False},
    )
    await publisher.publish("ckac:identity:platform", event, session=session)
    return _api_key_row(row)


@router.get("/journeys", response_model=JourneyMap, responses=auth_errors())
async def admin_journeys(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> JourneyMap:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="flags:read")
    """Map of core application data journeys with live counters for super-admin control."""
    _ = admin
    counts = (
        await session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM ckac_identity.owners) AS owners,
                  (SELECT COUNT(*) FROM ckac_identity.kitchens WHERE status = 'active') AS kitchens_active,
                  (SELECT COUNT(*) FROM ckac_identity.customers WHERE status = 'active') AS customers_active,
                  (SELECT COUNT(*) FROM ckac_orders.orders) AS orders,
                  (SELECT COUNT(*) FROM ckac_billing.payments WHERE status = 'captured') AS payments_captured,
                  (SELECT COUNT(*) FROM ckac_billing.refunds) AS refunds,
                  (SELECT COUNT(*) FROM ckac_support.support_tickets) AS tickets,
                  (SELECT COUNT(*) FROM ckac_identity.feature_flags WHERE enabled = true) AS flags_on,
                  (SELECT COUNT(*) FROM ckac_identity.feature_flags) AS flags_total
                """
            )
        )
    ).mappings().one()
    stages = [
        {
            "id": "owner_onboarding",
            "label": "Owner onboard → kitchen → menu",
            "control": "Kitchens · Owners · owner_registrations flag",
            "count": int(counts["owners"] or 0),
            "health": "ok",
        },
        {
            "id": "customer_discovery",
            "label": "Customer discover → menu → cart",
            "control": "Customers · customer_dashboard / multi_kitchen flags",
            "count": int(counts["customers_active"] or 0),
            "health": "ok",
        },
        {
            "id": "checkout_payment",
            "label": "Checkout → payment → settlement",
            "control": "Orders · Payments · Settlements",
            "count": int(counts["payments_captured"] or 0),
            "health": "ok",
        },
        {
            "id": "fulfillment",
            "label": "Accept → prep → delivery track",
            "control": "Orders · Kitchens suspend",
            "count": int(counts["orders"] or 0),
            "health": "ok",
        },
        {
            "id": "refunds",
            "label": "Dispute → refund (gateway/direct)",
            "control": "Refunds tab · refunds_* flags",
            "count": int(counts["refunds"] or 0),
            "health": "ok",
        },
        {
            "id": "support",
            "label": "Complaint → ticket → resolution",
            "control": "Tickets · customer_complaints flag",
            "count": int(counts["tickets"] or 0),
            "health": "ok",
        },
        {
            "id": "platform_flags",
            "label": "Feature kill-switches",
            "control": "Control plane flags",
            "count": int(counts["flags_on"] or 0),
            "meta": f"{counts['flags_on']}/{counts['flags_total']} enabled",
            "health": "ok",
        },
    ]
    return JourneyMap(stages=stages)


# --- Platform employees (CRUD) + RBAC -----------------------------------------

class AdminEmployeeRow(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    role: str
    is_active: bool
    created_at: datetime
    permissions: list[str] = Field(default_factory=list)


class AdminEmployeeCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="support", max_length=32)


class AdminEmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    role: str | None = Field(default=None, max_length=32)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None


async def _employee_to_row(session: AsyncSession, admin: PlatformAdmin) -> AdminEmployeeRow:
    from app.rbac import load_permissions_for_role

    perms = sorted(await load_permissions_for_role(session, admin.role))
    return AdminEmployeeRow(
        id=admin.id,
        email=admin.email,
        name=admin.name,
        role=admin.role,
        is_active=bool(admin.is_active),
        created_at=admin.created_at,
        permissions=perms,
    )


async def _count_active_superadmins(session: AsyncSession) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(PlatformAdmin)
                .where(
                    PlatformAdmin.role == "superadmin",
                    PlatformAdmin.is_active.is_(True),
                )
            )
        ).scalar_one()
    )


@router.get(
    "/employees",
    response_model=list[AdminEmployeeRow],
    summary="List platform employees",
    responses=auth_errors(),
    tags=["Admin Employees"],
)
async def admin_employees_list(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminEmployeeRow]:
    from app.rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="employees:read")
    rows = list(
        (await session.execute(select(PlatformAdmin).order_by(PlatformAdmin.created_at.desc())))
        .scalars()
        .all()
    )
    return [await _employee_to_row(session, r) for r in rows]


@router.get(
    "/employees/roles",
    response_model=list[str],
    summary="List assignable employee roles",
    responses=auth_errors(),
    tags=["Admin Employees"],
)
async def admin_employees_roles(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    from app.rbac import KNOWN_ROLES, assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="employees:read")
    return list(KNOWN_ROLES)


@router.post(
    "/employees",
    response_model=AdminEmployeeRow,
    status_code=status.HTTP_201_CREATED,
    summary="Create platform employee",
    responses=auth_errors(),
    tags=["Admin Employees"],
)
async def admin_employees_create(
    body: AdminEmployeeCreate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminEmployeeRow:
    from app.rbac import KNOWN_ROLES, assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="employees:write")
    if body.role not in KNOWN_ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role. Use one of: {', '.join(KNOWN_ROLES)}")
    email = body.email.lower().strip()
    existing = (
        await session.execute(select(PlatformAdmin).where(PlatformAdmin.email == email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Employee email already exists")
    row = PlatformAdmin(
        email=email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    session.add(row)
    await session.flush()
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="employee.created",
        resource_type="employee",
        resource_id=str(row.id),
        summary=f"Created employee {email} as {body.role}",
        after={"email": email, "role": body.role, "is_active": True},
    )
    await session.commit()
    await session.refresh(row)
    return await _employee_to_row(session, row)


@router.patch(
    "/employees/{employee_id}",
    response_model=AdminEmployeeRow,
    summary="Update platform employee",
    responses=auth_errors(include_404=True),
    tags=["Admin Employees"],
)
async def admin_employees_update(
    employee_id: uuid.UUID,
    body: AdminEmployeeUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminEmployeeRow:
    from app.rbac import KNOWN_ROLES, assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="employees:write")
    row = await session.get(PlatformAdmin, employee_id)
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    if body.role is not None:
        if body.role not in KNOWN_ROLES:
            raise HTTPException(status_code=400, detail=f"Unknown role. Use one of: {', '.join(KNOWN_ROLES)}")
        if row.role == "superadmin" and body.role != "superadmin":
            if await _count_active_superadmins(session) <= 1 and row.is_active:
                raise HTTPException(status_code=400, detail="Cannot demote the last active superadmin")
        row.role = body.role
    if body.name is not None:
        row.name = body.name.strip()
    if body.password is not None:
        row.password_hash = hash_password(body.password)
    if body.is_active is not None:
        if row.id == admin.id and body.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        if row.role == "superadmin" and body.is_active is False:
            if await _count_active_superadmins(session) <= 1:
                raise HTTPException(status_code=400, detail="Cannot deactivate the last active superadmin")
        row.is_active = body.is_active
    from app.admin_audit import record_admin_audit

    await record_admin_audit(
        session,
        actor=admin,
        action="employee.updated",
        resource_type="employee",
        resource_id=str(employee_id),
        summary=f"Updated employee {row.email}",
        after={
            "email": row.email,
            "role": row.role,
            "is_active": row.is_active,
            "password_changed": body.password is not None,
        },
    )
    await session.commit()
    await session.refresh(row)
    return await _employee_to_row(session, row)


@router.post(
    "/employees/{employee_id}/deactivate",
    response_model=AdminEmployeeRow,
    summary="Deactivate platform employee",
    responses=auth_errors(include_404=True),
    tags=["Admin Employees"],
)
async def admin_employees_deactivate(
    employee_id: uuid.UUID,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminEmployeeRow:
    return await admin_employees_update(
        employee_id,
        AdminEmployeeUpdate(is_active=False),
        admin,
        session,
    )
