#!/usr/bin/env python3
"""Fill missing locale leaves from en.json (keeps existing translations).

Also applies Hindi overlays from scripts/i18n_locale_data/hi_overlays.json when present.
Run: python scripts/sync-i18n-missing-keys.py
Then: python scripts/check-i18n-locale-parity.py
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "apps" / "website" / "src" / "i18n" / "locales"
OVERLAY_HI = Path(__file__).resolve().parent / "i18n_locale_data" / "hi_overlays.json"

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
    assert isinstance(node, dict)
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


def unflatten(flat: dict[str, str]) -> dict:
    root: dict = {}
    for path, value in flat.items():
        parts = path.split(".")
        cur = root
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
    return root


def deep_merge(base: dict, overlay: dict) -> dict:
    out = deepcopy(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def main() -> int:
    en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
    en_flat = flatten(en)
    hi_overlay = {}
    if OVERLAY_HI.is_file():
        hi_overlay = flatten(json.loads(OVERLAY_HI.read_text(encoding="utf-8")))

    for name in LOCALE_FILES:
        path = LOCALES / name
        loc = json.loads(path.read_text(encoding="utf-8"))
        loc_flat = flatten(loc)
        missing = sorted(set(en_flat) - set(loc_flat))
        for key in missing:
            loc_flat[key] = en_flat[key]
        if name == "hi.json" and hi_overlay:
            loc_flat.update(hi_overlay)
        # Drop extras not in en
        for key in list(loc_flat):
            if key not in en_flat:
                del loc_flat[key]
        rebuilt = unflatten(loc_flat)
        path.write_text(json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{name}: filled {len(missing)} missing keys")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
