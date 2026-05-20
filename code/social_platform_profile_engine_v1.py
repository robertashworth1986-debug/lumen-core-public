from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from application_context_resolver import CTX_LATEST, load_application_profile

ROOT = Path(__file__).resolve().parents[1]
OUT_OPS = ROOT / "out" / "ops"
OUT_OPP = ROOT / "out" / "opportunities" / "social"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
ROOT_DASHBOARD_DATA = ROOT.parent / "dashboard" / "data"

FUNDING_QUEUE = ROOT / "out" / "funding" / "funding_approval_queue.json"
CROWDFUND_CAMPAIGN_QUEUE = ROOT / "out" / "crowdfunding_approval_queue.json"
PROVIDER_KPI_LATEST = OUT_OPS / "provider_kpi_roi_pack_latest.json"
INVESTOR_READINESS_LATEST = OUT_OPS / "investor_metric_readiness_latest.json"
INVESTOR_MISSION_PACK_LATEST = OUT_OPS / "investor_mission_control" / "investor_mission_control_pack_latest.json"
LINKEDIN_BUILD_LATEST = OUT_OPS / "lumalinkedin_v1_build_latest.json"
LINKEDIN_LATEST = ROOT / "out" / "opportunities" / "linkedin" / "lumalinkedin_v1_latest.json"
RESUME_LATEST = ROOT / "out" / "resume" / "resume_lumalinkedin_v1_latest.json"

DEFAULT_ENV_FILES = [
    ROOT / ".env.live",
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "config" / "luma_outreach_keys.env",
    ROOT / "config" / ".env",
    ROOT / ".env",
]

PLATFORM_ALIAS_TERMS: dict[str, list[str]] = {
    "linkedin": ["LINKEDIN"],
    "x": ["TWITTER", "X_", "XAPI", "X-API"],
    "youtube": ["YOUTUBE", "GOOGLE_VIDEO", "GOOGLE_YT"],
    "instagram": ["INSTAGRAM", "IG_", "META_IG"],
    "facebook": ["FACEBOOK", "FB_", "META_"],
    "tiktok": ["TIKTOK"],
    "reddit": ["REDDIT"],
}

PLATFORM_SPECS: list[dict[str, Any]] = [
    {
        "id": "linkedin",
        "name": "LinkedIn",
        "required_groups": [
            ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI"],
            ["LINKEDIN_ACCESS_TOKEN"],
        ],
        "cadence": "3 to 5 posts per week",
        "tone": "institutional and evidence-first",
    },
    {
        "id": "x",
        "name": "X",
        "required_groups": [
            ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"],
            ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"],
            ["TWITTER_BEARER_TOKEN"],
        ],
        "cadence": "1 to 2 short updates per day",
        "tone": "fast alpha and proof snippets",
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "required_groups": [
            ["YOUTUBE_API_KEY"],
            ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET"],
        ],
        "cadence": "2 deep-dive videos per week",
        "tone": "long-form mission brief and explainers",
    },
    {
        "id": "instagram",
        "name": "Instagram",
        "required_groups": [
            ["INSTAGRAM_ACCESS_TOKEN"],
            ["INSTAGRAM_APP_ID", "INSTAGRAM_APP_SECRET"],
            ["META_ACCESS_TOKEN"],
        ],
        "cadence": "4 visuals and reels per week",
        "tone": "visual proof moments and founder narrative",
    },
    {
        "id": "facebook",
        "name": "Facebook",
        "required_groups": [
            ["FACEBOOK_PAGE_ACCESS_TOKEN"],
            ["FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"],
            ["META_ACCESS_TOKEN"],
        ],
        "cadence": "3 community and investor updates per week",
        "tone": "community credibility and pilot traction",
    },
    {
        "id": "tiktok",
        "name": "TikTok",
        "required_groups": [
            ["TIKTOK_ACCESS_TOKEN"],
            ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
        ],
        "cadence": "3 short clips per week",
        "tone": "tight founder story and mission highlights",
    },
    {
        "id": "reddit",
        "name": "Reddit",
        "required_groups": [
            ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_REFRESH_TOKEN"],
        ],
        "cadence": "2 evidence posts and AMAs per month",
        "tone": "technical transparency and deep Q and A",
    },
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
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        parsed[key] = value
    return parsed


def _load_keyring(env_files: list[Path]) -> dict[str, str]:
    keyring: dict[str, str] = {}
    for k, v in os.environ.items():
        keyring[k] = str(v)
    for env_file in env_files:
        file_values = _parse_env_file(env_file)
        for k, v in file_values.items():
            if not keyring.get(k):
                keyring[k] = v
    return keyring


def _present_keys(spec: dict[str, Any], keyring: dict[str, str]) -> list[str]:
    names: set[str] = set()
    for group in spec.get("required_groups", []):
        for key in group:
            names.add(str(key))
    return sorted([name for name in names if str(keyring.get(name, "")).strip()])


def _connected(spec: dict[str, Any], keyring: dict[str, str]) -> bool:
    groups = spec.get("required_groups", [])
    for group in groups:
        if all(str(keyring.get(str(k), "")).strip() for k in group):
            return True
    return False


def _alias_keys(platform_id: str, keyring: dict[str, str]) -> list[str]:
    terms = PLATFORM_ALIAS_TERMS.get(platform_id, [])
    if not terms:
        return []

    out: list[str] = []
    for key, value in keyring.items():
        up = str(key).upper()
        if not str(value or "").strip():
            continue
        if not any(term in up for term in terms):
            continue
        if not any(marker in up for marker in ("KEY", "TOKEN", "SECRET", "CLIENT", "APP", "PAGE")):
            continue
        out.append(str(key))
    out.sort()
    return out


def _first_non_empty(*values: Any, default: str = "") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return default


def _build_metrics() -> dict[str, Any]:
    kpi = _read_json(PROVIDER_KPI_LATEST)
    readiness = _read_json(INVESTOR_READINESS_LATEST)
    mission_pack = _read_json(INVESTOR_MISSION_PACK_LATEST)

    counts = (kpi or {}).get("counts", {}) if isinstance(kpi, dict) else {}
    readiness_summary = (readiness or {}).get("summary", {}) if isinstance(readiness, dict) else {}
    signal = readiness_summary.get("signal_evidence", {}) if isinstance(readiness_summary, dict) else {}

    annual_value = _safe_float(signal.get("annual_value_usd"), _safe_float(counts.get("total_month_value_usd")) * 12.0)
    top_sector = _first_non_empty(signal.get("top_sector"), default="infrastructure_intelligence")
    router_edge = _safe_float(signal.get("router_edge_pct"))

    live_fill = (mission_pack or {}).get("autonomous_grant_live_fill", {}) if isinstance(mission_pack, dict) else {}
    selected = live_fill.get("selected_opportunity", {}) if isinstance(live_fill, dict) else {}

    return {
        "generated_utc": _now_iso(),
        "provider_count": _safe_int(counts.get("provider_count"), 0),
        "measured_count": _safe_int(counts.get("measured_count"), 0),
        "measured_share_pct": _safe_float(counts.get("measured_share_pct"), 0.0),
        "total_month_value_usd": _safe_float(counts.get("total_month_value_usd"), 0.0),
        "annual_value_usd": annual_value,
        "top_sector": top_sector,
        "router_edge_pct": router_edge,
        "selected_grant": {
            "opp_num": selected.get("opp_num") if isinstance(selected, dict) else None,
            "title": selected.get("title") if isinstance(selected, dict) else None,
            "submit_url": selected.get("submit_url") if isinstance(selected, dict) else None,
        },
    }


def _crowdfunding_highlights(limit: int) -> dict[str, Any]:
    funding_queue = _read_json(FUNDING_QUEUE)
    campaign_queue = _read_json(CROWDFUND_CAMPAIGN_QUEUE)

    funding_rows = [
        row for row in (funding_queue if isinstance(funding_queue, list) else [])
        if isinstance(row, dict) and str(row.get("channel") or "").lower() == "crowdfund"
    ]
    funding_rows.sort(key=lambda row: _safe_float(row.get("priority_score"), 0.0), reverse=True)

    campaign_rows = [row for row in (campaign_queue if isinstance(campaign_queue, list) else []) if isinstance(row, dict)]
    campaign_rows.sort(key=lambda row: _safe_float((row.get("platform") or {}).get("fit_score"), 0.0), reverse=True)

    top_funding: list[dict[str, Any]] = []
    for row in funding_rows[: max(1, limit)]:
        top_funding.append(
            {
                "ticket_id": row.get("ticket_id"),
                "title": row.get("title"),
                "agency": row.get("agency"),
                "approval_state": row.get("approval_state"),
                "priority_score": _safe_float(row.get("priority_score"), 0.0),
                "days_to_deadline": _safe_int(row.get("days_to_deadline"), 0),
                "estimated_value_usd": _safe_float(row.get("estimated_value_usd"), 0.0),
                "reason": row.get("reason") if isinstance(row.get("reason"), list) else [],
            }
        )

    top_campaigns: list[dict[str, Any]] = []
    for row in campaign_rows[: max(1, limit)]:
        platform = row.get("platform") if isinstance(row.get("platform"), dict) else {}
        top_campaigns.append(
            {
                "ticket_id": row.get("ticket_id"),
                "platform": platform.get("name"),
                "platform_fit_score": _safe_float(platform.get("fit_score"), 0.0),
                "raise_target_usd": _safe_float(row.get("raise_target_usd"), 0.0),
                "approval_state": row.get("approval_state"),
                "headline": ((row.get("campaign_content") or {}).get("headline") if isinstance(row.get("campaign_content"), dict) else None),
            }
        )

    pending_human = sum(
        1
        for row in funding_rows
        if str(row.get("approval_state") or "").upper() == "PENDING_HUMAN_APPROVAL"
    )

    return {
        "generated_utc": _now_iso(),
        "funding_queue_count": len(funding_rows),
        "campaign_queue_count": len(campaign_rows),
        "pending_human_approval_count": pending_human,
        "top_funding_opportunities": top_funding,
        "top_campaign_blueprints": top_campaigns,
    }


def _clean_words(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned


def _build_platform_profile(
    spec: dict[str, Any],
    profile: dict[str, Any],
    metrics: dict[str, Any],
    highlights: dict[str, Any],
    keyring: dict[str, str],
) -> dict[str, Any]:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    founder = profile.get("pi", {}) if isinstance(profile, dict) else {}

    company_name = _first_non_empty(company.get("legal_name"), company.get("name"), default="LumenCore")
    founder_name = _first_non_empty(founder.get("name"), company.get("founder_pi"), default="Robert BabyRay Ashworth")
    website = _first_non_empty(company.get("website"), default="https://lumen-core.ai")

    measured = _safe_int(metrics.get("measured_count"), 0)
    providers = _safe_int(metrics.get("provider_count"), 0)
    measured_share = _safe_float(metrics.get("measured_share_pct"), 0.0)
    annual_value = _safe_float(metrics.get("annual_value_usd"), 0.0)
    top_sector = _first_non_empty(metrics.get("top_sector"), default="infrastructure")
    crowd_pending = _safe_int(highlights.get("pending_human_approval_count"), 0)

    present_keys = _present_keys(spec, keyring)
    alias_keys = _alias_keys(str(spec.get("id") or ""), keyring)
    merged_present_keys = sorted(set(present_keys + alias_keys))
    connected = _connected(spec, keyring)

    mission_line = (
        f"{company_name} builds predictive infrastructure intelligence with measured evidence "
        f"({measured}/{providers} providers measured, {measured_share:.2f}% coverage)."
    )
    value_line = (
        f"Current modeled annual value signal: ${annual_value:,.0f}. "
        f"Top lane: {top_sector}. Crowdfunding queue pending approvals: {crowd_pending}."
    )

    profile_variants = [
        _clean_words(f"{founder_name} | {company_name} | Institutional AI and Quant Systems"),
        _clean_words(f"{company_name} | Predictive Infrastructure Intelligence | Evidence-First"),
        _clean_words(f"Founder-Operator | Mission Control Pipelines | {company_name}"),
    ]

    post_templates = [
        {
            "title": f"{spec['name']} lane refresh",
            "text": _clean_words(
                f"{company_name} {spec['name']} lane refresh complete. {mission_line} {value_line}"
            ),
        },
        {
            "title": "Crowdfunding opportunity signal",
            "text": _clean_words(
                f"Crowdfunding pipeline is active with {crowd_pending} pending approval opportunities. "
                f"We are shipping profile + portal assets directly from the opportunity engine."
            ),
        },
    ]

    return {
        "platform_id": spec["id"],
        "platform_name": spec["name"],
        "connected": connected,
        "present_keys": merged_present_keys,
        "present_key_count": len(merged_present_keys),
        "detected_alias_keys": alias_keys,
        "needs_key_mapping": bool(alias_keys) and not connected,
        "required_group_count": len(spec.get("required_groups", [])),
        "cadence": spec.get("cadence"),
        "tone": spec.get("tone"),
        "profile_variants": profile_variants,
        "about": _clean_words(f"{mission_line} {value_line}"),
        "content_pillars": [
            "Measured provider coverage updates",
            "Proof artifacts and execution telemetry",
            "Crowdfunding and grant lane highlights",
            "Pilot deployment milestones",
        ],
        "call_to_action": [
            website,
            "https://lumen-core.ai/mission_control.html",
            "https://lumen-core.ai/evidence/",
        ],
        "post_templates": post_templates,
        "pipeline": {
            "source_artifacts": [
                str(LINKEDIN_BUILD_LATEST),
                str(LINKEDIN_LATEST),
                str(RESUME_LATEST),
                str(PROVIDER_KPI_LATEST),
                str(FUNDING_QUEUE),
                str(CROWDFUND_CAMPAIGN_QUEUE),
            ],
            "portal_targets": [
                str(DASHBOARD_DATA / "social_platform_profile_latest.json"),
                str(DASHBOARD_DATA / "crowdfunding_highlights_latest.json"),
                str(ROOT_DASHBOARD_DATA / "social_platform_profile_latest.json"),
                str(ROOT_DASHBOARD_DATA / "crowdfunding_highlights_latest.json"),
            ],
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Social Platform Profile Engine V1")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append("")

    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Platforms scanned: {summary.get('platforms_scanned', 0)}")
    lines.append(f"- Platforms connected: {summary.get('platforms_connected', 0)}")
    lines.append(f"- Crowdfunding pending approval: {summary.get('crowdfunding_pending_human_approval_count', 0)}")
    lines.append("")

    lines.append("## Platform Cards")
    lines.append("")
    for card in payload.get("platform_cards", []):
        if not isinstance(card, dict):
            continue
        lines.append(f"### {card.get('platform_name', 'Platform')}")
        lines.append(f"- Connected: {bool(card.get('connected'))}")
        lines.append(f"- Present keys: {', '.join(card.get('present_keys') or []) or 'none'}")
        lines.append(f"- Cadence: {card.get('cadence', '')}")
        lines.append(f"- Tone: {card.get('tone', '')}")
        variants = card.get("profile_variants") if isinstance(card.get("profile_variants"), list) else []
        for variant in variants[:2]:
            lines.append(f"- Variant: {variant}")
        lines.append("")

    highlights = payload.get("crowdfunding_highlights", {}) if isinstance(payload.get("crowdfunding_highlights"), dict) else {}
    lines.append("## Crowdfunding Highlights")
    lines.append("")
    top_rows = highlights.get("top_funding_opportunities") if isinstance(highlights.get("top_funding_opportunities"), list) else []
    if not top_rows:
        lines.append("- No crowdfunding opportunities found yet.")
    else:
        for row in top_rows[:8]:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"- {row.get('title', 'Untitled')} | score={row.get('priority_score', 0)} | "
                f"value=${_safe_float(row.get('estimated_value_usd'), 0.0):,.0f} | "
                f"state={row.get('approval_state', 'UNKNOWN')}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build multi-platform social profile and crowdfunding portal artifacts.")
    parser.add_argument("--max-platforms", type=int, default=8)
    parser.add_argument(
        "--publish-mode",
        choices=["none", "dry_run"],
        default="dry_run",
        help="Publishing mode placeholder. Current implementation emits post-ready payloads only.",
    )
    args = parser.parse_args()

    profile = load_application_profile() if CTX_LATEST.exists() else {}
    metrics = _build_metrics()
    highlights = _crowdfunding_highlights(limit=10)
    keyring = _load_keyring(DEFAULT_ENV_FILES)

    specs = PLATFORM_SPECS[: max(1, int(args.max_platforms))]
    cards: list[dict[str, Any]] = []
    for spec in specs:
        cards.append(_build_platform_profile(spec, profile, metrics, highlights, keyring))

    connected_count = sum(1 for card in cards if bool(card.get("connected")))

    payload = {
        "generated_utc": _now_iso(),
        "scope": "social_platform_profile_engine_v1",
        "publish_mode": args.publish_mode,
        "metrics": metrics,
        "crowdfunding_highlights": highlights,
        "summary": {
            "platforms_scanned": len(cards),
            "platforms_connected": connected_count,
            "crowdfunding_pending_human_approval_count": _safe_int(highlights.get("pending_human_approval_count"), 0),
            "funding_queue_count": _safe_int(highlights.get("funding_queue_count"), 0),
            "campaign_queue_count": _safe_int(highlights.get("campaign_queue_count"), 0),
        },
        "platform_cards": cards,
    }

    stamp = _stamp()
    OUT_OPP.mkdir(parents=True, exist_ok=True)
    OUT_OPS.mkdir(parents=True, exist_ok=True)

    tagged_json = OUT_OPP / f"social_platform_profile_v1_{stamp}.json"
    tagged_md = OUT_OPP / f"social_platform_profile_v1_{stamp}.md"
    latest_json = OUT_OPP / "social_platform_profile_latest.json"
    latest_md = OUT_OPP / "social_platform_profile_latest.md"

    summary_tagged = OUT_OPS / f"social_platform_profile_build_{stamp}.json"
    summary_latest = OUT_OPS / "social_platform_profile_build_latest.json"

    markdown = _render_markdown(payload)

    _write_json(tagged_json, payload)
    _write_json(latest_json, payload)
    _write_text(tagged_md, markdown)
    _write_text(latest_md, markdown)

    summary_payload = {
        "generated_utc": _now_iso(),
        "scope": "social_platform_profile_engine_v1",
        "publish_mode": args.publish_mode,
        "summary": payload.get("summary", {}),
        "artifacts": {
            "latest_json": str(latest_json),
            "latest_md": str(latest_md),
            "tagged_json": str(tagged_json),
            "tagged_md": str(tagged_md),
        },
        "portal_assets": [
            str(DASHBOARD_DATA / "social_platform_profile_latest.json"),
            str(DASHBOARD_DATA / "crowdfunding_highlights_latest.json"),
            str(ROOT_DASHBOARD_DATA / "social_platform_profile_latest.json"),
            str(ROOT_DASHBOARD_DATA / "crowdfunding_highlights_latest.json"),
        ],
    }

    _write_json(summary_tagged, summary_payload)
    _write_json(summary_latest, summary_payload)

    # Push portal feed artifacts for dashboard local-mode fallbacks.
    for dashboard_dir in (DASHBOARD_DATA, ROOT_DASHBOARD_DATA):
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        _write_json(dashboard_dir / "social_platform_profile_latest.json", payload)
        _write_json(dashboard_dir / "crowdfunding_highlights_latest.json", highlights)

    print(f"SOCIAL_JSON={latest_json}")
    print(f"SOCIAL_MD={latest_md}")
    print(f"SUMMARY={summary_tagged}")
    print(f"CROWDFUNDING_HIGHLIGHTS={DASHBOARD_DATA / 'crowdfunding_highlights_latest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
