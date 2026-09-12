"""GCP seed units must point at /opt/ckac — the VM clone path used by startup.sh.

A nested /opt/ckac/CKAC path would make weekly cron and bulk seed fail silently
on production after every redeploy.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GCP = ROOT / "infra" / "gcp-vm"
WRONG = "/opt/ckac/CKAC"
RIGHT = "/opt/ckac"


def test_startup_clones_to_opt_ckac() -> None:
    text = (GCP / "startup.sh").read_text(encoding="utf-8")
    assert "REPO_DIR=/opt/ckac" in text
    assert WRONG not in text


def test_weekly_units_use_opt_ckac() -> None:
    service = (GCP / "kitchcu-weekly-seed.service").read_text(encoding="utf-8")
    script = (GCP / "weekly-seed.sh").read_text(encoding="utf-8")
    assert WRONG not in service
    assert WRONG not in script
    assert "ExecStart=/bin/bash /opt/ckac/infra/gcp-vm/weekly-seed.sh" in service
    assert 'CKAC_REPO_DIR:-/opt/ckac}' in script


def test_bulk_units_use_opt_ckac() -> None:
    service = (GCP / "kitchcu-bulk-seed.service").read_text(encoding="utf-8")
    script = (GCP / "bulk-seed.sh").read_text(encoding="utf-8")
    assert WRONG not in service
    assert WRONG not in script
    assert "ExecStart=/bin/bash /opt/ckac/infra/gcp-vm/bulk-seed.sh" in service
    assert 'CKAC_REPO_DIR:-/opt/ckac}' in script
    assert "scripts/seed-all.sh" in script
    assert 'CKAC_BULK_MONTHS="${CKAC_BULK_MONTHS:-6}"' in script
    assert 'CKAC_FEATURE_VOLUME="${CKAC_FEATURE_VOLUME:-1}"' in script
    assert "CKAC_WEEKLY_MANIFEST" in script


def test_seed_all_runs_every_seeder() -> None:
    sh = (ROOT / "scripts" / "seed-all.sh").read_text(encoding="utf-8")
    ps1 = (ROOT / "scripts" / "seed-all.ps1").read_text(encoding="utf-8")
    for text in (sh, ps1):
        assert "seed-dev-data.py" in text
        assert "seed-bulk-data.py" in text
        assert "weekly_test_data.py" in text
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "seed-dev-data.py" in compose
    assert "seed-bulk-data.py" in compose
    assert "weekly_test_data.py" in compose


def test_weekly_timer_runs_saturday_morning_ist() -> None:
    """Saturday 03:30 IST == Friday 22:00 UTC on the VM clock."""
    timer = (GCP / "kitchcu-weekly-seed.timer").read_text(encoding="utf-8")
    assert "OnCalendar=Fri *-*-* 22:00:00 UTC" in timer
    assert "Saturday" in timer


def test_dry_run_smoke_skips_feature_volume() -> None:
    text = (GCP / "dry-run-local.ps1").read_text(encoding="utf-8")
    assert 'CKAC_FEATURE_VOLUME = "0"' in text
    assert 'CKAC_BULK_KITCHENS = "1"' in text


def test_startup_installs_weekly_timer_and_bulk_oneshot() -> None:
    text = (GCP / "startup.sh").read_text(encoding="utf-8")
    assert "kitchcu-weekly-seed.timer" in text
    assert "kitchcu-bulk-seed.service" in text
    assert "infra/gcp-vm/bulk-seed.sh" in text
