"""Package feature entitlement helpers."""

import pytest

from ckac_common.platform_config import feature_http_status, hard_mode_missing_feature_sql


def test_feature_http_status_package_missing():
    exc = ValueError("Feature 'loyalty_crm' is not included in this kitchen's package")
    assert feature_http_status(exc) == 403


def test_hard_mode_sql_includes_feature_and_alias():
    sql = hard_mode_missing_feature_sql("k.id", "discovery")
    assert "k.id" in sql
    assert "discovery" in sql
    assert "kitchen_packages" in sql


def test_hard_mode_sql_rejects_injection():
    with pytest.raises(ValueError):
        hard_mode_missing_feature_sql("k.id", "discovery'; drop table x;--")
