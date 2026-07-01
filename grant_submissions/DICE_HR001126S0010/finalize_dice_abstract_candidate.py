from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
SOURCE_DOCX = HERE / "LumenCore_DICE_Abstract_WORKING_DRAFT.docx"
FINAL_DOCX = HERE / "LumenCore_DICE_Abstract_FINAL_CANDIDATE.docx"
PORTAL_ZIP = HERE / "LumenCore_DICE_Abstract_PORTAL_UPLOAD.zip"
REPORT = HERE / "DICE_FINAL_CANDIDATE_REPORT.json"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def paragraph_text(node: ET.Element) -> str:
    return "".join(t.text or "" for t in node.findall(".//w:t", NS))


def remove_draft_warning(docx_in: Path, docx_out: Path) -> dict:
    removed = []
    tmp = docx_out.with_suffix(".tmp.docx")
    with ZipFile(docx_in, "r") as src, ZipFile(tmp, "w", ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                root = ET.fromstring(data)
                body = root.find("w:body", NS)
                if body is None:
                    raise RuntimeError("word/document.xml has no body")
                for p in list(body.findall("w:p", NS)):
                    text = paragraph_text(p).strip()
                    if text == "WORKING DRAFT - NOT APPROVED FOR SUBMISSION":
                        body.remove(p)
                        removed.append(text)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            dst.writestr(item, data)
    tmp.replace(docx_out)
    return {"removed_warning_paragraphs": removed}


def extract_visible_text(docx_path: Path) -> str:
    with ZipFile(docx_path, "r") as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    return "\n".join(
        paragraph_text(p).strip()
        for p in root.findall(".//w:p", NS)
        if paragraph_text(p).strip()
    )


def create_portal_zip(docx_path: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        zf.write(docx_path, docx_path.name)


def main() -> None:
    if not SOURCE_DOCX.exists():
        raise FileNotFoundError(SOURCE_DOCX)
    result = remove_draft_warning(SOURCE_DOCX, FINAL_DOCX)
    text = extract_visible_text(FINAL_DOCX)
    required_sections = [
        "1. Goals and Impact",
        "2. Technical Approach",
        "3. Capabilities/Management Plan",
        "4. Cost and Schedule",
        "5. Publications",
        "6. Bibliography",
    ]
    checks = {
        "source_docx": str(SOURCE_DOCX),
        "final_docx": str(FINAL_DOCX),
        "portal_zip": str(PORTAL_ZIP),
        "warning_present": "WORKING DRAFT" in text or "NOT APPROVED FOR SUBMISSION" in text,
        "required_sections_present": {
            section: section in text for section in required_sections
        },
        "forbidden_placeholders_present": any(
            token in text for token in ["TO_BE_FILLED", "TODO", "<INSERT", "Insert "]
        ),
        **result,
    }
    if checks["warning_present"]:
        raise RuntimeError("final candidate still contains draft warning")
    missing = [
        section
        for section, present in checks["required_sections_present"].items()
        if not present
    ]
    if missing:
        raise RuntimeError(f"final candidate missing required sections: {missing}")
    if checks["forbidden_placeholders_present"]:
        raise RuntimeError("final candidate contains unresolved placeholder text")

    create_portal_zip(FINAL_DOCX, PORTAL_ZIP)
    checks.update(
        {
            "final_docx_bytes": FINAL_DOCX.stat().st_size,
            "final_docx_sha256": sha256(FINAL_DOCX),
            "portal_zip_bytes": PORTAL_ZIP.stat().st_size,
            "portal_zip_sha256": sha256(PORTAL_ZIP),
            "zip_members": ZipFile(PORTAL_ZIP).namelist(),
        }
    )
    REPORT.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
