"""Platform employee RBAC — re-export shared helpers + identity convenience."""

from __future__ import annotations

from ckac_common.admin_rbac import (  # noqa: F401
    KNOWN_ROLES,
    assert_admin_permission,
    load_permissions_for_role,
    role_has_permission,
    tabs_for_permissions,
)
