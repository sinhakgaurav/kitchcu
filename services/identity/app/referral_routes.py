"""Customer + owner referral APIs (gateway → identity)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_routes import get_current_customer, get_publisher
from app.models import Customer, Owner
from app.referral import (
    CUSTOMER_TEMPLATE_HEADERS,
    OWNER_TEMPLATE_HEADERS,
    BulkReferralRequest,
    BulkReferralResult,
    CustomerKitchenReferralCreate,
    OwnerCustomerReferralCreate,
    ReferralDashboardResponse,
    ReferralLeadResponse,
    bulk_submit_customer,
    bulk_submit_owner,
    credit_dashboard,
    csv_template,
    lead_to_response,
    parse_csv_rows,
    submit_customer_kitchen_lead,
    submit_owner_customer_lead,
)
from app.routes import get_current_owner
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_401, RESP_403, RESP_422

router = APIRouter(tags=["Referrals"])


@router.get(
    "/customers/me/referrals",
    response_model=ReferralDashboardResponse,
    summary="Customer referral dashboard (kitchen leads + subscription credit)",
    responses={401: RESP_401},
)
async def customer_referral_dashboard(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReferralDashboardResponse:
    return await credit_dashboard(
        session,
        beneficiary_type="customer",
        beneficiary_id=customer.id,
        direction="customer_to_kitchen",
    )


@router.post(
    "/customers/me/referrals/kitchens",
    response_model=ReferralLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Refer a kitchen to the platform",
    responses={401: RESP_401, 403: RESP_403, 422: RESP_422},
)
async def customer_refer_kitchen(
    body: CustomerKitchenReferralCreate,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> ReferralLeadResponse:
    lead = await submit_customer_kitchen_lead(
        session, customer_id=customer.id, data=body, publisher=publisher
    )
    return lead_to_response(lead)


@router.post(
    "/customers/me/referrals/bulk",
    response_model=BulkReferralResult,
    summary="Bulk-add kitchen referral rows (JSON)",
    responses={401: RESP_401, 403: RESP_403, 422: RESP_422},
)
async def customer_refer_bulk(
    body: BulkReferralRequest,
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> BulkReferralResult:
    return await bulk_submit_customer(
        session, customer_id=customer.id, rows=body.rows, publisher=publisher
    )


@router.get(
    "/customers/me/referrals/template.csv",
    summary="Download Excel-compatible CSV template for kitchen referrals",
    responses={401: RESP_401},
)
async def customer_referral_template(
    customer: Annotated[Customer, Depends(get_current_customer)],
) -> Response:
    _ = customer
    return Response(
        content=csv_template(CUSTOMER_TEMPLATE_HEADERS),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="kitchcu-refer-kitchens-template.csv"'
        },
    )


@router.post(
    "/customers/me/referrals/upload",
    response_model=BulkReferralResult,
    summary="Upload CSV/Excel-exported file of kitchen referrals",
    responses={401: RESP_401, 403: RESP_403, 422: RESP_422},
)
async def customer_refer_upload(
    customer: Annotated[Customer, Depends(get_current_customer)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    file: UploadFile = File(...),
) -> BulkReferralResult:
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    rows = parse_csv_rows(raw, require_kitchen_name=True)
    return await bulk_submit_customer(
        session, customer_id=customer.id, rows=rows, publisher=publisher
    )


@router.get(
    "/owners/me/referrals",
    response_model=ReferralDashboardResponse,
    summary="Owner referral dashboard (customer leads + SaaS credit)",
    responses={401: RESP_401},
)
async def owner_referral_dashboard(
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReferralDashboardResponse:
    return await credit_dashboard(
        session,
        beneficiary_type="owner",
        beneficiary_id=owner.id,
        direction="kitchen_to_customer",
    )


@router.post(
    "/owners/me/referrals/customers",
    response_model=ReferralLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Refer a customer to onboard / order",
    responses={401: RESP_401, 403: RESP_403, 422: RESP_422},
)
async def owner_refer_customer(
    body: OwnerCustomerReferralCreate,
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> ReferralLeadResponse:
    lead = await submit_owner_customer_lead(
        session, owner_id=owner.id, data=body, publisher=publisher
    )
    return lead_to_response(lead)


@router.post(
    "/owners/me/referrals/bulk",
    response_model=BulkReferralResult,
    summary="Bulk-add customer referral rows (JSON)",
    responses={401: RESP_401, 403: RESP_403, 422: RESP_422},
)
async def owner_refer_bulk(
    body: BulkReferralRequest,
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> BulkReferralResult:
    if body.kitchen_id is None:
        raise HTTPException(status_code=422, detail="kitchen_id required for owner bulk referral")
    return await bulk_submit_owner(
        session,
        owner_id=owner.id,
        kitchen_id=body.kitchen_id,
        rows=body.rows,
        publisher=publisher,
    )


@router.get(
    "/owners/me/referrals/template.csv",
    summary="Download Excel-compatible CSV template for customer referrals",
    responses={401: RESP_401},
)
async def owner_referral_template(
    owner: Annotated[Owner, Depends(get_current_owner)],
) -> Response:
    _ = owner
    return Response(
        content=csv_template(OWNER_TEMPLATE_HEADERS),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="kitchcu-refer-customers-template.csv"'
        },
    )


@router.post(
    "/owners/me/referrals/upload",
    response_model=BulkReferralResult,
    summary="Upload CSV of customer referrals",
    responses={401: RESP_401, 403: RESP_403, 422: RESP_422},
)
async def owner_refer_upload(
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    kitchen_id: uuid.UUID,
    file: UploadFile = File(...),
) -> BulkReferralResult:
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    rows = parse_csv_rows(raw, require_kitchen_name=False)
    return await bulk_submit_owner(
        session,
        owner_id=owner.id,
        kitchen_id=kitchen_id,
        rows=rows,
        publisher=publisher,
    )
