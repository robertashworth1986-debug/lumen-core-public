from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

READINESS_JSON = OUT_OPS / "grant_submission_readiness_audit_latest.json"
DASHBOARD_FEED_JSON = OUT_OPS / "grant_dashboard_status_feed_latest.json"
PUBLIC_DASHBOARD_FEED_JSON = DASHBOARD_DATA / "grant_readiness_status.json"
HIGH_IMPACT_JSON = OUT_OPS / "lumencore_high_impact_goal_latest.json"
PUBLIC_HIGH_IMPACT_JSON = DASHBOARD_DATA / "lumencore_high_impact_goal.json"
HARBOR_GATE_JSON = OUT_OPS / "harbor_public_ais_gate_latest.json"
HARBOR_INJECTION_JSON = OUT_OPS / "harbor_ais_injection_benchmark_latest.json"
PROVENANCE_GATE_DOC = DOCS / "LIVE_BREADTH_PROVENANCE_GATE_CAPSULE_2026-06-21.md"

OUT_JSON = OUT_OPS / "public_visibility_packet_latest.json"
OUT_MD = DOCS / "PUBLIC_VISIBILITY_AND_SOURCE_AUTHORITY_2026-06-20.md"
DASHBOARD_JSON = DASHBOARD_DATA / "public_visibility_packet.json"


AUTHOR = {
    "name": "Robert Ashworth",
    "project": "LumenCore",
    "role": "Founder / independent builder",
    "public_repository": "https://github.com/robertashworth1986-debug/lumen-core-public",
    "public_site": "https://lumen-core.ai",
}

PRIMARY_SOURCES = [
    {
        "name": "DARPA DICE program page",
        "url": "https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence",
        "why_it_matters": "Primary public source for the DICE opportunity/research direction.",
    },
    {
        "name": "NOAA Office for Coastal Management AccessAIS",
        "url": "https://coast.noaa.gov/digitalcoast/tools/ais.html",
        "why_it_matters": "Primary public path for historical U.S. vessel-traffic AIS data access.",
    },
    {
        "name": "MarineCadastre AccessAIS",
        "url": "https://marinecadastre.gov/accessais/",
        "why_it_matters": "Official public AccessAIS surface for historical AIS downloads.",
    },
    {
        "name": "NOAA daily AIS bulk file used for pilot",
        "url": "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_01.zip",
        "why_it_matters": "Raw public AIS file acquired, hashed, profiled, and split on the external proof drive.",
    },
    {
        "name": "MarineCadastre AIS vessel traffic repository",
        "url": "https://github.com/ocm-marinecadastre/ais-vessel-traffic",
        "why_it_matters": "Public technical reference for analysis-ready AIS vessel traffic artifacts.",
    },
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
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def build_payload() -> dict[str, Any]:
    readiness = read_json(READINESS_JSON)
    dashboard = read_json(DASHBOARD_FEED_JSON)
    if not dashboard:
        dashboard = read_json(PUBLIC_DASHBOARD_FEED_JSON)
    if not readiness and dashboard:
        readiness = {
            "posture": dashboard.get("posture", "UNKNOWN"),
            "summary": dashboard.get("summary", {}),
        }
    high_impact = read_json(HIGH_IMPACT_JSON)
    if not high_impact:
        high_impact = read_json(PUBLIC_HIGH_IMPACT_JSON)
    harbor_gate = read_json(HARBOR_GATE_JSON)
    harbor_injection = read_json(HARBOR_INJECTION_JSON)
    summary = readiness.get("summary", {}) if isinstance(readiness.get("summary"), dict) else {}
    harbor = dashboard.get("harbor", {}) if isinstance(dashboard.get("harbor"), dict) else {}
    gate = harbor.get("public_ais_gate", {}) if isinstance(harbor.get("public_ais_gate"), dict) else {}
    if not harbor_gate and gate:
        harbor_gate = {"posture": gate.get("posture", "UNKNOWN")}
    if not harbor_injection:
        harbor_injection = (
            harbor.get("ais_injection_benchmark", {})
            if isinstance(harbor.get("ais_injection_benchmark"), dict)
            else {}
        )
    gate_checks = gate.get("gate_checks", {}) if isinstance(gate.get("gate_checks"), dict) else {}
    injection_ready = harbor_injection.get("posture") == "PUBLIC_AIS_INJECTION_BENCHMARK_READY"
    injection_result = harbor_injection.get("controlled_injection_benchmark", {})
    if not isinstance(injection_result, dict) or not injection_result:
        injection_result = harbor_injection
    best_baseline = (
        injection_result.get("baseline_suite", {})
        .get("best_single_axis_baseline", {})
        if isinstance(injection_result.get("baseline_suite", {}), dict)
        else {}
    )

    proof_claims = [
        {
            "claim": "DICE package is locally locked but portal/user gated.",
            "evidence": "DICE submission lock packet reports 0 local blockers, 7-page render packet, 12 visible URLs, and ROM cost boundary.",
            "boundary": "Does not approve BAAT upload, certify eligibility, validate cost, or replace human action-time approval.",
        },
        {
            "claim": "DICE now has a public-safe live-breadth replay evidence capsule.",
            "evidence": (
                "Frozen live-breadth replay uses 6 Kraken/EIA source files and 14 deterministic replay windows: "
                "safe-completion delta +0.0437, constraint-violation delta -0.1216, "
                "messages-per-safe-completion delta -2.8157, with false-rejection cost +0.0514."
            ),
            "boundary": (
                "Live rows are stress signals with deterministic derived labels. This does not prove DICE metric "
                "attainment, field validation, operational DoD performance, trading profit, award likelihood, or portal readiness."
            ),
        },
        {
            "claim": "Live-breadth frozen-delta evidence is now provenance-gated.",
            "evidence": (
                "Public-safe local gate reports 17 enabled live sources, 12 measured sources, 70.59% measured coverage, "
                "11 promoted live-measured source rows, and 8 context-only rows. The promoted live-measured value signal is "
                "$8,435/hour ($73,890,600/year); the much larger unmeasured/context surface is explicitly not promoted."
            ),
            "boundary": (
                "This is a provenance and claim-discipline gate. It does not prove actual customer savings, revenue, "
                "trading profit, grant merit, valuation, or field performance."
            ),
        },
        {
            "claim": "HarborSentinel now has public AIS data-readiness evidence.",
            "evidence": (
                "NOAA AIS raw ZIP acquired and hashed; 50,000-row development and 50,000-row validation splits frozen; "
                f"single-lane public AIS gate posture {harbor_gate.get('posture', gate.get('posture', 'UNKNOWN'))}."
            ),
            "boundary": "Does not establish HarborSentinel detection performance, ADS-B rights, radar validation, Navy/SSDS integration, or field validation.",
        },
        {
            "claim": "Top-five grant packets are locally ready but not submitted.",
            "evidence": f"Readiness audit reports {summary.get('local_blockers', 0)} local blockers and {summary.get('portal_user_blockers', 0)} portal/user gates across {summary.get('packages', 0)} packages.",
            "boundary": "Portal authority, compliance representations, cost review, teaming, and submit/certification actions remain unresolved.",
        },
        {
            "claim": "Public submission gates are explicitly mapped.",
            "evidence": (
                "docs/PUBLIC_SUBMISSION_GATE_MAP_2026-06-20.md separates reproducible evidence from portal authority, "
                "eligibility, compliance, cost, team, claim, and final submit gates."
            ),
            "boundary": (
                "The gate map is a public coordination artifact. It does not certify eligibility, approve a budget, "
                "prove compliance status, or submit any application."
            ),
        },
    ]
    if injection_ready:
        proof_claims.insert(
            2,
            {
                "claim": "HarborSentinel has a bounded public AIS controlled-injection benchmark.",
                "evidence": (
                    f"{injection_result.get('total_injected_segments', 0)} injected validation segments; "
                    f"motion-consistency recall {injection_result.get('motion_consistency_recall', 0)} versus "
                    f"speed-only baseline recall {injection_result.get('speed_only_baseline_recall', 0)} "
                    f"(lift {injection_result.get('recall_lift_vs_speed_only', 0)}); "
                    f"best single-axis baseline {best_baseline.get('name', 'n/a')} recall "
                    f"{best_baseline.get('recall', 'n/a')}."
                ),
                "boundary": (
                    "Controlled kinematic injections on public AIS validation data are not real adversary labels, "
                    "multi-source fusion, ADS-B/radar validation, Navy/SSDS integration, field performance, or operational suitability."
                ),
            },
        )
    proof_claims.insert(
        5 if injection_ready else 4,
        {
            "claim": "HarborSentinel now has a public AIS review-burden profile.",
            "evidence": (
                "Held-out validation queue: 48616 validation segments, 1742 natural candidates, candidate rate 0.0358, "
                "mean 145.167 candidates/hour, p95 158.7 candidates/hour, sparse-tier candidate rate 0.1191."
            ),
            "boundary": (
                "Natural candidate rates are unlabeled review queues, not precision, false-positive rates, real threat "
                "detection, field validation, operational suitability, award likelihood, or portal readiness."
            ),
        },
    )

    return {
        "generated_utc": now_utc(),
        "schema": "public_visibility_packet_v1",
        "author": AUTHOR,
        "positioning": {
            "one_line": (
                "Robert Ashworth is building LumenCore, a proof-driven adaptive orchestration stack "
                "that turns complex-system claims into reproducible evidence, bounded dashboards, and grant-ready artifacts."
            ),
            "reviewer_hook": (
                "The work is strongest where the evidence trail is visible: frozen manifests, held-out data splits, "
                "rendered grant packets, public-source registries, and explicit non-claim boundaries."
            ),
            "tone_rule": "Lead with proof and boundaries; let ambition show through disciplined evidence.",
        },
        "primary_sources": PRIMARY_SOURCES,
        "proof_claims": proof_claims,
        "source_backed_artifacts": {
            "grant_readiness_feed": "out/ops/grant_dashboard_status_feed_latest.json",
            "high_impact_goal": "out/ops/lumencore_high_impact_goal_latest.json",
            "dice_lock_packet": "out/ops/dice_submission_lock_packet_latest.json",
            "dice_public_live_breadth_replay": "docs/DICE_PUBLIC_LIVE_BREADTH_REPLAY_CAPSULE_2026-06-21.md",
            "live_breadth_provenance_gate": str(PROVENANCE_GATE_DOC.relative_to(ROOT)).replace("\\", "/"),
            "harbor_public_ais_gate": "out/ops/harbor_public_ais_gate_latest.json",
            "harbor_ais_injection_benchmark": "out/ops/harbor_ais_injection_benchmark_latest.json",
            "harbor_public_ais_review_burden": "docs/HARBOR_PUBLIC_AIS_REVIEW_BURDEN_CAPSULE_2026-06-21.md",
            "harbor_heldout_splits": "out/ops/harbor_ais_heldout_splits_latest.json",
            "harbor_ais_acquisition": "out/ops/harbor_ais_pilot_acquisition_latest.json",
            "public_submission_gate_map": "docs/PUBLIC_SUBMISSION_GATE_MAP_2026-06-20.md",
            "public_support_readiness": "docs/PUBLIC_SUPPORT_AND_REVIEWER_READINESS_2026-06-20.md",
        },
        "reviewer_path": [
            "Open the public-safe LumenCore repository/site first for reproducibility posture.",
            "Read the source authority packet and claim boundaries before any performance claim.",
            "Inspect the DICE lock packet for local package hygiene and remaining BAAT/SAM/human gates.",
            "Inspect the DICE public live-breadth replay capsule as stress-replay evidence, not field validation.",
            "Inspect the live-breadth provenance gate to separate promoted live-measured rows from context-only rows.",
            "Inspect the Harbor AIS gate for public-data readiness, split hashes, and validation boundaries.",
            "Inspect the Harbor controlled-injection benchmark only as bounded public AIS detector-vs-baseline evidence.",
            "Inspect the Harbor public AIS review-burden capsule only as an unlabeled queue/workload estimate.",
            "Inspect the public submission gate map to see what still requires human, legal/compliance, portal, or cost authority.",
            "Inspect the public support readiness packet to route help through official support lanes without sharing private portal data.",
            "Only then map the evidence into DICE/Harbor proposal language.",
        ],
        "outreach_copy": {
            "linkedin_short": (
                "I am building LumenCore as a proof-driven orchestration stack for complex systems. "
                "The latest public-safe milestones: DICE now has a frozen live-breadth replay capsule; live-breadth frozen deltas are provenance-gated; "
                "and HarborSentinel has public NOAA AIS held-out splits, a bounded controlled-injection benchmark, and an unlabeled review-burden profile. "
                "I am looking for serious reviewers, agency-aligned collaborators, "
                "and teams that care about evidence before claims."
            ),
            "reviewer_email_subject": "LumenCore proof packet: DICE local lock + public AIS HarborSentinel gate",
            "reviewer_email_body": (
                "I am sharing a public-safe proof packet for LumenCore. It includes a locally locked DARPA DICE abstract package, "
                "a public-safe DICE live-breadth replay capsule, a live-breadth provenance gate, "
                "a HarborSentinel public AIS data-readiness gate built from NOAA AIS, a bounded controlled-injection benchmark, "
                "an unlabeled review-burden profile, and explicit boundaries on what the evidence does "
                "and does not prove. I would value technical review focused on reproducibility, claim discipline, and agency fit."
            ),
            "goal_prompt": (
                "Operate as LumenCore's proof-and-traction engine. Every cycle must convert ambition into a verifiable artifact: "
                "source, hash, benchmark, split, dashboard feed, grant packet, outreach asset, or blocker board. Maximize respected visibility "
                "by publishing only defensible claims, preserving private submission materials, and making the evidence so clean that serious "
                "reviewers can audit it without a sales pitch. Do not chase fame directly; build the proof surface that makes attention rational."
            ),
        },
        "do_not_claim": [
            "Guaranteed awards, funding, wealth, or fame.",
            "CMMC Level 2 certification, clearance, export determination, or portal authority without current proof.",
            "Harbor/Navy/SSDS/field performance from public AIS single-lane data-readiness or controlled-injection results.",
            "Trading profitability or institutional-grade execution from governance audits.",
            "Partner, customer, investor, or agency endorsement without written confirmation.",
        ],
        "lumenstock_boundary": high_impact.get("lumenstock", {}).get("interpretation", ""),
        "gate_checks": gate_checks,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Public Visibility and Source Authority Packet",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Identity",
        "",
        f"- Name: {payload['author']['name']}",
        f"- Project: {payload['author']['project']}",
        f"- Role: {payload['author']['role']}",
        f"- Public site: {payload['author']['public_site']}",
        f"- Public repository: {payload['author']['public_repository']}",
        "",
        "## Positioning",
        "",
        payload["positioning"]["one_line"],
        "",
        payload["positioning"]["reviewer_hook"],
        "",
        f"Tone rule: {payload['positioning']['tone_rule']}",
        "",
        "## Primary Sources",
        "",
    ]
    for source in payload["primary_sources"]:
        lines.append(f"- [{source['name']}]({source['url']}): {source['why_it_matters']}")
    lines.extend(["", "## Proof Claims", ""])
    for item in payload["proof_claims"]:
        lines.extend(
            [
                f"### {item['claim']}",
                "",
                f"Evidence: {item['evidence']}",
                "",
                f"Boundary: {item['boundary']}",
                "",
            ]
        )
    lines.extend(["## Reviewer Path", ""])
    lines.extend(f"{idx}. {step}" for idx, step in enumerate(payload["reviewer_path"], start=1))
    lines.extend(["", "## Source Artifacts", ""])
    for name, path in payload["source_backed_artifacts"].items():
        lines.append(f"- {name}: `{path}`")
    lines.extend(["", "## Outreach Copy", "", "### LinkedIn Short", "", payload["outreach_copy"]["linkedin_short"], ""])
    lines.extend(
        [
            "### Reviewer Email",
            "",
            f"Subject: {payload['outreach_copy']['reviewer_email_subject']}",
            "",
            payload["outreach_copy"]["reviewer_email_body"],
            "",
            "### Goal Prompt",
            "",
            payload["outreach_copy"]["goal_prompt"],
            "",
            "## Do Not Claim",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["do_not_claim"])
    if payload.get("lumenstock_boundary"):
        lines.extend(["", "## LumenStock Boundary", "", payload["lumenstock_boundary"]])
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
                "proof_claims": len(payload["proof_claims"]),
                "sources": len(payload["primary_sources"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
