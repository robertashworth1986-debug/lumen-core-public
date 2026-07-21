from __future__ import annotations

import argparse
import hashlib
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / "docs"
    / "preprint"
    / "BOUNDED_REPRODUCIBILITY_CAPSULE_PREPRINT_2026-07-21.md"
)
OUTPUT = SOURCE.with_suffix(".pdf")
TITLE = (
    "A Bounded Reproducibility Capsule for Public-Data Benchmarking "
    "and Preserved Negative Gates"
)


class InvariantCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        kwargs["invariant"] = 1
        super().__init__(*args, **kwargs)
        self.setTitle(TITLE)
        self.setAuthor("Robert Ashworth")
        self.setSubject("Public preprint draft for bounded executable reproduction")
        self.setCreator("LumenCore deterministic preprint builder")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inline_markup(value: str) -> str:
    escaped = html.escape(value)
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def styles():
    base = getSampleStyleSheet()
    navy = colors.HexColor("#17243D")
    teal = colors.HexColor("#087E8B")
    muted = colors.HexColor("#536273")
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_LEFT,
            textColor=navy,
            spaceAfter=18,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=muted,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=navy,
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=teal,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13.6,
            textColor=colors.HexColor("#202832"),
            spaceAfter=7,
        ),
        "question": ParagraphStyle(
            "Question",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=16,
            leftIndent=16,
            rightIndent=16,
            borderColor=teal,
            borderWidth=1,
            borderPadding=10,
            backColor=colors.HexColor("#EDF7F7"),
            textColor=navy,
            spaceBefore=5,
            spaceAfter=12,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.4,
            leading=10.5,
            leftIndent=10,
            rightIndent=10,
            borderColor=colors.HexColor("#CDD5DE"),
            borderWidth=0.5,
            borderPadding=8,
            backColor=colors.HexColor("#F5F7F9"),
            spaceAfter=10,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=13,
            leftIndent=4,
            textColor=colors.HexColor("#202832"),
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=muted,
        ),
    }


def build_story(source_text: str, source_hash: str):
    style = styles()
    lines = source_text.splitlines()
    story = []
    paragraph: list[str] = []
    bullets: list[str] = []
    numbered: list[str] = []
    code_lines: list[str] = []
    in_code = False
    title_seen = False
    in_front_matter = False
    front_matter: list[str] = []

    def flush_paragraph():
        if paragraph:
            value = " ".join(item.strip() for item in paragraph)
            selected = style["question"] if value.endswith("?") else style["body"]
            story.append(Paragraph(inline_markup(value), selected))
            paragraph.clear()

    def flush_list(items: list[str], ordered: bool):
        if not items:
            return
        flowables = [
            ListItem(Paragraph(inline_markup(item), style["bullet"]))
            for item in items
        ]
        options = {
            "bulletType": "1" if ordered else "bullet",
            "leftIndent": 22,
            "bulletFontName": "Helvetica",
            "bulletFontSize": 8,
            "spaceAfter": 8,
        }
        if ordered:
            options["start"] = "1"
        story.append(ListFlowable(flowables, **options))
        items.clear()

    def flush_front_matter():
        if front_matter:
            value = "<br/>".join(inline_markup(item) for item in front_matter)
            story.append(Paragraph(value, style["subtitle"]))
            front_matter.clear()

    def flush_code():
        if code_lines:
            rendered = "<br/>".join(html.escape(line) or " " for line in code_lines)
            story.append(Paragraph(rendered, style["code"]))
            code_lines.clear()

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            flush_paragraph()
            flush_list(bullets, False)
            flush_list(numbered, True)
            if in_code:
                flush_code()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith("# "):
            flush_paragraph()
            title_seen = True
            in_front_matter = True
            story.append(Paragraph(inline_markup(line[2:]), style["title"]))
            continue
        if line.startswith("## "):
            flush_paragraph()
            flush_list(bullets, False)
            flush_list(numbered, True)
            story.append(Paragraph(inline_markup(line[3:]), style["h2"]))
            continue
        if line.startswith("### "):
            flush_paragraph()
            flush_list(bullets, False)
            flush_list(numbered, True)
            story.append(Paragraph(inline_markup(line[4:]), style["h3"]))
            continue
        if line.startswith("- "):
            flush_paragraph()
            flush_list(numbered, True)
            bullets.append(line[2:])
            continue
        numbered_match = re.match(r"^\d+\.\s+(.+)$", line)
        if numbered_match:
            flush_paragraph()
            flush_list(bullets, False)
            numbered.append(numbered_match.group(1))
            continue
        if not line.strip():
            flush_paragraph()
            flush_list(bullets, False)
            flush_list(numbered, True)
            flush_front_matter()
            in_front_matter = False
            continue
        if title_seen and in_front_matter:
            front_matter.append(line)
            continue
        paragraph.append(line)

    flush_paragraph()
    flush_list(bullets, False)
    flush_list(numbered, True)
    flush_front_matter()
    flush_code()
    story.extend(
        [
            Spacer(1, 12),
            Paragraph(
                "Authoritative Markdown source SHA-256: " + source_hash,
                style["footer"],
            ),
        ]
    )
    return story


def on_page(page_canvas, document):
    width, height = letter
    page_canvas.saveState()
    page_canvas.setStrokeColor(colors.HexColor("#D5DCE4"))
    page_canvas.setLineWidth(0.4)
    page_canvas.line(0.72 * inch, 0.55 * inch, width - 0.72 * inch, 0.55 * inch)
    page_canvas.setFont("Helvetica", 7.5)
    page_canvas.setFillColor(colors.HexColor("#536273"))
    page_canvas.drawString(0.72 * inch, 0.36 * inch, "LumenCore preprint draft v0.1")
    page_canvas.drawRightString(
        width - 0.72 * inch, 0.36 * inch, f"Page {document.page}"
    )
    page_canvas.restoreState()


def build_pdf(source: Path = SOURCE, output: Path = OUTPUT) -> dict[str, str | int]:
    source_text = source.read_text(encoding="utf-8")
    source_hash = sha256(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.67 * inch,
        bottomMargin=0.72 * inch,
        title=TITLE,
        author="Robert Ashworth",
    )
    document.build(
        build_story(source_text, source_hash),
        onFirstPage=on_page,
        onLaterPages=on_page,
        canvasmaker=InvariantCanvas,
    )
    return {
        "source": source.relative_to(ROOT).as_posix(),
        "source_sha256": source_hash,
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": sha256(output),
        "output_bytes": output.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    before = sha256(OUTPUT) if OUTPUT.is_file() else None
    result = build_pdf()
    result["deterministic_match"] = before in {None, result["output_sha256"]}
    print(result)
    if args.check and before is not None and before != result["output_sha256"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
