import io

from docx import Document

from core.exporter import to_docx, to_markdown

SAMPLE = "# Title\n\n## 1. Overview\nUses `main()` and **bold**.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n- item\n"


def test_markdown_export():
    assert to_markdown(SAMPLE).decode() == SAMPLE


def test_docx_export_has_structure():
    doc = Document(io.BytesIO(to_docx(SAMPLE)))
    texts = [p.text for p in doc.paragraphs]
    assert "Title" in texts
    assert "1. Overview" in texts
    assert len(doc.tables) == 1
