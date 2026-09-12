"""Seed SQL must land in the database the gateway is actually using.

The GCP parity dry-run (`infra/gcp-vm/dry-run-local.ps1`, which the pre-push gate
runs) leaves a second Postgres container up. `docker ps` happened to list it
first, so the bulk seeder pushed its backdating into `ckac-gcp-dry-postgres-1`
while every API call went to the dev gateway on :18000. Every row matched in the
wrong database, psql exited 0, and the seeder reported success while the dev data
stayed undated.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import seed_common  # noqa: E402

DEV = "ckac-postgres-1"
DRY_RUN = "ckac-gcp-dry-postgres-1"
GCP = "gcp-vm-postgres-1"


def fake_ps(monkeypatch, names: list[str]) -> None:
    monkeypatch.setattr(
        seed_common, "_docker_container_names", lambda: list(names), raising=False
    )


def test_dev_container_wins_when_dry_run_stack_is_also_up(monkeypatch) -> None:
    """docker ps order must not decide which database gets seeded."""
    fake_ps(monkeypatch, [DRY_RUN, "ckac-gcp-dry-gateway-1", DEV, "ckac-gateway-1"])
    assert seed_common.resolve_postgres_container() == DEV


def test_dev_container_wins_regardless_of_listing_order(monkeypatch) -> None:
    fake_ps(monkeypatch, [DEV, DRY_RUN])
    assert seed_common.resolve_postgres_container() == DEV


def test_gcp_vm_container_used_when_it_is_the_only_stack(monkeypatch) -> None:
    """On the VM there is no dev container, so the prod one must still resolve."""
    fake_ps(monkeypatch, ["gcp-vm-gateway-1", GCP, "gcp-vm-redis-1"])
    assert seed_common.resolve_postgres_container() == GCP


def test_dry_run_container_used_when_it_is_the_only_stack(monkeypatch) -> None:
    fake_ps(monkeypatch, [DRY_RUN, "ckac-gcp-dry-gateway-1"])
    assert seed_common.resolve_postgres_container() == DRY_RUN


def test_explicit_override_always_wins(monkeypatch) -> None:
    monkeypatch.setenv("CKAC_POSTGRES_CONTAINER", "my-postgres")
    fake_ps(monkeypatch, [DEV, DRY_RUN])
    assert seed_common.resolve_postgres_container() == "my-postgres"


def test_falls_back_to_dev_name_when_docker_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("CKAC_POSTGRES_CONTAINER", raising=False)
    fake_ps(monkeypatch, [])
    assert seed_common.resolve_postgres_container() == DEV


def test_underscore_compose_naming_still_resolves(monkeypatch) -> None:
    monkeypatch.delenv("CKAC_POSTGRES_CONTAINER", raising=False)
    fake_ps(monkeypatch, ["ckac_postgres_1"])
    assert seed_common.resolve_postgres_container() == "ckac_postgres_1"
