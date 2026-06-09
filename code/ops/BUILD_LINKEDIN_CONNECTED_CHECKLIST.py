from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "linkedin_connected_publish_checklist"

MAX_LATEST = ROOT / "out" / "ops" / "linkedin_max_innovation" / "linkedin_max_innovation_latest.json"
SETUP_LATEST = ROOT / "out" / "ops" / "linkedin_oauth_setup" / "linkedin_oauth_setup_latest.json"
LAUNCHPACK_LATEST = ROOT / "out" / "ops" / "linkedin_app_launchpack" / "linkedin_app_launchpack_latest.json"

GATEWAY_STATUS_URL = "http://127.0.0.1:8787/auth/linkedin/status"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


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


def _fetch_gateway_status() -> dict[str, Any]:
    req = urllib.request.Request(
        GATEWAY_STATUS_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
            return {
                "reachable": True,
                "error": "",
                "payload": payload if isinstance(payload, dict) else {},
            }
    except urllib.error.HTTPError as exc:
        return {"reachable": False, "error": f"http_{exc.code}", "payload": {}}
    except Exception as exc:
        return {"reachable": False, "error": str(exc), "payload": {}}


def _bool_item(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "detail": detail,
    }


def _build_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# LinkedIn Connected Publish Checklist")
    lines.append("")
    lines.append(f"- generated_utc: {payload.get('generated_utc', '')}")
    lines.append(f"- status: {payload.get('status', '')}")
    lines.append(f"- status_reason: {payload.get('status_reason', '')}")
    lines.append(f"- readiness_score_pct: {payload.get('readiness_score_pct', 0)}")
    lines.append(f"- checks_passed: {payload.get('checks_passed', 0)}/{payload.get('checks_total', 0)}")
    lines.append("")

    lines.append("## Checklist")
    for item in payload.get("checklist", []):
        mark = "PASS" if bool(item.get("passed")) else "FAIL"
        lines.append(f"- [{mark}] {item.get('name', '')}: {item.get('detail', '')}")
    lines.append("")

    lines.append("## Key Inputs")
    key_inputs = payload.get("key_inputs", {}) if isinstance(payload.get("key_inputs"), dict) else {}
    for key in (
        "profile_url",
        "company_page_url",
        "brand_asset_url",
        "redirect_uri",
        "recommended_logo",
    ):
        lines.append(f"- {key}: {_safe_text(key_inputs.get(key))}")
    lines.append("")

    lines.append("## Next Actions")
    actions = payload.get("next_actions", []) if isinstance(payload.get("next_actions"), list) else []
    if actions:
        for action in actions:
            lines.append(f"- {action}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Artifacts")
    artifacts = payload.get("artifacts", {}) if isinstance(payload.get("artifacts"), dict) else {}
    for key in sorted(artifacts.keys()):
        lines.append(f"- {key}: {artifacts.get(key)}")

    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    max_latest = _read_json(MAX_LATEST)
    setup_latest = _read_json(SETUP_LATEST)
    launchpack_latest = _read_json(LAUNCHPACK_LATEST)
    gateway = _fetch_gateway_status()
    gateway_payload = gateway.get("payload", {}) if isinstance(gateway.get("payload"), dict) else {}

    profile_url = _safe_text((launchpack_latest or {}).get("profile_url"))
    company_page_url = _safe_text((launchpack_latest or {}).get("company_page_url"))
    brand_asset_url = _safe_text((launchpack_latest or {}).get("brand_asset_url"))
    redirect_uri = _safe_text((launchpack_latest or {}).get("redirect_uri"))
    recommended_logo = _safe_text(((launchpack_latest or {}).get("logo_recommended") or {}).get("file"))

    keys_present = bool((launchpack_latest or {}).get("validation", {}).get("keys_present"))
    oauth_token_present = bool((launchpack_latest or {}).get("validation", {}).get("oauth_token_present"))
    gateway_reachable = bool(gateway.get("reachable"))
    gateway_configured = bool(gateway_payload.get("configured"))
    gateway_connected = bool(gateway_payload.get("connected"))
    readiness = int((max_latest or {}).get("readiness_score_pct") or (launchpack_latest or {}).get("readiness_score_pct") or 0)

    checklist = [
        _bool_item("keys_configured", keys_present, "LINKEDIN_CLIENT_ID/SECRET/REDIRECT present"),
        _bool_item("profile_url_present", bool(profile_url), profile_url or "missing"),
        _bool_item("company_page_url_present", bool(company_page_url), company_page_url or "missing"),
        _bool_item("brand_asset_url_present", bool(brand_asset_url), brand_asset_url or "missing"),
        _bool_item("recommended_logo_present", bool(recommended_logo), recommended_logo or "missing"),
        _bool_item("oauth_token_present", oauth_token_present, _safe_text((launchpack_latest or {}).get("oauth_token_path")) or "missing"),
        _bool_item("gateway_reachable", gateway_reachable, GATEWAY_STATUS_URL if gateway_reachable else _safe_text(gateway.get("error"))),
        _bool_item("gateway_configured", gateway_configured, "gateway reports configured=true" if gateway_configured else "gateway configured=false"),
        _bool_item("gateway_connected", gateway_connected, "gateway reports connected=true" if gateway_connected else "gateway connected=false"),
        _bool_item("readiness_100", readiness >= 100, f"readiness_score_pct={readiness}"),
    ]

    checks_total = len(checklist)
    checks_passed = sum(1 for item in checklist if bool(item.get("passed")))

    status = "publish_ready" if checks_passed == checks_total else "action_required"
    status_reason = "all_checks_passed" if status == "publish_ready" else "one_or_more_checks_failed"

    next_actions: list[str] = []
    if not keys_present:
        next_actions.append("Populate LinkedIn OAuth keys in config/luma_outreach_keys.env.")
    if not company_page_url:
        next_actions.append("Set LINKEDIN_COMPANY_PAGE_URL in config/luma_outreach_keys.env.")
    if not gateway_connected:
        next_actions.append("Complete OAuth consent via /auth/linkedin/login and re-check /auth/linkedin/status.")
    if not recommended_logo:
        next_actions.append("Upload or import a LinkedIn logo and regenerate launchpack.")
    if not next_actions:
        next_actions.append("Profile is connected and publish-ready. Proceed with outbound growth cadence.")

    payload = {
        "generated_utc": _now_iso(),
        "scope": "linkedin_connected_publish_checklist",
        "status": status,
        "status_reason": status_reason,
        "readiness_score_pct": readiness,
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "checklist": checklist,
        "key_inputs": {
            "profile_url": profile_url,
            "company_page_url": company_page_url,
            "brand_asset_url": brand_asset_url,
            "redirect_uri": redirect_uri,
            "recommended_logo": recommended_logo,
        },
        "gateway": {
            "status_url": GATEWAY_STATUS_URL,
            "reachable": gateway_reachable,
            "configured": gateway_configured,
            "connected": gateway_connected,
            "error": _safe_text(gateway.get("error")),
            "name": _safe_text(gateway_payload.get("name")),
            "email": _safe_text(gateway_payload.get("email")),
        },
        "next_actions": next_actions,
        "artifacts": {
            "linkedin_max_innovation_latest": str(MAX_LATEST),
            "linkedin_oauth_setup_latest": str(SETUP_LATEST),
            "linkedin_launchpack_latest": str(LAUNCHPACK_LATEST),
        },
    }

    stamp = _stamp()
    tagged_json = OUT_DIR / f"linkedin_connected_publish_checklist_{stamp}.json"
    latest_json = OUT_DIR / "linkedin_connected_publish_checklist_latest.json"
    tagged_md = OUT_DIR / f"linkedin_connected_publish_checklist_{stamp}.md"
    latest_md = OUT_DIR / "linkedin_connected_publish_checklist_latest.md"

    _write_json(tagged_json, payload)
    _write_json(latest_json, payload)

    markdown = _build_markdown(payload)
    _write_text(tagged_md, markdown)
    _write_text(latest_md, markdown)

    print(f"LINKEDIN_CONNECTED_CHECKLIST_STATUS={status}")
    print(f"LINKEDIN_CONNECTED_CHECKLIST_REASON={status_reason}")
    print(f"LINKEDIN_CONNECTED_CHECKLIST_CHECKS={checks_passed}/{checks_total}")
    print(f"LINKEDIN_CONNECTED_CHECKLIST_LATEST_JSON={latest_json}")
    print(f"LINKEDIN_CONNECTED_CHECKLIST_LATEST_MD={latest_md}")


if __name__ == "__main__":
    main()
