"""Platform employee RBAC — roles, permissions, enforcement."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

KNOWN_ROLES = ("superadmin", "ops", "support", "finance")


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
        # Pre-migration / empty schema — bootstrap superadmin only
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
