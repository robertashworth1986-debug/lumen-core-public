from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD = ROOT / "dashboard"
DASHBOARD_DATA = DASHBOARD / "data"
PRODUCTION_MANIFEST = DASHBOARD / "PRODUCTION_MANIFEST.json"

OUT_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "live_domain_deployment_feed.json"
OUT_MD = DOCS / "LIVE_DOMAIN_DEPLOYMENT_FEED_2026-06-27.md"

DEFAULT_LIVE_BASE = "https://lumen-core.ai"

BOUNDARY = (
    "Live-domain deployment feed only. Matching hosted hashes prove that the public domain is serving the same "
    "local proof feeds. They do not prove field validation, realized savings, grant award certainty, fixed frozen "
    "delta pricing, medical efficacy, or live trading performance."
)

PROOF_FEEDS = [
    {
        "key": "champion_metric_gauntlet",
        "local": "dashboard/data/champion_metric_gauntlet.json",
        "required": True,
        "why": "Current reviewer-safe champion summary and metric gates.",
    },
    {
        "key": "locked_source_baseline_replay_sweep",
        "local": "dashboard/data/locked_source_baseline_replay_sweep.json",
        "required": True,
        "why": "Full locked source-conditioned replay sweep across live-breadth rows and baselines.",
    },
    {
        "key": "kuramoto_holdout_expansion",
        "local": "dashboard/data/kuramoto_holdout_expansion.json",
        "required": True,
        "why": "Expanded source-conditioned holdout evidence for the current champion.",
    },
    {
        "key": "geometry_champion_of_champions",
        "local": "dashboard/data/geometry_champion_of_champions.json",
        "required": True,
        "why": "Family-level champion ranking and evidence status.",
    },
    {
        "key": "field_money_truth_sweep",
        "local": "dashboard/data/field_money_truth_sweep.json",
        "required": True,
        "why": "Safe money-path and truth-boundary gate.",
    },
    {
        "key": "live_proof_value_meter",
        "local": "dashboard/data/live_proof_value_meter.json",
        "required": True,
        "why": "Bounded estimated-value language and claim boundaries.",
    },
    {
        "key": "field_validated_dollar_claim_ladder",
        "local": "dashboard/data/field_validated_dollar_claim_ladder.json",
        "required": True,
        "why": "Ladder from internal proof to authorized field validation.",
    },
    {
        "key": "dollar_claim_gate",
        "local": "dashboard/data/dollar_claim_gate.json",
        "required": True,
        "why": "Explicit allowed and blocked dollar-claim states.",
    },
    {
        "key": "field_validation_control_room",
        "local": "dashboard/data/field_validation_control_room.json",
        "required": True,
        "why": "External validation unlocks, held-out data blockers, and buyer-accepted claim boundaries.",
    },
    {
        "key": "field_validation_outreach_board",
        "local": "dashboard/data/field_validation_outreach_board.json",
        "required": True,
        "why": "Ranked manual outreach targets and reviewer-safe validation request language.",
    },
    {
        "key": "proof_to_pilot_control_room",
        "local": "dashboard/data/proof_to_pilot_control_room.json",
        "required": True,
        "why": "Canonical proof-to-pilot board feed that ties champions to paid evaluation scope.",
    },
    {
        "key": "champion_sample_expansion_and_economic_bridge",
        "local": "dashboard/data/champion_sample_expansion_and_economic_bridge.json",
        "required": True,
        "why": "Expanded source breadth, sample-size diagnostics, and disciplined economic claim bridge.",
    },
    {
        "key": "champion_source_ablation",
        "local": "dashboard/data/champion_source_ablation.json",
        "required": True,
        "why": "Leave-one-source-out robustness gate showing the current champion is not carried by one source system.",
    },
    {
        "key": "geometry_asset_wiring_board",
        "local": "dashboard/data/geometry_asset_wiring_board.json",
        "required": False,
        "why": "Broader dataset and asset wiring context.",
    },
    {
        "key": "luma_context_dashboard_parity_audit",
        "local": "dashboard/data/luma_context_dashboard_parity_audit.json",
        "required": False,
        "why": "General dashboard parity and continuity audit.",
    },
    {
        "key": "champion_stress_test_matrix",
        "local": "dashboard/data/champion_stress_test_matrix.json",
        "required": False,
        "why": "Compact buyer/reviewer-safe stress matrix for the current champion.",
    },
    {
        "key": "champion_metric_battery",
        "local": "dashboard/data/champion_metric_battery.json",
        "required": False,
        "why": "Consolidated pass/ready/blocked metric battery for the current champion.",
    },
    {
        "key": "champion_expanded_metric_rollup",
        "local": "dashboard/data/champion_expanded_metric_rollup.json",
        "required": False,
        "why": "Lane-by-lane expanded metric rollup tying champion wins to baselines, sources, and claim gates.",
    },
    {
        "key": "proof_to_revenue_engine",
        "local": "dashboard/data/proof_to_revenue_engine.json",
        "required": False,
        "why": "Reviewer-safe proof-to-revenue bridge with blocked and allowed claim controls.",
    },
    {
        "key": "first_buyer_target_board",
        "local": "dashboard/data/first_buyer_target_board.json",
        "required": False,
        "why": "Named, source-verified first-buyer and field-replay target board.",
    },
    {
        "key": "live_domain_consolidation_audit",
        "local": "dashboard/data/live_domain_consolidation_audit.json",
        "required": False,
        "why": "Public-domain surface audit that identifies stale feeds, broken links, and claim-language cleanup.",
    },
    {
        "key": "luma_operator_context",
        "local": "dashboard/data/luma_operator_context.json",
        "required": False,
        "why": "Anti-drift operator context and proof-to-pilot execution state.",
    },
    {
        "key": "champion_phase_proxy_diagnostics",
        "local": "dashboard/data/champion_phase_proxy_diagnostics.json",
        "required": False,
        "why": "Replay-data phase/coherence/residual proxy diagnostics for the current champion.",
    },
    {
        "key": "safe_key_provider_ping",
        "local": "dashboard/data/safe_key_provider_ping.json",
        "required": False,
        "why": "Masked provider-key readiness and API ping status without exposing secrets.",
    },
    {
        "key": "live_source_measurement_maximizer",
        "local": "dashboard/data/live_source_measurement_maximizer.json",
        "required": False,
        "why": "Latest measured-source count, fresh row count, and blocked/thin source diagnostics.",
    },
    {
        "key": "geometry_live_wiring_matrix",
        "local": "dashboard/data/geometry_live_wiring_matrix.json",
        "required": False,
        "why": "Maps geometry lanes to measured live-source readiness and remaining claim gates.",
    },
    {
        "key": "geometry_live_breadth_proof_queue",
        "local": "dashboard/data/geometry_live_breadth_proof_queue.json",
        "required": False,
        "why": "Ranks candidate geometry families for live-breadth proof expansion.",
    },
    {
        "key": "branching_live_breadth_replay",
        "local": "dashboard/data/branching_live_breadth_replay.json",
        "required": False,
        "why": "Branching-family live replay status, including negative evidence when baselines still lead.",
    },
    {
        "key": "rolling_champion_gate",
        "local": "dashboard/data/rolling_champion_gate.json",
        "required": False,
        "why": "Promotion gate for repeat winners, triple-source candidates, and real-dollar claim blockers.",
    },
    {
        "key": "top_geometry_live_replay_results",
        "local": "dashboard/data/top_geometry_live_replay_results.json",
        "required": False,
        "why": "Top geometry replay cards and named-baseline beat counts across current live context.",
    },
    {
        "key": "real_noise_evidence_boundary_breaker",
        "local": "dashboard/data/real_noise_evidence_boundary_breaker.json",
        "required": False,
        "why": "Plan for replacing synthetic-only assumptions with real noisy data while preserving claim boundaries.",
    },
    {
        "key": "real_noise_promotion_sweep",
        "local": "dashboard/data/real_noise_promotion_sweep.json",
        "required": False,
        "why": "Fresh scan of local/provider CSV snapshots that identifies real-noise datasets ready for locked replay.",
    },
    {
        "key": "geometry_execution_context_audit",
        "local": "dashboard/data/geometry_execution_context_audit.json",
        "required": False,
        "why": "Current anti-drift audit covering geometry count, Vesica Piscis status, live-breadth readiness, and trading guardrails.",
    },
]

REMOTE_TEMPLATES = [
    "/data/{key}.json",
    "/dashboard/data/{key}.json",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def as_bool(value: Any) -> bool:
    return bool(value)


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def live_base() -> str:
    manifest = read_json(PRODUCTION_MANIFEST)
    return str(manifest.get("deployment_domain") or DEFAULT_LIVE_BASE).rstrip("/")


def fetch_url_bytes(url: str, timeout: int = 10) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "LumaDomainDeploymentVerifier/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            return {
                "ok": True,
                "url": url,
                "status": int(response.status),
                "bytes": len(body),
                "sha256": sha256_bytes(body),
                "content_type": response.headers.get("content-type", ""),
                "error": "",
            }
    except HTTPError as exc:
        return {
            "ok": False,
            "url": url,
            "status": int(exc.code),
            "bytes": 0,
            "sha256": "",
            "content_type": exc.headers.get("content-type", "") if exc.headers else "",
            "error": str(exc),
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "url": url,
            "status": 0,
            "bytes": 0,
            "sha256": "",
            "content_type": "",
            "error": str(exc),
        }


def local_feed_card(spec: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / str(spec["local"])
    exists = path.exists() and path.is_file()
    data = read_json(path)
    return {
        "key": spec["key"],
        "required": bool(spec["required"]),
        "why": spec["why"],
        "local_relative_path": str(path.relative_to(ROOT)).replace("\\", "/") if path.exists() else str(spec["local"]),
        "local_exists": exists,
        "local_bytes": path.stat().st_size if exists else 0,
        "local_sha256": sha256_file(path) if exists else "",
        "local_generated_utc": data.get("generated_utc"),
        "local_schema": data.get("schema"),
    }


def remote_candidates(key: str, base: str, check_live_domain: bool, timeout: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for template in REMOTE_TEMPLATES:
        url = f"{base}{template.format(key=key)}"
        if check_live_domain:
            candidates.append(fetch_url_bytes(url, timeout=timeout))
        else:
            candidates.append(
                {
                    "ok": False,
                    "url": url,
                    "status": None,
                    "bytes": 0,
                    "sha256": "",
                    "content_type": "",
                    "error": "live check skipped",
                }
            )
    return candidates


def build_feed_row(spec: dict[str, Any], base: str, check_live_domain: bool, timeout: int) -> dict[str, Any]:
    card = local_feed_card(spec)
    remotes = remote_candidates(str(spec["key"]), base, check_live_domain, timeout)
    local_sha = str(card.get("local_sha256") or "")
    matches = [
        row
        for row in remotes
        if bool(row.get("ok")) and local_sha and str(row.get("sha256")) == local_sha
    ]
    reachable = [row for row in remotes if bool(row.get("ok"))]
    first_reachable = reachable[0] if reachable else {}
    card.update(
        {
            "remote_candidates": remotes,
            "remote_reachable": bool(reachable),
            "remote_hash_match": bool(matches),
            "remote_match_url": matches[0]["url"] if matches else "",
            "remote_first_reachable_url": str(first_reachable.get("url") or ""),
            "remote_first_reachable_status": first_reachable.get("status"),
            "remote_first_reachable_sha256": str(first_reachable.get("sha256") or ""),
            "remote_first_reachable_bytes": as_int(first_reachable.get("bytes"), 0),
            "deployment_state": (
                "HOSTED_HASH_MATCH"
                if matches
                else ("LOCAL_READY_REMOTE_STALE_OR_MISSING" if card["local_exists"] else "LOCAL_MISSING")
            ),
        }
    )
    return card


def champion_snapshot() -> dict[str, Any]:
    gauntlet = read_json(DASHBOARD_DATA / "champion_metric_gauntlet.json")
    summary = gauntlet.get("summary", {}) if isinstance(gauntlet.get("summary"), dict) else {}
    strongest = gauntlet.get("strongest_current", {}) if isinstance(gauntlet.get("strongest_current"), dict) else {}
    return {
        "family": strongest.get("family"),
        "label": strongest.get("label"),
        "named_baseline": strongest.get("named_baseline"),
        "holdout_wins": summary.get("holdout_wins"),
        "holdout_count": summary.get("holdout_count"),
        "holdout_win_rate": summary.get("holdout_win_rate"),
        "estimated_rows_replayed": summary.get("estimated_rows_replayed"),
        "source_system_count": summary.get("source_system_count"),
        "buyer_authorized_field_replay_request_ready": as_bool(
            summary.get("buyer_authorized_field_replay_request_ready")
        ),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
    }


def build_payload(check_live_domain: bool = True, timeout: int = 10) -> dict[str, Any]:
    generated = now_utc()
    base = live_base()
    feeds = [build_feed_row(spec, base, check_live_domain, timeout) for spec in PROOF_FEEDS]
    required = [row for row in feeds if row["required"]]
    required_local_ready = [row for row in required if row["local_exists"]]
    required_remote_match = [row for row in required if row["remote_hash_match"]]
    required_remote_reachable = [row for row in required if row["remote_reachable"]]
    missing_local = [row for row in required if not row["local_exists"]]
    remote_missing_or_stale = [row for row in required if row["local_exists"] and not row["remote_hash_match"]]
    remote_reachable_but_stale = [
        row for row in remote_missing_or_stale if row.get("remote_reachable")
    ]
    local_ready = len(required_local_ready) == len(required)
    domain_verified = check_live_domain and local_ready and len(required_remote_match) == len(required)
    deploy_bundle = read_json(DASHBOARD_DATA / "live_domain_proof_feed_deploy_bundle.json")
    deploy_summary = deploy_bundle.get("summary", {}) if isinstance(deploy_bundle.get("summary"), dict) else {}
    safe_deploy_command = str(
        deploy_bundle.get("safe_deploy_command")
        or ".\\deploy\\PUSH_PROOF_FEEDS_TO_VPS.ps1"
    )

    payload: dict[str, Any] = {
        "generated_utc": generated,
        "schema": "live_domain_deployment_feed_v1",
        "purpose": "Hash-verify that the live domain is serving the current reviewer proof feeds.",
        "boundary": BOUNDARY,
        "live_base": base,
        "live_check_performed": bool(check_live_domain),
        "summary": {
            "required_feed_count": len(required),
            "required_local_ready_count": len(required_local_ready),
            "required_remote_reachable_count": len(required_remote_reachable),
            "required_remote_hash_match_count": len(required_remote_match),
            "required_remote_stale_or_missing_count": len(remote_missing_or_stale),
            "required_remote_reachable_but_stale_count": len(remote_reachable_but_stale),
            "optional_feed_count": len(feeds) - len(required),
            "local_required_ready": local_ready,
            "live_domain_reviewer_ready": domain_verified,
            "domain_deployment_state": (
                "LIVE_DOMAIN_HASH_VERIFIED"
                if domain_verified
                else ("LOCAL_READY_DOMAIN_NOT_VERIFIED_OR_STALE" if local_ready else "LOCAL_REQUIRED_FEEDS_MISSING")
            ),
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "plain_english_answer": (
                "The local proof stack is ready for reviewer packaging, but the live domain still needs hosted "
                "hash verification before we should point reviewers to it."
                if local_ready and not domain_verified
                else (
                    "The live domain is serving matching hashes for every required reviewer proof feed. This is "
                    "public deployment verification, not field validation."
                    if domain_verified
                    else "Required local reviewer proof feeds are missing, so deployment is not ready."
                )
            ),
            "next_domain_action": (
                "Deploy the local proof feeds to the live domain, then rerun this verifier until every required "
                "hosted hash matches."
                if local_ready and not domain_verified
                else (
                    "Use the reviewer URLs. Public hash deployment is verified, but field validation and dollar "
                    "savings claims still require an external system owner."
                    if domain_verified
                    else "Regenerate the missing required local proof feeds before deploying."
                )
            ),
            "safe_deploy_command": safe_deploy_command,
            "deploy_bundle_feed_only_ready": bool(deploy_summary.get("feed_only_deploy_ready")),
            "deploy_bundle_archive": str(deploy_bundle.get("archive_path") or ""),
            "deploy_bundle_archive_sha256": str(deploy_bundle.get("archive_sha256") or ""),
        },
        "current_champion": champion_snapshot(),
        "feeds": feeds,
        "missing_required_local_feeds": [
            row["local_relative_path"] for row in missing_local
        ],
        "required_remote_missing_or_stale": [
            {
                "key": row["key"],
                "local_sha256": row["local_sha256"],
                "local_sha256_prefix": str(row["local_sha256"])[:12],
                "remote_reachable": bool(row.get("remote_reachable")),
                "remote_first_reachable_url": row.get("remote_first_reachable_url", ""),
                "remote_first_reachable_status": row.get("remote_first_reachable_status"),
                "remote_first_reachable_sha256": row.get("remote_first_reachable_sha256", ""),
                "remote_first_reachable_sha256_prefix": str(row.get("remote_first_reachable_sha256") or "")[:12],
                "remote_first_reachable_bytes": row.get("remote_first_reachable_bytes", 0),
                "diagnosis": (
                    "HOSTED_COPY_STALE"
                    if row.get("remote_reachable")
                    else "HOSTED_COPY_MISSING_OR_UNREACHABLE"
                ),
                "candidate_urls": [candidate["url"] for candidate in row["remote_candidates"]],
            }
            for row in remote_missing_or_stale
        ],
        "reviewer_urls": {
            "mission_control": f"{base}/mission_control.html",
            "grants_console": f"{base}/grants.html?grant_id=nsf_sbir_phase_i",
            "quant_lab": f"{base}/quant_lab.html",
            "proof_to_pilot": f"{base}/proof_to_pilot.html",
            "champion_feed_primary": f"{base}/data/champion_metric_gauntlet.json",
            "champion_feed_fallback": f"{base}/dashboard/data/champion_metric_gauntlet.json",
            "locked_source_baseline_replay_sweep": f"{base}/data/locked_source_baseline_replay_sweep.json",
            "champion_sample_expansion_and_economic_bridge": (
                f"{base}/data/champion_sample_expansion_and_economic_bridge.json"
            ),
            "field_validation_control_room": f"{base}/data/field_validation_control_room.json",
            "field_validation_outreach_board": f"{base}/data/field_validation_outreach_board.json",
            "live_domain_consolidation_audit": f"{base}/data/live_domain_consolidation_audit.json",
        },
        "publish_and_verify_runbook": [
            "python .\\code\\ops\\BUILD_CHAMPION_METRIC_GAUNTLET.py",
            "python .\\code\\ops\\BUILD_LOCKED_SOURCE_BASELINE_REPLAY_SWEEP.py",
            "python .\\code\\ops\\BUILD_CHAMPION_SAMPLE_EXPANSION_AND_ECONOMIC_BRIDGE.py",
            "python .\\code\\ops\\BUILD_FIELD_VALIDATION_CONTROL_ROOM.py",
            "python .\\code\\ops\\BUILD_FIELD_VALIDATION_OUTREACH_BOARD.py",
            "python .\\code\\ops\\BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py",
            "python .\\code\\ops\\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py --skip-live-check",
            "python .\\code\\ops\\BUILD_LIVE_DOMAIN_CONSOLIDATION_AUDIT.py",
            "python .\\code\\ops\\BUILD_LIVE_DOMAIN_PROOF_FEED_DEPLOY_BUNDLE.py",
            ".\\deploy\\PUSH_PROOF_FEEDS_TO_VPS.ps1 -DryRun",
            ".\\deploy\\PUSH_PROOF_FEEDS_TO_VPS.ps1",
            "python .\\code\\ops\\BUILD_LIVE_DOMAIN_DEPLOYMENT_FEED.py",
        ],
        "what_to_ask_next": [
            "Which required proof feed is missing or stale on the live domain?",
            "What exact URL should a reviewer open first?",
            "Which claim is safe once hosted hashes match?",
            "What still blocks field validation after deployment is verified?",
            "What buyer-authorized replay would turn this from internal proof into a field claim?",
        ],
    }
    payload["deployment_feed_sha256"] = stable_sha256(
        {
            "live_base": payload["live_base"],
            "summary": payload["summary"],
            "current_champion": payload["current_champion"],
            "feeds": [
                {
                    "key": row["key"],
                    "required": row["required"],
                    "local_sha256": row["local_sha256"],
                    "remote_hash_match": row["remote_hash_match"],
                    "remote_match_url": row["remote_match_url"],
                }
                for row in feeds
            ],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    champion = payload["current_champion"]
    lines = [
        "# Live Domain Deployment Feed",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Live base: `{payload['live_base']}`",
        "",
        "## Current Answer",
        "",
        summary["plain_english_answer"],
        "",
        "## Deployment State",
        "",
        f"- Required local feeds ready: `{summary['required_local_ready_count']}/{summary['required_feed_count']}`",
        f"- Required hosted feeds reachable: `{summary['required_remote_reachable_count']}/{summary['required_feed_count']}`",
        f"- Required hosted hash matches: `{summary['required_remote_hash_match_count']}/{summary['required_feed_count']}`",
        f"- Live-domain reviewer-ready: `{str(summary['live_domain_reviewer_ready']).lower()}`",
        f"- Domain deployment state: `{summary['domain_deployment_state']}`",
        "",
        "## Current Champion Snapshot",
        "",
        f"- Family: `{champion.get('family')}`",
        f"- Label: `{champion.get('label')}`",
        f"- Named baseline: `{champion.get('named_baseline')}`",
        f"- Holdout wins: `{champion.get('holdout_wins')}/{champion.get('holdout_count')}`",
        f"- Estimated rows replayed: `{champion.get('estimated_rows_replayed')}`",
        f"- Source systems: `{champion.get('source_system_count')}`",
        f"- Buyer-authorized field replay request ready: `{str(champion.get('buyer_authorized_field_replay_request_ready')).lower()}`",
        f"- Field-validation claim allowed: `{str(champion.get('field_validation_claim_allowed')).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(champion.get('real_dollar_savings_claim_allowed')).lower()}`",
        "",
        "## Feed Hash Table",
        "",
        "| Feed | Required | Local | Hosted Match | Match URL |",
        "|---|---:|---:|---:|---|",
    ]
    for row in payload["feeds"]:
        lines.append(
            "| "
            f"`{row['key']}` | "
            f"`{str(row['required']).lower()}` | "
            f"`{str(row['local_exists']).lower()}` | "
            f"`{str(row['remote_hash_match']).lower()}` | "
            f"{row['remote_match_url'] or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Reviewer URLs",
            "",
        ]
    )
    for key, url in payload["reviewer_urls"].items():
        lines.append(f"- `{key}`: {url}")
    lines.extend(
        [
            "",
            "## Publish And Verify Runbook",
            "",
        ]
    )
    for command in payload["publish_and_verify_runbook"]:
        lines.append(f"- `{command}`")
    lines.extend(
        [
            "",
            "## What To Ask Next",
            "",
        ]
    )
    for question in payload["what_to_ask_next"]:
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            payload["boundary"],
            "",
            f"Deployment feed SHA-256: `{payload['deployment_feed_sha256']}`",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build live-domain deployment verification feed.")
    parser.add_argument("--skip-live-check", action="store_true", help="Build local feed without probing the domain.")
    parser.add_argument("--timeout", type=int, default=10, help="Per-URL live-domain timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(check_live_domain=not args.skip_live_check, timeout=max(args.timeout, 1))
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["summary"]["plain_english_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
