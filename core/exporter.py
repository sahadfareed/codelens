import io
import re

from docx import Document
from docx.shared import Pt, RGBColor

INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)")
CODE_FONT = "Courier New"


def to_markdown(markdown_text: str) -> bytes:
    return markdown_text.encode("utf-8")


def _add_inline(paragraph, text):
    """Handle **bold**, *italic* and `code` inside a line."""
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = CODE_FONT
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0xC7, 0x25, 0x4E)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            paragraph.add_run(part[1:-1]).italic = True
        else:
            paragraph.add_run(part)


def _add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    if not cells:
        return
    ncols = max(len(r) for r in cells)
    table = doc.add_table(rows=len(cells), cols=ncols)
    table.style = "Table Grid"
    for i, row in enumerate(cells):
        for j in range(ncols):
            p = table.cell(i, j).paragraphs[0]
            _add_inline(p, row[j] if j < len(row) else "")
            if i == 0:
                for run in p.runs:
                    run.bold = True
    doc.add_paragraph()


def _add_code_block(doc, lines):
    p = doc.add_paragraph()
    run = p.add_run("\n".join(lines))
    run.font.name = CODE_FONT
    run.font.size = Pt(9)


def to_docx(markdown_text: str) -> bytes:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    in_code, code_buf, table_buf = False, [], []

    for line in markdown_text.splitlines():
        stripped = line.strip()

        # fenced code blocks
        if stripped.startswith("```"):
            if in_code:
                _add_code_block(doc, code_buf)
                code_buf, in_code = [], False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        # tables
        if stripped.startswith("|"):
            table_buf.append(stripped)
            continue
        if table_buf:
            _add_table(doc, table_buf)
            table_buf = []

        if not stripped or re.fullmatch(r"[-*_]{3,}", stripped):
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)", stripped)
        bullet = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        numbered = re.match(r"^(\s*)\d+[.)]\s+(.*)", line)

        if heading:
            level = len(heading.group(1))
            text = heading.group(2).replace("`", "").replace("**", "")
            doc.add_heading(text, level=0 if level == 1 else min(level - 1, 4))
        elif bullet:
            style = "List Bullet 2" if len(bullet.group(1)) >= 2 else "List Bullet"
            _add_inline(doc.add_paragraph(style=style), bullet.group(2))
        elif numbered:
            _add_inline(doc.add_paragraph(style="List Number"), numbered.group(2))
        else:
            _add_inline(doc.add_paragraph(), stripped)

    if table_buf:
        _add_table(doc, table_buf)
    if in_code and code_buf:
        _add_code_block(doc, code_buf)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
