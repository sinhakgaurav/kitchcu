"""Shared PDF layout helpers for Kitchcu guide documents."""

from pathlib import Path

from fpdf import FPDF

from pdf_common import ACCENT, DARK, GRAY, LIGHT_BG, ORANGE, WHITE, ascii_safe


class GuidePDF(FPDF):
    def __init__(self, title: str, version: str, date: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self._doc_title = title
        self._version = version
        self._date = date
        self._chapter = 0

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(
            0,
            8,
            ascii_safe(f"{self._doc_title} v{self._version} | {self._date}"),
            align="C",
        )

    def cover(
        self,
        subtitle: str,
        audience: str,
        bullets: list[str],
        lenses: list[str],
    ):
        self.add_page()
        self.set_fill_color(*LIGHT_BG)
        self.rect(0, 0, 210, 297, "F")
        self.set_xy(20, 48)
        self.set_font("Helvetica", "B", 40)
        self.set_text_color(*ORANGE)
        self.cell(0, 14, "Kitchcu")
        self.ln(16)
        self.set_x(20)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*DARK)
        self.multi_cell(170, 8, ascii_safe(subtitle))
        self.ln(4)
        self.set_x(20)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY)
        self.multi_cell(
            170,
            6,
            "Kitchcu cloud kitchen platform",
        )
        self.ln(6)
        self.set_x(20)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*ACCENT)
        self.cell(0, 5, ascii_safe(audience))
        self.ln(8)
        self.set_x(20)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ORANGE)
        self.cell(0, 6, "Three executive lenses:")
        self.ln(6)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*DARK)
        for lens in lenses:
            self.set_x(22)
            self.multi_cell(166, 5, f"- {ascii_safe(lens)}")
        self.ln(4)
        self.set_x(20)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK)
        self.cell(0, 6, "This guide includes:")
        self.ln(5)
        self.set_font("Helvetica", "", 9)
        for b in bullets:
            self.set_x(22)
            self.multi_cell(166, 5, f"- {ascii_safe(b)}")
        self.set_xy(20, 268)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*GRAY)
        self.cell(0, 5, f"Version {self._version}  |  {self._date}  |  Confidential")

    def toc(self, sections: list[tuple[str, list[str]]]):
        self.add_page()
        self.set_xy(20, 22)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*ORANGE)
        self.cell(0, 9, "Table of Contents")
        self.ln(10)
        for part_title, items in sections:
            self.set_x(20)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*ACCENT)
            self.multi_cell(170, 6, ascii_safe(part_title))
            self.ln(1)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*DARK)
            for item in items:
                self.set_x(24)
                self.multi_cell(166, 5, ascii_safe(item))
            self.ln(3)

    def lens_part(self, lens: str, part_num: int, title: str):
        self.add_page()
        self.set_fill_color(*ORANGE)
        self.rect(0, 0, 210, 36, "F")
        self.set_xy(20, 10)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*WHITE)
        self.cell(0, 6, ascii_safe(f"{lens}  |  PART {part_num}"))
        self.ln(8)
        self.set_x(20)
        self.set_font("Helvetica", "B", 20)
        self.cell(0, 10, ascii_safe(title))
        self.ln(4)
        self._chapter = 0

    def chapter(self, title: str):
        self._chapter += 1
        if self.get_y() > 245:
            self.add_page()
            self.set_y(18)
        else:
            self.ln(2.5)
        self.set_x(20)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*ORANGE)
        self.multi_cell(170, 7, ascii_safe(f"{self._chapter}. {title}"))
        self.ln(1)

    def section(self, title: str):
        if self.get_y() > 265:
            self.add_page()
            self.set_y(18)
        self.set_x(20)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ACCENT)
        self.multi_cell(170, 6, ascii_safe(title))
        self.ln(0.5)

    def body(self, text: str, size: int = 9):
        self.set_x(20)
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        self.multi_cell(170, 5, ascii_safe(text))
        self.ln(1)

    def bullets(self, items: list[str], size: int = 9):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*DARK)
        for item in items:
            if self.get_y() > 272:
                self.add_page()
                self.set_y(18)
            self.set_x(22)
            self.cell(3, 5, "-")
            self.multi_cell(165, 5, ascii_safe(item))
        self.ln(1)

    def mono(self, text: str, size: int = 7, max_lines: int = 36, line_h: float = 3.5):
        """Render monospaced diagram/code block. Splits across pages if tall."""
        lines = ascii_safe(text.strip()).split("\n")
        remaining = lines
        while remaining:
            if self.get_y() > 250:
                self.add_page()
            avail = min(max_lines, max(8, int((275 - self.get_y()) / line_h) - 1))
            chunk = remaining[:avail]
            remaining = remaining[avail:]
            y = self.get_y()
            h = len(chunk) * line_h + 5
            self.set_fill_color(*LIGHT_BG)
            self.rect(20, y, 170, h, "F")
            self.set_xy(22, y + 2)
            self.set_font("Courier", "", size)
            self.set_text_color(*DARK)
            for line in chunk:
                self.cell(166, line_h, line[:100])
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
            widths = [170 // n] * n
            widths[-1] += 170 - sum(widths)
        if self.get_y() > 240:
            self.add_page()

        def _header_row():
            self.set_x(20)
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
            if self.get_y() > 276:
                self.add_page()
                _header_row()
                self.set_font("Helvetica", "", size)
                self.set_text_color(*DARK)
            self.set_x(20)
            if fill:
                self.set_fill_color(*LIGHT_BG)
            for i, cell in enumerate(row):
                self.cell(widths[i], 5, ascii_safe(cell)[:40], border=1, fill=fill)
            self.ln()
            fill = not fill
        self.ln(2)

    def stat_boxes(self, stats: list[tuple[str, str]]):
        if self.get_y() > 245:
            self.add_page()
        y = self.get_y() + 1
        w = 170 / len(stats)
        x = 20
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
        if self.get_y() > 260:
            self.add_page()
        self.set_x(20)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*DARK)
        self.multi_cell(170, 5, ascii_safe(f'"{text}"'))
        self.ln(3)

    def figure(self, path: str | Path, caption: str, max_h: float = 88):
        """Embed a screenshot/diagram with caption. Leaves top padding; tight gap after image."""
        img = Path(path)
        if not img.is_file():
            self.body(f"[Missing figure: {img.name}] — {caption}", size=8)
            return
        if self.get_y() > 230 - min(max_h, 36):
            self.add_page()
            self.set_y(18)
        elif self.get_y() < 16:
            self.set_y(18)
        self.set_x(20)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*ACCENT)
        self.multi_cell(170, 4, ascii_safe(caption))
        self.ln(0.5)
        y = self.get_y()
        try:
            from PIL import Image as PILImage

            with PILImage.open(img) as im:
                w_px, h_px = im.size
            aspect = h_px / max(w_px, 1)
            w_mm = 170.0
            h_mm = min(max_h, w_mm * aspect)
            if y + h_mm > 272:
                self.add_page()
                self.set_y(18)
                y = self.get_y()
            self.image(str(img), x=20, y=y, w=w_mm, h=h_mm)
            self.set_y(y + h_mm + 2.5)
        except Exception:
            self.image(str(img), x=20, w=170)
            self.ln(2)
