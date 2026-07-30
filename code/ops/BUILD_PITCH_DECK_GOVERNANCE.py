"""Build a fail-closed registry for current and historical pitch decks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "pitch_deck_governance_v1.json"
OUTPUT_JSON = ROOT / "out" / "ops" / "pitch_deck_governance_latest.json"
OUTPUT_MD = ROOT / "docs" / "PITCH_DECK_GOVERNANCE_2026-07-29.md"
CURRENT_REVIEW_PDF = (
    ROOT
    / "output"
    / "pdf"
    / "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pdf"
)
SCHEMA = "lumencore.pitch_deck_governance.v1"
CONFIG_SCHEMA = "lumencore.pitch_deck_governance_config.v1"
ALLOWED_STATUSES = {
    "APPLICATION_SPECIFIC_REVIEW_REQUIRED_DO_NOT_SEND",
    "CURRENT_HUMAN_REVIEW_REQUIRED",
    "ARCHIVAL_PROVENANCE_DO_NOT_SEND",
    "GENERATED_HISTORICAL_DO_NOT_SEND",
    "HISTORICAL_APPLICATION_SPECIFIC_DO_NOT_SEND",
    "HISTORICAL_STALE_DO_NOT_SEND",
    "HISTORICAL_SPECULATIVE_DO_NOT_SEND",
    "LEGACY_HIGH_RISK_DO_NOT_SEND",
    "SOURCE_TEMPLATE_NOT_A_LUMENCORE_DECK",
}
EXPECTED_CONTROLS = {
    "action_time_human_approval_required": True,
    "external_release_default": False,
    "historical_decks_blocked": True,
    "preserve_negative_results": True,
    "source_notes_required_for_current_deck": True,
    "unregistered_pptx_blocks_release": True,
    "unsupported_financial_claims_block_release": True,
}
TEXT_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"


class DeckGovernanceError(ValueError):
    """Raised when a deck-governance invariant fails."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeckGovernanceError(f"Unreadable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DeckGovernanceError(f"Expected an object: {path}")
    return value


def canonical_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def normalize(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DeckGovernanceError("as_of_utc must be canonical UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise DeckGovernanceError("as_of_utc is invalid") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 1:
        raise DeckGovernanceError("Unsupported pitch-deck governance config")
    if config.get("controls") != EXPECTED_CONTROLS:
        raise DeckGovernanceError("Pitch-deck controls are not fail-closed")
    discovery = config.get("discovery")
    if not isinstance(discovery, dict) or not discovery.get("roots"):
        raise DeckGovernanceError("Deck discovery roots are required")
    if discovery.get("extension") != ".pptx":
        raise DeckGovernanceError("Deck discovery must be limited to .pptx")
    artifacts = config.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise DeckGovernanceError("Deck artifacts must be a nonempty list")
    collections = config.get("legacy_collections")
    if not isinstance(collections, list) or not collections:
        raise DeckGovernanceError("Legacy deck collections must be a nonempty list")
    collection_ids: set[str] = set()
    collection_prefixes: set[str] = set()
    for index, collection in enumerate(collections):
        label = f"legacy_collections[{index}]"
        if not isinstance(collection, dict):
            raise DeckGovernanceError(f"{label} must be an object")
        collection_id = collection.get("id")
        prefix = collection.get("path_prefix")
        if not isinstance(collection_id, str) or not collection_id:
            raise DeckGovernanceError(f"{label}.id is required")
        if (
            not isinstance(prefix, str)
            or not prefix
            or not prefix.endswith("/")
        ):
            raise DeckGovernanceError(f"{label}.path_prefix is invalid")
        if collection_id in collection_ids or prefix in collection_prefixes:
            raise DeckGovernanceError("Duplicate legacy collection id or prefix")
        collection_ids.add(collection_id)
        collection_prefixes.add(prefix)
        if collection.get("status") not in ALLOWED_STATUSES:
            raise DeckGovernanceError(f"{label}.status is invalid")
        if collection.get("external_release_authorized") is not False:
            raise DeckGovernanceError(f"{label} must block external release")
        if collection.get("send_eligible") is not False:
            raise DeckGovernanceError(f"{label} must block sending")
    ids: set[str] = set()
    paths: set[str] = set()
    current_count = 0
    for index, artifact in enumerate(artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise DeckGovernanceError(f"{label} must be an object")
        artifact_id = artifact.get("id")
        path = artifact.get("path")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise DeckGovernanceError(f"{label}.id is required")
        if not isinstance(path, str) or not path.endswith(".pptx"):
            raise DeckGovernanceError(f"{label}.path must be a .pptx")
        if artifact_id in ids or path in paths:
            raise DeckGovernanceError("Duplicate pitch-deck id or path")
        ids.add(artifact_id)
        paths.add(path)
        status = artifact.get("status")
        if status not in ALLOWED_STATUSES:
            raise DeckGovernanceError(f"{label}.status is invalid")
        current_count += status == "CURRENT_HUMAN_REVIEW_REQUIRED"
        if artifact.get("external_release_authorized") is not False:
            raise DeckGovernanceError(f"{label} must block external release")
        if artifact.get("send_eligible") is not False:
            raise DeckGovernanceError(f"{label} must block sending")
        for field in (
            "required_text_markers",
            "banned_text_markers",
            "dependencies",
        ):
            values = artifact.get(field)
            if not isinstance(values, list) or not all(
                isinstance(value, str) and value for value in values
            ):
                raise DeckGovernanceError(f"{label}.{field} is invalid")
    if current_count != 1:
        raise DeckGovernanceError("Exactly one current deck is required")
    if config.get("source_template") not in paths:
        raise DeckGovernanceError("source_template must be a registered deck")
    if not config.get("claim_boundary"):
        raise DeckGovernanceError("claim_boundary is required")


def discover_pptx(config: dict[str, Any]) -> list[str]:
    discovered: set[str] = set()
    for root_name in config["discovery"]["roots"]:
        root = ROOT / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*.pptx"):
            if path.is_file():
                discovered.add(normalize(path))
    return sorted(discovered)


def legacy_collection_for(
    path: str,
    collections: list[dict[str, Any]],
) -> dict[str, Any] | None:
    matches = [
        collection
        for collection in collections
        if path.startswith(collection["path_prefix"])
    ]
    if len(matches) > 1:
        raise DeckGovernanceError(
            f"Deck matches multiple legacy collections: {path}"
        )
    return matches[0] if matches else None


def natural_xml_key(name: str) -> tuple[str, int]:
    match = re.search(r"(\d+)\.xml$", name)
    return name, int(match.group(1)) if match else -1


def pptx_text_receipt(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            slide_names = sorted(
                (
                    name
                    for name in names
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
                ),
                key=natural_xml_key,
            )
            note_names = sorted(
                (
                    name
                    for name in names
                    if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)
                ),
                key=natural_xml_key,
            )
            slide_text = []
            for name in slide_names:
                root = ElementTree.fromstring(archive.read(name))
                slide_text.extend(node.text or "" for node in root.iter(TEXT_TAG))
            note_texts: list[str] = []
            for name in note_names:
                root = ElementTree.fromstring(archive.read(name))
                note_texts.append(
                    "\n".join(node.text or "" for node in root.iter(TEXT_TAG))
                )
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise DeckGovernanceError(f"Unreadable PPTX: {path}") from exc
    return {
        "slide_count": len(slide_names),
        "notes_count": len(note_names),
        "notes_with_sources_count": sum("[Sources]" in text for text in note_texts),
        "text": "\n".join(slide_text),
    }


def pdf_text_receipt(path: Path) -> dict[str, Any]:
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise DeckGovernanceError(f"Encrypted PDF companion: {path}")
        page_text = [page.extract_text() or "" for page in reader.pages]
    except DeckGovernanceError:
        raise
    except Exception as exc:
        raise DeckGovernanceError(f"Unreadable PDF companion: {path}") from exc
    text = re.sub(r"\s+", " ", "\n".join(page_text)).strip()
    return {
        "page_count": len(reader.pages),
        "text": text,
    }


def build_registry(
    config_path: Path = CONFIG_PATH,
    *,
    as_of_utc: str,
) -> dict[str, Any]:
    parse_utc(as_of_utc)
    config = read_json(config_path)
    validate_config(config)
    registered = {artifact["path"] for artifact in config["artifacts"]}
    discovered = set(discover_pptx(config))
    collection_matches = {
        path: legacy_collection_for(path, config["legacy_collections"])
        for path in sorted(discovered - registered)
    }
    unregistered = sorted(
        path for path, collection in collection_matches.items() if collection is None
    )

    missing_artifacts: list[str] = []
    missing_dependencies: list[str] = []
    marker_failures: list[str] = []
    banned_marker_failures: list[str] = []
    count_failures: list[str] = []
    records: list[dict[str, Any]] = []

    for artifact in config["artifacts"]:
        path = ROOT / artifact["path"]
        if not path.is_file():
            missing_artifacts.append(artifact["path"])
            continue
        receipt = pptx_text_receipt(path)
        missing_markers = [
            marker
            for marker in artifact["required_text_markers"]
            if marker not in receipt["text"]
        ]
        present_banned = [
            marker
            for marker in artifact["banned_text_markers"]
            if marker in receipt["text"]
        ]
        if missing_markers:
            marker_failures.append(artifact["path"])
        if present_banned:
            banned_marker_failures.append(artifact["path"])
        if (
            artifact.get("required_slide_count") is not None
            and receipt["slide_count"] != artifact["required_slide_count"]
        ):
            count_failures.append(artifact["path"])
        if (
            artifact.get("required_notes_sources_count") is not None
            and receipt["notes_with_sources_count"]
            != artifact["required_notes_sources_count"]
        ):
            count_failures.append(artifact["path"])

        dependency_receipts = []
        for dependency in artifact["dependencies"]:
            dependency_path = ROOT / dependency
            if not dependency_path.is_file():
                missing_dependencies.append(dependency)
                continue
            dependency_receipts.append(
                {
                    "path": dependency,
                    "bytes": dependency_path.stat().st_size,
                    "sha256": sha256_file(dependency_path),
                }
            )
        records.append(
            {
                **artifact,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "slide_count": receipt["slide_count"],
                "notes_count": receipt["notes_count"],
                "notes_with_sources_count": receipt["notes_with_sources_count"],
                "missing_text_markers": missing_markers,
                "present_banned_text_markers": present_banned,
                "dependencies": dependency_receipts,
            }
        )

    legacy_collection_file_count = 0
    for path_text, collection in collection_matches.items():
        if collection is None:
            continue
        path = ROOT / path_text
        receipt = pptx_text_receipt(path)
        records.append(
            {
                "id": f"{collection['id']}::{path_text}",
                "collection_id": collection["id"],
                "path": path_text,
                "status": collection["status"],
                "external_release_authorized": False,
                "send_eligible": False,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "slide_count": receipt["slide_count"],
                "notes_count": receipt["notes_count"],
                "notes_with_sources_count": receipt["notes_with_sources_count"],
                "required_text_markers": [],
                "banned_text_markers": [],
                "missing_text_markers": [],
                "present_banned_text_markers": [],
                "dependencies": [],
            }
        )
        legacy_collection_file_count += 1

    records.sort(key=lambda row: (row["status"] != "CURRENT_HUMAN_REVIEW_REQUIRED", row["path"]))
    current = next(
        (
            row
            for row in records
            if row["status"] == "CURRENT_HUMAN_REVIEW_REQUIRED"
        ),
        None,
    )
    current_pdf: dict[str, Any] | None = None
    missing_current_pdf: list[str] = []
    pdf_page_count_failures: list[str] = []
    pdf_marker_failures: list[str] = []
    pdf_freshness_failures: list[str] = []
    if current is not None:
        if not CURRENT_REVIEW_PDF.is_file():
            missing_current_pdf.append(normalize(CURRENT_REVIEW_PDF))
        else:
            pdf_receipt = pdf_text_receipt(CURRENT_REVIEW_PDF)
            normalized_markers = {
                marker: re.sub(r"\s+", " ", marker).strip()
                for marker in current["required_text_markers"]
            }
            missing_pdf_markers = [
                marker
                for marker, normalized_marker in normalized_markers.items()
                if normalized_marker not in pdf_receipt["text"]
            ]
            if pdf_receipt["page_count"] != current["slide_count"]:
                pdf_page_count_failures.append(normalize(CURRENT_REVIEW_PDF))
            if missing_pdf_markers:
                pdf_marker_failures.append(normalize(CURRENT_REVIEW_PDF))
            current_source = ROOT / current["path"]
            if CURRENT_REVIEW_PDF.stat().st_mtime_ns < current_source.stat().st_mtime_ns:
                pdf_freshness_failures.append(normalize(CURRENT_REVIEW_PDF))
            current_pdf = {
                "path": normalize(CURRENT_REVIEW_PDF),
                "bytes": CURRENT_REVIEW_PDF.stat().st_size,
                "sha256": sha256_file(CURRENT_REVIEW_PDF),
                "page_count": pdf_receipt["page_count"],
                "source_pptx_path": current["path"],
                "source_pptx_sha256": current["sha256"],
                "missing_text_markers": missing_pdf_markers,
                "external_release_authorized": False,
                "send_eligible": False,
                "status": "CURRENT_PDF_COMPANION_HUMAN_REVIEW_REQUIRED",
            }

    blockers = {
        "missing_artifacts": sorted(set(missing_artifacts)),
        "unregistered_pptx": unregistered,
        "registered_but_undiscovered_pptx": sorted(registered - discovered),
        "missing_dependencies": sorted(set(missing_dependencies)),
        "required_marker_failures": sorted(set(marker_failures)),
        "banned_marker_failures": sorted(set(banned_marker_failures)),
        "slide_or_notes_count_failures": sorted(set(count_failures)),
        "missing_current_pdf": missing_current_pdf,
        "current_pdf_page_count_failures": pdf_page_count_failures,
        "current_pdf_marker_failures": pdf_marker_failures,
        "current_pdf_freshness_failures": pdf_freshness_failures,
    }
    blocked = any(blockers.values())
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "status": (
            "PITCH_DECK_GOVERNANCE_BLOCKED"
            if blocked
            else "GOVERNED_CURRENT_DECK_WITH_ARCHIVED_LEGACY"
        ),
        "as_of_utc": as_of_utc,
        "summary": {
            "registered_pptx_count": len(records),
            "registered_exact_pptx_count": len(config["artifacts"]),
            "legacy_collection_file_count": legacy_collection_file_count,
            "verified_pptx_count": len(records),
            "current_deck_count": int(current is not None),
            "current_pdf_companion_count": int(current_pdf is not None),
            "historical_or_template_count": sum(
                row["status"] != "CURRENT_HUMAN_REVIEW_REQUIRED"
                for row in records
            ),
            "external_release_authorized_count": sum(
                bool(row["external_release_authorized"]) for row in records
            ),
            "send_eligible_count": sum(bool(row["send_eligible"]) for row in records),
        },
        "controls": config["controls"],
        "source_template": config["source_template"],
        "current_deck": current,
        "current_pdf_companion": current_pdf,
        "artifacts": records,
        "blockers": blockers,
        "claim_boundary": config["claim_boundary"],
        "safest_next_action": (
            "Resolve every deck registry blocker before reviewer use."
            if blocked
            else (
                "Use only the current review-required deck or its governed PDF companion after founder, recipient, "
                "and venue-specific review; this receipt does not authorize sending or publication."
            )
        ),
        "control_sha256": "",
    }
    payload["control_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "control_sha256"}
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Pitch Deck Governance",
        "",
        f"- Status: `{payload['status']}`",
        f"- As of: `{payload['as_of_utc']}`",
        f"- Registered PPTX files: `{payload['summary']['registered_pptx_count']}`",
        f"- Current PDF companion: `{payload['summary']['current_pdf_companion_count']}`",
        "- External release authorized: `false`",
        "- Send eligible: `false`",
        "",
        "## Deck Registry",
        "",
        "| Deck | Status | Slides | Sources notes | Release |",
        "|---|---|---:|---:|---|",
    ]
    for row in payload["artifacts"]:
        lines.append(
            f"| `{row['path']}` | `{row['status']}` | "
            f"{row['slide_count']} | {row['notes_with_sources_count']} | blocked |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            "## Safest Next Action",
            "",
            payload["safest_next_action"],
            "",
            f"Control SHA-256: `{payload['control_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument(
        "--as-of-utc",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_registry(args.config, as_of_utc=args.as_of_utc)
    if not args.check:
        write_outputs(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] != "PITCH_DECK_GOVERNANCE_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
