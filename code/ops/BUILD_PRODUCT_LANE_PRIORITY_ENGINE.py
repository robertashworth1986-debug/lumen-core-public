from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "product_lane_priority_v1.json"
OUT_JSON = ROOT / "dashboard" / "data" / "product_lane_priority_engine_20260718.json"
OUT_MD = ROOT / "docs" / "PRODUCT_LANE_PRIORITY_ENGINE_2026-07-18.md"
MINDWISE_MD = ROOT / "docs" / "MINDWISE_PAID_DESIGN_PARTNER_PILOT_2026-07-18.md"
MINDWISE_EMAIL = ROOT / "docs" / "MINDWISE_DESIGN_PARTNER_FOLLOWUP_EMAIL_2026-07-18.txt"
BUNDLE_MANIFEST = ROOT / "docs" / "receipts" / "PRODUCT_LANE_PRIORITY_BUNDLE_MANIFEST_2026-07-18.json"
MINDWISE_DEMO_FEED = ROOT / "dashboard" / "data" / "mindwise_healthcare_candidate_feed_20260718.json"

RUN_IDS = (
    "20260505T082948Z",
    "20260505T104706Z",
    "20260505T121657Z",
    "20260511T175644Z",
    "20260526T050639Z",
)
RUN_ROOT = ROOT / "dashboard" / "evidence" / "runs"
RAW_RUN_ROOT = ROOT / "out" / "master_universe_v2"
HEALTHCARE_FEED = ROOT / "out" / "ops" / "healthcare_grants_engine" / "healthcare_website_feed_latest.json"

BOUNDARY = (
    "Product-lane priority engine. Scores are a transparent founder strategy heuristic, not market valuation, "
    "patentability, customer acceptance, award probability, field validation, or guaranteed revenue."
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_receipt(path: Path) -> dict[str, Any]:
    relative_path = str(path.relative_to(ROOT)).replace("\\", "/")
    if not path.is_file():
        return {"path": relative_path, "exists": False, "bytes": 0, "sha256": None}
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {
        "path": relative_path,
        "exists": True,
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def build_bundle_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    paths = (
        CONFIG,
        Path(__file__).resolve(),
        OUT_JSON,
        OUT_MD,
        MINDWISE_MD,
        MINDWISE_EMAIL,
        ROOT / "dashboard" / "js" / "luma_healthcare_grants_embed.js",
        ROOT / "dashboard" / "embed" / "healthcare_grants_widget_example.html",
        ROOT / "dashboard" / "embed" / "mindwise_premium_flow_demo.html",
        ROOT / "code" / "ops" / "HEALTHCARE_WEBSITE_EMBED_PLAYBOOK.md",
        ROOT / "tests" / "test_product_lane_priority_engine.py",
        MINDWISE_DEMO_FEED,
    )
    receipts = [file_receipt(path) for path in paths]
    manifest: dict[str, Any] = {
        "schema": "product_lane_priority_bundle_manifest_v1",
        "generated_utc": payload["generated_utc"],
        "product_lane_priority_sha256": payload["product_lane_priority_sha256"],
        "all_artifacts_present": all(receipt["exists"] for receipt in receipts),
        "artifact_count": len(receipts),
        "artifacts": receipts,
        "boundary": (
            "File receipts prove byte identity and presence only. They do not prove eligibility, correctness, "
            "independent validation, customer acceptance, award probability, or commercial value."
        ),
    }
    manifest["manifest_payload_sha256"] = stable_hash(manifest)
    return manifest


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def audit_run(run_id: str) -> dict[str, Any]:
    run_dir = RUN_ROOT / run_id
    summary = read_json(run_dir / "summary.json")
    scorecard_path = run_dir / "UNDENIABLE_SCORECARD_V2.md"
    scorecard = scorecard_path.read_text(encoding="utf-8", errors="replace") if scorecard_path.exists() else ""

    model_rows: Counter[str] = Counter()
    valid_rows: Counter[str] = Counter()
    error_rows: Counter[str] = Counter()
    results_path = run_dir / "results.csv"
    if results_path.exists():
        with results_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                model = str(row.get("model") or "unknown")
                model_rows[model] += 1
                if parse_float(row.get("rmse")) is not None:
                    valid_rows[model] += 1
                else:
                    error_rows[model] += 1

    failures = {
        model: {
            "invalid_rows": int(error_rows[model]),
            "total_rows": int(model_rows[model]),
        }
        for model in sorted(model_rows)
        if error_rows[model]
    }
    all_models_complete = bool(model_rows) and not failures
    raw_dir = RAW_RUN_ROOT / run_id / "raw"
    raw_count = len(list(raw_dir.glob("*.csv"))) if raw_dir.exists() else 0
    scorecard_calls_walk_forward = "walk-forward" in scorecard.lower()

    return {
        "run_id": run_id,
        "datasets_succeeded": int(summary.get("n_datasets_succeeded") or 0),
        "attempted_datasets": int(summary.get("n_datasets_in_universe") or 0),
        "models_reported": sorted(model_rows),
        "model_count": len(model_rows),
        "all_models_complete": all_models_complete,
        "model_failures": failures,
        "raw_csv_count": raw_count,
        "dashboard_manifest_note": (
            "Dashboard copy hashes six summary artifacts; raw CSVs remain in the canonical out/master_universe_v2 run."
        ),
        "evaluation_design": "single_chronological_80_20_holdout",
        "scorecard_calls_method_walk_forward": scorecard_calls_walk_forward,
        "method_language_status": "stale_overstatement" if scorecard_calls_walk_forward else "bounded",
        "reviewer_use": (
            "bounded_exploratory_reference"
            if all_models_complete
            else "blocked_from_comparative_headline"
        ),
    }


def audit_healthcare_feed(at: datetime) -> dict[str, Any]:
    feed = read_json(HEALTHCARE_FEED)
    generated_text = str(feed.get("generated_utc") or "")
    generated: datetime | None = None
    try:
        generated = datetime.fromisoformat(generated_text.replace("Z", "+00:00"))
    except ValueError:
        pass
    if generated is not None and generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    age_hours = (at - generated).total_seconds() / 3600 if generated is not None else None
    records = feed.get("records") if isinstance(feed.get("records"), list) else []
    is_fresh = age_hours is not None and 0 <= age_hours <= 24
    return {
        "path": str(HEALTHCARE_FEED.relative_to(ROOT)).replace("\\", "/"),
        "generated_utc": generated_text,
        "record_count": len(records),
        "freshness_sla_hours": 24,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
        "freshness_label_allowed": is_fresh,
        "eligibility_label_allowed": False,
        "submission_ready_label_allowed": False,
        "status": "fresh" if is_fresh else "stale_or_unverifiable",
        "boundary": (
            "Freshness applies only to the candidate source feed. Relevance scores do not establish applicant "
            "eligibility, current requirements, submission readiness, or award probability."
        ),
    }


def build_mindwise_demo_feed() -> dict[str, Any]:
    source = read_json(HEALTHCARE_FEED)
    source_records = source.get("records") if isinstance(source.get("records"), list) else []
    records = [row for row in source_records[:6] if isinstance(row, dict)]

    def closes_within(row: dict[str, Any], days: int) -> bool:
        value = parse_float(row.get("days_to_close"))
        return value is not None and 0 <= value <= days

    snapshot: dict[str, Any] = {
        "schema": "mindwise_healthcare_candidate_feed_demo_v1",
        "generated_utc": source.get("generated_utc"),
        "source": source.get("source", {}),
        "summary": {
            "close_7_days": sum(1 for row in records if closes_within(row, 7)),
            "close_14_days": sum(1 for row in records if closes_within(row, 14)),
            "immediate_or_fast": sum(
                1
                for row in records
                if str(row.get("action") or "").upper() in {"IMMEDIATE_SUBMIT", "FAST_TRACK"}
            ),
            "snapshot_records": len(records),
        },
        "records": records,
        "boundary": (
            "Frozen demonstration snapshot from a source-linked candidate feed. Scores and queue labels reflect "
            "configured relevance and urgency only; they do not establish organizational eligibility, current "
            "requirements, submission readiness, or award probability."
        ),
    }
    snapshot["snapshot_payload_sha256"] = stable_hash(snapshot)
    return snapshot


def rank_lanes(config: dict[str, Any]) -> list[dict[str, Any]]:
    weights = config.get("weights") if isinstance(config.get("weights"), dict) else {}
    if round(sum(float(value) for value in weights.values()), 8) != 100:
        raise ValueError("product-lane weights must sum to 100")

    ranked: list[dict[str, Any]] = []
    for lane in config.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        scores = lane.get("scores") if isinstance(lane.get("scores"), dict) else {}
        missing_dimensions = sorted(set(weights) - set(scores))
        if missing_dimensions:
            raise ValueError(f"{lane.get('id')} missing score dimensions: {missing_dimensions}")
        weighted = sum(float(scores[key]) * float(weight) for key, weight in weights.items()) / 100
        evidence_paths = [str(value) for value in lane.get("evidence_paths", [])]
        evidence_checks = [
            {"path": path, "exists": (ROOT / path).exists()}
            for path in evidence_paths
        ]
        evidence_coverage = (
            sum(1 for item in evidence_checks if item["exists"]) / len(evidence_checks)
            if evidence_checks
            else 0.0
        )
        ranked.append(
            {
                **lane,
                "strategy_score": round(weighted, 2),
                "evidence_coverage": round(evidence_coverage, 4),
                "evidence_checks": evidence_checks,
            }
        )
    ranked.sort(key=lambda row: (-float(row["strategy_score"]), str(row["id"])))
    for index, lane in enumerate(ranked, start=1):
        lane["rank"] = index
    return ranked


def mindwise_pilot() -> dict[str, Any]:
    return {
        "name": "MindWise x ProofLock Opportunity Operations - 30-day design-partner pilot",
        "buyer": "Kishore Tummala, CEO and Founder, MindWise Health",
        "scope_boundary": "Phase 1 uses opportunity, workflow, and synthetic/sample organization data only; no PHI.",
        "commercial_posture": "Paid design-partner pilot; credit the agreed pilot fee toward an annual subscription if acceptance gates pass.",
        "week_1_baseline": [
            "Measure current time from opportunity discovery to pursue/no-pursue decision.",
            "Measure current time from pursue decision to reviewer-ready draft.",
            "Count eligibility reversals, missing attachments, and missed internal review dates.",
            "Lock the source portals, eligibility rubric, roles, and final human approval gate.",
        ],
        "weeks_2_to_4": [
            "Refresh permitted opportunity sources and rank candidates with evidence links.",
            "Generate source-grounded draft structures and an attachment/blocker ledger.",
            "Route unresolved facts to named owners; abstain instead of guessing.",
            "Emit a replayable receipt for every shortlist, draft, and preflight decision.",
        ],
        "acceptance_metrics": [
            {"metric": "qualified opportunity precision", "definition": "buyer-approved qualified matches / reviewed matches"},
            {"metric": "time to pursue decision", "definition": "median elapsed time from discovery to documented decision"},
            {"metric": "time to reviewer-ready draft", "definition": "median elapsed time from pursue decision to internal review state"},
            {"metric": "preflight defect rate", "definition": "missing or contradictory required items per package at review"},
            {"metric": "deadline reliability", "definition": "packages reaching internal review by the buyer-set cutoff / pursued packages"},
            {"metric": "provenance completeness", "definition": "material claims with a traceable source / material claims reviewed"},
        ],
        "human_gates": [
            "buyer confirms organizational eligibility",
            "buyer approves claims and representations",
            "authorized official certifies and submits",
            "no system action bypasses portal attestations or signatures",
        ],
        "go_no_go": "Convert only if the buyer confirms a measured workflow improvement and the evidence/eligibility error rate remains within the agreed threshold.",
    }


def build_payload(at: datetime | None = None) -> dict[str, Any]:
    at = at or now_utc()
    config = read_json(CONFIG)
    ranked = rank_lanes(config)
    run_audits = [audit_run(run_id) for run_id in RUN_IDS]
    comparable = [row for row in run_audits if row["all_models_complete"]]
    best_exploratory = max(comparable, key=lambda row: row["datasets_succeeded"], default={})
    pilot = mindwise_pilot()
    feed_audit = audit_healthcare_feed(at)
    allowed_now = [
        "working grant-ranking, draft-assembly, preflight, and receipt components exist",
        "five historical benchmark runs and raw source directories exist",
        "the 673-dataset run is a bounded exploratory single-holdout reference",
        "a paid design-partner pilot can measure workflow improvement",
    ]
    if feed_audit["freshness_label_allowed"]:
        allowed_now.append(
            "the healthcare candidate feed was refreshed within its 24-hour SLA; freshness does not establish eligibility"
        )
    blocked_now = [
        "organizational eligibility from relevance scores alone",
        "urgent or priority labels as authorization to apply or submit",
        "prospective router superiority until train-only features pass",
        "field validation or realized savings",
        "guaranteed awards or autonomous final submission",
        "patentability",
    ]
    if not feed_audit["freshness_label_allowed"]:
        blocked_now.insert(0, "current-feed language until the candidate feed is refreshed within the freshness SLA")

    payload: dict[str, Any] = {
        "schema": "product_lane_priority_engine_v1",
        "generated_utc": at.isoformat(),
        "boundary": BOUNDARY,
        "weights": config.get("weights", {}),
        "ranking": ranked,
        "recommendation": {
            "commercial_lane": ranked[0]["id"] if ranked else None,
            "commercial_offer": ranked[0]["offer"] if ranked else None,
            "technical_wedge": "prooflock_evidence_router_api",
            "technical_wedge_boundary": (
                "The defensible target is not generic grant search or AI writing. It is a constrained router that "
                "uses train-only or source-available features, abstains when eligibility or evidence gates fail, "
                "and emits replayable policy/source receipts. Patentability still requires a dedicated search."
            ),
            "first_design_partner": "MindWise Health",
            "why_now": (
                "A warm founder relationship, a working vertical demo, and a current candidate feed exist. "
                "The feed still requires buyer-specific eligibility review and measured pilot acceptance gates."
            ),
        },
        "evidence_audit": {
            "runs": run_audits,
            "best_bounded_exploratory_run": best_exploratory.get("run_id"),
            "best_bounded_exploratory_dataset_count": best_exploratory.get("datasets_succeeded"),
            "router_risk": (
                "The historical meta-router extracts features from each full series, including the benchmark test "
                "window. Cross-dataset CV does not remove that within-series look-ahead. Rebuild features from each "
                "training window as train-only inputs before making prospective routing claims."
            ),
            "latest_run_blocker": (
                "Run 20260526T050639Z is blocked from comparative headline use because i_sarima has no valid RMSE "
                "on all 1,118 datasets while the scorecard still describes a classical comparison."
            ),
            "healthcare_feed": feed_audit,
        },
        "market_boundary": {
            "crowded_features": [
                "grant matching and tracking",
                "AI-assisted proposal drafting",
                "grant database search and APIs",
                "grantmaker workflow and review management",
            ],
            "official_product_sources_checked_2026_07_18": [
                "https://www.instrumentl.com/product-overview",
                "https://grantable.co/",
                "https://ops.opengrants.io/api-docs",
                "https://www.submittable.com/solutions/grants",
            ],
            "inference": (
                "Generic grant finding/filling is not a defensible category claim. Lead with evidence-bound "
                "eligibility, deterministic abstention, deadline controls, and replayable submission receipts."
            ),
        },
        "mindwise_pilot": pilot,
        "claim_controls": {
            "allowed_now": allowed_now,
            "blocked_now": blocked_now,
        },
    }
    payload["product_lane_priority_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Product Lane Priority Engine",
        "",
        f"Generated: `{payload['generated_utc']}`",
        "",
        f"> {payload['boundary']}",
        "",
        "## Decision",
        "",
        "Build and sell **ProofLock Opportunity Operations** first. Use the **ProofLock Evidence Router API** as the narrower technical wedge. Keep LumaScout as a later vertical after a forward outcome study.",
        "",
        "## Ranked Lanes",
        "",
        "| Rank | Lane | Strategy score | Evidence present | First validation |",
        "|---:|---|---:|---:|---|",
    ]
    for lane in payload["ranking"]:
        lines.append(
            f"| {lane['rank']} | {lane['name']} | {lane['strategy_score']:.2f} | "
            f"{lane['evidence_coverage'] * 100:.0f}% | {lane['first_validation']} |"
        )

    audit = payload["evidence_audit"]
    feed = audit["healthcare_feed"]
    lines.extend(
        [
            "",
            "## Evidence Audit",
            "",
            f"- Best bounded exploratory run: `{audit['best_bounded_exploratory_run']}` with `{audit['best_bounded_exploratory_dataset_count']}` datasets.",
            f"- Latest-run blocker: {audit['latest_run_blocker']}",
            f"- Router blocker: {audit['router_risk']}",
            f"- MindWise candidate feed: `{feed['status']}`; age `{feed['age_hours']}` hours; freshness label allowed `{str(feed['freshness_label_allowed']).lower()}`; eligibility label allowed `{str(feed['eligibility_label_allowed']).lower()}`.",
            f"- Feed boundary: {feed['boundary']}",
            "",
            "## Commercial Wedge",
            "",
            payload["recommendation"]["technical_wedge_boundary"],
            "",
            "The first recurring product is an organization subscription for monitored opportunities, controlled collaboration, evidence storage, and preflight. Final certifications and submissions remain with the authorized human.",
            "",
            "## MindWise Pilot",
            "",
            f"- Scope: {payload['mindwise_pilot']['scope_boundary']}",
            f"- Commercial posture: {payload['mindwise_pilot']['commercial_posture']}",
            f"- Go/no-go: {payload['mindwise_pilot']['go_no_go']}",
            "",
            "Acceptance metrics:",
        ]
    )
    for item in payload["mindwise_pilot"]["acceptance_metrics"]:
        lines.append(f"- **{item['metric']}**: {item['definition']}")
    lines.extend(
        [
            "",
            "## Claim Gates",
            "",
            "Allowed now:",
        ]
    )
    lines.extend(f"- {value}" for value in payload["claim_controls"]["allowed_now"])
    lines.extend(["", "Blocked now:"])
    lines.extend(f"- {value}" for value in payload["claim_controls"]["blocked_now"])
    lines.extend(["", "## Receipt", "", f"SHA-256: `{payload['product_lane_priority_sha256']}`"])
    return "\n".join(lines)


def render_mindwise_brief(payload: dict[str, Any]) -> str:
    pilot = payload["mindwise_pilot"]
    lines = [
        "# MindWise x ProofLock Opportunity Operations",
        "",
        "## 30-Day Paid Design-Partner Pilot",
        "",
        "### Objective",
        "",
        "Measure whether an evidence-bound opportunity workflow can reduce administrative cycle time and package defects without making unsupported eligibility, award, or savings claims.",
        "",
        "### Boundary",
        "",
        pilot["scope_boundary"],
        "",
        "### Week 1: Lock the Baseline",
        "",
    ]
    lines.extend(f"- {item}" for item in pilot["week_1_baseline"])
    lines.extend(["", "### Weeks 2-4: Run the Pilot", ""])
    lines.extend(f"- {item}" for item in pilot["weeks_2_to_4"])
    lines.extend(["", "### Acceptance Metrics", ""])
    lines.extend(f"- **{item['metric']}**: {item['definition']}" for item in pilot["acceptance_metrics"])
    lines.extend(["", "### Human Authority Gates", ""])
    lines.extend(f"- {item}" for item in pilot["human_gates"])
    lines.extend(
        [
            "",
            "### Commercial Path",
            "",
            pilot["commercial_posture"],
            "",
            "No value or savings figure is quoted until MindWise supplies or approves the baseline inputs and the pilot produces a traceable measurement.",
        ]
    )
    return "\n".join(lines)


def render_mindwise_email() -> str:
    return "\n".join(
        [
            "Subject: MindWise x Luma: measurable 30-day grant-operations pilot",
            "",
            "Hi Kishore,",
            "",
            "I appreciated your earlier response to the MindWise grant-flow demo. I took a harder look at what is actually differentiated and ready to measure.",
            "",
            "The strongest next step is not another broad AI-writing demo. It is a bounded 30-day design-partner pilot for opportunity operations: permitted-source monitoring, evidence-linked eligibility review, reviewer-ready draft structure, attachment/blocker preflight, and a replayable receipt for every material decision. Final certifications and submissions remain with your authorized team.",
            "",
            "In week one, we would measure your current workflow and lock the baseline. During the pilot we would track qualified-match precision, time to pursue/no-pursue, time to reviewer-ready draft, preflight defects, deadline reliability, and provenance completeness. Phase 1 would use no PHI.",
            "",
            "If the measured results do not justify continuing, we stop. If they do, we convert the proven workflow into a MindWise subscription or customer-facing add-on under terms we agree together.",
            "",
            "Would you be open to a 20-minute scoping call next week to choose one workflow and one baseline?",
            "",
            "Respectfully,",
            "Robert Ashworth",
        ]
    )


def main() -> int:
    payload = build_payload()
    demo_feed = build_mindwise_demo_feed()
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    write_text(MINDWISE_MD, render_mindwise_brief(payload))
    write_text(MINDWISE_EMAIL, render_mindwise_email())
    write_json(MINDWISE_DEMO_FEED, demo_feed)
    manifest = build_bundle_manifest(payload)
    write_json(BUNDLE_MANIFEST, manifest)
    print(json.dumps({
        "output_json": str(OUT_JSON),
        "output_markdown": str(OUT_MD),
        "mindwise_brief": str(MINDWISE_MD),
        "mindwise_email_draft": str(MINDWISE_EMAIL),
        "mindwise_demo_feed": str(MINDWISE_DEMO_FEED),
        "bundle_manifest": str(BUNDLE_MANIFEST),
        "top_lane": payload["recommendation"]["commercial_lane"],
        "sha256": payload["product_lane_priority_sha256"],
        "bundle_manifest_sha256": manifest["manifest_payload_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
