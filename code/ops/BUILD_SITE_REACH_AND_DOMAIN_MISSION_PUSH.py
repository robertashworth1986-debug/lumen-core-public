from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
OUT_DIR = ROOT / "out" / "ops" / "site_reach_mission"
HEARTBEAT_LATEST_PATH = OUT_DIR / "site_reach_mission_heartbeat_latest.json"

LIVE_SOURCES_PATH = ROOT / "config" / "live_sources.json"
KEY_STATUS_PATH = ROOT / "dashboard" / "api_key_status.txt"
LIVE_KEYS_PATH = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
OUTREACH_KEYS_PATH = ROOT / "config" / "luma_outreach_keys.env"
LINKEDIN_TOKEN_PATH = ROOT / "config" / "linkedin_token.json"

INVESTOR_MISSION_PACK_PATH = ROOT / "out" / "ops" / "investor_mission_control" / "investor_mission_control_pack_latest.json"
ALPHA_EDGE_PATH = ROOT / "out" / "ops" / "alpha_edge_lock" / "alpha_edge_lock_engine_latest.json"
BLUEPRINT_VAULT_PATH = ROOT / "out" / "ops" / "gov_blueprint_vault" / "gov_blueprint_vault_latest.json"
GRANT_FIT_PATH = ROOT / "out" / "ops" / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_key_status(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, status = line.split(":", 1)
        out[key.strip().upper()] = status.strip().lower()
    return out


def load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def looks_real_secret(value: str | None) -> bool:
    v = str(value or "").strip()
    if len(v) < 8:
        return False
    bad = [
        "your_",
        "changeme",
        "example",
        "replace",
        "placeholder",
        "<",
        ">",
    ]
    lower = v.lower()
    return not any(token in lower for token in bad)


def merge_env_maps(*maps: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in maps:
        for key, value in source.items():
            if key not in merged and str(value or "").strip():
                merged[key] = str(value).strip()
    return merged


def first_value(env_map: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = env_map.get(name) or os.environ.get(name)
        if looks_real_secret(value):
            return str(value).strip()
    return ""


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except Exception:
        return default


def _http_json(url: str, *, headers: dict[str, str] | None = None, body: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = None
    method = "GET"
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if body is not None:
        method = "POST"
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    req = Request(url, data=data, headers=request_headers, method=method)
    with urlopen(req, timeout=timeout) as resp:
        txt = resp.read().decode("utf-8", errors="replace")
        return json.loads(txt)


def _extract_num(payload: Any, *path: str) -> float | None:
    cur = payload
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur.get(key)
    return safe_float(cur, None)


def collect_cloudflare(days: int, token: str, zone_id: str) -> dict[str, Any]:
    out = {
        "provider": "cloudflare",
        "configured": bool(looks_real_secret(token) and looks_real_secret(zone_id)),
        "status": "not_configured",
        "metrics": {},
    }
    if not out["configured"]:
        return out

    try:
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/analytics/dashboard?since=-{int(days)}d"
        payload = _http_json(url, headers={"Authorization": f"Bearer {token}"})
        if not bool(payload.get("success", False)):
            errs = payload.get("errors", [])
            out["status"] = "api_error"
            out["error"] = str(errs[:2])
            return out

        result = payload.get("result", {}) if isinstance(payload, dict) else {}
        totals = result.get("totals", {}) if isinstance(result, dict) else {}

        requests_30d = (
            _extract_num(totals, "requests", "all")
            or _extract_num(totals, "requests")
            or 0.0
        )
        pageviews_30d = (
            _extract_num(totals, "pageviews", "all")
            or _extract_num(totals, "pageviews")
            or None
        )
        visitors_30d = (
            _extract_num(totals, "uniques", "all")
            or _extract_num(totals, "uniques")
            or None
        )

        out["status"] = "ok"
        out["metrics"] = {
            "requests_30d": requests_30d,
            "pageviews_30d": pageviews_30d,
            "visitors_30d": visitors_30d,
        }
        return out
    except (HTTPError, URLError) as exc:
        out["status"] = "network_error"
        out["error"] = str(exc)
        return out
    except Exception as exc:
        out["status"] = "error"
        out["error"] = str(exc)
        return out


def collect_plausible(days: int, token: str, site_id: str) -> dict[str, Any]:
    out = {
        "provider": "plausible",
        "configured": bool(looks_real_secret(token) and bool(site_id.strip())),
        "status": "not_configured",
        "metrics": {},
    }
    if not out["configured"]:
        return out

    try:
        query = urlencode(
            {
                "site_id": site_id,
                "period": f"{int(days)}d",
                "metrics": "visitors,pageviews,visits,bounce_rate,visit_duration",
            }
        )
        url = f"https://plausible.io/api/v1/stats/aggregate?{query}"
        payload = _http_json(url, headers={"Authorization": f"Bearer {token}"})
        results = payload.get("results", {}) if isinstance(payload, dict) else {}

        visitors = _extract_num(results, "visitors", "value")
        pageviews = _extract_num(results, "pageviews", "value")
        visits = _extract_num(results, "visits", "value")

        out["status"] = "ok"
        out["metrics"] = {
            "visitors_30d": visitors,
            "pageviews_30d": pageviews,
            "visits_30d": visits,
        }
        return out
    except (HTTPError, URLError) as exc:
        out["status"] = "network_error"
        out["error"] = str(exc)
        return out
    except Exception as exc:
        out["status"] = "error"
        out["error"] = str(exc)
        return out


def collect_umami(days: int, base_url: str, token: str, website_id: str) -> dict[str, Any]:
    out = {
        "provider": "umami",
        "configured": bool(base_url.strip() and looks_real_secret(token) and bool(website_id.strip())),
        "status": "not_configured",
        "metrics": {},
    }
    if not out["configured"]:
        return out

    try:
        end_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_at = int((datetime.now(timezone.utc) - timedelta(days=int(days))).timestamp() * 1000)
        base = base_url.rstrip("/")
        query = urlencode({"startAt": start_at, "endAt": end_at})
        url = f"{base}/api/websites/{website_id}/stats?{query}"
        payload = _http_json(url, headers={"Authorization": f"Bearer {token}"})

        visitors = _extract_num(payload, "visitors", "value")
        pageviews = _extract_num(payload, "pageviews", "value")
        visits = _extract_num(payload, "visits", "value")

        out["status"] = "ok"
        out["metrics"] = {
            "visitors_30d": visitors,
            "pageviews_30d": pageviews,
            "visits_30d": visits,
        }
        return out
    except (HTTPError, URLError) as exc:
        out["status"] = "network_error"
        out["error"] = str(exc)
        return out
    except Exception as exc:
        out["status"] = "error"
        out["error"] = str(exc)
        return out


def pick_canonical_visitors(providers: list[dict[str, Any]]) -> tuple[float | None, str]:
    for preferred in ("cloudflare", "plausible", "umami"):
        row = next((p for p in providers if str(p.get("provider")) == preferred), None)
        if not isinstance(row, dict):
            continue
        visitors = safe_float(((row.get("metrics") or {}).get("visitors_30d")), None)
        if visitors is not None:
            return visitors, preferred
    return None, "none"


def build_mission_copy(alpha_payload: dict[str, Any], mission_pack: dict[str, Any], blueprint_payload: dict[str, Any]) -> dict[str, Any]:
    alpha_summary = alpha_payload.get("summary", {}) if isinstance(alpha_payload, dict) else {}
    mission_live_fill = mission_pack.get("autonomous_grant_live_fill", {}) if isinstance(mission_pack, dict) else {}
    selected = mission_live_fill.get("selected_opportunity", {}) if isinstance(mission_live_fill, dict) else {}
    blueprint_assets = blueprint_payload.get("assets", []) if isinstance(blueprint_payload, dict) else []

    top_problem = str(alpha_summary.get("top_problem") or "critical systems instability")
    grade_a = int(alpha_summary.get("grade_a_locks") or 0)
    opp_num = str(selected.get("opp_num") or "")
    opp_url = str(selected.get("submit_url") or "https://simpler.grants.gov/")

    featured_assets: list[str] = []
    for row in blueprint_assets[:4] if isinstance(blueprint_assets, list) else []:
        if isinstance(row, dict):
            featured_assets.append(str(row.get("asset_name") or ""))

    title = "LumenCore Mission: Harmonic, Alpha Lock, Harmonic Edge Lock"
    text = (
        "LumenCore is building a government-grade operating stack bound to one execution family: "
        "Harmonic + Alpha Lock + Harmonic Edge Lock. "
        f"Current top mission problem: {top_problem}. "
        f"Grade-A lock candidates in latest run: {grade_a}. "
        "We are exposing high-impact blueprint systems across advanced hardware, energy storage, XR simulation, "
        "robotics, haptics, neuro-interface, and deep-space autonomy with evidence-first validation. "
        f"Current autonomous grant lane lead: {opp_num or 'in selection'} ({opp_url})."
    )

    return {
        "title": title,
        "text": text,
        "call_to_action_url": "https://lumen-core.ai/mission_control.html",
        "hashtags": [
            "#LumenCore",
            "#HarmonicEdgeLock",
            "#AlphaLock",
            "#GovTech",
            "#DeepTech",
            "#Robotics",
            "#XR",
            "#Haptics",
            "#InfrastructureAI",
        ],
        "featured_assets": featured_assets,
    }


def _linkedin_ready(env_map: dict[str, str]) -> tuple[bool, str]:
    cid = first_value(env_map, ["LINKEDIN_CLIENT_ID"])
    csec = first_value(env_map, ["LINKEDIN_CLIENT_SECRET"])
    token_ok = LINKEDIN_TOKEN_PATH.exists()
    if not cid or not csec:
        return False, "linkedin_keys_missing"
    if not token_ok:
        return False, "linkedin_token_missing"
    return True, "ready"


def _push_linkedin(mission: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    title = str(mission.get("title") or "LumenCore Mission Update")
    text = str(mission.get("text") or "LumenCore mission update")
    url = str(mission.get("call_to_action_url") or "https://lumen-core.ai")

    if dry_run:
        return {
            "status": "dry_run",
            "title": title,
            "url": url,
            "text_preview": text[:420],
        }

    try:
        sys.path.insert(0, str(CODE))
        import linkedin_oauth as li  # type: ignore

        result = li.share_text(
            text,
            link=url,
            link_title=title,
            link_desc="LumenCore mission update and government-grade blueprint stack",
        )
        return {
            "status": "posted",
            "response": result,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


def build_promotion_channels(
    env_map: dict[str, str],
    mission: dict[str, Any],
    allow_live_push: bool,
    selected_submit_url: str,
) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []

    linkedin_ok, linkedin_reason = _linkedin_ready(env_map)
    linkedin_item: dict[str, Any] = {
        "channel": "linkedin",
        "domain": "linkedin.com",
        "status": "ready" if linkedin_ok else "blocked",
        "reason": linkedin_reason,
        "capability": "api_share",
        "live_push": None,
    }
    if allow_live_push and linkedin_ok:
        linkedin_item["live_push"] = _push_linkedin(mission, dry_run=False)
    else:
        linkedin_item["live_push"] = _push_linkedin(mission, dry_run=True)
    channels.append(linkedin_item)

    x_token = first_value(env_map, ["TWITTER_BEARER_TOKEN", "X_BEARER_TOKEN"])
    channels.append(
        {
            "channel": "x",
            "domain": "x.com",
            "status": "manual" if x_token else "blocked",
            "reason": "bearer_token_supports_read_only_search" if x_token else "x_token_missing",
            "capability": "oauth_share_required",
            "prepared_post": {
                "title": mission.get("title"),
                "text": mission.get("text"),
                "url": mission.get("call_to_action_url"),
            },
        }
    )

    yt_key = first_value(env_map, ["YOUTUBE_API_KEY", "GOOGLE_API_KEY"])
    channels.append(
        {
            "channel": "youtube",
            "domain": "youtube.com",
            "status": "manual" if yt_key else "blocked",
            "reason": "api_key_supports_data_api_not_channel_post" if yt_key else "youtube_key_missing",
            "capability": "oauth_video_publish_required",
            "prepared_video_concept": {
                "title": mission.get("title"),
                "description": mission.get("text"),
                "cta_url": mission.get("call_to_action_url"),
            },
        }
    )

    channels.append(
        {
            "channel": "simpler_grants",
            "domain": "simpler.grants.gov",
            "status": "ready",
            "reason": "grant_submission_lane",
            "capability": "application_submission",
            "target_url": selected_submit_url or "https://simpler.grants.gov/",
        }
    )

    channels.append(
        {
            "channel": "skip",
            "domain": "helloskip.com",
            "status": "ready",
            "reason": "grant_network_profile_and_submission_lane",
            "capability": "application_submission",
            "target_url": "https://helloskip.com/dashboard/business",
        }
    )

    return channels


def write_heartbeat(
    *,
    status: str,
    reason: str,
    run_tag: str,
    days: int,
    allow_live_push: bool,
    summary: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_utc": now_iso(),
        "scope": "site_reach_and_domain_mission_push",
        "mode": "export",
        "status": str(status),
        "reason": str(reason),
        "run_tag": str(run_tag),
        "config": {
            "days": int(days),
            "allow_live_push": bool(allow_live_push),
        },
        "summary": summary if isinstance(summary, dict) else {},
        "artifacts": artifacts if isinstance(artifacts, dict) else {},
    }
    if error:
        payload["error"] = str(error)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat_ts = OUT_DIR / f"site_reach_mission_heartbeat_{run_tag}.json"
    txt = json.dumps(payload, indent=2)
    heartbeat_ts.write_text(txt, encoding="utf-8")
    HEARTBEAT_LATEST_PATH.write_text(txt, encoding="utf-8")
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    providers = payload.get("providers", []) if isinstance(payload, dict) else []
    channels = payload.get("promotion_channels", []) if isinstance(payload, dict) else []
    mission = payload.get("mission_message", {}) if isinstance(payload, dict) else {}

    lines: list[str] = []
    lines.append("# Site Reach and Domain Mission Push")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Days Window: {payload.get('parameters', {}).get('days', 0)}")
    lines.append("")
    lines.append("## Reach Summary")
    lines.append(f"- Canonical visitors (30d): {summary.get('canonical_visitors_30d')}")
    lines.append(f"- Canonical source: {summary.get('canonical_visitors_source')}")
    lines.append(f"- Providers configured: {summary.get('providers_configured', 0)}")
    lines.append(f"- Providers reporting metrics: {summary.get('providers_reporting', 0)}")
    lines.append("")
    lines.append("## Providers")
    for row in providers if isinstance(providers, list) else []:
        if not isinstance(row, dict):
            continue
        metrics = row.get("metrics", {}) if isinstance(row.get("metrics"), dict) else {}
        lines.append(
            f"- {row.get('provider', '')}: status={row.get('status', '')} configured={row.get('configured', False)} "
            f"visitors_30d={metrics.get('visitors_30d')} pageviews_30d={metrics.get('pageviews_30d')}"
        )
    lines.append("")
    lines.append("## Mission Message")
    lines.append(f"- Title: {mission.get('title', '')}")
    lines.append(f"- CTA: {mission.get('call_to_action_url', '')}")
    lines.append(f"- Hashtags: {', '.join(str(x) for x in mission.get('hashtags', []))}")
    lines.append("")
    lines.append(str(mission.get("text", "")))
    lines.append("")
    lines.append("## Promotion Channels")
    for row in channels if isinstance(channels, list) else []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('channel', '')} ({row.get('domain', '')}): status={row.get('status', '')} reason={row.get('reason', '')}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build site reach analytics and domain mission push package.")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days")
    parser.add_argument("--allow-live-push", action="store_true", help="Attempt live mission push where channel auth is fully configured")
    args = parser.parse_args()

    days = max(1, int(args.days))
    allow_live_push = bool(args.allow_live_push)
    run_tag = now_tag()

    write_heartbeat(
        status="running",
        reason="build_started",
        run_tag=run_tag,
        days=days,
        allow_live_push=allow_live_push,
    )

    try:
        env_runtime = {k: str(v) for k, v in os.environ.items() if isinstance(v, str)}
        env_keys = merge_env_maps(
            load_env_file(LIVE_KEYS_PATH),
            load_env_file(OUTREACH_KEYS_PATH),
            env_runtime,
        )

        live_sources = load_json(LIVE_SOURCES_PATH, {})
        key_status = load_key_status(KEY_STATUS_PATH)
        mission_pack = load_json(INVESTOR_MISSION_PACK_PATH, {})
        alpha_edge = load_json(ALPHA_EDGE_PATH, {})
        blueprint = load_json(BLUEPRINT_VAULT_PATH, {})
        grant_fit = load_json(GRANT_FIT_PATH, {})

        cloudflare_token = first_value(env_keys, ["CLOUDFLARE_API_TOKEN", "CF_API_TOKEN"])
        cloudflare_zone = first_value(env_keys, ["CLOUDFLARE_ZONE_ID", "CF_ZONE_ID"])

        plausible_token = first_value(env_keys, ["PLAUSIBLE_API_KEY", "PLAUSIBLE_TOKEN"])
        plausible_site = first_value(env_keys, ["PLAUSIBLE_SITE_ID", "PLAUSIBLE_DOMAIN"])

        umami_base = first_value(env_keys, ["UMAMI_BASE_URL"]) or ""
        umami_token = first_value(env_keys, ["UMAMI_API_TOKEN", "UMAMI_TOKEN"])
        umami_site = first_value(env_keys, ["UMAMI_WEBSITE_ID", "UMAMI_SITE_ID"])

        providers = [
            collect_cloudflare(days=days, token=cloudflare_token, zone_id=cloudflare_zone),
            collect_plausible(days=days, token=plausible_token, site_id=plausible_site),
            collect_umami(days=days, base_url=umami_base, token=umami_token, website_id=umami_site),
        ]

        canonical_visitors, canonical_source = pick_canonical_visitors(providers)

        selected_submit_url = ""
        live_fill = mission_pack.get("autonomous_grant_live_fill", {}) if isinstance(mission_pack, dict) else {}
        if isinstance(live_fill, dict):
            selected = live_fill.get("selected_opportunity", {})
            if isinstance(selected, dict):
                selected_submit_url = str(selected.get("submit_url") or "")

        mission = build_mission_copy(alpha_payload=alpha_edge, mission_pack=mission_pack, blueprint_payload=blueprint)
        promotion_channels = build_promotion_channels(
            env_map=env_keys,
            mission=mission,
            allow_live_push=allow_live_push,
            selected_submit_url=selected_submit_url,
        )

        live_source_enabled: list[str] = []
        if isinstance(live_sources, dict):
            for source, row in live_sources.items():
                if isinstance(row, dict) and bool(row.get("enabled", False)):
                    live_source_enabled.append(str(source))

        opportunities = grant_fit.get("opportunities", []) if isinstance(grant_fit, dict) else []
        fit_likely = 0
        if isinstance(opportunities, list):
            fit_likely = sum(1 for row in opportunities if isinstance(row, dict) and str(row.get("fit_status", "")).upper() == "FIT_LIKELY")

        payload = {
            "generated_utc": now_iso(),
            "scope": "site_reach_and_domain_mission_push",
            "parameters": {
                "days": days,
                "allow_live_push": allow_live_push,
            },
            "providers": providers,
            "site_reach": {
                "canonical_visitors_30d": canonical_visitors,
                "canonical_visitors_source": canonical_source,
                "measurement_status": "measured" if canonical_visitors is not None else "analytics_not_configured",
            },
            "mission_message": mission,
            "promotion_channels": promotion_channels,
            "live_sources_enabled": sorted(live_source_enabled),
            "key_status_summary": {
                "present": sorted([k for k, v in key_status.items() if v in {"present", "live_key_present"}]),
                "missing": sorted([k for k, v in key_status.items() if v not in {"present", "live_key_present"}]),
            },
            "grant_alignment_context": {
                "fit_likely_count": fit_likely,
                "selected_submit_url": selected_submit_url or None,
            },
        }

        providers_configured = sum(1 for row in providers if bool((row or {}).get("configured")))
        providers_reporting = sum(
            1
            for row in providers
            if bool((row or {}).get("configured")) and (row.get("metrics") or {}).get("visitors_30d") is not None
        )
        channels_ready = sum(1 for row in promotion_channels if str((row or {}).get("status")) == "ready")
        channels_blocked = sum(1 for row in promotion_channels if str((row or {}).get("status")) == "blocked")

        payload["summary"] = {
            "canonical_visitors_30d": canonical_visitors,
            "canonical_visitors_source": canonical_source,
            "providers_configured": providers_configured,
            "providers_reporting": providers_reporting,
            "promotion_channels": len(promotion_channels),
            "promotion_channels_ready": channels_ready,
            "promotion_channels_blocked": channels_blocked,
            "live_sources_enabled_count": len(live_source_enabled),
            "fit_likely_count": fit_likely,
        }

        json_ts = OUT_DIR / f"site_reach_mission_{run_tag}.json"
        md_ts = OUT_DIR / f"site_reach_mission_{run_tag}.md"
        json_latest = OUT_DIR / "site_reach_mission_latest.json"
        md_latest = OUT_DIR / "site_reach_mission_latest.md"

        write_json(json_ts, payload)
        write_json(json_latest, payload)
        write_text(md_ts, render_markdown(payload))
        write_text(md_latest, render_markdown(payload))

        write_heartbeat(
            status="ok",
            reason="build_complete",
            run_tag=run_tag,
            days=days,
            allow_live_push=allow_live_push,
            summary=payload.get("summary", {}),
            artifacts={
                "json_latest": str(json_latest),
                "json_timestamped": str(json_ts),
                "md_latest": str(md_latest),
                "md_timestamped": str(md_ts),
            },
        )

        print("BUILD_SITE_REACH_AND_DOMAIN_MISSION_PUSH")
        print(f"canonical_visitors_30d={payload['summary'].get('canonical_visitors_30d')}")
        print(f"canonical_source={payload['summary'].get('canonical_visitors_source')}")
        print(f"providers_reporting={payload['summary'].get('providers_reporting')}")
        print(f"channels_ready={payload['summary'].get('promotion_channels_ready')}")
        print(f"json={json_latest}")
        print(f"md={md_latest}")
        return 0
    except Exception as exc:
        write_heartbeat(
            status="error",
            reason="build_failed",
            run_tag=run_tag,
            days=days,
            allow_live_push=allow_live_push,
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
