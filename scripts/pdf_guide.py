"""Shared PDF layout helpers for Kitchcu guide documents.

Layout contract (v3.2+):
- Top content margin clears the running header (no overlap with titles/figures).
- Part divider pages draw a full-width orange band; body starts below it.
- Figures: caption above image; page-break before media if it would collide with footer.
- Chapter/section helpers force a new page when near the bottom margin.
"""

from pathlib import Path

from fpdf import FPDF

from pdf_common import ACCENT, DARK, GRAY, LIGHT_BG, ORANGE, WHITE, ascii_safe

# Geometry (A4 = 210 x 297 mm)
MARGIN_LEFT = 20
MARGIN_RIGHT = 20
MARGIN_TOP = 24  # clears running header
MARGIN_BOTTOM = 20
CONTENT_WIDTH = 210 - MARGIN_LEFT - MARGIN_RIGHT  # 170
FOOTER_Y = 283
BODY_MAX_Y = 272
PART_BAND_H = 38
PART_BODY_Y = 46


class GuidePDF(FPDF):
    def __init__(self, title: str, version: str, date: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=MARGIN_BOTTOM)
        self.set_margins(MARGIN_LEFT, MARGIN_TOP, MARGIN_RIGHT)
        self._doc_title = title
        self._version = version
        self._date = date
        self._chapter = 0
        self._skip_running_header = True  # cover / part pages
        self._part_label = ""

    def header(self):
        """Running header on body pages only — thin teal rule + short title."""
        if self._skip_running_header:
            return
        self.set_y(8)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GRAY)
        label = ascii_safe(self._part_label or self._doc_title)
        self.set_x(MARGIN_LEFT)
        self.cell(CONTENT_WIDTH * 0.62, 4, label[:70], align="L")
        self.cell(CONTENT_WIDTH * 0.38, 4, f"v{self._version}", align="R")
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.35)
        y = 14
        self.line(MARGIN_LEFT, y, MARGIN_LEFT + CONTENT_WIDTH, y)
        # Ensure body never starts under the rule
        self.set_y(MARGIN_TOP)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.set_x(MARGIN_LEFT)
        self.cell(
            CONTENT_WIDTH * 0.7,
            6,
            ascii_safe(f"{self._doc_title} v{self._version} | {self._date}"),
            align="L",
        )
        self.cell(CONTENT_WIDTH * 0.3, 6, f"{self.page_no()}", align="R")

    def _body_page(self):
        """Start a normal body page (running header on)."""
        self._skip_running_header = False
        self.add_page()
        self.set_y(MARGIN_TOP)

    def _ensure_space(self, need_mm: float):
        if self.get_y() + need_mm > BODY_MAX_Y:
            self._body_page()

    def cover(
        self,
        subtitle: str,
        audience: str,
        bullets: list[str],
        lenses: list[str],
    ):
        self._skip_running_header = True
        self.add_page()
        self.set_fill_color(*LIGHT_BG)
        self.rect(0, 0, 210, 297, "F")
        self.set_xy(MARGIN_LEFT, 48)
        self.set_font("Helvetica", "B", 40)
        self.set_text_color(*ORANGE)
        self.cell(0, 14, "Kitchcu")
        self.ln(16)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*DARK)
        self.multi_cell(CONTENT_WIDTH, 8, ascii_safe(subtitle))
        self.ln(4)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY)
        self.multi_cell(CONTENT_WIDTH, 6, "Kitchcu cloud kitchen platform")
        self.ln(6)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*ACCENT)
        self.multi_cell(CONTENT_WIDTH, 5, ascii_safe(audience))
        self.ln(6)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ORANGE)
        self.cell(0, 6, "Three executive lenses:")
        self.ln(6)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        for lens in lenses:
            self.set_x(MARGIN_LEFT + 2)
            self.multi_cell(CONTENT_WIDTH - 2, 5, f"- {ascii_safe(lens)}")
        self.ln(4)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK)
        self.cell(0, 6, "This guide includes:")
        self.ln(5)
        self.set_font("Helvetica", "", 9)
        for b in bullets:
            self.set_x(MARGIN_LEFT + 2)
            self.multi_cell(CONTENT_WIDTH - 2, 5, f"- {ascii_safe(b)}")
        self.set_xy(MARGIN_LEFT, 268)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*GRAY)
        self.cell(0, 5, f"Version {self._version}  |  {self._date}  |  Confidential")

    def toc(self, sections: list[tuple[str, list[str]]]):
        self._skip_running_header = False
        self._part_label = "Table of Contents"
        self.add_page()
        self.set_y(MARGIN_TOP)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*ORANGE)
        self.set_x(MARGIN_LEFT)
        self.cell(0, 9, "Table of Contents")
        self.ln(10)
        for part_title, items in sections:
            self._ensure_space(18)
            self.set_x(MARGIN_LEFT)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*ACCENT)
            self.multi_cell(CONTENT_WIDTH, 6, ascii_safe(part_title))
            self.ln(1)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*DARK)
            for item in items:
                self._ensure_space(8)
                self.set_x(MARGIN_LEFT + 4)
                self.multi_cell(CONTENT_WIDTH - 4, 5, ascii_safe(item))
            self.ln(3)

    def lens_part(self, lens: str, part_num: int, title: str):
        """Part divider — full-width orange band; body starts BELOW the band."""
        self._skip_running_header = True
        self.add_page()
        self.set_fill_color(*ORANGE)
        self.rect(0, 0, 210, PART_BAND_H, "F")
        self.set_xy(MARGIN_LEFT, 11)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*WHITE)
        self.cell(0, 6, ascii_safe(f"{lens}  |  PART {part_num}"))
        self.ln(8)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 18)
        # Constrain title to band so it never spills into body
        self.multi_cell(CONTENT_WIDTH, 8, ascii_safe(title)[:72])
        self.set_y(PART_BODY_Y)
        self._chapter = 0
        self._part_label = ascii_safe(f"Part {part_num} — {title}")[:60]
        # Following content uses running header on next pages
        self._skip_running_header = False

    def chapter(self, title: str):
        self._chapter += 1
        self._ensure_space(20)
        self.ln(2)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*ORANGE)
        self.multi_cell(CONTENT_WIDTH, 7, ascii_safe(f"{self._chapter}. {title}"))
        self.ln(1)

    def section(self, title: str):
        self._ensure_space(14)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ACCENT)
        self.multi_cell(CONTENT_WIDTH, 6, ascii_safe(title))
        self.ln(0.5)

    def body(self, text: str, size: int = 9):
        self._ensure_space(12)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        self.multi_cell(CONTENT_WIDTH, 5, ascii_safe(text))
        self.ln(1)

    def bullets(self, items: list[str], size: int = 9):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        for item in items:
            self._ensure_space(10)
            self.set_x(MARGIN_LEFT + 2)
            self.cell(3, 5, "-")
            self.multi_cell(CONTENT_WIDTH - 5, 5, ascii_safe(item))
        self.ln(1)

    def mono(self, text: str, size: int = 7, max_lines: int = 36, line_h: float = 3.5):
        lines = ascii_safe(text.strip()).split("\n")
        remaining = lines
        while remaining:
            self._ensure_space(24)
            avail = min(max_lines, max(8, int((BODY_MAX_Y - self.get_y()) / line_h) - 1))
            chunk = remaining[:avail]
            remaining = remaining[avail:]
            y = self.get_y()
            h = len(chunk) * line_h + 5
            self.set_fill_color(*LIGHT_BG)
            self.rect(MARGIN_LEFT, y, CONTENT_WIDTH, h, "F")
            self.set_xy(MARGIN_LEFT + 2, y + 2)
            self.set_font("Courier", "", size)
            self.set_text_color(*DARK)
            for line in chunk:
                self.cell(CONTENT_WIDTH - 4, line_h, line[:100])
                self.ln(line_h)
            self.set_y(y + h + 2)

    def table(
        self,
        headers: list[str],
        rows: list[list[str]],
        widths: list[int] | None = None,
        size: int = 7,
    ):
        if not widths:
            n = len(headers)
            widths = [CONTENT_WIDTH // n] * n
            widths[-1] += CONTENT_WIDTH - sum(widths)
        self._ensure_space(22)

        def _header_row():
            self.set_x(MARGIN_LEFT)
            self.set_font("Helvetica", "B", size)
            self.set_fill_color(*ORANGE)
            self.set_text_color(*WHITE)
            for i, h in enumerate(headers):
                self.cell(widths[i], 5.5, ascii_safe(h)[:32], border=1, fill=True)
            self.ln()

        _header_row()
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        fill = False
        for row in rows:
            if self.get_y() > BODY_MAX_Y - 6:
                self._body_page()
                _header_row()
                self.set_font("Helvetica", "", size)
                self.set_text_color(*DARK)
            self.set_x(MARGIN_LEFT)
            if fill:
                self.set_fill_color(*LIGHT_BG)
            for i, cell in enumerate(row):
                self.cell(widths[i], 5, ascii_safe(cell)[:40], border=1, fill=fill)
            self.ln()
            fill = not fill
        self.ln(2)

    def stat_boxes(self, stats: list[tuple[str, str]]):
        self._ensure_space(28)
        y = self.get_y() + 1
        w = CONTENT_WIDTH / max(len(stats), 1)
        x = MARGIN_LEFT
        for label, value in stats:
            self.set_xy(x, y)
            self.set_fill_color(*LIGHT_BG)
            self.rect(x, y, w - 3, 20, "F")
            self.set_xy(x + 3, y + 2)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*ORANGE)
            self.cell(w - 6, 7, ascii_safe(value))
            self.set_xy(x + 3, y + 11)
            self.set_font("Helvetica", "", 6)
            self.set_text_color(*GRAY)
            self.multi_cell(w - 6, 3.5, ascii_safe(label))
            x += w
        self.set_y(y + 24)

    def quote(self, text: str):
        self._ensure_space(16)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*DARK)
        self.multi_cell(CONTENT_WIDTH, 5, ascii_safe(f'"{text}"'))
        self.ln(3)

    def figure(self, path: str | Path, caption: str, max_h: float = 86):
        """Embed a screenshot with caption above — never under a header band."""
        img = Path(path)
        if not img.is_file():
            self.body(f"[Missing figure: {img.name}] -- {caption}", size=8)
            return

        # Estimate height so we break early instead of overlapping the footer
        est_h = max_h
        try:
            from PIL import Image as PILImage

            with PILImage.open(img) as im:
                w_px, h_px = im.size
            aspect = h_px / max(w_px, 1)
            est_h = min(max_h, CONTENT_WIDTH * aspect)
        except Exception:
            pass

        # Caption (~10mm) + image + gap
        self._ensure_space(est_h + 14)
        self.set_x(MARGIN_LEFT)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*ACCENT)
        self.multi_cell(CONTENT_WIDTH, 4, ascii_safe(caption))
        self.ln(1.2)
        y = self.get_y()
        try:
            from PIL import Image as PILImage

            with PILImage.open(img) as im:
                w_px, h_px = im.size
            aspect = h_px / max(w_px, 1)
            w_mm = float(CONTENT_WIDTH)
            h_mm = min(max_h, w_mm * aspect)
            if y + h_mm > BODY_MAX_Y:
                self._body_page()
                self.set_x(MARGIN_LEFT)
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*ACCENT)
                self.multi_cell(CONTENT_WIDTH, 4, ascii_safe(caption))
                self.ln(1.2)
                y = self.get_y()
            self.image(str(img), x=MARGIN_LEFT, y=y, w=w_mm, h=h_mm)
            self.set_y(y + h_mm + 4)
        except Exception:
            self.image(str(img), x=MARGIN_LEFT, w=CONTENT_WIDTH)
            self.ln(3)
