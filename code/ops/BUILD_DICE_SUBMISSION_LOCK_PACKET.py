from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "ops"
DICE = ROOT / "grant_submissions" / "DICE_HR001126S0010"

JSON_OUT = OUT / "dice_submission_lock_packet_latest.json"
MD_OUT = DICE / "DICE_SUBMISSION_LOCK_PACKET_2026-06-20.md"

DOCX = DICE / "LumenCore_DICE_Abstract_WORKING_DRAFT.docx"
RENDER_DIR = DICE / "render_qa_20260619_manual_clean_v5"
RENDER_PDF = RENDER_DIR / "LumenCore_DICE_Abstract_WORKING_DRAFT.pdf"

REQUIRED_SECTIONS = [
    "1. Goals and Impact",
    "2. Technical Approach",
    "3. Capabilities/Management Plan",
    "4. Cost and Schedule",
    "5. Publications",
    "6. Bibliography",
]

REQUIRED_ARTIFACTS = [
    DOCX,
    RENDER_PDF,
    DICE / "A1_DICE_Abstract_Template_OFFICIAL.docx",
    DICE / "HR001126S0010_OFFICIAL.pdf",
    DICE / "build_dice_abstract.py",
    DICE / "DICE_FINALIZATION_AUDIT_2026-06-19.md",
    DICE / "DICE_DOCX_QA_AND_REFERENCE_CHECK_2026-06-19.md",
    DICE / "DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md",
    DICE / "DICE_HEILMEIER_REVIEWER_MATRIX_2026-06-20.md",
    DICE / "DICE_EVIDENCE_SYNTHESIS_2026-06-20.md",
    DICE / "DICE_LIVE_BREADTH_REPLAY_2026-06-20.md",
    DICE / "DICE_COST_BASIS_WORKING.md",
    DICE / "DICE_NEXT_11_DAY_SPRINT_2026-06-19.md",
]

FORBIDDEN_DOCX_PARTS = [
    "word/comments.xml",
    "word/commentsExtended.xml",
    "word/commentsExtensible.xml",
    "word/commentsIds.xml",
    "word/people.xml",
    "docProps/custom.xml",
    "docMetadata/LabelInfo.xml",
]

FORBIDDEN_DOCX_PREFIXES = [
    "customXml/",
]

PLACEHOLDER_PATTERNS = [
    r"TO_BE_FILLED",
    r"\bTODO\b",
    r"\bInsert\b",
    r"\bplaceholder\b",
    r"<[^>\n]{2,80}>",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": rel(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists and path.is_file() else None,
        "sha256": sha256_file(path) if exists and path.is_file() else None,
    }


def _extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    chunks: list[str] = []
    for paragraph in document.findall(".//w:p", namespaces):
        text = "".join(
            node.text or ""
            for node in paragraph.findall(".//w:t", namespaces)
        )
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _docx_part_check(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "zip_ok": False,
        "part_count": 0,
        "forbidden_parts_present": [],
        "forbidden_prefix_parts_present": [],
        "stale_relationship_or_content_type_refs": [],
    }
    try:
        with zipfile.ZipFile(path) as archive:
            bad_file = archive.testzip()
            if bad_file:
                result["bad_file"] = bad_file
                return result
            names = set(archive.namelist())
            result["zip_ok"] = True
            result["part_count"] = len(names)
            result["forbidden_parts_present"] = [
                name for name in FORBIDDEN_DOCX_PARTS if name in names
            ]
            result["forbidden_prefix_parts_present"] = [
                name
                for name in sorted(names)
                if any(name.startswith(prefix) for prefix in FORBIDDEN_DOCX_PREFIXES)
            ]
            for rel_name in ("word/_rels/document.xml.rels", "[Content_Types].xml"):
                if rel_name not in names:
                    continue
                text = archive.read(rel_name).decode("utf-8", errors="ignore")
                for marker in ("comments", "people.xml", "customXml", "docMetadata/LabelInfo"):
                    if marker in text:
                        result["stale_relationship_or_content_type_refs"].append(
                            f"{rel_name}: {marker}"
                        )
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _visible_text_check(text: str) -> dict[str, Any]:
    urls = re.findall(r"https?://[^\s)>\]]+", text)
    trailing_punctuation = [
        url for url in urls if url[-1:] in {".", ",", ";", ":"}
    ]
    placeholder_hits: list[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            placeholder_hits.append(pattern)
    return {
        "characters": len(text),
        "working_draft_warning_present": "WORKING DRAFT - NOT APPROVED FOR SUBMISSION" in text,
        "required_sections_present": {
            section: section in text for section in REQUIRED_SECTIONS
        },
        "visible_url_count": len(urls),
        "visible_urls": urls,
        "visible_urls_with_trailing_punctuation": trailing_punctuation,
        "placeholder_hits": placeholder_hits,
        "rom_cost_boundary_present": (
            "ROM" in text
            and "full-proposal" in text.lower()
            and "$4,920,000" in text
        ),
    }


def _render_check() -> dict[str, Any]:
    pngs = sorted(RENDER_DIR.glob("page-*.png")) if RENDER_DIR.exists() else []
    return {
        "render_dir": rel(RENDER_DIR),
        "render_dir_exists": RENDER_DIR.exists(),
        "pdf": artifact_status(RENDER_PDF),
        "page_png_count": len(pngs),
        "page_pngs": [artifact_status(path) for path in pngs],
        "expected_page_png_count": 7,
        "ok": RENDER_DIR.exists() and RENDER_PDF.exists() and len(pngs) == 7,
    }


def build_packet() -> dict[str, Any]:
    artifacts = [artifact_status(path) for path in REQUIRED_ARTIFACTS]
    png_artifacts = _render_check()["page_pngs"]
    all_artifacts = [*artifacts, *png_artifacts]
    missing = [row["path"] for row in artifacts if not row["exists"]]

    docx_checks: dict[str, Any] = {
        "exists": DOCX.exists(),
    }
    if DOCX.exists():
        docx_checks["parts"] = _docx_part_check(DOCX)
        text = _extract_docx_text(DOCX)
        docx_checks["visible_text"] = _visible_text_check(text)
    else:
        docx_checks["parts"] = {}
        docx_checks["visible_text"] = {}

    render = _render_check()
    local_blockers: list[str] = []
    local_blockers.extend(f"missing required artifact: {path}" for path in missing)
    parts = docx_checks.get("parts", {})
    text_check = docx_checks.get("visible_text", {})
    if not parts.get("zip_ok"):
        local_blockers.append("DOCX ZIP/package integrity failed")
    for item in parts.get("forbidden_parts_present", []):
        local_blockers.append(f"forbidden DOCX part present: {item}")
    for item in parts.get("forbidden_prefix_parts_present", []):
        local_blockers.append(f"forbidden DOCX prefix part present: {item}")
    for item in parts.get("stale_relationship_or_content_type_refs", []):
        local_blockers.append(f"stale DOCX relationship/content-type reference: {item}")
    if not text_check.get("working_draft_warning_present"):
        local_blockers.append("working draft warning missing")
    for section, present in text_check.get("required_sections_present", {}).items():
        if not present:
            local_blockers.append(f"required section missing: {section}")
    if text_check.get("visible_urls_with_trailing_punctuation"):
        local_blockers.append("visible URL trailing punctuation found")
    for pattern in text_check.get("placeholder_hits", []):
        local_blockers.append(f"visible placeholder-like pattern found: {pattern}")
    if not text_check.get("rom_cost_boundary_present"):
        local_blockers.append("ROM/full-proposal cost boundary not detected in visible text")
    if not render["ok"]:
        local_blockers.append("render packet incomplete or page count changed")

    portal_user_blockers = [
        "BAAT account, organization profile, and submitter authority are unverified.",
        "SAM.gov entity status/linkage must be verified.",
        "Final human reference-relevance signoff remains required.",
        "The $4.92 million cost basis is a ROM planning estimate, not a reviewed cost proposal.",
        "Optional independent Word/BAAT upload-environment layout preview remains prudent.",
        "Fresh action-time approval is required before any upload, consent, certification, or submit action.",
    ]

    posture = "LOCAL_LOCKED_PORTAL_BLOCKED" if not local_blockers else "LOCAL_LOCK_BLOCKED"
    return {
        "generated_utc": now_utc(),
        "schema": "dice_submission_lock_packet_v1",
        "posture": posture,
        "artifacts": all_artifacts,
        "docx_checks": docx_checks,
        "render_check": render,
        "local_blockers": local_blockers,
        "portal_user_blockers": portal_user_blockers,
        "claim_boundary": (
            "This lock packet freezes the local DICE abstract package state. "
            "It does not approve upload, certify eligibility, validate cost, "
            "or replace BAAT/SAM/human signoff."
        ),
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# DICE Submission Lock Packet",
        "",
        f"Generated UTC: {packet['generated_utc']}",
        "",
        f"Posture: `{packet['posture']}`",
        "",
        "Status: local package lock only; not approved for BAAT upload or submission.",
        "",
        "## Claim Boundary",
        "",
        packet["claim_boundary"],
        "",
        "## Locked Artifacts",
        "",
        "| Artifact | Bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    for artifact in packet["artifacts"]:
        if not artifact["exists"]:
            lines.append(f"| `{artifact['path']}` | missing | missing |")
        else:
            lines.append(
                f"| `{artifact['path']}` | {artifact['bytes']} | `{artifact['sha256']}` |"
            )

    text = packet["docx_checks"].get("visible_text", {})
    parts = packet["docx_checks"].get("parts", {})
    render = packet["render_check"]
    lines.extend(
        [
            "",
            "## DOCX Checks",
            "",
            f"- ZIP/package integrity: {parts.get('zip_ok')}",
            f"- forbidden DOCX parts present: {len(parts.get('forbidden_parts_present', []))}",
            f"- forbidden custom XML prefix parts present: {len(parts.get('forbidden_prefix_parts_present', []))}",
            f"- stale relationship/content-type references: {len(parts.get('stale_relationship_or_content_type_refs', []))}",
            f"- working-draft warning present: {text.get('working_draft_warning_present')}",
            f"- visible URLs: {text.get('visible_url_count')}",
            f"- visible URL trailing punctuation findings: {len(text.get('visible_urls_with_trailing_punctuation', []))}",
            f"- visible placeholder findings: {len(text.get('placeholder_hits', []))}",
            f"- ROM/full-proposal cost boundary present: {text.get('rom_cost_boundary_present')}",
            "",
            "## Render Lock",
            "",
            f"- render directory: `{render['render_dir']}`",
            f"- PDF present: {render['pdf']['exists']}",
            f"- page PNG count: {render['page_png_count']}/{render['expected_page_png_count']}",
            f"- render check ok: {render['ok']}",
            "",
            "## Local Blockers",
            "",
        ]
    )
    if packet["local_blockers"]:
        lines.extend(f"- {item}" for item in packet["local_blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Portal/User Blockers", ""])
    lines.extend(f"- {item}" for item in packet["portal_user_blockers"])
    lines.extend(
        [
            "",
            "## Upload Rule",
            "",
            "Do not remove the working-draft warning, upload, consent, certify, or submit until BAAT/SAM authority, cost boundary, reference relevance, layout preview, and human action-time approval are all cleared.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DICE.mkdir(parents=True, exist_ok=True)
    packet = build_packet()
    JSON_OUT.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    MD_OUT.write_text(render_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "posture": packet["posture"],
                "local_blockers": len(packet["local_blockers"]),
                "portal_user_blockers": len(packet["portal_user_blockers"]),
                "json": rel(JSON_OUT),
                "md": rel(MD_OUT),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
