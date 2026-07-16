from __future__ import annotations

import argparse
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE / "NV063_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.md"
DEFAULT_TEMPLATE = (
    HERE
    / "source_attachments"
    / "DON_PHASE_I_CONVENTIONAL_VOLUME2_TEMPLATE_2026-03-04.docx"
)
DEFAULT_OUTPUT = HERE / "NV063_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.docx"

FONT = "Arial"
FIRST_PAGE_LEGEND = (
    "This proposal includes data that must not be disclosed outside the Government "
    "and must not be duplicated, used, or disclosed-in whole or in part-for any "
    "purpose other than to evaluate this proposal. If, however, a contract is "
    "awarded to this proposing SBC as a result of-or in connection with-the "
    "submission of this data, the Government has the right to duplicate, use, or "
    "disclose the data to the extent provided in the resulting contract. This "
    "restriction does not limit the Government's right to use information contained "
    "in this data if it is obtained from another source without restriction. The "
    "data subject to this restriction are contained in all pages of this Volume 2."
)
PAGE_LEGEND = (
    "Use or disclosure of data contained on this page is subject to the restriction "
    "on the first page of this volume."
)


def scrub_package_artifacts(docx_path: Path) -> None:
    tmp_path = docx_path.with_suffix(".scrubbed.tmp.docx")
    with ZipFile(docx_path, "r") as src, ZipFile(tmp_path, "w", ZIP_DEFLATED) as dst:
        for item in src.infolist():
            name = item.filename
            if name == "docProps/custom.xml" or name.startswith("customXml/"):
                continue
            data = src.read(name)
            if name == "[Content_Types].xml":
                root = ET.fromstring(data)
                for node in list(root):
                    part_name = node.attrib.get("PartName", "")
                    if part_name.startswith("/customXml/") or part_name == "/docProps/custom.xml":
                        root.remove(node)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            elif name.endswith(".rels"):
                root = ET.fromstring(data)
                for node in list(root):
                    rel_type = node.attrib.get("Type", "")
                    target = node.attrib.get("Target", "").replace("\\", "/")
                    if (
                        rel_type.endswith("/customXml")
                        or rel_type.endswith("/custom-properties")
                        or target.startswith("customXml/")
                        or target.startswith("../customXml/")
                        or target == "docProps/custom.xml"
                    ):
                        root.remove(node)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            dst.writestr(item, data)
    tmp_path.replace(docx_path)


def clear_body(doc: Document) -> None:
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def set_cell_margins(cell, top=72, start=90, bottom=72, end=90) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_simple_field(paragraph, instruction: str, cached_text: str) -> None:
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), instruction)
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = cached_text
    run.append(text)
    field.append(run)
    paragraph._p.append(field)


def add_page_number(paragraph) -> None:
    paragraph.add_run("Page ")
    add_simple_field(paragraph, "PAGE", "1")
    paragraph.add_run(" of ")
    add_simple_field(paragraph, "NUMPAGES", "1")


def clear_header_or_footer(part) -> None:
    element = part._element
    for child in list(element):
        if child.tag == qn("w:p"):
            element.remove(child)


def create_bullet_numbering(doc: Document) -> int:
    numbering = doc.part.numbering_part.element
    abstract_ids = [
        int(node.get(qn("w:abstractNumId")))
        for node in numbering.findall(qn("w:abstractNum"))
        if node.get(qn("w:abstractNumId")) is not None
    ]
    num_ids = [
        int(node.get(qn("w:numId")))
        for node in numbering.findall(qn("w:num"))
        if node.get(qn("w:numId")) is not None
    ]
    abstract_id = max(abstract_ids, default=0) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "bullet")
    level_text = OxmlElement("w:lvlText")
    level_text.set(qn("w:val"), "\u2022")
    level_justification = OxmlElement("w:lvlJc")
    level_justification.set(qn("w:val"), "left")
    paragraph_properties = OxmlElement("w:pPr")
    indent = OxmlElement("w:ind")
    indent.set(qn("w:left"), "360")
    indent.set(qn("w:hanging"), "180")
    paragraph_properties.append(indent)
    level.extend([start, num_fmt, level_text, level_justification, paragraph_properties])
    abstract.append(level)
    numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    numbering.append(num)
    return num_id


def apply_bullet(paragraph, num_id: int) -> None:
    paragraph_properties = paragraph._p.get_or_add_pPr()
    num_properties = OxmlElement("w:numPr")
    level = OxmlElement("w:ilvl")
    level.set(qn("w:val"), "0")
    num = OxmlElement("w:numId")
    num.set(qn("w:val"), str(num_id))
    num_properties.extend([level, num])
    paragraph_properties.append(num_properties)


def configure_document(doc: Document, released: bool) -> int:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.35)
    section.footer_distance = Inches(0.35)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1
    normal.paragraph_format.left_indent = Inches(0)
    normal.paragraph_format.right_indent = Inches(0)
    normal.paragraph_format.first_line_indent = Inches(0)

    for style_name, size, before, after in (
        ("Heading 1", 12, 7, 3),
        ("Heading 2", 11, 5, 2),
        ("Heading 3", 10, 4, 1),
    ):
        try:
            style = doc.styles[style_name]
        except KeyError:
            style = doc.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = FONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = 1
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.left_indent = Inches(0)
        style.paragraph_format.right_indent = Inches(0)
        style.paragraph_format.first_line_indent = Inches(0)

    try:
        list_bullet = doc.styles["List Bullet"]
    except KeyError:
        list_bullet = doc.styles.add_style("List Bullet", WD_STYLE_TYPE.PARAGRAPH)
    list_bullet.font.name = FONT
    list_bullet.font.size = Pt(10)
    list_bullet.paragraph_format.space_before = Pt(0)
    list_bullet.paragraph_format.space_after = Pt(1)
    list_bullet.paragraph_format.line_spacing = 1

    clear_header_or_footer(section.header)
    header = section.header.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header.paragraph_format.space_after = Pt(0)
    header_run = header.add_run(
        "Robert Ashworth d/b/a LumenCore | DON26BZ03-NV063 | Proposal No. [assigned in DSIP]"
    )
    header_run.font.name = FONT
    header_run.font.size = Pt(7.5)

    clear_header_or_footer(section.footer)
    footer_legend = section.footer.add_paragraph()
    footer_legend.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_legend.paragraph_format.space_after = Pt(0)
    legend = footer_legend.add_run(PAGE_LEGEND)
    legend.font.name = FONT
    legend.font.size = Pt(6.5)

    footer_page = section.footer.add_paragraph()
    footer_page.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_page.paragraph_format.space_after = Pt(0)
    add_page_number(footer_page)
    if not released:
        draft = footer_page.add_run(" | REVIEW CANDIDATE - NOT CERTIFIED")
        draft.font.name = FONT
        draft.font.size = Pt(7.5)
        draft.font.bold = True

    return create_bullet_numbering(doc)


def add_title_block(doc: Document, released: bool) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run("Volume 2: Technical Volume")
    run.font.name = FONT
    run.font.size = Pt(14)
    run.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(
        "HarborSentinel: Explainable Low-Storage Pattern-of-Life Analysis for Congested Maritime Environments"
    )
    run.font.name = FONT
    run.font.size = Pt(11)
    run.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(5)
    run = p.add_run("DON26BZ03-NV063 | Navy SBIR 2026 Release 3 Phase I")
    run.font.name = FONT
    run.font.size = Pt(9)

    if not released:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run("REVIEW CANDIDATE - COMPLETE LIVE DSIP AND HUMAN CERTIFICATION GATES BEFORE SUBMISSION")
        run.font.name = FONT
        run.font.size = Pt(8)
        run.font.bold = True

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    run = p.add_run(FIRST_PAGE_LEGEND)
    run.font.name = FONT
    run.font.size = Pt(8)
    run.font.italic = True


def markdown_blocks(text: str):
    paragraph: list[str] = []

    def flush():
        if paragraph:
            yield "paragraph", " ".join(paragraph).strip()
            paragraph.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            yield from flush()
            continue
        if line.startswith("# "):
            yield from flush()
            yield "title", line[2:].strip()
        elif line.startswith("## "):
            yield from flush()
            yield "h1", line[3:].strip()
        elif line.startswith("### "):
            yield from flush()
            yield "h2", line[4:].strip()
        elif line.startswith("- "):
            yield from flush()
            yield "bullet", line[2:].strip()
        else:
            paragraph.append(line)
    yield from flush()


def add_markdown(doc: Document, source_text: str, bullet_num_id: int) -> None:
    skip_prefixes = (
        "Topic:",
        "Program:",
        "Proposal title:",
        "Status:",
    )
    for kind, text in markdown_blocks(source_text):
        if kind == "title" or text.startswith(skip_prefixes):
            continue
        if kind == "h1":
            doc.add_paragraph(text, style="Heading 1")
        elif kind == "h2":
            doc.add_paragraph(text, style="Heading 2")
        elif kind == "bullet":
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1
            apply_bullet(p, bullet_num_id)
            run = p.add_run(text)
            run.font.name = FONT
            run.font.size = Pt(10)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1
            p.paragraph_format.left_indent = Inches(0)
            p.paragraph_format.right_indent = Inches(0)
            p.paragraph_format.first_line_indent = Inches(0)
            run = p.add_run(text)
            run.font.name = FONT
            run.font.size = Pt(10)


def remove_empty_template_tables(doc: Document) -> None:
    for table in list(doc.tables):
        table._element.getparent().remove(table._element)


def build(source: Path, template: Path, output: Path, released: bool) -> None:
    doc = Document(template)
    clear_body(doc)
    remove_empty_template_tables(doc)
    bullet_num_id = configure_document(doc, released=released)
    add_title_block(doc, released=released)
    add_markdown(doc, source.read_text(encoding="utf-8"), bullet_num_id)

    doc.core_properties.title = "HarborSentinel Navy SBIR Phase I Volume 2"
    doc.core_properties.subject = "DON26BZ03-NV063"
    doc.core_properties.author = "Robert Ashworth"
    doc.core_properties.comments = (
        "Released submission candidate" if released else "Review candidate; not certified"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    scrub_package_artifacts(output)
    Document(output).save(output)
    print(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--release",
        action="store_true",
        help="Remove visible review-candidate controls only after all live DSIP gates clear.",
    )
    args = parser.parse_args()
    build(args.source, args.template, args.output, released=args.release)


if __name__ == "__main__":
    main()
