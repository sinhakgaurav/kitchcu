#!/usr/bin/env python3
"""Fail if any Alembic down_revision points at a missing revision id."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"

REV_RE = re.compile(
    r"^revision(?:\s*:\s*[^=\n]+)?\s*=\s*[\"']([^\"']+)[\"']",
    re.M,
)
DOWN_RE = re.compile(
    r"^down_revision(?:\s*:\s*[^=\n]+)?\s*=\s*(None|[\"'][^\"']+[\"'])",
    re.M,
)


def check_service(svc: Path) -> list[str]:
    versions = svc / "alembic" / "versions"
    if not versions.is_dir():
        return []
    revs: dict[str, str] = {}
    downs: dict[str, str | None] = {}
    for path in versions.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        m = REV_RE.search(text)
        d = DOWN_RE.search(text)
        if not m:
            return [f"{svc.name}: {path.name}: missing revision id"]
        rid = m.group(1)
        revs[rid] = path.name
        if not d or d.group(1) == "None":
            downs[rid] = None
        else:
            downs[rid] = d.group(1).strip("\"'")
    errors: list[str] = []
    for rid, down in downs.items():
        if down and down not in revs:
            errors.append(
                f"{svc.name}: {revs[rid]} revision={rid!r} -> missing down_revision={down!r}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    for svc in sorted(SERVICES.iterdir()):
        if svc.is_dir():
            errors.extend(check_service(svc))
    if errors:
        print("Broken Alembic chains:")
        for e in errors:
            print(" ", e)
        return 1
    print("OK: all Alembic down_revision links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
