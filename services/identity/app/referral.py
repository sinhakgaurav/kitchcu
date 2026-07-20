"""Dual referral program — customer→kitchen and kitchen→customer leads + INR credits."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Kitchen,
    Owner,
    ReferralCredit,
    ReferralCreditLedger,
    ReferralLead,
    ReferralSettings,
)
from app.schemas import normalize_india_phone
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

DIR_CUSTOMER_TO_KITCHEN = "customer_to_kitchen"
DIR_KITCHEN_TO_CUSTOMER = "kitchen_to_customer"
STATUS_SUBMITTED = "submitted"
STATUS_CONVERTED = "converted"
STATUS_REJECTED = "rejected"
BENEFICIARY_CUSTOMER = "customer"
BENEFICIARY_OWNER = "owner"
MAX_BULK_ROWS = 200

CUSTOMER_TEMPLATE_HEADERS = [
    "kitchen_name",
    "contact_name",
    "contact_phone",
    "contact_email",
    "city",
    "address_line",
    "notes",
]
OWNER_TEMPLATE_HEADERS = [
    "contact_name",
    "contact_phone",
    "contact_email",
    "city",
    "notes",
]


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _f(value: Decimal | float | None) -> float:
    return float(_money(value))


# --- Pydantic API models -------------------------------------------------------


class ReferralSettingsResponse(BaseModel):
    enabled: bool
    customer_to_kitchen_reward_inr: float
    kitchen_to_customer_reward_inr: float
    kitchen_reward_trigger: str
    updated_at: datetime | None = None


class ReferralSettingsUpdate(BaseModel):
    enabled: bool | None = None
    customer_to_kitchen_reward_inr: float | None = Field(default=None, ge=0, le=10000)
    kitchen_to_customer_reward_inr: float | None = Field(default=None, ge=0, le=10000)
    kitchen_reward_trigger: Literal[
        "onboard", "first_order", "first_order_or_onboard"
    ] | None = None


class CustomerKitchenReferralCreate(BaseModel):
    kitchen_name: str = Field(..., min_length=2, max_length=200)
    contact_name: str | None = Field(default=None, max_length=120)
    contact_phone: str = Field(..., min_length=10, max_length=20)
    contact_email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=100)
    address_line: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("contact_phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return normalize_india_phone(v)


class OwnerCustomerReferralCreate(BaseModel):
    kitchen_id: uuid.UUID
    contact_name: str | None = Field(default=None, max_length=120)
    contact_phone: str = Field(..., min_length=10, max_length=20)
    contact_email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("contact_phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return normalize_india_phone(v)


class BulkReferralRow(BaseModel):
    kitchen_name: str | None = None
    contact_name: str | None = None
    contact_phone: str
    contact_email: str | None = None
    city: str | None = None
    address_line: str | None = None
    notes: str | None = None

    @field_validator("contact_phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return normalize_india_phone(v)


class BulkReferralRequest(BaseModel):
    kitchen_id: uuid.UUID | None = None
    rows: list[BulkReferralRow] = Field(..., min_length=1, max_length=MAX_BULK_ROWS)


class ReferralLeadResponse(BaseModel):
    id: uuid.UUID
    direction: str
    status: str
    kitchen_name: str | None = None
    contact_name: str | None = None
    contact_phone: str
    contact_email: str | None = None
    city: str | None = None
    notes: str | None = None
    reward_inr: float | None = None
    matched_kitchen_id: uuid.UUID | None = None
    matched_customer_id: uuid.UUID | None = None
    rejection_reason: str | None = None
    created_at: datetime
    converted_at: datetime | None = None


class ReferralCreditResponse(BaseModel):
    beneficiary_type: str
    beneficiary_id: uuid.UUID
    balance_inr: float
    lifetime_earned_inr: float
    lifetime_applied_inr: float
    reward_per_conversion_inr: float
    subscription_credit_note: str


class ReferralDashboardResponse(BaseModel):
    settings: ReferralSettingsResponse
    credit: ReferralCreditResponse
    leads: list[ReferralLeadResponse]
    converted_count: int
    pending_count: int
    estimated_subscription_savings_inr: float


class BulkReferralResult(BaseModel):
    accepted: int
    rejected: int
    errors: list[str] = Field(default_factory=list)
    leads: list[ReferralLeadResponse] = Field(default_factory=list)


class AdminLeadRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class AdminLeadGrantRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ApplyOwnerCreditRequest(BaseModel):
    charge_amount_inr: float = Field(..., ge=0)


class ApplyOwnerCreditResponse(BaseModel):
    applied_inr: float
    remaining_charge_inr: float
    balance_after_inr: float


# --- Settings / credits --------------------------------------------------------


async def ensure_settings(session: AsyncSession) -> ReferralSettings:
    row = await session.get(ReferralSettings, 1)
    if row is None:
        row = ReferralSettings(id=1)
        session.add(row)
        await session.flush()
    return row


async def get_settings_response(session: AsyncSession) -> ReferralSettingsResponse:
    s = await ensure_settings(session)
    return ReferralSettingsResponse(
        enabled=bool(s.enabled),
        customer_to_kitchen_reward_inr=_f(s.customer_to_kitchen_reward_inr),
        kitchen_to_customer_reward_inr=_f(s.kitchen_to_customer_reward_inr),
        kitchen_reward_trigger=s.kitchen_reward_trigger,
        updated_at=s.updated_at,
    )


async def update_settings(
    session: AsyncSession,
    data: ReferralSettingsUpdate,
    *,
    admin_id: uuid.UUID | None,
) -> ReferralSettings:
    s = await ensure_settings(session)
    if data.enabled is not None:
        s.enabled = data.enabled
    if data.customer_to_kitchen_reward_inr is not None:
        s.customer_to_kitchen_reward_inr = data.customer_to_kitchen_reward_inr
    if data.kitchen_to_customer_reward_inr is not None:
        s.kitchen_to_customer_reward_inr = data.kitchen_to_customer_reward_inr
    if data.kitchen_reward_trigger is not None:
        s.kitchen_reward_trigger = data.kitchen_reward_trigger
    s.updated_at = datetime.now(UTC)
    s.updated_by = admin_id
    await session.flush()
    return s


async def get_or_create_credit(
    session: AsyncSession,
    *,
    beneficiary_type: str,
    beneficiary_id: uuid.UUID,
) -> ReferralCredit:
    result = await session.execute(
        select(ReferralCredit).where(
            ReferralCredit.beneficiary_type == beneficiary_type,
            ReferralCredit.beneficiary_id == beneficiary_id,
        )
    )
    credit = result.scalar_one_or_none()
    if credit:
        return credit
    credit = ReferralCredit(
        beneficiary_type=beneficiary_type,
        beneficiary_id=beneficiary_id,
        balance_inr=0,
        lifetime_earned_inr=0,
        lifetime_applied_inr=0,
    )
    session.add(credit)
    await session.flush()
    return credit


async def credit_earn(
    session: AsyncSession,
    *,
    beneficiary_type: str,
    beneficiary_id: uuid.UUID,
    amount: Decimal,
    lead_id: uuid.UUID,
    note: str,
    publisher: EventPublisher | None,
) -> ReferralCredit:
    credit = await get_or_create_credit(
        session, beneficiary_type=beneficiary_type, beneficiary_id=beneficiary_id
    )
    amt = _money(amount)
    credit.balance_inr = _money(credit.balance_inr) + amt
    credit.lifetime_earned_inr = _money(credit.lifetime_earned_inr) + amt
    credit.updated_at = datetime.now(UTC)
    session.add(
        ReferralCreditLedger(
            credit_id=credit.id,
            entry_type="earn",
            amount_inr=amt,
            balance_after_inr=credit.balance_inr,
            lead_id=lead_id,
            note=note,
        )
    )
    await session.flush()
    if publisher:
        event = EventPublisher.build(
            event_type="referral.rewarded",
            aggregate_type="referral",
            aggregate_id=str(lead_id),
            producer="identity-service",
            payload={
                "lead_id": str(lead_id),
                "beneficiary_type": beneficiary_type,
                "beneficiary_id": str(beneficiary_id),
                "amount_inr": float(amt),
                "balance_inr": float(_money(credit.balance_inr)),
            },
        )
        await publisher.publish(stream_key("identity", "referral"), event, session=session)
    return credit


async def apply_owner_credit(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    charge_amount_inr: float,
    publisher: EventPublisher | None = None,
) -> ApplyOwnerCreditResponse:
    charge = _money(charge_amount_inr)
    credit = await get_or_create_credit(
        session, beneficiary_type=BENEFICIARY_OWNER, beneficiary_id=owner_id
    )
    bal = _money(credit.balance_inr)
    applied = min(bal, charge)
    if applied > 0:
        credit.balance_inr = bal - applied
        credit.lifetime_applied_inr = _money(credit.lifetime_applied_inr) + applied
        credit.updated_at = datetime.now(UTC)
        session.add(
            ReferralCreditLedger(
                credit_id=credit.id,
                entry_type="apply_subscription",
                amount_inr=-applied,
                balance_after_inr=credit.balance_inr,
                note=f"Applied to SaaS charge ₹{charge}",
            )
        )
        await session.flush()
        if publisher:
            event = EventPublisher.build(
                event_type="referral.credit_applied",
                aggregate_type="referral",
                aggregate_id=str(credit.id),
                producer="identity-service",
                payload={
                    "beneficiary_type": BENEFICIARY_OWNER,
                    "beneficiary_id": str(owner_id),
                    "applied_inr": float(applied),
                    "balance_inr": float(_money(credit.balance_inr)),
                },
            )
            await publisher.publish(stream_key("identity", "referral"), event, session=session)
    return ApplyOwnerCreditResponse(
        applied_inr=_f(applied),
        remaining_charge_inr=_f(charge - applied),
        balance_after_inr=_f(credit.balance_inr),
    )


def lead_to_response(lead: ReferralLead) -> ReferralLeadResponse:
    return ReferralLeadResponse(
        id=lead.id,
        direction=lead.direction,
        status=lead.status,
        kitchen_name=lead.kitchen_name,
        contact_name=lead.contact_name,
        contact_phone=lead.contact_phone,
        contact_email=lead.contact_email,
        city=lead.city,
        notes=lead.notes,
        reward_inr=_f(lead.reward_inr) if lead.reward_inr is not None else None,
        matched_kitchen_id=lead.matched_kitchen_id,
        matched_customer_id=lead.matched_customer_id,
        rejection_reason=lead.rejection_reason,
        created_at=lead.created_at,
        converted_at=lead.converted_at,
    )


async def credit_dashboard(
    session: AsyncSession,
    *,
    beneficiary_type: str,
    beneficiary_id: uuid.UUID,
    direction: str,
) -> ReferralDashboardResponse:
    settings = await get_settings_response(session)
    credit = await get_or_create_credit(
        session, beneficiary_type=beneficiary_type, beneficiary_id=beneficiary_id
    )
    if direction == DIR_CUSTOMER_TO_KITCHEN:
        q = select(ReferralLead).where(ReferralLead.referrer_customer_id == beneficiary_id)
        reward = settings.customer_to_kitchen_reward_inr
        note = (
            "Credit applies to your next kitchen subscription / eligible order charges "
            "when kitchens you referred go live."
        )
    else:
        q = select(ReferralLead).where(ReferralLead.referrer_owner_id == beneficiary_id)
        reward = settings.kitchen_to_customer_reward_inr
        note = "Credit is deducted automatically from your next KitchCu SaaS subscription charge."
    q = q.order_by(ReferralLead.created_at.desc()).limit(100)
    leads = list((await session.execute(q)).scalars().all())
    converted = sum(1 for L in leads if L.status == STATUS_CONVERTED)
    pending = sum(1 for L in leads if L.status == STATUS_SUBMITTED)
    return ReferralDashboardResponse(
        settings=settings,
        credit=ReferralCreditResponse(
            beneficiary_type=beneficiary_type,
            beneficiary_id=beneficiary_id,
            balance_inr=_f(credit.balance_inr),
            lifetime_earned_inr=_f(credit.lifetime_earned_inr),
            lifetime_applied_inr=_f(credit.lifetime_applied_inr),
            reward_per_conversion_inr=reward,
            subscription_credit_note=note,
        ),
        leads=[lead_to_response(L) for L in leads],
        converted_count=converted,
        pending_count=pending,
        estimated_subscription_savings_inr=_f(credit.balance_inr),
    )


# --- Submit leads --------------------------------------------------------------


async def _assert_program_enabled(session: AsyncSession) -> ReferralSettings:
    s = await ensure_settings(session)
    if not s.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Referral program is disabled",
        )
    return s


async def _duplicate_open_lead(
    session: AsyncSession,
    *,
    direction: str,
    contact_phone: str,
    referrer_customer_id: uuid.UUID | None = None,
    referrer_owner_id: uuid.UUID | None = None,
) -> ReferralLead | None:
    q = select(ReferralLead).where(
        ReferralLead.direction == direction,
        ReferralLead.contact_phone == contact_phone,
        ReferralLead.status == STATUS_SUBMITTED,
    )
    if referrer_customer_id:
        q = q.where(ReferralLead.referrer_customer_id == referrer_customer_id)
    if referrer_owner_id:
        q = q.where(ReferralLead.referrer_owner_id == referrer_owner_id)
    return (await session.execute(q)).scalar_one_or_none()


async def submit_customer_kitchen_lead(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    data: CustomerKitchenReferralCreate,
    publisher: EventPublisher | None,
) -> ReferralLead:
    await _assert_program_enabled(session)
    existing = await _duplicate_open_lead(
        session,
        direction=DIR_CUSTOMER_TO_KITCHEN,
        contact_phone=data.contact_phone,
        referrer_customer_id=customer_id,
    )
    if existing:
        return existing
    lead = ReferralLead(
        direction=DIR_CUSTOMER_TO_KITCHEN,
        status=STATUS_SUBMITTED,
        referrer_customer_id=customer_id,
        kitchen_name=data.kitchen_name.strip(),
        contact_name=(data.contact_name or "").strip() or None,
        contact_phone=data.contact_phone,
        contact_email=str(data.contact_email) if data.contact_email else None,
        city=(data.city or "").strip() or None,
        notes=(data.notes or "").strip() or None,
        extra={"address_line": data.address_line} if data.address_line else {},
    )
    session.add(lead)
    await session.flush()
    if publisher:
        event = EventPublisher.build(
            event_type="referral.lead_submitted",
            aggregate_type="referral",
            aggregate_id=str(lead.id),
            producer="identity-service",
            payload={
                "lead_id": str(lead.id),
                "direction": lead.direction,
                "referrer_customer_id": str(customer_id),
            },
        )
        await publisher.publish(stream_key("identity", "referral"), event, session=session)
    return lead


async def submit_owner_customer_lead(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    data: OwnerCustomerReferralCreate,
    publisher: EventPublisher | None,
) -> ReferralLead:
    await _assert_program_enabled(session)
    kitchen = await session.get(Kitchen, data.kitchen_id)
    if kitchen is None or kitchen.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    existing = await _duplicate_open_lead(
        session,
        direction=DIR_KITCHEN_TO_CUSTOMER,
        contact_phone=data.contact_phone,
        referrer_owner_id=owner_id,
    )
    if existing:
        return existing
    lead = ReferralLead(
        direction=DIR_KITCHEN_TO_CUSTOMER,
        status=STATUS_SUBMITTED,
        referrer_kitchen_id=kitchen.id,
        referrer_owner_id=owner_id,
        contact_name=(data.contact_name or "").strip() or None,
        contact_phone=data.contact_phone,
        contact_email=str(data.contact_email) if data.contact_email else None,
        city=(data.city or "").strip() or None,
        notes=(data.notes or "").strip() or None,
        extra={},
    )
    session.add(lead)
    await session.flush()
    if publisher:
        event = EventPublisher.build(
            event_type="referral.lead_submitted",
            aggregate_type="referral",
            aggregate_id=str(lead.id),
            producer="identity-service",
            payload={
                "lead_id": str(lead.id),
                "direction": lead.direction,
                "referrer_kitchen_id": str(kitchen.id),
                "referrer_owner_id": str(owner_id),
            },
        )
        await publisher.publish(stream_key("identity", "referral"), event, session=session)
    return lead


async def bulk_submit_customer(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    rows: list[BulkReferralRow],
    publisher: EventPublisher | None,
) -> BulkReferralResult:
    accepted = 0
    rejected = 0
    errors: list[str] = []
    leads: list[ReferralLeadResponse] = []
    for i, row in enumerate(rows, start=1):
        if not (row.kitchen_name or "").strip():
            rejected += 1
            errors.append(f"Row {i}: kitchen_name required")
            continue
        try:
            lead = await submit_customer_kitchen_lead(
                session,
                customer_id=customer_id,
                data=CustomerKitchenReferralCreate(
                    kitchen_name=row.kitchen_name.strip(),
                    contact_name=row.contact_name,
                    contact_phone=row.contact_phone,
                    contact_email=row.contact_email,
                    city=row.city,
                    address_line=row.address_line,
                    notes=row.notes,
                ),
                publisher=publisher,
            )
            accepted += 1
            leads.append(lead_to_response(lead))
        except HTTPException as exc:
            rejected += 1
            errors.append(f"Row {i}: {exc.detail}")
        except Exception as exc:  # noqa: BLE001
            rejected += 1
            errors.append(f"Row {i}: {exc}")
    return BulkReferralResult(accepted=accepted, rejected=rejected, errors=errors, leads=leads)


async def bulk_submit_owner(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    rows: list[BulkReferralRow],
    publisher: EventPublisher | None,
) -> BulkReferralResult:
    accepted = 0
    rejected = 0
    errors: list[str] = []
    leads: list[ReferralLeadResponse] = []
    for i, row in enumerate(rows, start=1):
        try:
            lead = await submit_owner_customer_lead(
                session,
                owner_id=owner_id,
                data=OwnerCustomerReferralCreate(
                    kitchen_id=kitchen_id,
                    contact_name=row.contact_name,
                    contact_phone=row.contact_phone,
                    contact_email=row.contact_email,
                    city=row.city,
                    notes=row.notes,
                ),
                publisher=publisher,
            )
            accepted += 1
            leads.append(lead_to_response(lead))
        except HTTPException as exc:
            rejected += 1
            errors.append(f"Row {i}: {exc.detail}")
        except Exception as exc:  # noqa: BLE001
            rejected += 1
            errors.append(f"Row {i}: {exc}")
    return BulkReferralResult(accepted=accepted, rejected=rejected, errors=errors, leads=leads)


def csv_template(headers: list[str]) -> str:
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf)
    writer.writerow(headers)
    if headers == CUSTOMER_TEMPLATE_HEADERS:
        writer.writerow(
            [
                "Home Spice Kitchen",
                "Priya Sharma",
                "9876543210",
                "priya@example.com",
                "Pune",
                "Lane 2, Kothrud",
                "Makes great thalis",
            ]
        )
    else:
        writer.writerow(
            ["Asha Patel", "9123456789", "asha@example.com", "Pune", "Regular lunch customer"]
        )
    return buf.getvalue()


def parse_csv_rows(content: str, *, require_kitchen_name: bool) -> list[BulkReferralRow]:
    text = content.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row")
    rows: list[BulkReferralRow] = []
    for i, raw in enumerate(reader, start=2):
        if len(rows) >= MAX_BULK_ROWS:
            break
        phone = (raw.get("contact_phone") or "").strip()
        if not phone:
            continue
        kitchen_name = (raw.get("kitchen_name") or "").strip() or None
        if require_kitchen_name and not kitchen_name:
            raise HTTPException(status_code=400, detail=f"Row {i}: kitchen_name required")
        rows.append(
            BulkReferralRow(
                kitchen_name=kitchen_name,
                contact_name=(raw.get("contact_name") or "").strip() or None,
                contact_phone=phone,
                contact_email=(raw.get("contact_email") or "").strip() or None,
                city=(raw.get("city") or "").strip() or None,
                address_line=(raw.get("address_line") or "").strip() or None,
                notes=(raw.get("notes") or "").strip() or None,
            )
        )
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in CSV")
    return rows


# --- Conversion / reward -------------------------------------------------------


async def _convert_lead(
    session: AsyncSession,
    lead: ReferralLead,
    *,
    reward: Decimal,
    beneficiary_type: str,
    beneficiary_id: uuid.UUID,
    matched_kitchen_id: uuid.UUID | None = None,
    matched_customer_id: uuid.UUID | None = None,
    publisher: EventPublisher | None,
) -> ReferralLead:
    if lead.status == STATUS_CONVERTED:
        return lead
    credit = await credit_earn(
        session,
        beneficiary_type=beneficiary_type,
        beneficiary_id=beneficiary_id,
        amount=reward,
        lead_id=lead.id,
        note=f"Referral converted ({lead.direction})",
        publisher=publisher,
    )
    lead.status = STATUS_CONVERTED
    lead.reward_inr = reward
    lead.credit_id = credit.id
    lead.matched_kitchen_id = matched_kitchen_id
    lead.matched_customer_id = matched_customer_id
    lead.converted_at = datetime.now(UTC)
    lead.updated_at = datetime.now(UTC)
    await session.flush()
    return lead


async def try_reward_kitchen_onboard(
    session: AsyncSession,
    *,
    kitchen: Kitchen,
    owner: Owner,
    publisher: EventPublisher | None,
) -> ReferralLead | None:
    settings = await ensure_settings(session)
    if not settings.enabled:
        return None
    result = await session.execute(
        select(ReferralLead)
        .where(
            ReferralLead.direction == DIR_CUSTOMER_TO_KITCHEN,
            ReferralLead.status == STATUS_SUBMITTED,
            ReferralLead.contact_phone == owner.phone,
        )
        .order_by(ReferralLead.created_at.asc())
        .limit(1)
    )
    lead = result.scalar_one_or_none()
    if lead is None or lead.referrer_customer_id is None:
        return None
    return await _convert_lead(
        session,
        lead,
        reward=_money(settings.customer_to_kitchen_reward_inr),
        beneficiary_type=BENEFICIARY_CUSTOMER,
        beneficiary_id=lead.referrer_customer_id,
        matched_kitchen_id=kitchen.id,
        publisher=publisher,
    )


async def try_reward_customer_onboard(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    phone: str | None,
    publisher: EventPublisher | None,
) -> ReferralLead | None:
    if not phone:
        return None
    settings = await ensure_settings(session)
    if not settings.enabled:
        return None
    trigger = settings.kitchen_reward_trigger or "first_order_or_onboard"
    if trigger not in ("onboard", "first_order_or_onboard"):
        return None
    try:
        phone_n = normalize_india_phone(phone)
    except Exception:
        phone_n = phone
    result = await session.execute(
        select(ReferralLead)
        .where(
            ReferralLead.direction == DIR_KITCHEN_TO_CUSTOMER,
            ReferralLead.status == STATUS_SUBMITTED,
            ReferralLead.contact_phone == phone_n,
        )
        .order_by(ReferralLead.created_at.asc())
        .limit(1)
    )
    lead = result.scalar_one_or_none()
    if lead is None or lead.referrer_owner_id is None:
        return None
    return await _convert_lead(
        session,
        lead,
        reward=_money(settings.kitchen_to_customer_reward_inr),
        beneficiary_type=BENEFICIARY_OWNER,
        beneficiary_id=lead.referrer_owner_id,
        matched_customer_id=customer_id,
        publisher=publisher,
    )


async def try_reward_customer_first_order(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    phone: str | None,
    publisher: EventPublisher | None,
) -> ReferralLead | None:
    settings = await ensure_settings(session)
    if not settings.enabled:
        return None
    trigger = settings.kitchen_reward_trigger or "first_order_or_onboard"
    if trigger not in ("first_order", "first_order_or_onboard"):
        return None
    phone_n = None
    if phone:
        try:
            phone_n = normalize_india_phone(phone)
        except Exception:
            phone_n = phone
    q = select(ReferralLead).where(
        ReferralLead.direction == DIR_KITCHEN_TO_CUSTOMER,
        ReferralLead.status == STATUS_SUBMITTED,
    )
    if phone_n:
        q = q.where(ReferralLead.contact_phone == phone_n)
    else:
        return None
    q = q.order_by(ReferralLead.created_at.asc()).limit(1)
    lead = (await session.execute(q)).scalar_one_or_none()
    if lead is None or lead.referrer_owner_id is None:
        return None
    return await _convert_lead(
        session,
        lead,
        reward=_money(settings.kitchen_to_customer_reward_inr),
        beneficiary_type=BENEFICIARY_OWNER,
        beneficiary_id=lead.referrer_owner_id,
        matched_customer_id=customer_id,
        publisher=publisher,
    )


async def reject_lead(
    session: AsyncSession,
    lead_id: uuid.UUID,
    *,
    reason: str,
) -> ReferralLead:
    lead = await session.get(ReferralLead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.status != STATUS_SUBMITTED:
        raise HTTPException(status_code=400, detail=f"Lead is already {lead.status}")
    lead.status = STATUS_REJECTED
    lead.rejection_reason = reason
    lead.updated_at = datetime.now(UTC)
    await session.flush()
    return lead


async def admin_grant_lead(
    session: AsyncSession,
    lead_id: uuid.UUID,
    *,
    note: str | None,
    publisher: EventPublisher | None,
) -> ReferralLead:
    lead = await session.get(ReferralLead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.status == STATUS_CONVERTED:
        return lead
    settings = await ensure_settings(session)
    if lead.direction == DIR_CUSTOMER_TO_KITCHEN:
        if lead.referrer_customer_id is None:
            raise HTTPException(status_code=400, detail="Lead missing referrer customer")
        return await _convert_lead(
            session,
            lead,
            reward=_money(settings.customer_to_kitchen_reward_inr),
            beneficiary_type=BENEFICIARY_CUSTOMER,
            beneficiary_id=lead.referrer_customer_id,
            publisher=publisher,
        )
    if lead.referrer_owner_id is None:
        raise HTTPException(status_code=400, detail="Lead missing referrer owner")
    lead.notes = (lead.notes or "") + (f"\nAdmin grant: {note}" if note else "")
    return await _convert_lead(
        session,
        lead,
        reward=_money(settings.kitchen_to_customer_reward_inr),
        beneficiary_type=BENEFICIARY_OWNER,
        beneficiary_id=lead.referrer_owner_id,
        publisher=publisher,
    )


async def list_admin_leads(
    session: AsyncSession,
    *,
    direction: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
) -> list[ReferralLead]:
    q = select(ReferralLead).order_by(ReferralLead.created_at.desc()).limit(min(limit, 200))
    if direction:
        q = q.where(ReferralLead.direction == direction)
    if status_filter:
        q = q.where(ReferralLead.status == status_filter)
    return list((await session.execute(q)).scalars().all())
