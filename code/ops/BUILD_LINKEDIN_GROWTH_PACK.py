from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "linkedin_growth_pack_v1.json"
DEFAULT_OUT_DIR = ROOT / "out" / "linkedin_growth_pack"

CONFIG_SCHEMA = "lumencore.linkedin_growth_pack.config.v1"
PACK_SCHEMA = "lumencore.linkedin_growth_pack.v1"
MANIFEST_SCHEMA = "lumencore.linkedin_growth_pack.manifest.v1"
VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}

PRIVATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "email_address",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        "us_phone_number",
        re.compile(
            r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?!\d)"
        ),
    ),
    ("uei_label", re.compile(r"\bUEI\b", re.IGNORECASE)),
    ("cage_label", re.compile(r"\bCAGE\b", re.IGNORECASE)),
    ("firm_pin", re.compile(r"\bfirm\s+pin\b", re.IGNORECASE)),
    ("credential_query", re.compile(r"[?&](?:token|code|auth|key|secret)=", re.IGNORECASE)),
    ("api_key_shape", re.compile(r"\b(?:sk|xox[baprs])-[A-Za-z0-9_-]{10,}\b")),
)

UNSUPPORTED_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("award_winning", re.compile(r"\baward[- ]winning\b", re.IGNORECASE)),
    ("best_in_class", re.compile(r"\bbest[- ]in[- ]class\b", re.IGNORECASE)),
    ("number_one", re.compile(r"(?<!\w)#\s*1\b", re.IGNORECASE)),
    ("guaranteed", re.compile(r"\bguarante(?:e|ed|es|eing)\b", re.IGNORECASE)),
    ("government_approved", re.compile(r"\bgovernment[- ]approved\b", re.IGNORECASE)),
    ("government_grade", re.compile(r"\bgovernment[- ]grade\b", re.IGNORECASE)),
    ("institutional_grade", re.compile(r"\binstitutional[- ]grade\b", re.IGNORECASE)),
    ("field_validated", re.compile(r"\bfield[- ]validated\b", re.IGNORECASE)),
    ("externally_validated", re.compile(r"\bexternally[- ]validated\b", re.IGNORECASE)),
    (
        "independently_validated",
        re.compile(r"\bindependently[- ]validated\b", re.IGNORECASE),
    ),
    ("production_ready", re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE)),
    ("patented", re.compile(r"\bpatented\b", re.IGNORECASE)),
    ("proven_savings", re.compile(r"\bproven\s+(?:cost\s+)?savings\b", re.IGNORECASE)),
    ("risk_free", re.compile(r"\brisk[- ]free\b", re.IGNORECASE)),
)


class GrowthPackError(ValueError):
    """Raised when the growth pack cannot be built safely."""


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def pretty_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GrowthPackError(f"Unable to read JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GrowthPackError(f"Expected a JSON object in {path}")
    return payload


def normalize_relpath(value: str) -> str:
    normalized = str(value or "").replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or any(":" in part for part in path.parts)
    ):
        raise GrowthPackError(f"Unsafe repository-relative path: {value!r}")
    return path.as_posix()


def resolve_repo_path(root: Path, value: str) -> Path:
    relative = normalize_relpath(value)
    candidate = (root / Path(relative)).resolve()
    resolved_root = root.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise GrowthPackError(f"Path escapes repository root: {value!r}") from exc
    return candidate


def parse_utc(value: str) -> datetime:
    text = str(value or "").strip()
    if not text.endswith("Z"):
        raise GrowthPackError(f"UTC timestamp must end in Z: {value!r}")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise GrowthPackError(f"Invalid UTC timestamp: {value!r}") from exc
    return parsed


def require_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise GrowthPackError(f"{key} must be a list")
    return value


def require_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise GrowthPackError(f"{key} must be an object")
    return value


def duplicate_values(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        output: list[str] = []
        for key in sorted(value):
            output.extend(flatten_text(value[key]))
        return output
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(flatten_text(item))
        return output
    return []


def public_copy_payload(config: dict[str, Any]) -> dict[str, Any]:
    featured = [
        item
        for item in require_list(config, "featured_links")
        if isinstance(item, dict) and item.get("decision") == "FEATURE"
    ]
    return {
        "profile": require_dict(config, "profile"),
        "featured_links": featured,
        "live_profile_snapshot": require_dict(config, "live_profile_snapshot"),
        "profile_gap_actions": require_list(config, "profile_gap_actions"),
        "project_drafts": require_list(config, "project_drafts"),
        "calendar": require_list(config, "calendar"),
        "post_drafts": require_list(config, "post_drafts"),
        "reply_templates": require_list(config, "reply_templates"),
        "message_action_drafts": require_list(config, "message_action_drafts"),
        "content_risk_register": require_list(config, "content_risk_register"),
        "storyboard_briefs": require_list(config, "storyboard_briefs"),
    }


def scan_public_copy(config: dict[str, Any]) -> dict[str, list[str]]:
    text = "\n".join(flatten_text(public_copy_payload(config)))
    private_hits = [
        name for name, pattern in PRIVATE_PATTERNS if pattern.search(text)
    ]
    unsupported_hits = [
        name for name, pattern in UNSUPPORTED_CLAIM_PATTERNS if pattern.search(text)
    ]
    return {
        "private_hits": sorted(set(private_hits)),
        "unsupported_claim_hits": sorted(set(unsupported_hits)),
    }


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA:
        raise GrowthPackError(
            f"schema must be {CONFIG_SCHEMA!r}; got {config.get('schema')!r}"
        )
    parse_utc(str(config.get("as_of_utc") or ""))

    controls = require_dict(config, "action_controls")
    required_false = (
        "linkedin_access_allowed",
        "profile_edit_allowed",
        "post_allowed",
        "message_allowed",
        "follow_action_allowed",
        "external_send_allowed",
    )
    for key in required_false:
        if controls.get(key) is not False:
            raise GrowthPackError(f"action_controls.{key} must be false")
    if controls.get("human_review_required") is not True:
        raise GrowthPackError("action_controls.human_review_required must be true")

    for source in require_list(config, "source_evidence"):
        if not isinstance(source, dict):
            raise GrowthPackError("Each source_evidence entry must be an object")
        normalize_relpath(str(source.get("path") or ""))

    profile = require_dict(config, "profile")
    headlines = [str(profile.get("headline") or "")] + [
        str(item) for item in require_list(profile, "headline_variants")
    ]
    if any(not value for value in headlines):
        raise GrowthPackError("Every headline must be non-empty")
    if any(len(value) > 220 for value in headlines):
        raise GrowthPackError("LinkedIn headlines must be 220 characters or fewer")
    if len(str(profile.get("about") or "")) < 600:
        raise GrowthPackError("Profile About draft is unexpectedly short")
    if len(require_list(profile, "experience_bullets")) < 5:
        raise GrowthPackError("At least five experience bullets are required")

    featured_links = require_list(config, "featured_links")
    positions: list[int] = []
    for item in featured_links:
        if not isinstance(item, dict):
            raise GrowthPackError("Each featured link must be an object")
        decision = item.get("decision")
        if decision not in {"FEATURE", "HOLD"}:
            raise GrowthPackError("Featured link decision must be FEATURE or HOLD")
        if decision == "FEATURE":
            if int(item.get("http_status") or 0) != 200:
                raise GrowthPackError("FEATURE links must have a recorded HTTP 200")
            position = int(item.get("position") or 0)
            if position <= 0:
                raise GrowthPackError("FEATURE links require a positive position")
            positions.append(position)
    if sorted(positions) != list(range(1, len(positions) + 1)):
        raise GrowthPackError("FEATURE positions must be contiguous starting at 1")

    snapshot = require_dict(config, "live_profile_snapshot")
    if snapshot.get("source") != "USER_SUPPLIED_READ_ONLY_LINKEDIN_FINDINGS":
        raise GrowthPackError("live_profile_snapshot must identify its read-only source")
    parse_utc(str(snapshot.get("observed_utc") or ""))
    if snapshot.get("access_mode") != "READ_ONLY_NO_MUTATION":
        raise GrowthPackError("live_profile_snapshot access_mode must be read-only")
    metrics = require_dict(snapshot, "metrics")
    for key in (
        "connections",
        "followers",
        "profile_views",
        "post_impressions_7d",
        "search_appearances",
    ):
        value = metrics.get(key)
        if not isinstance(value, int) or value < 0:
            raise GrowthPackError(f"live_profile_snapshot.metrics.{key} must be >= 0")

    gap_actions = require_list(config, "profile_gap_actions")
    gap_ids = [
        str(item.get("id") or "") for item in gap_actions if isinstance(item, dict)
    ]
    if len(gap_actions) < 8 or duplicate_values(gap_ids):
        raise GrowthPackError("At least eight unique profile gap actions are required")

    project_drafts = require_list(config, "project_drafts")
    project_ids = [
        str(item.get("id") or "") for item in project_drafts if isinstance(item, dict)
    ]
    if len(project_drafts) < 2 or duplicate_values(project_ids):
        raise GrowthPackError("At least two unique project drafts are required")

    posts = require_list(config, "post_drafts")
    post_ids = [str(item.get("id") or "") for item in posts if isinstance(item, dict)]
    if len(posts) < 10 or any(not value for value in post_ids):
        raise GrowthPackError("At least ten identified post drafts are required")
    if duplicate_values(post_ids):
        raise GrowthPackError("Post draft IDs must be unique")

    calendar = require_list(config, "calendar")
    if len(calendar) != 30:
        raise GrowthPackError("The content calendar must contain exactly 30 days")
    known_post_ids = set(post_ids)
    prior_date: date | None = None
    for expected_day, item in enumerate(calendar, start=1):
        if not isinstance(item, dict):
            raise GrowthPackError("Each calendar entry must be an object")
        if int(item.get("day") or 0) != expected_day:
            raise GrowthPackError("Calendar day numbers must be contiguous")
        try:
            current_date = date.fromisoformat(str(item.get("date") or ""))
        except ValueError as exc:
            raise GrowthPackError("Calendar dates must use YYYY-MM-DD") from exc
        if prior_date is not None and (current_date - prior_date).days != 1:
            raise GrowthPackError("Calendar dates must be consecutive")
        prior_date = current_date
        draft_id = str(item.get("draft_id") or "")
        if draft_id and draft_id not in known_post_ids:
            raise GrowthPackError(f"Unknown calendar draft_id: {draft_id}")

    replies = require_list(config, "reply_templates")
    reply_ids = [
        str(item.get("id") or "") for item in replies if isinstance(item, dict)
    ]
    if len(replies) < 10 or duplicate_values(reply_ids):
        raise GrowthPackError("At least ten uniquely identified reply templates are required")

    message_drafts = require_list(config, "message_action_drafts")
    message_ids = [
        str(item.get("id") or "") for item in message_drafts if isinstance(item, dict)
    ]
    if len(message_drafts) < 2 or duplicate_values(message_ids):
        raise GrowthPackError("At least two unique message action drafts are required")
    for item in message_drafts:
        if not isinstance(item, dict):
            raise GrowthPackError("Each message action draft must be an object")
        if item.get("send_allowed") is not False:
            raise GrowthPackError("Every message action draft must keep send_allowed false")
        if item.get("status") != "DRAFT_NOT_SENT":
            raise GrowthPackError("Every message action draft must be DRAFT_NOT_SENT")

    risks = require_list(config, "content_risk_register")
    risk_ids = [str(item.get("id") or "") for item in risks if isinstance(item, dict)]
    if not risks or duplicate_values(risk_ids):
        raise GrowthPackError("Content risk register IDs must be present and unique")
    if not any(
        isinstance(item, dict)
        and item.get("severity") == "HIGH"
        and item.get("automation_action") == "NONE"
        for item in risks
    ):
        raise GrowthPackError(
            "Content risk register must preserve a high-risk human-only review item"
        )

    media = require_dict(config, "media")
    scan_roots = [normalize_relpath(str(item)) for item in require_list(media, "scan_roots")]
    if not scan_roots:
        raise GrowthPackError("At least one media scan root is required")
    asset_paths: list[str] = []
    for asset in require_list(media, "primary_assets"):
        if not isinstance(asset, dict):
            raise GrowthPackError("Each primary media asset must be an object")
        asset_paths.append(normalize_relpath(str(asset.get("path") or "")))
        receipt_path = str(asset.get("receipt_path") or "")
        if receipt_path:
            normalize_relpath(receipt_path)
    if duplicate_values(asset_paths):
        raise GrowthPackError("Primary media asset paths must be unique")

    storyboards = require_list(config, "storyboard_briefs")
    if len(storyboards) < 3:
        raise GrowthPackError("At least three storyboard briefs are required")
    for storyboard in storyboards:
        if not isinstance(storyboard, dict):
            raise GrowthPackError("Each storyboard brief must be an object")
        source_path = normalize_relpath(str(storyboard.get("source_path") or ""))
        if source_path not in asset_paths:
            raise GrowthPackError(
                f"Storyboard source is not a configured primary asset: {source_path}"
            )
        if len(storyboard.get("scenes") or []) < 4:
            raise GrowthPackError("Each storyboard needs at least four scenes")

    safety = scan_public_copy(config)
    if safety["private_hits"]:
        raise GrowthPackError(
            "Public copy contains private markers: "
            + ", ".join(safety["private_hits"])
        )
    if safety["unsupported_claim_hits"]:
        raise GrowthPackError(
            "Public copy contains unsupported claims: "
            + ", ".join(safety["unsupported_claim_hits"])
        )


def source_evidence(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    missing_required: list[str] = []
    for item in require_list(config, "source_evidence"):
        relative = normalize_relpath(str(item.get("path") or ""))
        path = resolve_repo_path(root, relative)
        required = bool(item.get("required", True))
        present = path.is_file()
        if required and not present:
            missing_required.append(relative)
        record = {
            "path": relative,
            "required": required,
            "present": present,
            "supports": [str(value) for value in item.get("supports", [])],
            "public_use_note": str(item.get("public_use_note") or ""),
            "bytes": path.stat().st_size if present else 0,
            "sha256": sha256_file(path) if present else "",
        }
        records.append(record)
    if missing_required:
        raise GrowthPackError(
            "Required evidence sources are missing: " + ", ".join(missing_required)
        )
    return records


def discover_videos(root: Path, scan_roots: list[str]) -> list[Path]:
    discovered: dict[str, Path] = {}
    for root_text in scan_roots:
        scan_root = resolve_repo_path(root, root_text)
        if not scan_root.is_dir():
            continue
        for current, directories, filenames in os.walk(scan_root):
            directories.sort()
            filenames.sort()
            for filename in filenames:
                path = Path(current) / filename
                if path.suffix.lower() not in VIDEO_EXTENSIONS or path.is_symlink():
                    continue
                relative = path.resolve().relative_to(root.resolve()).as_posix()
                discovered[relative] = path
    return [discovered[key] for key in sorted(discovered)]


def classify_video(relative: str, configured: dict[str, dict[str, Any]]) -> str:
    if relative in configured:
        return str(configured[relative].get("media_class") or "PRIMARY_ASSET")
    parts = PurePosixPath(relative).parts
    if len(parts) >= 2 and parts[:2] == ("out", "reviewer_handoffs"):
        return "HANDOFF_COPY"
    if "segments" in parts:
        if PurePosixPath(relative).name.startswith("xfade_test"):
            return "TEST_DERIVATIVE"
        return "DERIVATIVE_SEGMENT"
    return "LOCAL_VIDEO"


def probe_video(path: Path) -> dict[str, Any]:
    try:
        import imageio_ffmpeg  # type: ignore
    except ImportError:
        return {"state": "PROBE_DEPENDENCY_UNAVAILABLE"}

    try:
        executable = imageio_ffmpeg.get_ffmpeg_exe()
        completed = subprocess.run(
            [executable, "-hide_banner", "-i", str(path)],
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "state": "PROBE_FAILED",
            "error_class": exc.__class__.__name__,
        }

    probe_text = completed.stderr
    duration_match = re.search(
        r"Duration:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)",
        probe_text,
    )
    video_match = re.search(
        r"Video:\s*([^,\s]+).*?,\s*(\d{2,5})x(\d{2,5})(?:[,\s])",
        probe_text,
    )
    fps_match = re.search(r"(\d+(?:\.\d+)?)\s+fps", probe_text)
    if not video_match:
        return {
            "state": "PROBE_FAILED",
            "error_class": "VideoStreamNotFound",
        }

    width = int(video_match.group(2))
    height = int(video_match.group(3))
    duration_seconds = 0.0
    if duration_match:
        duration_seconds = (
            int(duration_match.group(1)) * 3600
            + int(duration_match.group(2)) * 60
            + float(duration_match.group(3))
        )
    if width and height:
        orientation = (
            "portrait" if height > width else "landscape" if width > height else "square"
        )
    else:
        orientation = "unknown"
    return {
        "state": "PROBED",
        "codec": video_match.group(1),
        "duration_seconds": round(duration_seconds, 3),
        "fps": round(float(fps_match.group(1)), 3) if fps_match else 0.0,
        "width": width,
        "height": height,
        "orientation": orientation,
    }


def receipt_metadata(root: Path, asset: dict[str, Any]) -> dict[str, Any]:
    receipt_text = str(asset.get("receipt_path") or "")
    if not receipt_text:
        return {
            "state": "NO_RECEIPT_CONFIGURED",
            "path": "",
            "schema": "",
            "schema_matches": False,
            "sha256": "",
        }
    relative = normalize_relpath(receipt_text)
    path = resolve_repo_path(root, relative)
    if not path.is_file():
        return {
            "state": "RECEIPT_MISSING",
            "path": relative,
            "schema": "",
            "schema_matches": False,
            "sha256": "",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
    schema = str(payload.get("schema") or "") if isinstance(payload, dict) else ""
    expected = str(asset.get("receipt_schema") or "")
    return {
        "state": "RECEIPT_PRESENT",
        "path": relative,
        "schema": schema,
        "schema_matches": bool(expected and schema == expected),
        "sha256": sha256_file(path),
    }


def preferred_canonical(
    paths: list[str],
    preferred_order: dict[str, int],
    classes: dict[str, str],
) -> str:
    class_order = {
        "PRIMARY_RENDER": 0,
        "RAW_LOCAL_CLIP": 1,
        "LOCAL_VIDEO": 2,
        "DERIVATIVE_SEGMENT": 3,
        "TEST_DERIVATIVE": 4,
        "HANDOFF_COPY": 5,
    }
    return min(
        paths,
        key=lambda value: (
            preferred_order.get(value, 10_000),
            class_order.get(classes.get(value, ""), 100),
            len(value),
            value,
        ),
    )


def video_inventory(
    root: Path,
    config: dict[str, Any],
    *,
    probe_media: bool,
) -> dict[str, Any]:
    media = require_dict(config, "media")
    configured_assets: dict[str, dict[str, Any]] = {}
    primary_order: dict[str, int] = {}
    for index, asset in enumerate(require_list(media, "primary_assets")):
        relative = normalize_relpath(str(asset.get("path") or ""))
        configured_assets[relative] = asset
        primary_order[relative] = index

    scan_roots = [
        normalize_relpath(str(item)) for item in require_list(media, "scan_roots")
    ]
    paths = discover_videos(root, scan_roots)
    items: list[dict[str, Any]] = []
    classes: dict[str, str] = {}
    hashes: dict[str, list[str]] = {}

    for path in paths:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        media_class = classify_video(relative, configured_assets)
        classes[relative] = media_class
        digest = sha256_file(path)
        hashes.setdefault(digest, []).append(relative)
        asset = configured_assets.get(relative, {})
        should_probe = probe_media and media_class in {"PRIMARY_RENDER", "RAW_LOCAL_CLIP"}
        probe = (
            probe_video(path)
            if should_probe
            else {"state": "SKIPPED_NONPRIMARY_OR_DISABLED"}
        )
        receipt = receipt_metadata(root, asset) if asset else {
            "state": "NOT_APPLICABLE",
            "path": "",
            "schema": "",
            "schema_matches": False,
            "sha256": "",
        }
        items.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": digest,
                "extension": path.suffix.lower(),
                "media_class": media_class,
                "title": str(asset.get("title") or path.stem),
                "content_summary": str(asset.get("content_summary") or ""),
                "public_use_state": str(
                    asset.get("public_use_state") or "NOT_REVIEWED_FOR_PUBLIC_USE"
                ),
                "claim_boundary": str(asset.get("claim_boundary") or ""),
                "storyboard_rank": int(asset.get("storyboard_rank") or 0),
                "probe": probe,
                "receipt": receipt,
                "duplicate_of": "",
                "duplicate_group_size": 1,
            }
        )

    item_by_path = {item["path"]: item for item in items}
    for digest, duplicate_paths in hashes.items():
        if len(duplicate_paths) < 2:
            continue
        canonical = preferred_canonical(
            duplicate_paths,
            preferred_order=primary_order,
            classes=classes,
        )
        for relative in duplicate_paths:
            item = item_by_path[relative]
            item["duplicate_group_size"] = len(duplicate_paths)
            if relative != canonical:
                item["duplicate_of"] = canonical

    items.sort(
        key=lambda item: (
            -int(item.get("storyboard_rank") or 0),
            str(item.get("path") or ""),
        )
    )
    primary = [
        item
        for item in items
        if item["media_class"] in {"PRIMARY_RENDER", "RAW_LOCAL_CLIP"}
    ]
    receipt_backed = [
        item
        for item in primary
        if item["receipt"]["state"] == "RECEIPT_PRESENT"
        and item["receipt"]["schema_matches"]
    ]
    return {
        "scan_roots": scan_roots,
        "video_file_count": len(items),
        "unique_content_count": len(hashes),
        "duplicate_file_count": sum(1 for item in items if item["duplicate_of"]),
        "primary_asset_count": len(primary),
        "receipt_backed_primary_count": len(receipt_backed),
        "items": items,
    }


def build_pack(
    root: Path,
    config: dict[str, Any],
    *,
    probe_media: bool = True,
) -> dict[str, Any]:
    validate_config(config)
    sources = source_evidence(root, config)
    inventory = video_inventory(root, config, probe_media=probe_media)
    safety = scan_public_copy(config)

    pack: dict[str, Any] = {
        "schema": PACK_SCHEMA,
        "as_of_utc": str(config["as_of_utc"]),
        "status": "DRAFT_LOCAL_ONLY_HUMAN_PUBLICATION_REQUIRED",
        "owner_public_name": str(config.get("owner_public_name") or ""),
        "brand": str(config.get("brand") or ""),
        "objective": str(config.get("objective") or ""),
        "action_controls": deepcopy(config["action_controls"]),
        "source_evidence": sources,
        "profile": deepcopy(config["profile"]),
        "featured_links": deepcopy(config["featured_links"]),
        "live_profile_snapshot": deepcopy(config["live_profile_snapshot"]),
        "profile_gap_actions": deepcopy(config["profile_gap_actions"]),
        "project_drafts": deepcopy(config["project_drafts"]),
        "calendar": deepcopy(config["calendar"]),
        "post_drafts": deepcopy(config["post_drafts"]),
        "reply_templates": deepcopy(config["reply_templates"]),
        "message_action_drafts": deepcopy(config["message_action_drafts"]),
        "content_risk_register": deepcopy(config["content_risk_register"]),
        "video_inventory": inventory,
        "storyboard_briefs": deepcopy(config["storyboard_briefs"]),
        "safety": {
            "private_hits": safety["private_hits"],
            "unsupported_claim_hits": safety["unsupported_claim_hits"],
            "public_copy_private_hit_count": len(safety["private_hits"]),
            "public_copy_unsupported_claim_hit_count": len(
                safety["unsupported_claim_hits"]
            ),
            "all_public_actions_blocked": True,
            "rule": (
                "This package drafts public copy only. A human must review the exact "
                "text, links, media rights, and current evidence before any LinkedIn action."
            ),
        },
    }
    pack["pack_sha256"] = sha256_bytes(canonical_json_bytes(pack))
    return pack


def md_text(value: Any) -> str:
    return str(value or "").strip()


def render_profile(pack: dict[str, Any]) -> str:
    profile = pack["profile"]
    lines = [
        "# LinkedIn Profile Rewrite",
        "",
        f"Status: `{pack['status']}`",
        f"Evidence cut: `{pack['as_of_utc']}`",
        "",
        "## Recommended Headline",
        "",
        md_text(profile["headline"]),
        "",
        f"Character count: `{len(profile['headline'])}` / 220",
        "",
        "## Headline Variants",
        "",
    ]
    for index, value in enumerate(profile["headline_variants"], start=1):
        lines.append(f"{index}. {md_text(value)}")
    lines.extend(
        [
            "",
            "## About",
            "",
            md_text(profile["about"]),
            "",
            "## Experience",
            "",
            f"### {md_text(profile['experience_title'])}",
            "",
            md_text(profile["experience_intro"]),
            "",
        ]
    )
    for bullet in profile["experience_bullets"]:
        lines.append(f"- {md_text(bullet)}")
    lines.extend(
        [
            "",
            "## Skills Priority",
            "",
            ", ".join(md_text(item) for item in profile["skills"]),
            "",
            "## Use Notes",
            "",
        ]
    )
    for note in profile["use_notes"]:
        lines.append(f"- {md_text(note)}")
    return "\n".join(lines) + "\n"


def render_featured(pack: dict[str, Any]) -> str:
    lines = [
        "# Featured Section Plan",
        "",
        "Only rows marked `FEATURE` belong in the live Featured section. Held links "
        "must be rechecked and repaired before use.",
        "",
        "| Decision | Position | Card title | URL | Recorded status | Purpose |",
        "|---|---:|---|---|---|---|",
    ]
    for item in pack["featured_links"]:
        position = item.get("position") or ""
        status = f"{item.get('http_status')} @ {item.get('verified_utc')}"
        lines.append(
            "| {decision} | {position} | {title} | {url} | {status} | {purpose} |".format(
                decision=md_text(item["decision"]),
                position=position,
                title=md_text(item["card_title"]).replace("|", "/"),
                url=md_text(item["url"]),
                status=md_text(status),
                purpose=md_text(item["purpose"]).replace("|", "/"),
            )
        )
    lines.extend(["", "## Card Copy", ""])
    for item in pack["featured_links"]:
        if item["decision"] != "FEATURE":
            continue
        lines.extend(
            [
                f"### {item['position']}. {md_text(item['card_title'])}",
                "",
                f"- Description: {md_text(item['description'])}",
                f"- Thumbnail copy: `{md_text(item['thumbnail_copy'])}`",
                f"- Visitor action: {md_text(item['visitor_action'])}",
                "",
            ]
        )
    lines.extend(["## Hold Queue", ""])
    for item in pack["featured_links"]:
        if item["decision"] == "HOLD":
            lines.append(
                f"- {md_text(item['url'])}: {md_text(item['hold_reason'])}"
            )
    return "\n".join(lines) + "\n"


def render_profile_gap_action_plan(pack: dict[str, Any]) -> str:
    snapshot = pack["live_profile_snapshot"]
    current = snapshot["current_profile"]
    metrics = snapshot["metrics"]
    lines = [
        "# LinkedIn Profile Gap and Action Plan",
        "",
        f"Observed: `{snapshot['observed_utc']}`",
        f"Source: `{snapshot['source']}`",
        f"Access mode: `{snapshot['access_mode']}`",
        "",
        "This plan records user-supplied read-only findings. It does not confirm that "
        "any profile edit, post edit, message, service change, or removal occurred.",
        "",
        "## Current Read-Only Snapshot",
        "",
        f"- Headline: {md_text(current['headline_summary'])}",
        f"- About: {md_text(current['about_summary'])}",
        f"- Recent video captions: {md_text(current['recent_video_caption_summary'])}",
        "",
        "### Visible Section State",
        "",
        "| Section | Visible |",
        "|---|---|",
    ]
    for section, visible in current["visible_sections"].items():
        lines.append(f"| {section} | {'yes' if visible else 'no'} |")
    lines.extend(
        [
            "",
            "### Current Services",
            "",
            ", ".join(md_text(item) for item in current["services"]),
            "",
            "### Baseline Metrics",
            "",
            "| Metric | Observed value |",
            "|---|---:|",
            f"| Connections | {metrics['connections']} |",
            f"| Followers | {metrics['followers']} |",
            f"| Profile views | {metrics['profile_views']} |",
            f"| Post impressions, 7 days | {metrics['post_impressions_7d']} |",
            f"| Search appearances | {metrics['search_appearances']} |",
            "",
            "These are baseline observations, not performance promises or proof that a "
            "future profile change caused any later movement.",
            "",
            "## Prioritized Actions",
            "",
            "| Priority | Area | Current state | Draft or action | Human gate |",
            "|---:|---|---|---|---|",
        ]
    )
    for item in sorted(pack["profile_gap_actions"], key=lambda value: value["priority"]):
        lines.append(
            "| {priority} | {area} | {current} | {action} | {gate} |".format(
                priority=item["priority"],
                area=md_text(item["area"]).replace("|", "/"),
                current=md_text(item["current_state"]).replace("|", "/"),
                action=md_text(item["draft_or_action"]).replace("|", "/"),
                gate=md_text(item["human_gate"]).replace("|", "/"),
            )
        )
    lines.extend(["", "## Project Section Drafts", ""])
    for project in pack["project_drafts"]:
        lines.extend(
            [
                f"### {md_text(project['title'])}",
                "",
                f"- Role: {md_text(project['role'])}",
                f"- Description: {md_text(project['description'])}",
                f"- Evidence link: {md_text(project['evidence_link'])}",
                f"- Boundary: {md_text(project['boundary'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Content Risk Register",
            "",
            "| Severity | Item | Risk | Human action | Automation action |",
            "|---|---|---|---|---|",
        ]
    )
    for item in pack["content_risk_register"]:
        lines.append(
            "| {severity} | {item} | {risk} | {human} | {automation} |".format(
                severity=md_text(item["severity"]),
                item=md_text(item["item"]).replace("|", "/"),
                risk=md_text(item["risk"]).replace("|", "/"),
                human=md_text(item["human_action"]).replace("|", "/"),
                automation=md_text(item["automation_action"]),
            )
        )
    return "\n".join(lines) + "\n"


def render_message_action_drafts(pack: dict[str, Any]) -> str:
    lines = [
        "# LinkedIn Message and Opportunity Action Drafts",
        "",
        "Every draft below is unsent. The package does not open LinkedIn, send a "
        "message, apply for a role, attach a resume, or disclose private conversation text.",
        "",
    ]
    for item in pack["message_action_drafts"]:
        lines.extend(
            [
                f"## {md_text(item['id'])} - {md_text(item['recipient_public_name'])}",
                "",
                f"- Status: `{md_text(item['status'])}`",
                f"- Context: {md_text(item['context_summary'])}",
                f"- Deadline: {md_text(item['deadline'])}",
                f"- Risk state: `{md_text(item['risk_state'])}`",
                f"- Selected action: `{md_text(item['selected_action'])}`",
                "",
            ]
        )
        if item.get("supported_fit"):
            lines.append("### Publicly Supported Fit")
            lines.append("")
            for value in item["supported_fit"]:
                lines.append(f"- {md_text(value)}")
            lines.append("")
        if item.get("missing_or_unverified_fit"):
            lines.append("### Missing or Unverified Fit")
            lines.append("")
            for value in item["missing_or_unverified_fit"]:
                lines.append(f"- {md_text(value)}")
            lines.append("")
        lines.extend(
            [
                "### Draft",
                "",
                md_text(item["draft"]),
                "",
                "### Safest Next Action",
                "",
                md_text(item["safest_next_action"]),
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_calendar(pack: dict[str, Any]) -> str:
    lines = [
        "# 30-Day LinkedIn Content Calendar",
        "",
        "This is a draft operating calendar. Every public action remains manual and "
        "requires review of the exact post, link, media, and current evidence.",
        "",
        "| Day | Date | Action | Pillar | Draft | Format | Objective |",
        "|---:|---|---|---|---|---|---|",
    ]
    for item in pack["calendar"]:
        lines.append(
            "| {day} | {date} | {action} | {pillar} | {draft} | {format} | {objective} |".format(
                day=item["day"],
                date=md_text(item["date"]),
                action=md_text(item["action"]).replace("|", "/"),
                pillar=md_text(item["pillar"]).replace("|", "/"),
                draft=md_text(item.get("draft_id") or "-"),
                format=md_text(item["format"]).replace("|", "/"),
                objective=md_text(item["objective"]).replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"


def render_posts(pack: dict[str, Any]) -> str:
    lines = [
        "# LinkedIn Post Drafts",
        "",
        "These are bounded drafts, not published posts. Recheck any linked evidence "
        "and media rights immediately before use.",
        "",
    ]
    for item in pack["post_drafts"]:
        lines.extend(
            [
                f"## {md_text(item['id'])} - {md_text(item['title'])}",
                "",
                f"**Pillar:** {md_text(item['pillar'])}",
                "",
                md_text(item["body"]),
                "",
                f"**Asset:** {md_text(item['asset'])}",
                "",
                f"**Link:** {md_text(item['link']) or 'none'}",
                "",
                f"**Boundary:** {md_text(item['boundary'])}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_replies(pack: dict[str, Any]) -> str:
    lines = [
        "# Public-Safe Engagement Reply Templates",
        "",
        "Use only as a starting point for a public comment after reading the source "
        "post. These templates are not direct messages and must never imply review, "
        "endorsement, employment, partnership, or procurement status that is not documented.",
        "",
    ]
    for item in pack["reply_templates"]:
        lines.extend(
            [
                f"## {md_text(item['id'])} - {md_text(item['situation'])}",
                "",
                md_text(item["template"]),
                "",
                f"**Use when:** {md_text(item['use_when'])}",
                "",
                f"**Do not use when:** {md_text(item['do_not_use_when'])}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_video_inventory(pack: dict[str, Any]) -> str:
    inventory = pack["video_inventory"]
    lines = [
        "# Local Video Inventory",
        "",
        f"- Video files: `{inventory['video_file_count']}`",
        f"- Unique content hashes: `{inventory['unique_content_count']}`",
        f"- Duplicate files: `{inventory['duplicate_file_count']}`",
        f"- Configured primary assets: `{inventory['primary_asset_count']}`",
        f"- Receipt-backed primary assets: `{inventory['receipt_backed_primary_count']}`",
        "",
        "| Rank | Class | Path | Duration | Frame | Public-use state | Duplicate of |",
        "|---:|---|---|---:|---|---|---|",
    ]
    for item in inventory["items"]:
        probe = item["probe"]
        duration = (
            str(probe.get("duration_seconds"))
            if probe.get("state") == "PROBED"
            else "-"
        )
        frame = (
            f"{probe.get('width')}x{probe.get('height')} {probe.get('orientation')}"
            if probe.get("state") == "PROBED"
            else "-"
        )
        lines.append(
            "| {rank} | {media_class} | `{path}` | {duration} | {frame} | {use} | {duplicate} |".format(
                rank=item["storyboard_rank"] or "",
                media_class=item["media_class"],
                path=item["path"].replace("|", "/"),
                duration=duration,
                frame=frame,
                use=md_text(item["public_use_state"]).replace("|", "/"),
                duplicate=md_text(item["duplicate_of"] or "-").replace("|", "/"),
            )
        )
    lines.extend(["", "## Primary Asset Notes", ""])
    for item in inventory["items"]:
        if item["media_class"] not in {"PRIMARY_RENDER", "RAW_LOCAL_CLIP"}:
            continue
        lines.extend(
            [
                f"### {md_text(item['title'])}",
                "",
                f"- Path: `{item['path']}`",
                f"- SHA-256: `{item['sha256']}`",
                f"- Summary: {md_text(item['content_summary'])}",
                f"- Public-use state: `{md_text(item['public_use_state'])}`",
                f"- Claim boundary: {md_text(item['claim_boundary'])}",
                f"- Receipt state: `{item['receipt']['state']}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def render_storyboards(pack: dict[str, Any]) -> str:
    lines = [
        "# CapCut-Ready Storyboard Briefs",
        "",
        "All briefs are edit plans only. Confirm media rights, captions, links, and "
        "the exact evidence boundary before export or upload.",
        "",
    ]
    for item in pack["storyboard_briefs"]:
        lines.extend(
            [
                f"## {md_text(item['id'])} - {md_text(item['title'])}",
                "",
                f"- Source: `{md_text(item['source_path'])}`",
                f"- Target: {md_text(item['target_format'])}",
                f"- Duration: {md_text(item['target_duration'])}",
                f"- Audience: {md_text(item['audience'])}",
                f"- Hook: {md_text(item['hook'])}",
                f"- CTA: {md_text(item['cta'])}",
                f"- Audio: {md_text(item['audio'])}",
                f"- Caption style: {md_text(item['caption_style'])}",
                f"- Export: {md_text(item['export_settings'])}",
                f"- Boundary: {md_text(item['claim_boundary'])}",
                "",
                "| Time | Visual | On-screen text | Voiceover / edit note |",
                "|---|---|---|---|",
            ]
        )
        for scene in item["scenes"]:
            lines.append(
                "| {time} | {visual} | {text} | {note} |".format(
                    time=md_text(scene["time"]).replace("|", "/"),
                    visual=md_text(scene["visual"]).replace("|", "/"),
                    text=md_text(scene["on_screen_text"]).replace("|", "/"),
                    note=md_text(scene["voiceover_or_edit_note"]).replace("|", "/"),
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_readme(pack: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LinkedIn Growth Pack",
            "",
            f"Status: `{pack['status']}`",
            f"Evidence cut: `{pack['as_of_utc']}`",
            f"Pack SHA-256: `{pack['pack_sha256']}`",
            "",
            "This directory is a deterministic, local-only profile and content package. "
            "It does not access LinkedIn, edit a profile, publish a post, send a message, "
            "or perform a follow action.",
            "",
            "## Files",
            "",
            "- `LINKEDIN_PROFILE_REWRITE.md` - headline, About, experience, and skills.",
            "- `FEATURED_SECTION_PLAN.md` - ordered links and held-link queue.",
            "- `PROFILE_GAP_ACTION_PLAN.md` - live read-only gaps, metrics, projects, and content risks.",
            "- `CONTENT_CALENDAR_30_DAY.md` - 30 consecutive days of posts and preparation.",
            "- `POST_DRAFTS.md` - full evidence-bounded post drafts.",
            "- `ENGAGEMENT_REPLY_TEMPLATES.md` - public comment starting points.",
            "- `MESSAGE_ACTION_DRAFTS.md` - unsent networking and role-fit replies.",
            "- `VIDEO_INVENTORY.md` - deduplicated local video inventory.",
            "- `CAPCUT_STORYBOARDS.md` - edit-ready briefs for the strongest clips.",
            "- `linkedin_growth_pack.json` - complete machine-readable package.",
            "- `MANIFEST.json` - byte counts and SHA-256 values for every generated file.",
            "",
            "## Human Gate",
            "",
            "Review the exact copy, current URL status, media rights, and evidence state "
            "before taking any public action.",
            "",
        ]
    )


def render_outputs(pack: dict[str, Any]) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {
        "README.md": render_readme(pack).encode("utf-8"),
        "LINKEDIN_PROFILE_REWRITE.md": render_profile(pack).encode("utf-8"),
        "FEATURED_SECTION_PLAN.md": render_featured(pack).encode("utf-8"),
        "PROFILE_GAP_ACTION_PLAN.md": render_profile_gap_action_plan(pack).encode(
            "utf-8"
        ),
        "CONTENT_CALENDAR_30_DAY.md": render_calendar(pack).encode("utf-8"),
        "POST_DRAFTS.md": render_posts(pack).encode("utf-8"),
        "ENGAGEMENT_REPLY_TEMPLATES.md": render_replies(pack).encode("utf-8"),
        "MESSAGE_ACTION_DRAFTS.md": render_message_action_drafts(pack).encode(
            "utf-8"
        ),
        "VIDEO_INVENTORY.md": render_video_inventory(pack).encode("utf-8"),
        "CAPCUT_STORYBOARDS.md": render_storyboards(pack).encode("utf-8"),
        "linkedin_growth_pack.json": pretty_json_bytes(pack),
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "as_of_utc": pack["as_of_utc"],
        "pack_sha256": pack["pack_sha256"],
        "files": [
            {
                "path": name,
                "bytes": len(outputs[name]),
                "sha256": sha256_bytes(outputs[name]),
            }
            for name in sorted(outputs)
        ],
    }
    manifest["manifest_facts_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    outputs["MANIFEST.json"] = pretty_json_bytes(manifest)
    return outputs


def write_outputs(out_dir: Path, outputs: dict[str, bytes]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in sorted(outputs):
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(outputs[name])


def check_outputs(out_dir: Path, outputs: dict[str, bytes]) -> list[str]:
    failures: list[str] = []
    expected_names = set(outputs)
    actual_names = (
        {
            path.relative_to(out_dir).as_posix()
            for path in out_dir.rglob("*")
            if path.is_file()
        }
        if out_dir.is_dir()
        else set()
    )
    for name in sorted(expected_names - actual_names):
        failures.append(f"missing:{name}")
    for name in sorted(actual_names - expected_names):
        failures.append(f"unexpected:{name}")
    for name in sorted(expected_names & actual_names):
        actual = (out_dir / name).read_bytes()
        if actual != outputs[name]:
            failures.append(f"mismatch:{name}")
    return failures


def summary(pack: dict[str, Any], *, mode: str, failures: list[str] | None = None) -> dict[str, Any]:
    return {
        "mode": mode,
        "status": pack["status"],
        "pack_sha256": pack["pack_sha256"],
        "post_draft_count": len(pack["post_drafts"]),
        "calendar_day_count": len(pack["calendar"]),
        "reply_template_count": len(pack["reply_templates"]),
        "message_action_draft_count": len(pack["message_action_drafts"]),
        "profile_gap_action_count": len(pack["profile_gap_actions"]),
        "content_risk_count": len(pack["content_risk_register"]),
        "storyboard_count": len(pack["storyboard_briefs"]),
        "video_file_count": pack["video_inventory"]["video_file_count"],
        "unique_video_content_count": pack["video_inventory"]["unique_content_count"],
        "private_hit_count": pack["safety"]["public_copy_private_hit_count"],
        "unsupported_claim_hit_count": pack["safety"][
            "public_copy_unsupported_claim_hit_count"
        ],
        "failures": failures or [],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic, public-safe LinkedIn growth package."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare generated bytes with the output directory without writing.",
    )
    parser.add_argument(
        "--no-probe",
        action="store_true",
        help="Skip optional video metadata probing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    config_path = args.config
    if not config_path.is_absolute():
        config_path = (root / config_path).resolve()
    out_dir = args.out_dir
    if not out_dir.is_absolute():
        out_dir = (root / out_dir).resolve()

    try:
        config = load_json(config_path)
        pack = build_pack(root, config, probe_media=not args.no_probe)
        outputs = render_outputs(pack)
        if args.check:
            failures = check_outputs(out_dir, outputs)
            print(
                json.dumps(
                    summary(pack, mode="check", failures=failures),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1 if failures else 0
        write_outputs(out_dir, outputs)
        print(json.dumps(summary(pack, mode="write"), indent=2, sort_keys=True))
        return 0
    except GrowthPackError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
