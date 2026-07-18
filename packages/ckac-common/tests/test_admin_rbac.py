"""Unit tests for shared admin RBAC helpers."""

from ckac_common.admin_rbac import role_has_permission, tabs_for_permissions, TAB_PERMISSIONS


def test_wildcard_grants_all_tabs():
    tabs = tabs_for_permissions({"*"})
    assert set(tabs) == set(TAB_PERMISSIONS.keys())


def test_support_tabs_exclude_secrets_and_employees():
    grants = {"tickets:write", "kitchens:read", "customers:read"}
    tabs = tabs_for_permissions(grants)
    assert "tickets" in tabs
    assert "overview" in tabs
    assert "kitchens" in tabs
    assert "customers" in tabs
    assert "api-keys" not in tabs
    assert "employees" not in tabs
    assert "packages" not in tabs
    assert "refunds" not in tabs


def test_finance_tabs_include_packages_and_refunds():
    grants = {"packages:write", "refunds:read", "kitchens:read"}
    tabs = tabs_for_permissions(grants)
    assert "packages" in tabs
    assert "refunds" in tabs
    assert "overview" in tabs
    assert "api-keys" not in tabs


def test_write_implies_read_for_tabs():
    assert role_has_permission({"packages:write"}, "packages:read")
    tabs = tabs_for_permissions({"packages:write"})
    assert "packages" in tabs


def test_audit_tab_requires_audit_read():
    assert "audit" in tabs_for_permissions({"audit:read"})
    assert "audit" not in tabs_for_permissions({"tickets:write", "kitchens:read"})
