"""Master third-party integrations kill-switch helpers."""

from ckac_common.platform_config import (
    THIRD_PARTY_INTEGRATIONS_FLAG,
    env_third_party_override,
    third_party_integrations_enabled_sync,
)


def test_flag_key_stable():
    assert THIRD_PARTY_INTEGRATIONS_FLAG == "third_party_integrations"


def test_env_override_false(monkeypatch):
    monkeypatch.setenv("THIRD_PARTY_INTEGRATIONS", "0")
    assert env_third_party_override() is False
    assert third_party_integrations_enabled_sync(default=True) is False


def test_env_override_true(monkeypatch):
    monkeypatch.setenv("THIRD_PARTY_INTEGRATIONS", "true")
    assert env_third_party_override() is True
    assert third_party_integrations_enabled_sync(default=False) is True


def test_sync_default_off_without_env(monkeypatch):
    monkeypatch.delenv("THIRD_PARTY_INTEGRATIONS", raising=False)
    assert env_third_party_override() is None
    assert third_party_integrations_enabled_sync(default=False) is False
