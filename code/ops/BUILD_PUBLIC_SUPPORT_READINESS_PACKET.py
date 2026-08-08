from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

GRANT_FEED_JSON = OUT_OPS / "grant_dashboard_status_feed_latest.json"
PUBLIC_GRANT_FEED_JSON = DASHBOARD_DATA / "grant_readiness_status.json"
PUBLIC_VISIBILITY_JSON = OUT_OPS / "public_visibility_packet_latest.json"
PUBLIC_VISIBILITY_DASHBOARD_JSON = DASHBOARD_DATA / "public_visibility_packet.json"
PROVENANCE_GATE_JSON = DASHBOARD_DATA / "live_breadth_provenance_gate.json"

OUT_JSON = OUT_OPS / "public_support_readiness_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "public_support_readiness_packet.json"
OUT_MD = DOCS / "PUBLIC_SUPPORT_AND_REVIEWER_READINESS_2026-06-20.md"


BOUNDARY = (
    "This is a public coordination packet for reviewers and support organizations. "
    "It does not prove portal authority, certify eligibility or CMMC/SPRS status, "
    "approve costs, create legal representation, submit an application, or make "
    "trading or investment claims."
)

OFFICIAL_SUPPORT_LANES = [
    {
        "id": "apex_federal_contracting",
        "name": "SBA federal contracting assistance / APEX Accelerator path",
        "url": "https://www.sba.gov/local-assistance/federal-contracting-assistance",
        "public_ask": "Review federal portal readiness, submitter authority, registrations, and representation boundaries.",
        "helps_with": ["DICE", "HarborSentinel", "MissionWeave", "NV065"],
    },
    {
        "id": "dod_osbp_cyber_resources",
        "name": "DoD OSBP cybersecurity resources / Project Spectrum path",
        "url": "https://business.defense.gov/Programs/Cyber-Security-Resources/",
        "public_ask": "Clarify CMMC/SPRS/PIEE facts and the evidence needed before any cybersecurity representation.",
        "helps_with": ["HarborSentinel", "MissionWeave", "NV065"],
    },
    {
        "id": "uspto_patent_pro_bono",
        "name": "USPTO Patent Pro Bono Program",
        "url": "https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program",
        "public_ask": "Route urgent patent-deadline questions to a qualified patent attorney or agent.",
        "helps_with": ["Patent/legal rescue"],
    },
    {
        "id": "sbir_fast",
        "name": "SBIR.gov FAST support",
        "url": "https://www.sbir.gov/community/fast",
        "public_ask": "Find regional SBIR/STTR proposal coaching and agency-fit support.",
        "helps_with": ["DICE", "HarborSentinel", "NSF Project Pitch"],
    },
    {
        "id": "sbir_program_context",
        "name": "SBIR.gov program context",
        "url": "https://www.sbir.gov/about",
        "public_ask": "Ground public proposal language in SBIR/STTR purpose without implying awards or revenue.",
        "helps_with": ["DICE", "HarborSentinel", "NSF Project Pitch"],
    },
]

NO_SHARE = [
    "passwords, MFA codes, API keys, tokens, tax IDs, banking data, or private portal screenshots",
    "UEI, CAGE/NCAGE, non-public SAM screenshots, or private registry dumps",
    "unsupported claims of CMMC level, SPRS score, clearances, facilities, partners, customers, revenue, or field validation",
    "private grant upload files unless a safe channel and reviewer role are established",
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def build_package_snapshot(feed: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in feed.get("packages", []) or []:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "name": str(row.get("name", "")),
                "portal": str(row.get("portal", "")),
                "readiness": str(row.get("readiness", "")),
                "local_blockers": int(row.get("local_blockers", 0) or 0),
                "portal_user_blockers": int(row.get("portal_user_blockers", 0) or 0),
                "required_artifacts_present": int(row.get("required_artifacts_present", 0) or 0),
                "required_artifacts_total": int(row.get("required_artifacts_total", 0) or 0),
                "manifest_matched": int(row.get("manifest_matched", 0) or 0),
                "manifest_expected": int(row.get("manifest_expected", 0) or 0),
            }
        )
    return rows


def build_payload(
    grant_feed: dict[str, Any] | None = None,
    visibility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    grant_feed = grant_feed or read_json(GRANT_FEED_JSON) or read_json(PUBLIC_GRANT_FEED_JSON)
    visibility = (
        visibility
        or read_json(PUBLIC_VISIBILITY_JSON)
        or read_json(PUBLIC_VISIBILITY_DASHBOARD_JSON)
    )
    provenance_gate = read_json(PROVENANCE_GATE_JSON)
    provenance_metrics = (
        provenance_gate.get("public_safe_metrics", {})
        if isinstance(provenance_gate.get("public_safe_metrics"), dict)
        else {}
    )
    truth_chain = (
        provenance_gate.get("truth_chain_interpretation", {})
        if isinstance(provenance_gate.get("truth_chain_interpretation"), dict)
        else {}
    )
    summary = grant_feed.get("summary", {}) if isinstance(grant_feed.get("summary"), dict) else {}
    harbor = grant_feed.get("harbor", {}) if isinstance(grant_feed.get("harbor"), dict) else {}
    injection = harbor.get("ais_injection_benchmark", {}) if isinstance(harbor.get("ais_injection_benchmark"), dict) else {}

    return {
        "generated_utc": now_utc(),
        "schema": "public_support_readiness_packet_v1",
        "boundary": BOUNDARY,
        "public_posture": {
            "packages": int(summary.get("packages", 0) or 0),
            "local_blockers": int(summary.get("local_blockers", 0) or 0),
            "portal_user_blockers": int(summary.get("portal_user_blockers", 0) or 0),
            "submitted_by_feed": int(summary.get("submitted_by_feed", 0) or 0),
            "dashboard_signal": str(summary.get("dashboard_signal", "UNKNOWN")),
        },
        "package_snapshot": build_package_snapshot(grant_feed),
        "strong_public_evidence": [
            "DICE local package hygiene is tracked, and a public-safe live-breadth replay capsule summarizes 6 live-source files and 14 deterministic replay windows without publishing private portal materials.",
            (
                "The historical live-breadth snapshot is provenance-gated: "
                f"{provenance_metrics.get('measured_live_sources', 12)}/"
                f"{provenance_metrics.get('enabled_live_sources', 17)} live sources are measured, "
                f"{provenance_metrics.get('promoted_live_measured_source_rows', 11)} rows are promoted, "
                f"and {provenance_metrics.get('context_only_source_rows', 8)} rows remain context-only. "
                "Economic estimates are omitted; the snapshot is not current-runtime or performance proof."
            ),
            "HarborSentinel public AIS acquisition, held-out splits, and full-hash split preflight are tracked.",
            (
                "HarborSentinel controlled-injection benchmark is available as bounded detector-vs-baseline evidence "
                f"with posture {injection.get('posture', 'UNKNOWN')}."
            ),
            "HarborSentinel public AIS review-burden profile estimates natural validation queue load without claiming precision or false-positive rates.",
            "The public submission gate map separates proof from portal, compliance, cost, team, and submit gates.",
        ],
        "official_support_lanes": OFFICIAL_SUPPORT_LANES,
        "reviewer_requests": [
            "Challenge reproducibility and claim boundaries before proposal language is strengthened.",
            "Help convert portal and compliance unknowns into written factual confirmations.",
            "Review DICE and HarborSentinel agency fit without implying endorsement.",
            "Identify labeled or adjudicated validation sources that can improve HarborSentinel beyond controlled injections.",
            "Review cost assumptions only as planning estimates until a proper budget reviewer is involved.",
        ],
        "do_not_share": NO_SHARE,
        "do_not_claim": [
            "submitted, awarded, accepted, CMMC Level 2 certified, agency endorsed, partner committed, field validated, profit proven, institutional-grade, guaranteed funding, or guaranteed revenue",
        ],
        "source_artifacts": {
            "public_visibility_packet": "docs/PUBLIC_VISIBILITY_AND_SOURCE_AUTHORITY_2026-06-20.md",
            "dice_public_live_breadth_replay": "docs/DICE_PUBLIC_LIVE_BREADTH_REPLAY_CAPSULE_2026-06-21.md",
            "live_breadth_provenance_gate": "docs/LIVE_BREADTH_PROVENANCE_GATE_CAPSULE_2026-06-21.md",
            "live_breadth_provenance_gate_json": "dashboard/data/live_breadth_provenance_gate.json",
            "public_submission_gate_map": "docs/PUBLIC_SUBMISSION_GATE_MAP_2026-06-20.md",
            "harbor_public_ais_packet": "docs/HARBOR_PUBLIC_AIS_PROOF_PACKET_2026-06-20.md",
            "harbor_public_ais_review_burden": "docs/HARBOR_PUBLIC_AIS_REVIEW_BURDEN_CAPSULE_2026-06-21.md",
            "grant_dashboard_feed": "dashboard/data/grant_readiness_status.json",
        },
        "visibility_goal_prompt": (
            visibility.get("outreach_copy", {}).get("goal_prompt", "")
            if isinstance(visibility.get("outreach_copy"), dict)
            else ""
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Public Support And Reviewer Readiness",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## Public Posture",
        "",
    ]
    posture = payload["public_posture"]
    lines.extend(
        [
            f"- Packages tracked: {posture['packages']}",
            f"- Local blockers: {posture['local_blockers']}",
            f"- Portal/user blockers: {posture['portal_user_blockers']}",
            f"- Submitted by public feed: {posture['submitted_by_feed']}",
            f"- Dashboard signal: `{posture['dashboard_signal']}`",
            "",
            "## Package Snapshot",
            "",
            "| Package | Portal | Readiness | Local blockers | Portal/user blockers | Artifacts | Manifest matches |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in payload["package_snapshot"]:
        artifacts = f"{row['required_artifacts_present']}/{row['required_artifacts_total']}"
        manifests = f"{row['manifest_matched']}/{row['manifest_expected']}"
        lines.append(
            f"| {row['name']} | {row['portal']} | `{row['readiness']}` | "
            f"{row['local_blockers']} | {row['portal_user_blockers']} | {artifacts} | {manifests} |"
        )

    lines.extend(["", "## Strong Public Evidence", ""])
    lines.extend(f"- {item}" for item in payload["strong_public_evidence"])
    lines.extend(["", "## Official Support Lanes", ""])
    for lane in payload["official_support_lanes"]:
        helps = ", ".join(lane["helps_with"])
        lines.extend(
            [
                f"### {lane['name']}",
                "",
                f"- Source: {lane['url']}",
                f"- Public ask: {lane['public_ask']}",
                f"- Helps with: {helps}",
                "",
            ]
        )
    lines.extend(["## Reviewer Requests", ""])
    lines.extend(f"- {item}" for item in payload["reviewer_requests"])
    lines.extend(["", "## Do Not Share", ""])
    lines.extend(f"- {item}" for item in payload["do_not_share"])
    lines.extend(["", "## Do Not Claim", ""])
    lines.extend(f"- {item}" for item in payload["do_not_claim"])
    lines.extend(["", "## Source Artifacts", ""])
    for name, path in payload["source_artifacts"].items():
        lines.append(f"- {name}: `{path}`")
    if payload.get("visibility_goal_prompt"):
        lines.extend(["", "## Visibility Rule", "", payload["visibility_goal_prompt"]])
    return "\n".join(lines)


def write_payload(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    return payload


def main() -> int:
    payload = write_payload()
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "local_blockers": payload["public_posture"]["local_blockers"],
                "portal_user_blockers": payload["public_posture"]["portal_user_blockers"],
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
