from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
OUT_DIR = OUT_OPS / "social_pro_dashboard"
STACK_DASHBOARD_DATA = ROOT / "dashboard" / "data"
ROOT_DASHBOARD_DATA = ROOT.parent / "dashboard" / "data"

SOCIAL_PROFILE_CANDIDATES = [
    ROOT / "out" / "opportunities" / "social" / "social_platform_profile_latest.json",
    STACK_DASHBOARD_DATA / "social_platform_profile_latest.json",
]

VERIFICATION_TARGETS = [
    ROOT / "out" / "ops" / "social_platform_profile_build_latest.json",
    ROOT / "out" / "opportunities" / "social" / "social_platform_profile_latest.json",
    ROOT / "out" / "ops" / "frozen_delta_truth_chain" / "frozen_delta_truth_chain_latest.json",
    ROOT / "out" / "ops" / "frozen_delta_truth_chain" / "frozen_delta_truth_chain_verify_latest.json",
    ROOT / "out" / "ops" / "investor_metric_readiness_latest.json",
    ROOT / "out" / "ops" / "provider_kpi_roi_pack_latest.json",
    ROOT / "out" / "ops" / "sector_energy_evidence_pipeline_latest.json",
    ROOT / "out" / "ops" / "trader_learnings" / "learned_runtime_overrides.json",
    ROOT / "rolling_performance.json",
    ROOT / "execution_events.jsonl",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def fmt_usd(value: Any) -> str:
    return f"${safe_float(value):,.0f}"


def root_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def pick_social_profile() -> tuple[dict[str, Any], str]:
    for cand in SOCIAL_PROFILE_CANDIDATES:
        payload = read_json(cand)
        if isinstance(payload, dict):
            return payload, root_relative(cand)
    return {"platform_cards": [], "metrics": {}, "summary": {}}, "missing"


def pick_platform_card(payload: dict[str, Any], platform_id: str, max_templates: int) -> dict[str, Any]:
    cards = payload.get("platform_cards", []) if isinstance(payload.get("platform_cards"), list) else []
    selected: dict[str, Any] = {}
    for card in cards:
        if not isinstance(card, dict):
            continue
        if str(card.get("platform_id", "")).strip().lower() == platform_id:
            selected = card
            break

    templates = []
    raw_templates = selected.get("post_templates", []) if isinstance(selected.get("post_templates"), list) else []
    for row in raw_templates[: max(1, max_templates)]:
        if not isinstance(row, dict):
            continue
        templates.append(
            {
                "title": str(row.get("title", "Update")).strip() or "Update",
                "text": str(row.get("text", "")).strip(),
            }
        )

    return {
        "platform_id": platform_id,
        "platform_name": str(selected.get("platform_name", platform_id.title())),
        "connected": bool(selected.get("connected", False)),
        "present_key_count": safe_int(selected.get("present_key_count", 0), 0),
        "present_keys": [str(k) for k in (selected.get("present_keys", []) or []) if str(k).strip()],
        "cadence": str(selected.get("cadence", "")),
        "tone": str(selected.get("tone", "")),
        "about": str(selected.get("about", "")),
        "content_pillars": [str(x) for x in (selected.get("content_pillars", []) or []) if str(x).strip()],
        "call_to_action": [str(x) for x in (selected.get("call_to_action", []) or []) if str(x).strip()],
        "post_templates": templates,
    }


def collect_verification_rows() -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    present = 0
    for target in VERIFICATION_TARGETS:
        exists = target.exists() and target.is_file()
        size_bytes = int(target.stat().st_size) if exists else 0
        mtime_utc = (
            datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc).isoformat() if exists else ""
        )
        digest = sha256_file(target) if exists else ""
        if exists:
            present += 1
        rows.append(
            {
                "path": root_relative(target),
                "exists": exists,
                "size_bytes": size_bytes,
                "modified_utc": mtime_utc,
                "sha256": digest,
                "sha256_short": digest[:16] if digest else "",
            }
        )
    return rows, present


def build_payload(max_templates: int) -> dict[str, Any]:
    social_payload, social_source = pick_social_profile()
    metrics = social_payload.get("metrics", {}) if isinstance(social_payload.get("metrics"), dict) else {}

    linkedin = pick_platform_card(social_payload, "linkedin", max_templates)
    facebook = pick_platform_card(social_payload, "facebook", max_templates)

    verification_rows, verification_present = collect_verification_rows()

    connected_count = int(bool(linkedin.get("connected"))) + int(bool(facebook.get("connected")))

    repro_commands = [
        "c:/LumaTrader/venv3.11/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/social_platform_profile_engine_v1.py --publish-mode dry_run",
        "c:/LumaTrader/venv3.11/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/ops/BUILD_SOCIAL_PRO_DASHBOARD_FEED.py",
        "pwsh -NoProfile -ExecutionPolicy Bypass -File c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/ops/AUDIT_DASHBOARD_MIRROR_PARITY.ps1",
    ]

    claims = [
        f"Measured provider coverage: {safe_float(metrics.get('measured_share_pct'), 0.0):.2f}%",
        f"Modeled annual value signal: {fmt_usd(metrics.get('annual_value_usd'))}",
        f"Top sector lane: {str(metrics.get('top_sector', 'unknown'))}",
        "Hashes and timestamps are regenerated on every refresh run.",
    ]

    return {
        "generated_utc": now_iso(),
        "scope": "social_pro_dashboard_feed",
        "schema": "social_pro_dashboard_v1",
        "social_profile_source": social_source,
        "summary": {
            "platform_connected_count": connected_count,
            "platform_target_count": 2,
            "verification_target_count": len(verification_rows),
            "verification_target_present_count": verification_present,
            "measured_share_pct": round(safe_float(metrics.get("measured_share_pct"), 0.0), 2),
            "annual_value_usd": round(safe_float(metrics.get("annual_value_usd"), 0.0), 2),
            "top_sector": str(metrics.get("top_sector", "unknown")),
            "router_edge_pct": round(safe_float(metrics.get("router_edge_pct"), 0.0), 2),
            "selected_grant": metrics.get("selected_grant", {}),
        },
        "platforms": [linkedin, facebook],
        "verification_targets": verification_rows,
        "credibility_claims": claims,
        "reproducibility": {
            "commands": repro_commands,
            "notes": [
                "Run the commands in order to regenerate social profile data, attestation feed, and mirror parity results.",
                "Share the dashboard URL together with the latest attestation JSON for third-party review.",
            ],
        },
        "promotion": {
            "linkedin_templates": linkedin.get("post_templates", []),
            "facebook_templates": facebook.get("post_templates", []),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    platforms = payload.get("platforms", []) if isinstance(payload.get("platforms"), list) else []
    rows = payload.get("verification_targets", []) if isinstance(payload.get("verification_targets"), list) else []

    lines: list[str] = []
    lines.append("# Social Pro Dashboard Feed")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Schema: {payload.get('schema', '')}")
    lines.append(f"Social source: {payload.get('social_profile_source', '')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"- Platform connected count: {safe_int(summary.get('platform_connected_count'), 0)}/{safe_int(summary.get('platform_target_count'), 0)}"
    )
    lines.append(
        f"- Verification targets present: {safe_int(summary.get('verification_target_present_count'), 0)}/{safe_int(summary.get('verification_target_count'), 0)}"
    )
    lines.append(f"- Measured share: {safe_float(summary.get('measured_share_pct'), 0.0):.2f}%")
    lines.append(f"- Annual value signal: {fmt_usd(summary.get('annual_value_usd'))}")
    lines.append(f"- Top sector: {summary.get('top_sector', 'unknown')}")
    lines.append("")

    lines.append("## Platform Status")
    lines.append("")
    for card in platforms:
        if not isinstance(card, dict):
            continue
        lines.append(f"### {card.get('platform_name', 'Platform')}")
        lines.append(f"- Connected: {bool(card.get('connected'))}")
        lines.append(f"- Present key count: {safe_int(card.get('present_key_count'), 0)}")
        lines.append(f"- Cadence: {card.get('cadence', '')}")
        lines.append(f"- Tone: {card.get('tone', '')}")
        cta = card.get("call_to_action", []) if isinstance(card.get("call_to_action"), list) else []
        if cta:
            lines.append(f"- CTA: {', '.join(str(x) for x in cta[:3])}")
        lines.append("")

    lines.append("## Verification Targets")
    lines.append("")
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = "PASS" if bool(row.get("exists")) else "MISSING"
        lines.append(
            f"- [{status}] {row.get('path', '')} | sha256={row.get('sha256_short', '')} | size={safe_int(row.get('size_bytes'), 0)}"
        )
    lines.append("")

    lines.append("## Reproducibility Commands")
    lines.append("")
    repro = payload.get("reproducibility", {}) if isinstance(payload.get("reproducibility"), dict) else {}
    for cmd in repro.get("commands", []):
        lines.append(f"- {cmd}")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build social pro dashboard feed with verifiable artifacts.")
    parser.add_argument("--max-templates", type=int, default=3, help="Maximum templates per platform in output payload.")
    args = parser.parse_args()

    payload = build_payload(max_templates=max(1, int(args.max_templates)))
    markdown = render_markdown(payload)

    stamp = utc_tag()
    tagged_json = OUT_DIR / f"social_pro_dashboard_feed_{stamp}.json"
    latest_json = OUT_DIR / "social_pro_dashboard_feed_latest.json"
    tagged_md = OUT_DIR / f"social_pro_dashboard_feed_{stamp}.md"
    latest_md = OUT_DIR / "social_pro_dashboard_feed_latest.md"

    write_json(tagged_json, payload)
    write_json(latest_json, payload)
    write_text(tagged_md, markdown)
    write_text(latest_md, markdown)

    write_json(STACK_DASHBOARD_DATA / "social_pro_dashboard_latest.json", payload)
    write_json(ROOT_DASHBOARD_DATA / "social_pro_dashboard_latest.json", payload)

    print(f"SOCIAL_PRO_JSON={latest_json}")
    print(f"SOCIAL_PRO_MD={latest_md}")
    print(f"STACK_DASHBOARD_DATA={STACK_DASHBOARD_DATA / 'social_pro_dashboard_latest.json'}")
    print(f"ROOT_DASHBOARD_DATA={ROOT_DASHBOARD_DATA / 'social_pro_dashboard_latest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
