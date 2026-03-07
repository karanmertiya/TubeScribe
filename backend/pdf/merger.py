"""Build an index page PDF and merge multiple PDFs into one."""
from __future__ import annotations
import datetime
import re
from io import BytesIO

from pypdf import PdfWriter
from weasyprint import HTML as WP

from .renderer import _CSS, _safe   # reuse same stylesheet


_INDEX_EXTRA = """
.index-page { page-break-after: always; }
.index-page > h1 { font-size: 24pt; text-align: center; border: none; margin-bottom: 8px; }
.index-subtitle {
  text-align: center; color: var(--muted); margin-bottom: 36px;
  font-family: 'JetBrains Mono', monospace; font-size: 9pt;
}
.index-item {
  display: flex; align-items: baseline; gap: 8px;
  padding: 10px 0; border-bottom: 1px dashed var(--border); font-size: 11pt;
}
.index-num  { color: var(--muted); font-family: 'JetBrains Mono', monospace; font-size: 9pt; min-width: 28px; }
.index-dots { flex: 1; border-bottom: 1px dotted var(--border); margin: 0 6px 3px; }
"""


def build_index(playlist_title: str, video_titles: list[str]) -> bytes:
    """Generate a styled table-of-contents cover page."""
    ts    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    items = "".join(
        f'<div class="index-item">'
        f'  <span class="index-num">{i+1:02d}</span>'
        f'  <span>{_safe(t)}</span>'
        f'  <span class="index-dots"></span>'
        f'</div>'
        for i, t in enumerate(video_titles)
    )
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>{_CSS}{_INDEX_EXTRA}</style></head>
<body>
  <div class="index-page">
    <h1>📚 Course Notes</h1>
    <p class="index-subtitle">{_safe(playlist_title)} &nbsp;·&nbsp; {len(video_titles)} videos &nbsp;·&nbsp; {ts}</p>
    {items}
  </div>
</body></html>"""
    buf = BytesIO()
    WP(string=html).write_pdf(buf)
    return buf.getvalue()


def merge(pdf_list: list[bytes]) -> bytes:
    """Merge a list of PDF byte-strings into a single PDF."""
    writer = PdfWriter()
    for b in pdf_list:
        writer.append(BytesIO(b))
    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()
