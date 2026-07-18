"""RBAC helpers — unit (no DB)."""

from app.rbac import role_has_permission, tabs_for_permissions


def test_wildcard_grants_all():
    assert role_has_permission({"*"}, "employees:write")
    assert role_has_permission({"*"}, "packages:read")


def test_exact_permission():
    assert role_has_permission({"employees:read"}, "employees:read")
    assert not role_has_permission({"employees:read"}, "employees:write")


def test_write_implies_read():
    assert role_has_permission({"kitchens:write"}, "kitchens:read")
    assert role_has_permission({"packages:write"}, "packages:read")


def test_empty_grants_deny():
    assert not role_has_permission(set(), "employees:read")


def test_tabs_for_ops_exclude_api_keys():
    tabs = tabs_for_permissions({"kitchens:write", "owners:write", "packages:read"})
    assert "kitchens" in tabs
    assert "owners" in tabs
    assert "packages" in tabs
    assert "api-keys" not in tabs
    assert "employees" not in tabs
