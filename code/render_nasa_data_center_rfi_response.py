from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.md"
)
DEFAULT_OUTPUT = DEFAULT_INPUT.with_suffix(".pdf")

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2B5F87")
TEAL = colors.HexColor("#1B7F79")
PALE_BLUE = colors.HexColor("#EAF2F8")
PALE_GRAY = colors.HexColor("#F4F6F7")
TEXT = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#526473")


def inline_markup(value: str) -> str:
    rendered = html.escape(value.strip())
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", rendered)
    rendered = re.sub(
        r"`([^`]+)`", r'<font name="Courier">\1</font>', rendered
    )
    return rendered


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SubmissionTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "SubmissionSubtitle",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=BLUE,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "SubmissionH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "SubmissionH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=TEAL,
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "SubmissionBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=14.5,
            textColor=TEXT,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "SubmissionBullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=14.5,
            textColor=TEXT,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=2,
        ),
        "table_header": ParagraphStyle(
            "SubmissionTableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.white,
        ),
        "table_body": ParagraphStyle(
            "SubmissionTableBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=TEXT,
        ),
        "footer": ParagraphStyle(
            "SubmissionFooter",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=9,
            textColor=MUTED,
        ),
    }


def parse_table(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    parsed = [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in lines]
    if len(parsed) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in parsed[1]):
        parsed.pop(1)

    wrapped: list[list[Paragraph]] = []
    for row_index, row in enumerate(parsed):
        style = styles["table_header"] if row_index == 0 else styles["table_body"]
        wrapped.append([Paragraph(inline_markup(cell), style) for cell in row])

    available_width = 7.1 * inch
    columns = max(len(row) for row in wrapped)
    if columns == 2:
        widths = [1.55 * inch, available_width - 1.55 * inch]
    elif columns == 3:
        widths = [1.15 * inch, 2.4 * inch, available_width - 3.55 * inch]
    else:
        widths = [available_width / columns] * columns

    table = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7C4")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GRAY]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def markdown_story(text: str, styles: dict[str, ParagraphStyle]) -> list[object]:
    lines = text.splitlines()
    story: list[object] = []
    paragraph_parts: list[str] = []
    bullet_parts: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_parts:
            story.append(Paragraph(inline_markup(" ".join(paragraph_parts)), styles["body"]))
            paragraph_parts.clear()

    def flush_bullets() -> None:
        if bullet_parts:
            items = [
                ListItem(Paragraph(inline_markup(item), styles["bullet"]), leftIndent=12)
                for item in bullet_parts
            ]
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    bulletFontName="Helvetica",
                    bulletFontSize=7,
                    leftIndent=18,
                    bulletIndent=4,
                    spaceAfter=5,
                )
            )
            bullet_parts.clear()

    index = 0
    title_seen = False
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            flush_bullets()
            table_lines: list[str] = []
            while index < len(lines):
                candidate = lines[index].strip()
                if not (candidate.startswith("|") and candidate.endswith("|")):
                    break
                table_lines.append(candidate)
                index += 1
            story.append(parse_table(table_lines, styles))
            story.append(Spacer(1, 8))
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            flush_bullets()
            if title_seen:
                story.append(Spacer(1, 6))
            story.append(Paragraph(inline_markup(stripped[2:]), styles["title"]))
            story.append(HRFlowable(width="100%", thickness=1.2, color=TEAL, spaceAfter=8))
            title_seen = True
        elif stripped.startswith("## "):
            flush_paragraph()
            flush_bullets()
            heading_text = inline_markup(stripped[3:])
            if not any(isinstance(item, Paragraph) and item.style.name == "SubmissionSubtitle" for item in story):
                story.append(Paragraph(heading_text, styles["subtitle"]))
            else:
                story.append(KeepTogether([Paragraph(heading_text, styles["h2"])]))
        elif stripped.startswith("### "):
            flush_paragraph()
            flush_bullets()
            story.append(KeepTogether([Paragraph(inline_markup(stripped[4:]), styles["h3"])]))
        elif stripped.startswith("- "):
            flush_paragraph()
            bullet_parts.append(stripped[2:])
        elif re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            bullet_parts.append(re.sub(r"^\d+\.\s+", "", stripped))
        elif not stripped:
            flush_paragraph()
            flush_bullets()
        else:
            flush_bullets()
            paragraph_parts.append(stripped)
        index += 1

    flush_paragraph()
    flush_bullets()
    return story


def draw_footer(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B9C5CF"))
    canvas.setLineWidth(0.5)
    canvas.line(0.7 * inch, 0.52 * inch, 7.8 * inch, 0.52 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.7 * inch, 0.34 * inch, "Robert Ashworth | LumenCore | RFI 80TECH26RFI0020")
    canvas.drawRightString(7.8 * inch, 0.34 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    story = markdown_story(input_path.read_text(encoding="utf-8"), styles)
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.68 * inch,
        title="Response to RFI 80TECH26RFI0020",
        author="Robert Ashworth",
        subject="Strategic Partnerships for NASA Data Center Infrastructure",
    )
    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    built = build_pdf(args.input, args.output)
    print(built)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
