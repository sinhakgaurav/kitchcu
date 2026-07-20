"""Identity service client — subscription sync + platform admin audit (no cross-schema writes)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

import httpx

from ckac_common.config import get_settings
from ckac_common.internal_auth import resolve_internal_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


async def sync_owner_subscription(
    owner_id: uuid.UUID,
    *,
    plan_tier: str,
    subscription_expires_at: datetime,
) -> None:
    """Notify identity to update owner subscription fields after billing activation."""
    url = (
        f"{settings.identity_service_url.rstrip('/')}"
        f"/api/v1/internal/owners/{owner_id}/subscription"
    )
    payload = {
        "plan_tier": plan_tier,
        "subscription_status": "active",
        "subscription_expires_at": subscription_expires_at.isoformat(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.patch(
            url,
            json=payload,
            headers={"X-Internal-Key": resolve_internal_api_key()},
        )
        response.raise_for_status()


async def apply_owner_referral_credit(
    owner_id: uuid.UUID,
    *,
    charge_amount_inr: float,
) -> dict[str, float]:
    """Apply referral credit against SaaS charge; returns applied/remaining amounts."""
    url = (
        f"{settings.identity_service_url.rstrip('/')}"
        f"/api/v1/internal/referrals/apply-owner-credit"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json={
                    "owner_id": str(owner_id),
                    "charge_amount_inr": charge_amount_inr,
                },
                headers={"X-Internal-Key": resolve_internal_api_key()},
            )
            if response.status_code >= 400:
                logger.warning(
                    "referral credit apply failed status=%s body=%s",
                    response.status_code,
                    response.text[:200],
                )
                return {
                    "applied_inr": 0.0,
                    "remaining_charge_inr": float(charge_amount_inr),
                    "balance_after_inr": 0.0,
                }
            data = response.json()
            return {
                "applied_inr": float(data.get("applied_inr") or 0),
                "remaining_charge_inr": float(
                    data.get("remaining_charge_inr") or charge_amount_inr
                ),
                "balance_after_inr": float(data.get("balance_after_inr") or 0),
            }
    except Exception as exc:
        logger.warning("billing→identity referral credit failed: %s", exc)
        return {
            "applied_inr": 0.0,
            "remaining_charge_inr": float(charge_amount_inr),
            "balance_after_inr": 0.0,
        }


async def record_remote_admin_audit(
    *,
    actor_admin_id: uuid.UUID | None,
    actor_email: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    kitchen_id: uuid.UUID | None = None,
    summary: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """Best-effort audit write into identity (never fails the billing mutation)."""
    url = f"{settings.identity_service_url.rstrip('/')}/api/v1/internal/admin-audit"
    payload = {
        "actor_admin_id": str(actor_admin_id) if actor_admin_id else None,
        "actor_email": actor_email,
        "actor_role": actor_role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "kitchen_id": str(kitchen_id) if kitchen_id else None,
        "summary": summary,
        "before": before,
        "after": after,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"X-Internal-Key": resolve_internal_api_key()},
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("billing→identity admin audit failed: %s", exc)
