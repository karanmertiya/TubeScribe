"""Convert Markdown to a beautifully typeset PDF via WeasyPrint."""
from __future__ import annotations
import datetime
import re
from io import BytesIO

import markdown2
from weasyprint import HTML as WP

_CSS = """
/* Fonts are baked into the Docker image at /usr/local/share/fonts/tubescribe/
   — no outbound HTTP requests during PDF rendering.
   fc-cache is run at image build time so WeasyPrint finds them by family name. */
@font-face {
  font-family: 'Source Serif 4';
  font-style: normal;
  src: local('Source Serif 4'), url('/usr/local/share/fonts/tubescribe/SourceSerif4.ttf');
}
@font-face {
  font-family: 'Source Serif 4';
  font-style: italic;
  src: local('Source Serif 4 Italic'), url('/usr/local/share/fonts/tubescribe/SourceSerif4-Italic.ttf');
}
@font-face {
  font-family: 'JetBrains Mono';
  font-weight: normal;
  src: local('JetBrains Mono'), url('/usr/local/share/fonts/tubescribe/JetBrainsMono-Regular.ttf');
}
@font-face {
  font-family: 'JetBrains Mono';
  font-weight: 600;
  src: local('JetBrains Mono SemiBold'), url('/usr/local/share/fonts/tubescribe/JetBrainsMono-SemiBold.ttf');
}

:root {
  --ink:     #1a1a2e;
  --accent:  #0f3460;
  --accent2: #533483;
  --muted:   #64748b;
  --surface: #f8fafc;
  --border:  #e2e8f0;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 11.5pt; line-height: 1.8;
  color: var(--ink); background: white;
  padding: 54px 64px; max-width: 800px; margin: 0 auto;
}

.doc-header {
  border-bottom: 3px solid var(--accent);
  padding-bottom: 20px; margin-bottom: 32px;
}
.doc-header h1 {
  font-size: 22pt; font-weight: 700;
  color: var(--accent); line-height: 1.2; margin-bottom: 8px;
}
.doc-meta {
  font-size: 9pt; color: var(--muted);
  font-family: 'JetBrains Mono', monospace; letter-spacing: 0.03em;
}

h1 { font-size: 18pt; color: var(--accent); border-bottom: 2px solid var(--border); padding-bottom: 6px; margin: 36px 0 14px; }
h2 { font-size: 14pt; color: var(--accent); margin: 28px 0 10px; }
h3 { font-size: 12pt; color: var(--accent2); margin: 20px 0 8px; }
h4 { font-size: 11pt; color: var(--ink); margin: 16px 0 6px; font-weight: 600; }

p { margin: 0 0 12px; }
strong { color: var(--accent); font-weight: 700; }
em { font-style: italic; color: var(--accent2); }

ul, ol { margin: 8px 0 14px 24px; }
li { margin-bottom: 5px; line-height: 1.7; }

blockquote {
  border-left: 4px solid var(--accent2);
  background: linear-gradient(135deg, #f8f4ff 0%, #fdf4ff 100%);
  padding: 12px 18px; margin: 18px 0;
  border-radius: 0 6px 6px 0;
  font-style: italic; color: var(--accent2);
}
blockquote strong { color: var(--accent2); }

code {
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 9.5pt; background: var(--surface);
  border: 1px solid var(--border); padding: 2px 6px;
  border-radius: 3px; color: #c7254e;
}
pre {
  background: #0f172a; color: #e2e8f0;
  padding: 16px 20px; border-radius: 6px; margin: 14px 0;
  font-family: 'JetBrains Mono', monospace; font-size: 9pt; line-height: 1.6;
}
pre code { background: none; border: none; color: inherit; padding: 0; }

table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 10.5pt; }
th { background: var(--accent); color: white; padding: 8px 12px; text-align: left; font-weight: 600; }
td { padding: 7px 12px; border-bottom: 1px solid var(--border); }
tr:nth-child(even) td { background: var(--surface); }

hr { border: none; border-top: 1px solid var(--border); margin: 28px 0; }
"""


def _safe(s: str) -> str:
    """Escape HTML special characters to prevent injection in PDF output."""
    return re.sub(r"[<>&\"']", "", s)


def _fix_inline_lists(md: str) -> str:
    """
    Fix two LLM formatting habits that break Markdown list rendering:

    1. Inline dash lists on one line:
         'We have: - item1 - item2 - item3'
       becomes:
         'We have:\n- item1\n- item2\n- item3'

    2. Inline asterisk lists like '* item one * item two':
       becomes:
         '- item one\n- item two'
    """
    lines = md.splitlines()
    result = []

    for line in lines:
        # Pattern 1: inline asterisk list  (* item * item)
        # Guard against bold/italic (**text** or *italic*) by requiring space after *
        if re.search(r'(?<!\*)\* \S.+(?<!\*)\* \S', line):
            m = re.match(r'^(.*?)\s*(?<!\*)\*\s+(.+)$', line)
            if m:
                prefix = m.group(1).rstrip()
                rest   = m.group(2)
                items  = re.split(r'\s+(?<!\*)\*\s+', rest)
                if prefix:
                    result.append(prefix)
                for item in items:
                    item = item.strip()
                    if item:
                        result.append(f'- {item}')
                continue

        # Pattern 2: inline dash list  (text - item - item)
        # Needs at least 2 " - " occurrences to avoid false positives on ranges like "5 - 10"
        if len(re.findall(r'\s-\s', line)) >= 2:
            m = re.match(r'^(.*?)\s+-\s+(.+)$', line)
            if m:
                prefix = m.group(1).rstrip()
                rest   = '- ' + m.group(2)
                items  = re.split(r'\s+-\s+', rest)
                if prefix:
                    result.append(prefix)
                for item in items:
                    item = item.strip()
                    if item:
                        result.append(item if item.startswith('-') else f'- {item}')
                continue

        result.append(line)

    return '\n'.join(result)


def to_pdf(title: str, md_content: str, provider_label: str = "") -> bytes:
    """Render a titled Markdown document to PDF bytes."""
    ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    body = markdown2.markdown(
        _fix_inline_lists(md_content),
        extras=["fenced-code-blocks", "tables", "footnotes", "strike", "task_list"],
    )
    meta = f"Generated: {ts}" + (f" &nbsp;|&nbsp; {provider_label}" if provider_label else "")
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><style>{_CSS}</style></head>
<body>
  <div class="doc-header">
    <h1>{_safe(title)}</h1>
    <div class="doc-meta">{meta}</div>
  </div>
  {body}
</body></html>"""
    buf = BytesIO()
    WP(string=html).write_pdf(buf)
    return buf.getvalue()
