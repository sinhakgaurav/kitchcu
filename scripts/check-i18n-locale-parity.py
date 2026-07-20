#!/usr/bin/env python3
"""Ensure every website i18n locale has the same leaf keys as en.json.

Exit codes:
  0 — PASS (all locales match en.json key set)
  1 — FAIL (missing/extra keys or invalid JSON)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LOCALES_DIR = (
    Path(__file__).resolve().parents[1]
    / "apps"
    / "website"
    / "src"
    / "i18n"
    / "locales"
)

LOCALE_FILES = (
    "hi.json",
    "mr.json",
    "ta.json",
    "te.json",
    "kn.json",
    "ml.json",
    "bn.json",
    "gu.json",
    "pa.json",
    "bho.json",
    "mai.json",
)


def flatten(node: object, prefix: str = "") -> dict[str, str]:
    if not isinstance(node, dict):
        raise ValueError(f"expected object at {prefix or '<root>'}")
    out: dict[str, str] = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(flatten(value, path))
        elif isinstance(value, str):
            out[path] = value
        else:
            raise ValueError(f"leaf must be string at {path}")
    return out


def load_flat(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return flatten(data)


def main() -> int:
    en_path = LOCALES_DIR / "en.json"
    if not en_path.is_file():
        print(f"FAIL: missing source of truth {en_path}")
        return 1

    try:
        en_keys = set(load_flat(en_path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot load en.json: {exc}")
        return 1

    print(f"en.json keys: {len(en_keys)}")
    failed = False

    for name in LOCALE_FILES:
        path = LOCALES_DIR / name
        if not path.is_file():
            print(f"{name}: FAIL missing file")
            failed = True
            continue
        try:
            keys = set(load_flat(path))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"{name}: FAIL invalid JSON/structure: {exc}")
            failed = True
            continue

        missing = sorted(en_keys - keys)
        extra = sorted(keys - en_keys)
        status = "PASS" if not missing and not extra else "FAIL"
        print(f"{name}: keys={len(keys)} {status}")
        if missing:
            print(f"  missing ({len(missing)}): {', '.join(missing[:12])}"
                  + (" …" if len(missing) > 12 else ""))
            failed = True
        if extra:
            print(f"  extra ({len(extra)}): {', '.join(extra[:12])}"
                  + (" …" if len(extra) > 12 else ""))
            failed = True

    if failed:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
