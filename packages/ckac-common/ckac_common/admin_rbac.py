"""Shared platform-admin RBAC checks (cross-service)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

KNOWN_ROLES = ("superadmin", "ops", "support", "finance")

# Tab → minimum permission (write implies read for resource:action pairs)
TAB_PERMISSIONS: dict[str, str] = {
    "overview": "kitchens:read",
    "kitchens": "kitchens:read",
    "owners": "owners:write",  # ops has owners:write; support lacks — hide owners tab
    "customers": "customers:read",
    "orders": "kitchens:read",
    "refunds": "refunds:read",
    "tickets": "tickets:write",
    "packages": "packages:read",
    "employees": "employees:read",
    "api-keys": "api_keys:write",
    "control": "flags:read",
    "audit": "audit:read",
    "referrals": "referrals:read",
}


async def load_permissions_for_role(session: AsyncSession, role: str) -> set[str]:
    try:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT permission_code
                    FROM ckac_identity.admin_role_permissions
                    WHERE role = :role
                    """
                ),
                {"role": role},
            )
        ).scalars().all()
    except Exception:
        return {"*"} if role == "superadmin" else set()
    grants = {str(r) for r in rows}
    if not grants and role == "superadmin":
        return {"*"}
    return grants


def role_has_permission(grants: set[str], required: str) -> bool:
    if "*" in grants:
        return True
    if required in grants:
        return True
    if required.endswith(":read"):
        write = required[:-5] + ":write"
        if write in grants:
            return True
    return False


async def assert_admin_permission(
    session: AsyncSession,
    *,
    role: str,
    permission: str,
) -> None:
    grants = await load_permissions_for_role(session, role)
    if not role_has_permission(grants, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {permission}",
        )


def tabs_for_permissions(grants: set[str]) -> list[str]:
    if "*" in grants:
        return list(TAB_PERMISSIONS.keys())
    return [tab for tab, perm in TAB_PERMISSIONS.items() if role_has_permission(grants, perm)]
