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
    assert "scripts/seed-bulk-data.py" in script


def test_startup_installs_weekly_timer_and_bulk_oneshot() -> None:
    text = (GCP / "startup.sh").read_text(encoding="utf-8")
    assert "kitchcu-weekly-seed.timer" in text
    assert "kitchcu-bulk-seed.service" in text
    assert "infra/gcp-vm/bulk-seed.sh" in text
