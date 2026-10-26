"""Convert the Markdown articles in data/kb_src/ into the PDFs in data/kb/.

The PDFs are what you upload to Azure Blob Storage for the Foundry IQ knowledge base.
Run:  python scripts/generate_kb_pdfs.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from common.config import KB_DIR, KB_SRC_DIR


def inline(text: str) -> str:
    """Escape XML characters and convert `code` and **bold** to ReportLab markup."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10.5, leading=15)
    story, items, ordered = [], [], False

    def flush():
        nonlocal items
        if items:
            story.append(ListFlowable(items, bulletType="1" if ordered else "bullet", leftIndent=16))
            story.append(Spacer(1, 6))
            items = []

    for line in md_path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        numbered = re.match(r"^(\d+)\.\s+(.*)", line)
        bullet = re.match(r"^[-*]\s+(.*)", line)
        if numbered or bullet:
            if items and ordered != bool(numbered):
                flush()
            ordered = bool(numbered)
            text = (numbered or bullet).group(2 if numbered else 1)
            items.append(ListItem(Paragraph(inline(text), body)))
            continue
        flush()
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["Title"]))
        elif line.startswith("## "):
            story.append(Spacer(1, 8))
            story.append(Paragraph(inline(line[3:]), styles["Heading2"]))
        elif line.strip():
            story.append(Paragraph(inline(line), body))
            story.append(Spacer(1, 4))
    flush()
    SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm, title=md_path.stem).build(story)


def main() -> None:
    KB_DIR.mkdir(parents=True, exist_ok=True)
    sources = sorted(KB_SRC_DIR.glob("KB-*.md"))
    for md_path in sources:
        pdf_path = KB_DIR / (md_path.stem + ".pdf")
        build_pdf(md_path, pdf_path)
        print("wrote", pdf_path.relative_to(KB_DIR.parent.parent))
    print(f"{len(sources)} PDFs ready in data/kb/")


if __name__ == "__main__":
    main()
