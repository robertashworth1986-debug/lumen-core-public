from __future__ import annotations

import argparse
import json
import re
import struct
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
OPS_OUT = ROOT / "out" / "ops"
SETUP_DIR = OPS_OUT / "linkedin_oauth_setup"
LAUNCHPACK_DIR = OPS_OUT / "linkedin_app_launchpack"
GOOGLE_DRIVE_IMPORT_DIR = SETUP_DIR / "google_drive_imports"
GOOGLE_DRIVE_LOGO_ALIAS = SETUP_DIR / "luma_linkedin_logo_from_drive"
LOCAL_IMPORT_DIR = SETUP_DIR / "local_imports"
LOCAL_LOGO_ALIAS = SETUP_DIR / "luma_linkedin_logo_from_local"

LINKEDIN_PAYLOAD_PATH = ROOT / "out" / "opportunities" / "linkedin" / "lumalinkedin_v1_latest.json"
SETUP_LATEST_PATH = SETUP_DIR / "linkedin_oauth_setup_latest.json"
TOKEN_PATH = CONFIG_DIR / "linkedin_token.json"

ENV_FILES = [
    CONFIG_DIR / "luma_outreach_keys.env",
    CONFIG_DIR / "luma_live_keys.env",
    ROOT / ".env",
]

DEFAULT_URLS = {
    "developer_portal_url": "https://developer.linkedin.com/",
    "developer_login_url": "https://www.linkedin.com/developers/login",
    "app_list_url": "https://www.linkedin.com/developers/apps?appStatus=active",
    "app_create_url": "https://www.linkedin.com/developers/apps/new?src=direct%2Fnone&veh=direct%2Fnone",
    "company_page_create_url": "https://www.linkedin.com/company/setup/new/",
    "gateway_status_url": "http://127.0.0.1:8787/auth/linkedin/status",
    "gateway_login_url": "http://127.0.0.1:8787/auth/linkedin/login",
}

REQUIRED_KEYS = [
    "LINKEDIN_CLIENT_ID",
    "LINKEDIN_CLIENT_SECRET",
    "LINKEDIN_REDIRECT_URI",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")
    tmp.replace(path)


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def _load_env_map() -> dict[str, str]:
    env_map: dict[str, str] = {}
    for path in ENV_FILES:
        parsed = _parse_env_file(path)
        for key, value in parsed.items():
            if key not in env_map or not env_map[key]:
                env_map[key] = value
    return env_map


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as fh:
            header = fh.read(24)
    except Exception:
        return None

    if len(header) < 24:
        return None
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    try:
        width, height = struct.unpack(">II", header[16:24])
    except Exception:
        return None
    return width, height


def _jpeg_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        data = path.read_bytes()
    except Exception:
        return None

    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None

    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # Start Of Frame markers carrying dimensions.
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            block_len = (data[i + 2] << 8) + data[i + 3]
            if block_len < 7 or i + 2 + block_len > len(data):
                return None
            height = (data[i + 5] << 8) + data[i + 6]
            width = (data[i + 7] << 8) + data[i + 8]
            return int(width), int(height)

        if marker in (0xD8, 0xD9):
            i += 2
            continue

        if i + 4 > len(data):
            break
        seg_len = (data[i + 2] << 8) + data[i + 3]
        if seg_len <= 1:
            break
        i += 2 + seg_len
    return None


def _image_dimensions(path: Path) -> tuple[int, int] | None:
    dims = _png_dimensions(path)
    if dims:
        return dims
    return _jpeg_dimensions(path)


def _extract_drive_file_id(url: str) -> str:
    text = _safe_text(url)
    if not text:
        return ""

    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", text)
    if m:
        return m.group(1)

    try:
        parsed = urllib.parse.urlparse(text)
        query = urllib.parse.parse_qs(parsed.query)
        if "id" in query and query["id"]:
            return _safe_text(query["id"][0])
    except Exception:
        return ""
    return ""


def _fetch_url_bytes(url: str, timeout_sec: int = 45) -> tuple[bytes | None, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.read(), _safe_text(resp.headers.get("Content-Type"))
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except Exception as e:
        return None, f"request_failed:{e}"


def _guess_image_extension(blob: bytes, content_type: str) -> str:
    ct = _safe_text(content_type).lower()
    if blob.startswith(b"\x89PNG\r\n\x1a\n") or "png" in ct:
        return ".png"
    if blob.startswith(b"\xff\xd8\xff") or "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    return ".bin"


def _normalize_ext(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return ".jpg"
    if ext == ".png":
        return ".png"
    return ""


def _looks_like_html(blob: bytes, content_type: str) -> bool:
    ct = _safe_text(content_type).lower()
    if "text/html" in ct:
        return True
    preview = blob[:512].lstrip().lower()
    return preview.startswith(b"<!doctype html") or preview.startswith(b"<html")


def _download_google_drive_logo(google_drive_file_url: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "attempted": False,
        "source_url": _safe_text(google_drive_file_url),
        "file_id": "",
        "download_url": "",
        "thumbnail_url": "",
        "content_type": "",
        "import_method": "",
        "imported_file": "",
        "alias_file": "",
        "error": "",
    }
    if not result["source_url"]:
        return result

    result["attempted"] = True
    file_id = _extract_drive_file_id(result["source_url"])
    result["file_id"] = file_id
    if not file_id:
        result["error"] = "drive_file_id_not_found"
        return result

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1600"
    result["download_url"] = download_url
    result["thumbnail_url"] = thumbnail_url

    blob, content_type = _fetch_url_bytes(download_url)
    result["content_type"] = _safe_text(content_type)
    if blob is None:
        result["error"] = content_type
        return result

    if _looks_like_html(blob, result["content_type"]):
        thumb_blob, thumb_content_type = _fetch_url_bytes(thumbnail_url)
        if thumb_blob is None:
            result["import_method"] = "thumbnail_fallback_failed"
            result["error"] = "google_auth_required_or_file_not_shareable"
            return result
        thumb_ext = _guess_image_extension(thumb_blob, thumb_content_type)
        if thumb_ext == ".bin":
            result["import_method"] = "thumbnail_fallback_failed"
            result["error"] = "google_auth_required_or_file_not_shareable"
            return result
        blob = thumb_blob
        result["content_type"] = _safe_text(thumb_content_type)
        result["import_method"] = "thumbnail_fallback"
    else:
        result["import_method"] = "direct_download"

    ext = _guess_image_extension(blob, result["content_type"])
    if ext == ".bin":
        result["error"] = "unsupported_content_type"
        return result

    GOOGLE_DRIVE_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    tagged = GOOGLE_DRIVE_IMPORT_DIR / f"google_drive_logo_{file_id}_{stamp}{ext}"
    tagged.write_bytes(blob)

    alias = Path(str(GOOGLE_DRIVE_LOGO_ALIAS) + ext)
    alias.write_bytes(blob)

    result["imported_file"] = str(tagged)
    result["alias_file"] = str(alias)
    return result


def _import_local_logo(local_logo_path: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "attempted": False,
        "source_path": _safe_text(local_logo_path),
        "imported_file": "",
        "alias_file": "",
        "error": "",
    }
    source = Path(result["source_path"])
    if not result["source_path"]:
        return result

    result["attempted"] = True
    if not source.exists() or not source.is_file():
        result["error"] = "local_logo_not_found"
        return result

    ext = _normalize_ext(source)
    if not ext:
        result["error"] = "unsupported_local_logo_type"
        return result

    try:
        blob = source.read_bytes()
    except Exception as e:
        result["error"] = f"local_logo_read_failed:{e}"
        return result

    if not blob:
        result["error"] = "local_logo_empty"
        return result

    LOCAL_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    tagged = LOCAL_IMPORT_DIR / f"local_logo_import_{stamp}{ext}"
    tagged.write_bytes(blob)

    alias = Path(str(LOCAL_LOGO_ALIAS) + ext)
    alias.write_bytes(blob)

    result["imported_file"] = str(tagged)
    result["alias_file"] = str(alias)
    return result


def _logo_candidates() -> list[dict[str, Any]]:
    candidates: dict[str, Path] = {}
    for pattern in (
        "luma_linkedin_logo*.*",
        "*linkedin*logo*.*",
        "luma_linkedin_logo_from_drive.*",
        "luma_linkedin_logo_from_local.*",
        "google_drive_logo_*.*",
        "local_logo_import_*.*",
    ):
        for path in SETUP_DIR.glob(pattern):
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                candidates[str(path.resolve())] = path
    for path in GOOGLE_DRIVE_IMPORT_DIR.glob("google_drive_logo_*.*"):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            candidates[str(path.resolve())] = path
    for path in LOCAL_IMPORT_DIR.glob("local_logo_import_*.*"):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            candidates[str(path.resolve())] = path

    out: list[dict[str, Any]] = []
    for path in candidates.values():
        size_bytes = path.stat().st_size
        dims = _image_dimensions(path)
        width = int(dims[0]) if dims else 0
        height = int(dims[1]) if dims else 0
        ext = path.suffix.lower()
        out.append(
            {
                "file": str(path),
            "ext": ext,
                "size_bytes": int(size_bytes),
                "size_kb": round(size_bytes / 1024.0, 2),
                "width": width,
                "height": height,
                "is_square": bool(width and height and width == height),
                "under_5mb": bool(size_bytes <= 5_000_000),
            }
        )

    def sort_key(item: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        size_bytes = int(item.get("size_bytes") or 0)
        ext = _safe_text(item.get("ext")).lower()
        exact_512 = width == 512 and height == 512
        square = bool(item.get("is_square"))
        under_5mb = bool(item.get("under_5mb"))
        distance = abs(width - 512) + abs(height - 512)
        return (
            0 if exact_512 else 1,
            0 if under_5mb else 1,
            0 if square else 1,
            0 if ext == ".png" else 1,
            distance,
            size_bytes,
        )

    out.sort(key=sort_key)
    for idx, item in enumerate(out):
        item["recommended"] = idx == 0
    return out


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _trim_text(text: str, limit: int) -> str:
    clean = _safe_text(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "..."


def _slug_from_profile_url(profile_url: str) -> str:
    text = _safe_text(profile_url).rstrip("/")
    if "/in/" not in text:
        return ""
    return text.rsplit("/", 1)[-1]


def _google_drive_file_id(url: str) -> str:
    text = _safe_text(url)
    if not text:
        return ""
    patterns = [
        r"/file/d/([A-Za-z0-9_-]+)",
        r"[?&]id=([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _safe_text(match.group(1))
    return ""


def _google_asset_bundle(url: str) -> dict[str, Any]:
    source = _safe_text(url)
    file_id = _google_drive_file_id(source)
    if not source:
        return {
            "source_url": "",
            "is_google_drive": False,
            "file_id": "",
            "view_url": "",
            "download_url": "",
            "thumbnail_url": "",
        }
    is_google_drive = "drive.google.com" in source.lower() and bool(file_id)
    view_url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}" if file_id else ""
    thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1600" if file_id else ""
    return {
        "source_url": source,
        "is_google_drive": is_google_drive,
        "file_id": file_id,
        "view_url": view_url,
        "download_url": download_url,
        "thumbnail_url": thumbnail_url,
    }


def _first_featured_url(profile_seed: dict[str, Any]) -> str:
    links = profile_seed.get("featured_links") if isinstance(profile_seed, dict) else []
    if not isinstance(links, list):
        return ""
    for item in links:
        if not isinstance(item, dict):
            continue
        url = _safe_text(item.get("url"))
        if url:
            return url
    return ""


def _build_app_prefill(
    profile_seed: dict[str, Any],
    profile_url: str,
    company_page_url: str,
    redirect_uri: str,
) -> dict[str, Any]:
    name = _safe_text(profile_seed.get("name")) or "LumaTrader"
    headline = _safe_text(profile_seed.get("headline_recommended"))
    about_short = _safe_text(profile_seed.get("about_short"))
    website_url = _first_featured_url(profile_seed)
    slug = _slug_from_profile_url(profile_url)

    app_name_a = "LumaTrader Developer App"
    app_name_b = "LumaTrader LinkedIn Integration"
    app_name_c = "LumenCore Institutional Evidence App"
    if name:
        first_token = name.split(" ", 1)[0]
        app_name_c = f"{first_token} Luma Integration App"

    app_desc = _trim_text(
        about_short
        or "Institutional quant and evidence automation integration for profile optimization and mission updates.",
        300,
    )
    tagline = _trim_text(headline or "Institutional automation and evidence-first workflows.", 120)

    return {
        "app_name_suggestions": [app_name_a, app_name_b, app_name_c],
        "tagline": tagline,
        "short_description_300": app_desc,
        "website_url": website_url,
        "profile_url": profile_url,
        "profile_slug": slug,
        "company_page_url": company_page_url,
        "redirect_uri": redirect_uri,
    }


def _build_readiness(
    validation: dict[str, Any],
    missing_keys: list[str],
    profile_url: str,
    company_page_url: str,
    brand_asset_url: str,
    external_logo_import_error: str,
) -> tuple[int, dict[str, int], list[str], list[str]]:
    keys_ok = not missing_keys
    logo_ok = bool(validation.get("logo_present"))
    profile_ok = bool(_safe_text(profile_url))
    company_ok = bool(_safe_text(company_page_url))
    brand_asset_ok = bool(_safe_text(brand_asset_url))
    token_ok = bool(validation.get("oauth_token_present"))

    components = {
        "keys": 30 if keys_ok else 0,
        "logo": 20 if logo_ok else 0,
        "profile": 10 if profile_ok else 0,
        "company_page": 15 if company_ok else 0,
        "brand_asset": 10 if brand_asset_ok else 0,
        "oauth_token": 15 if token_ok else 0,
    }
    score = int(sum(components.values()))

    blockers: list[str] = []
    if missing_keys:
        blockers.append("missing_keys:" + ",".join(missing_keys))
    if not logo_ok:
        blockers.append("missing_logo")
    if not profile_ok:
        blockers.append("missing_profile_url")
    if not company_ok:
        blockers.append("missing_company_page_url")
    if not brand_asset_ok:
        blockers.append("missing_brand_asset_url")
    if not token_ok:
        blockers.append("oauth_consent_not_completed")
    if _safe_text(external_logo_import_error):
        blockers.append("google_drive_logo_import_failed")

    next_actions: list[str] = []
    if missing_keys:
        next_actions.append("Paste LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET into config/luma_outreach_keys.env.")
    if not profile_ok:
        next_actions.append("Set LINKEDIN_PROFILE_URL to your public LinkedIn profile URL.")
    if not company_ok:
        next_actions.append("Create or copy your LinkedIn company page URL and set LINKEDIN_COMPANY_PAGE_URL.")
    if not brand_asset_ok:
        next_actions.append("Set LINKEDIN_BRAND_ASSET_URL using your Google Drive image link or local asset URL.")
    if not token_ok:
        next_actions.append("Run OAuth consent via /auth/linkedin/login after keys are configured.")
    if _safe_text(external_logo_import_error):
        next_actions.append("Share the Google Drive file with link access or use local logo file fallback.")
    if not blockers:
        next_actions.append("Launchpack is fully ready for live publishing and consent checks.")

    return score, components, blockers, next_actions


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# LinkedIn App Launchpack")
    lines.append("")
    lines.append(f"- generated_utc: {payload.get('generated_utc', '')}")
    lines.append(f"- status: {payload.get('status', '')}")
    lines.append(f"- status_reason: {payload.get('status_reason', '')}")
    lines.append(f"- readiness_score_pct: {payload.get('readiness_score_pct', 0)}")
    lines.append("")

    lines.append("## Readiness Components")
    readiness = payload.get("readiness_components", {}) if isinstance(payload.get("readiness_components"), dict) else {}
    for key in sorted(readiness.keys()):
        lines.append(f"- {key}: {readiness.get(key, 0)}")
    lines.append("")

    lines.append("## Google Drive Import")
    drive = payload.get("google_drive_import", {}) if isinstance(payload.get("google_drive_import"), dict) else {}
    lines.append(f"- attempted: {drive.get('attempted', False)}")
    lines.append(f"- source_url: {_safe_text(drive.get('source_url'))}")
    lines.append(f"- file_id: {_safe_text(drive.get('file_id'))}")
    lines.append(f"- download_url: {_safe_text(drive.get('download_url'))}")
    lines.append(f"- thumbnail_url: {_safe_text(drive.get('thumbnail_url'))}")
    lines.append(f"- import_method: {_safe_text(drive.get('import_method'))}")
    lines.append(f"- imported_file: {_safe_text(drive.get('imported_file'))}")
    lines.append(f"- error: {_safe_text(drive.get('error'))}")
    lines.append("")

    lines.append("## Local Import")
    local = payload.get("local_logo_import", {}) if isinstance(payload.get("local_logo_import"), dict) else {}
    lines.append(f"- attempted: {local.get('attempted', False)}")
    lines.append(f"- source_path: {_safe_text(local.get('source_path'))}")
    lines.append(f"- imported_file: {_safe_text(local.get('imported_file'))}")
    lines.append(f"- error: {_safe_text(local.get('error'))}")
    lines.append("")

    lines.append("## Blockers")
    blockers = payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Next Actions")
    for action in payload.get("next_actions", []):
        lines.append(f"- {action}")
    lines.append("")

    lines.append("## Validation")
    validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
    lines.append(f"- keys_present: {validation.get('keys_present', False)}")
    lines.append(f"- logo_present: {validation.get('logo_present', False)}")
    lines.append(f"- company_page_url_present: {validation.get('company_page_url_present', False)}")
    lines.append(f"- profile_url_present: {validation.get('profile_url_present', False)}")
    lines.append(f"- oauth_token_present: {validation.get('oauth_token_present', False)}")
    lines.append("")

    lines.append("## Recommended Logo")
    logo = payload.get("logo_recommended") if isinstance(payload.get("logo_recommended"), dict) else None
    if logo:
        lines.append(f"- file: {logo.get('file', '')}")
        lines.append(f"- dimensions: {logo.get('width', 0)}x{logo.get('height', 0)}")
        lines.append(f"- size_kb: {logo.get('size_kb', 0)}")
    else:
        lines.append("- file: missing")
    lines.append("")

    lines.append("## Identity Inputs")
    lines.append(f"- profile_url: {payload.get('profile_url', '')}")
    lines.append(f"- company_page_url: {payload.get('company_page_url', '')}")
    lines.append(f"- brand_asset_url: {payload.get('brand_asset_url', '')}")
    lines.append(f"- google_drive_file_url: {payload.get('google_drive_file_url', '')}")
    lines.append(f"- redirect_uri: {payload.get('redirect_uri', '')}")
    lines.append("")

    lines.append("## Google Asset")
    g = payload.get("google_asset", {}) if isinstance(payload.get("google_asset"), dict) else {}
    lines.append(f"- source_url: {_safe_text(g.get('source_url'))}")
    lines.append(f"- file_id: {_safe_text(g.get('file_id'))}")
    lines.append(f"- view_url: {_safe_text(g.get('view_url'))}")
    lines.append(f"- download_url: {_safe_text(g.get('download_url'))}")
    lines.append(f"- thumbnail_url: {_safe_text(g.get('thumbnail_url'))}")
    lines.append("")

    lines.append("## Checklist")
    for step in payload.get("checklist", []):
        lines.append(f"- {step}")
    lines.append("")

    lines.append("## Execute Now")
    commands = payload.get("execute_now", {}) if isinstance(payload.get("execute_now"), dict) else {}
    for key in sorted(commands.keys()):
        lines.append(f"- {key}: {commands.get(key)}")
    lines.append("")

    lines.append("## App Prefill")
    prefill = payload.get("app_prefill", {}) if isinstance(payload.get("app_prefill"), dict) else {}
    app_names = prefill.get("app_name_suggestions", []) if isinstance(prefill.get("app_name_suggestions"), list) else []
    for idx, name in enumerate(app_names, start=1):
        lines.append(f"- app_name_suggestion_{idx}: {name}")
    lines.append(f"- tagline: {_safe_text(prefill.get('tagline'))}")
    lines.append(f"- short_description_300: {_safe_text(prefill.get('short_description_300'))}")
    lines.append(f"- website_url: {_safe_text(prefill.get('website_url'))}")
    lines.append("")

    lines.append("## Profile Seed")
    seed = payload.get("profile_seed", {}) if isinstance(payload.get("profile_seed"), dict) else {}
    lines.append(f"- name: {_safe_text(seed.get('name'))}")
    lines.append(f"- headline_recommended: {_safe_text(seed.get('headline_recommended'))}")
    lines.append(f"- about_short: {_safe_text(seed.get('about_short'))}")
    lines.append("")

    lines.append("## Key Artifacts")
    artifacts = payload.get("artifacts", {}) if isinstance(payload.get("artifacts"), dict) else {}
    for key in sorted(artifacts.keys()):
        lines.append(f"- {key}: {artifacts.get(key)}")

    return "\n".join(lines)


def build_launchpack(
    profile_url: str = "",
    company_page_url: str = "",
    redirect_uri: str = "",
    google_drive_file_url: str = "",
    local_logo_path: str = "",
    brand_asset_url: str = "",
) -> dict[str, Any]:
    env_map = _load_env_map()
    setup_latest = _read_json(SETUP_LATEST_PATH)
    linkedin_payload = _read_json(LINKEDIN_PAYLOAD_PATH)

    profile_url = _safe_text(profile_url) or _safe_text(env_map.get("LINKEDIN_PROFILE_URL"))
    company_page_url = _safe_text(company_page_url) or _safe_text(env_map.get("LINKEDIN_COMPANY_PAGE_URL"))
    brand_asset_url = _safe_text(brand_asset_url) or _safe_text(env_map.get("LINKEDIN_BRAND_ASSET_URL"))
    google_drive_file_url = _safe_text(google_drive_file_url)
    if (not google_drive_file_url) and ("drive.google.com" in brand_asset_url.lower()):
        google_drive_file_url = brand_asset_url
    redirect_uri = _safe_text(redirect_uri) or _safe_text(env_map.get("LINKEDIN_REDIRECT_URI")) or "http://127.0.0.1:8787/auth/linkedin/callback"
    google_asset = _google_asset_bundle(brand_asset_url)

    urls = dict(DEFAULT_URLS)
    if isinstance(setup_latest, dict):
        for key in urls:
            value = _safe_text(setup_latest.get(key))
            if value:
                urls[key] = value

    present_keys = [k for k in REQUIRED_KEYS if _safe_text(env_map.get(k))]
    missing_keys = [k for k in REQUIRED_KEYS if k not in present_keys]

    local_logo_import = _import_local_logo(local_logo_path)
    google_drive_import = _download_google_drive_logo(google_drive_file_url)

    external_logo_import_error = ""
    google_error = _safe_text(google_drive_import.get("error"))
    local_imported = bool(_safe_text(local_logo_import.get("imported_file")))
    if google_error and not local_imported:
        external_logo_import_error = google_error

    logos = _logo_candidates()
    recommended_logo = logos[0] if logos else None

    validation = {
        "keys_present": not missing_keys,
        "logo_present": bool(recommended_logo),
        "company_page_url_present": bool(company_page_url),
        "profile_url_present": bool(profile_url),
        "oauth_token_present": TOKEN_PATH.exists(),
        "google_drive_logo_imported": bool(_safe_text(google_drive_import.get("imported_file"))),
        "local_logo_imported": local_imported,
    }

    status = "submission_ready"
    status_reason = "ready"
    if not validation["keys_present"]:
        status = "keys_pending"
        status_reason = "missing_required_keys"
    elif not validation["logo_present"]:
        status = "logo_pending"
        status_reason = "linkedin_logo_not_found"
    elif not validation["company_page_url_present"]:
        status = "company_page_pending"
        status_reason = "company_page_url_missing"
    elif not validation["profile_url_present"]:
        status = "profile_url_pending"
        status_reason = "profile_url_missing"

    profile_seed: dict[str, Any] = {}
    if isinstance(linkedin_payload, dict):
        profile_seed = {
            "name": linkedin_payload.get("name"),
            "headline_recommended": linkedin_payload.get("headline_recommended"),
            "about_short": linkedin_payload.get("about_short"),
            "featured_links": linkedin_payload.get("featured_links", []),
            "impact_snapshot": linkedin_payload.get("impact_snapshot", []),
        }

    app_prefill = _build_app_prefill(
        profile_seed=profile_seed,
        profile_url=profile_url,
        company_page_url=company_page_url,
        redirect_uri=redirect_uri,
    )

    readiness_score, readiness_components, blockers, next_actions = _build_readiness(
        validation=validation,
        missing_keys=missing_keys,
        profile_url=profile_url,
        company_page_url=company_page_url,
        brand_asset_url=brand_asset_url,
        external_logo_import_error=external_logo_import_error,
    )

    execute_now = {
        "setup_oauth": (
            f"powershell -ExecutionPolicy Bypass -File {ROOT / 'code' / 'ops' / 'SETUP_LINKEDIN_OAUTH.ps1'} "
            f"-OpenBrowser -ProfileUrl {profile_url or '<set_profile_url>'} "
            f"-CompanyPageUrl {company_page_url or '<set_company_page_url>'} "
            f"-GoogleDriveAssetUrl {brand_asset_url or '<set_brand_asset_url>'}"
        ),
        "build_launchpack": (
            f"python {ROOT / 'code' / 'ops' / 'BUILD_LINKEDIN_APP_LAUNCHPACK.py'} "
            f"--profile-url {profile_url or '<set_profile_url>'} "
            f"--company-page-url {company_page_url or '<set_company_page_url>'} "
            f"--brand-asset-url {brand_asset_url or '<set_brand_asset_url>'} "
            f"--google-drive-file-url {google_drive_file_url or '<set_google_drive_file_url>'}"
        ),
        "gateway_status": urls["gateway_status_url"],
    }

    checklist = [
        f"Sign in at {urls['developer_login_url']}.",
        f"Open {urls['app_create_url']} and create or open the LinkedIn app.",
        "Select your LinkedIn company page in the app form.",
        "Upload the recommended logo file from this launchpack.",
        "In Auth settings, set OAuth redirect URL to this launchpack redirect_uri value.",
        "Enable products: Sign In with LinkedIn (OIDC) and Share on LinkedIn.",
        "Copy Client ID and Client Secret into config/luma_outreach_keys.env.",
        f"Run {ROOT / 'code' / 'ops' / 'SETUP_LINKEDIN_OAUTH.ps1'} -OpenBrowser for guided consent checks.",
        f"Verify status at {urls['gateway_status_url']}.",
    ]

    return {
        "generated_utc": _now_iso(),
        "scope": "linkedin_app_launchpack",
        "status": status,
        "status_reason": status_reason,
        "readiness_score_pct": readiness_score,
        "readiness_components": readiness_components,
        "blockers": blockers,
        "next_actions": next_actions,
        "profile_url": profile_url,
        "company_page_url": company_page_url,
        "brand_asset_url": brand_asset_url,
        "google_asset": google_asset,
        "redirect_uri": redirect_uri,
        "google_drive_import": google_drive_import,
        "google_drive_file_url": google_drive_file_url,
        "local_logo_import": local_logo_import,
        "developer_urls": urls,
        "required_keys": REQUIRED_KEYS,
        "present_keys": present_keys,
        "missing_keys": missing_keys,
        "validation": validation,
        "oauth_token_path": str(TOKEN_PATH),
        "logo_recommended": recommended_logo,
        "logo_candidates": logos,
        "profile_seed": profile_seed,
        "app_prefill": app_prefill,
        "execute_now": execute_now,
        "checklist": checklist,
        "artifacts": {
            "linkedin_payload": str(LINKEDIN_PAYLOAD_PATH),
            "oauth_setup_latest": str(SETUP_LATEST_PATH),
            "logo_directory": str(SETUP_DIR),
            "key_file": str(CONFIG_DIR / "luma_outreach_keys.env"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic LinkedIn app launchpack.")
    parser.add_argument("--profile-url", default="", help="Public LinkedIn profile URL.")
    parser.add_argument("--company-page-url", default="", help="LinkedIn company page URL used in app registration.")
    parser.add_argument("--redirect-uri", default="", help="OAuth redirect URI override.")
    parser.add_argument("--brand-asset-url", default="", help="Primary brand image URL (Google Drive or direct URL).")
    parser.add_argument("--google-drive-file-url", default="", help="Google Drive file URL for logo import.")
    parser.add_argument("--local-logo-path", default="", help="Local image path to import as LinkedIn logo candidate.")
    args = parser.parse_args()

    try:
        launchpack = build_launchpack(
            profile_url=args.profile_url,
            company_page_url=args.company_page_url,
            redirect_uri=args.redirect_uri,
            brand_asset_url=args.brand_asset_url,
            google_drive_file_url=args.google_drive_file_url,
            local_logo_path=args.local_logo_path,
        )
    except TypeError as exc:
        if "brand_asset_url" not in str(exc):
            raise
        launchpack = build_launchpack(
            profile_url=args.profile_url,
            company_page_url=args.company_page_url,
            redirect_uri=args.redirect_uri,
            google_drive_file_url=args.google_drive_file_url,
            local_logo_path=args.local_logo_path,
        )

    stamp = _stamp()
    tagged_json = LAUNCHPACK_DIR / f"linkedin_app_launchpack_{stamp}.json"
    latest_json = LAUNCHPACK_DIR / "linkedin_app_launchpack_latest.json"
    tagged_md = LAUNCHPACK_DIR / f"linkedin_app_launchpack_{stamp}.md"
    latest_md = LAUNCHPACK_DIR / "linkedin_app_launchpack_latest.md"

    _write_json(tagged_json, launchpack)
    _write_json(latest_json, launchpack)

    markdown = _render_markdown(launchpack)
    _write_text(tagged_md, markdown)
    _write_text(latest_md, markdown)

    build_summary = {
        "generated_utc": _now_iso(),
        "scope": "linkedin_app_launchpack_build",
        "status": launchpack.get("status"),
        "status_reason": launchpack.get("status_reason"),
        "latest_json": str(latest_json),
        "latest_md": str(latest_md),
        "tagged_json": str(tagged_json),
        "tagged_md": str(tagged_md),
    }

    tagged_build = OPS_OUT / f"linkedin_app_launchpack_build_{stamp}.json"
    latest_build = OPS_OUT / "linkedin_app_launchpack_build_latest.json"
    _write_json(tagged_build, build_summary)
    _write_json(latest_build, build_summary)

    print(f"LINKEDIN_LAUNCHPACK_STATUS={launchpack.get('status', '')}")
    print(f"LINKEDIN_LAUNCHPACK_REASON={launchpack.get('status_reason', '')}")
    print(f"LINKEDIN_LAUNCHPACK_LATEST_JSON={latest_json}")
    print(f"LINKEDIN_LAUNCHPACK_LATEST_MD={latest_md}")
    print(f"LINKEDIN_LAUNCHPACK_BUILD_SUMMARY={tagged_build}")


if __name__ == "__main__":
    main()
