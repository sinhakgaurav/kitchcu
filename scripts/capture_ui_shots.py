"""Capture UI screenshots via CDP JSON dumps + convert PDF JPEG variants."""
from __future__ import annotations

import base64
import json
from pathlib import Path

from PIL import Image

UI = Path(r"e:\projects\CKAC\docs\assets\ui")
LOGS = Path(r"C:\Users\Trouble Zone\.cursor\browser-logs")


def latest_cdp_png() -> Path | None:
    files = sorted(LOGS.glob("cdp-response-Page.captureScreenshot-*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def save_from_cdp(out: Path) -> None:
    src = latest_cdp_png()
    if not src:
        raise SystemExit("No CDP screenshot found")
    data = json.loads(src.read_text(encoding="utf-8"))
    b64 = data.get("data") or data.get("result", {}).get("data")
    if not b64:
        raise SystemExit(f"No image data in {src}")
    out.write_bytes(base64.b64decode(b64))
    print(f"wrote {out} ({out.stat().st_size} bytes) from {src.name}")


def to_pdf_jpg(stem: str) -> None:
    png = UI / f"{stem}.png"
    if not png.is_file():
        print("skip missing", png)
        return
    im = Image.open(png).convert("RGB")
    # Slight top pad so cropped hero branding isn't flush in PDF embeds
    pad_top = 24
    canvas = Image.new("RGB", (im.width, im.height + pad_top), (247, 244, 239))
    canvas.paste(im, (0, pad_top))
    out = UI / f"{stem}-pdf.jpg"
    canvas.save(out, "JPEG", quality=82, optimize=True)
    print(f"jpg {out.name} {out.stat().st_size}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "save":
        stem = sys.argv[2]
        save_from_cdp(UI / f"{stem}.png")
    for stem in [
        "01-portal-home",
        "02-customer-home",
        "03-kitchen-login",
        "04-owner-dashboard",
        "05-admin-overview",
    ]:
        to_pdf_jpg(stem)
