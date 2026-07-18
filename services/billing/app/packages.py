"""Package mapper domain — features → packages → plans → kitchen assignment."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from ckac_common.auth import stream_key
from ckac_common.database import Base
from ckac_common.event_bus import EventPublisher


class PlatformFeature(Base):
    __tablename__ = "platform_features"
    __table_args__ = {"schema": "ckac_billing"}

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str] = mapped_column(String(20), default="owner")
    module_key: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Package(Base):
    __tablename__ = "packages"
    __table_args__ = {"schema": "ckac_billing"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    audience: Mapped[str] = mapped_column(String(20), default="owner")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PackageFeature(Base):
    __tablename__ = "package_features"
    __table_args__ = {"schema": "ckac_billing"}

    package_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    feature_key: Mapped[str] = mapped_column(String(64), primary_key=True)


class PlanPackage(Base):
    __tablename__ = "plan_packages"
    __table_args__ = {"schema": "ckac_billing"}

    plan_tier: Mapped[str] = mapped_column(String(32), primary_key=True)
    package_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    audience: Mapped[str] = mapped_column(String(20), default="owner")


class KitchenPackage(Base):
    __tablename__ = "kitchen_packages"
    __table_args__ = {"schema": "ckac_billing"}

    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    package_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FeatureResponse(BaseModel):
    key: str
    label: str
    description: str | None = None
    audience: str
    module_key: str | None = None


class PackageResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    audience: str
    description: str | None
    is_active: bool
    feature_keys: list[str]
    plan_tiers: list[str]


class PackageUpsertRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    audience: str = Field(default="owner", pattern="^(owner|customer|both)$")
    description: str | None = None
    is_active: bool = True
    feature_keys: list[str] = Field(default_factory=list)
    plan_tiers: list[str] = Field(default_factory=list)


class PlanMapRequest(BaseModel):
    plan_tier: str = Field(..., min_length=2, max_length=32)
    package_id: uuid.UUID
    audience: str = Field(default="owner", pattern="^(owner|customer|both)$")


class KitchenPackageResponse(BaseModel):
    kitchen_id: uuid.UUID
    package: PackageResponse | None
    source: str  # assigned | plan_default | none
    owner_plan_tier: str | None = None


class KitchenPackageAssignRequest(BaseModel):
    package_id: uuid.UUID
    notes: str | None = None
    sync_module_flags: bool = Field(
        default=True,
        description="When true, enable kitchen modules that map from package features.",
    )


async def list_features(session: AsyncSession) -> list[FeatureResponse]:
    rows = list((await session.execute(select(PlatformFeature).order_by(PlatformFeature.key))).scalars().all())
    return [
        FeatureResponse(
            key=r.key,
            label=r.label,
            description=r.description,
            audience=r.audience,
            module_key=r.module_key,
        )
        for r in rows
    ]


async def _package_response(session: AsyncSession, pkg: Package) -> PackageResponse:
    feats = (
        await session.execute(
            select(PackageFeature.feature_key).where(PackageFeature.package_id == pkg.id)
        )
    ).scalars().all()
    tiers = (
        await session.execute(
            select(PlanPackage.plan_tier).where(PlanPackage.package_id == pkg.id)
        )
    ).scalars().all()
    return PackageResponse(
        id=pkg.id,
        code=pkg.code,
        name=pkg.name,
        audience=pkg.audience,
        description=pkg.description,
        is_active=bool(pkg.is_active),
        feature_keys=sorted(str(f) for f in feats),
        plan_tiers=sorted(str(t) for t in tiers),
    )


async def list_packages(session: AsyncSession, audience: str | None = None) -> list[PackageResponse]:
    q = select(Package).order_by(Package.audience, Package.code)
    if audience:
        q = q.where(Package.audience.in_([audience, "both"]))
    rows = list((await session.execute(q)).scalars().all())
    return [await _package_response(session, r) for r in rows]


async def upsert_package(
    session: AsyncSession,
    publisher: EventPublisher,
    body: PackageUpsertRequest,
    package_id: uuid.UUID | None = None,
) -> PackageResponse:
    code = body.code.strip().lower().replace(" ", "_")
    if package_id:
        pkg = await session.get(Package, package_id)
        if not pkg:
            raise HTTPException(status_code=404, detail="Package not found")
    else:
        existing = (
            await session.execute(select(Package).where(Package.code == code))
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Package code already exists")
        # Set NOT NULL columns before any flush (feature validation SELECTs can autoflush).
        pkg = Package(
            code=code,
            name=body.name.strip(),
            audience=body.audience,
            description=body.description,
            is_active=body.is_active,
        )
        session.add(pkg)

    # Validate features
    if body.feature_keys:
        valid = set(
            (
                await session.execute(
                    select(PlatformFeature.key).where(PlatformFeature.key.in_(body.feature_keys))
                )
            ).scalars().all()
        )
        missing = set(body.feature_keys) - valid
        if missing:
            raise HTTPException(status_code=400, detail=f"Unknown features: {sorted(missing)}")

    pkg.code = code
    pkg.name = body.name.strip()
    pkg.audience = body.audience
    pkg.description = body.description
    pkg.is_active = body.is_active
    pkg.updated_at = datetime.now(UTC)
    await session.flush()

    await session.execute(
        text("DELETE FROM ckac_billing.package_features WHERE package_id = :pid"),
        {"pid": pkg.id},
    )
    for fk in body.feature_keys:
        session.add(PackageFeature(package_id=pkg.id, feature_key=fk))

    await session.execute(
        text("DELETE FROM ckac_billing.plan_packages WHERE package_id = :pid"),
        {"pid": pkg.id},
    )
    for tier in body.plan_tiers:
        # Clear other package owning this tier for same audience
        await session.execute(
            text(
                "DELETE FROM ckac_billing.plan_packages WHERE plan_tier = :tier AND audience = :aud"
            ),
            {"tier": tier.strip().lower(), "aud": body.audience},
        )
        session.add(
            PlanPackage(
                plan_tier=tier.strip().lower(),
                package_id=pkg.id,
                audience=body.audience,
            )
        )
    await session.flush()

    event = EventPublisher.build(
        event_type="package.updated",
        aggregate_type="package",
        aggregate_id=str(pkg.id),
        producer="billing-service",
        payload={"package_id": str(pkg.id), "code": pkg.code, "feature_keys": body.feature_keys},
    )
    await publisher.publish(stream_key("billing", "package"), event, session=session)
    return await _package_response(session, pkg)


async def map_plan(
    session: AsyncSession,
    publisher: EventPublisher,
    body: PlanMapRequest,
) -> PackageResponse:
    pkg = await session.get(Package, body.package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    tier = body.plan_tier.strip().lower()
    await session.execute(
        text("DELETE FROM ckac_billing.plan_packages WHERE plan_tier = :tier AND audience = :aud"),
        {"tier": tier, "aud": body.audience},
    )
    session.add(PlanPackage(plan_tier=tier, package_id=pkg.id, audience=body.audience))
    await session.flush()
    event = EventPublisher.build(
        event_type="plan_package.mapped",
        aggregate_type="package",
        aggregate_id=str(pkg.id),
        producer="billing-service",
        payload={"plan_tier": tier, "package_id": str(pkg.id), "audience": body.audience},
    )
    await publisher.publish(stream_key("billing", "package"), event, session=session)
    return await _package_response(session, pkg)


async def get_kitchen_package(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> KitchenPackageResponse:
    assigned = await session.get(KitchenPackage, kitchen_id)
    owner_tier = (
        await session.execute(
            text(
                """
                SELECT o.subscription_tier
                FROM ckac_identity.kitchens k
                JOIN ckac_identity.owners o ON o.id = k.owner_id
                WHERE k.id = :kid
                LIMIT 1
                """
            ),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()

    if assigned:
        pkg = await session.get(Package, assigned.package_id)
        return KitchenPackageResponse(
            kitchen_id=kitchen_id,
            package=await _package_response(session, pkg) if pkg else None,
            source="assigned",
            owner_plan_tier=str(owner_tier) if owner_tier else None,
        )

    if owner_tier:
        plan_row = (
            await session.execute(
                select(PlanPackage).where(
                    PlanPackage.plan_tier == str(owner_tier),
                    PlanPackage.audience.in_(("owner", "both")),
                )
            )
        ).scalar_one_or_none()
        if plan_row:
            pkg = await session.get(Package, plan_row.package_id)
            return KitchenPackageResponse(
                kitchen_id=kitchen_id,
                package=await _package_response(session, pkg) if pkg else None,
                source="plan_default",
                owner_plan_tier=str(owner_tier),
            )

    return KitchenPackageResponse(
        kitchen_id=kitchen_id,
        package=None,
        source="none",
        owner_plan_tier=str(owner_tier) if owner_tier else None,
    )


class KitchenEntitlementsResponse(BaseModel):
    kitchen_id: uuid.UUID
    package_code: str | None = None
    package_name: str | None = None
    source: str
    hard_mode: bool
    feature_keys: list[str]
    modules: dict[str, bool]


async def get_kitchen_entitlements(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> KitchenEntitlementsResponse:
    from ckac_common.platform_config import is_kitchen_module_enabled, kitchen_has_assigned_package
    from ckac_common.risk_config import KITCHEN_MODULE_KEYS

    pkg_info = await get_kitchen_package(session, kitchen_id)
    hard = await kitchen_has_assigned_package(session, kitchen_id)
    modules = {
        mk: await is_kitchen_module_enabled(session, kitchen_id, mk)
        for mk in KITCHEN_MODULE_KEYS
    }
    feature_keys = list(pkg_info.package.feature_keys) if pkg_info.package else []
    return KitchenEntitlementsResponse(
        kitchen_id=kitchen_id,
        package_code=pkg_info.package.code if pkg_info.package else None,
        package_name=pkg_info.package.name if pkg_info.package else None,
        source=pkg_info.source,
        hard_mode=hard,
        feature_keys=feature_keys,
        modules=modules,
    )


async def assign_kitchen_package(
    session: AsyncSession,
    publisher: EventPublisher,
    kitchen_id: uuid.UUID,
    body: KitchenPackageAssignRequest,
) -> KitchenPackageResponse:
    exists = (
        await session.execute(
            text("SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    pkg = await session.get(Package, body.package_id)
    if not pkg or not pkg.is_active:
        raise HTTPException(status_code=400, detail="Package not found or inactive")

    row = await session.get(KitchenPackage, kitchen_id)
    if row is None:
        row = KitchenPackage(kitchen_id=kitchen_id, package_id=pkg.id)
        session.add(row)
    else:
        row.package_id = pkg.id
    row.assigned_at = datetime.now(UTC)
    row.notes = body.notes
    await session.flush()

    if body.sync_module_flags:
        from ckac_common.risk_config import KITCHEN_MODULE_KEYS

        feat_rows = (
            await session.execute(
                select(PlatformFeature).join(
                    PackageFeature,
                    PackageFeature.feature_key == PlatformFeature.key,
                ).where(PackageFeature.package_id == pkg.id)
            )
        ).scalars().all()
        enabled_mods = {f.module_key for f in feat_rows if f.module_key}
        for mod in KITCHEN_MODULE_KEYS:
            await session.execute(
                text(
                    """
                    INSERT INTO ckac_identity.kitchen_module_flags
                        (kitchen_id, module_key, enabled, updated_at)
                    VALUES (:kid, :mod, :en, now())
                    ON CONFLICT (kitchen_id, module_key)
                    DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = now()
                    """
                ),
                {"kid": kitchen_id, "mod": mod, "en": mod in enabled_mods},
            )

    event = EventPublisher.build(
        event_type="kitchen_package.assigned",
        aggregate_type="package",
        aggregate_id=str(pkg.id),
        producer="billing-service",
        payload={"kitchen_id": str(kitchen_id), "package_id": str(pkg.id), "code": pkg.code},
    )
    await publisher.publish(stream_key("billing", "package"), event, session=session)
    return await get_kitchen_package(session, kitchen_id)
