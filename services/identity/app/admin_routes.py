"""Platform admin API — full control over owners, kitchens, orders."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Kitchen, Owner, PlatformAdmin
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.openapi import RESP_401, RESP_422, auth_errors

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


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


class AdminProfile(BaseModel):
    """Platform admin profile returned by `GET /admin/me`."""

    id: uuid.UUID = Field(..., description="Admin UUID primary key.")
    email: str = Field(..., description="Admin login email.", examples=["admin@kitchcu.dev"])
    name: str = Field(..., description="Admin display name.", examples=["kitchCU Platform Admin"])
    role: str = Field(..., description="Admin role.", examples=["superadmin"])

    model_config = {"from_attributes": True}


class PlatformStats(BaseModel):
    """Aggregate platform counters returned by `GET /admin/stats`."""

    owners: int = Field(..., description="Total registered owners.", examples=[42])
    kitchens: int = Field(..., description="Total kitchens across all owners.", examples=[57])
    active_kitchens: int = Field(..., description="Kitchens with status=active.", examples=[49])
    orders: int = Field(..., description="Total orders placed platform-wide.", examples=[1830])
    dishes: int = Field(..., description="Total active dishes across all catalogs.", examples=[612])


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
    email = settings.admin_email.lower()
    result = await session.execute(select(PlatformAdmin).where(PlatformAdmin.email == email))
    if result.scalar_one_or_none():
        return
    session.add(
        PlatformAdmin(
            email=email,
            password_hash=hash_password(settings.admin_password),
            name="kitchCU Platform Admin",
            role="superadmin",
        )
    )
    await session.flush()


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
async def admin_me(admin: Annotated[PlatformAdmin, Depends(get_current_admin)]) -> AdminProfile:
    return AdminProfile.model_validate(admin)


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
    return PlatformStats(
        owners=owners,
        kitchens=kitchens,
        active_kitchens=active,
        orders=orders,
        dishes=dishes,
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
    _ = admin
    result = await session.execute(
        select(Kitchen, Owner)
        .join(Owner, Owner.id == Kitchen.owner_id)
        .order_by(Kitchen.created_at.desc())
        .limit(300)
    )
    return [
        AdminKitchenRow(
            id=k.id,
            code=k.code,
            name=k.name,
            city=k.city,
            status=k.status,
            owner_name=o.name,
            owner_phone=o.phone,
        )
        for k, o in result.all()
    ]


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
    kitchen.status = body.status
    await session.commit()
    return AdminKitchenRow(
        id=kitchen.id,
        code=kitchen.code,
        name=kitchen.name,
        city=kitchen.city,
        status=kitchen.status,
        owner_name=owner.name,
        owner_phone=owner.phone,
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
