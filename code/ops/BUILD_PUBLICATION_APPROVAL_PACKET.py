from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

PUBLIC_VISIBILITY_MD = DOCS / "PUBLIC_VISIBILITY_AND_SOURCE_AUTHORITY_2026-06-20.md"
GEOMETRY_AUDIT_JSON = OUT_OPS / "geometry_synthetic_live_coverage_audit_latest.json"
GEOMETRY_AUDIT_MD = DOCS / "GEOMETRY_SYNTHETIC_LIVE_COVERAGE_AUDIT_2026-06-23.md"

OUT_JSON = OUT_OPS / "publication_approval_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "publication_approval_packet.json"
OUT_MD = DOCS / "PUBLICATION_APPROVAL_PACKET_2026-06-23.md"

GITHUB_BRANCH = "geometry-coverage-audit-20260623"
GITHUB_PR_URL = (
    "https://github.com/robertashworth1986-debug/"
    "lumen-core-public/pull/new/geometry-coverage-audit-20260623"
)
PUBLIC_REPO_URL = "https://github.com/robertashworth1986-debug/lumen-core-public"
PUBLIC_SITE_URL = "https://lumen-core.ai"


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


def geometry_summary() -> dict[str, Any]:
    audit = read_json(GEOMETRY_AUDIT_JSON)
    summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
    if not summary:
        summary = {
            "registered_family_count": 75,
            "lane_count": 12,
            "synthetic_benchmark_result_count": 4,
            "proof_priority_candidate_count": 11,
            "test_spec_ready_no_result_count": 57,
            "field_validated_family_count": 0,
            "safe_answer_to_have_we_tested_all": (
                "No. The registered universe is ranked and mostly test-spec-ready, "
                "but only a small subset has generated benchmark evidence and none are field validated."
            ),
        }
    return summary


def build_linkedin_profile(summary: dict[str, Any]) -> dict[str, str]:
    headline = (
        "Founder, LumenCore | Proof-Driven AI Infrastructure | "
        "Geometry Benchmarking, Live-Source Evidence, Grant-Ready Systems"
    )
    about = (
        "I am building LumenCore, a proof-driven adaptive orchestration stack for complex systems. "
        "The work is organized around a simple discipline: synthetic benchmarks discover candidates, "
        "frozen live-data replay proves what survives, and field validation is required before real-world "
        "performance or dollar claims.\n\n"
        f"The current public geometry audit ranks {summary.get('registered_family_count', 0)} route/path "
        f"families across {summary.get('lane_count', 0)} lanes. It identifies "
        f"{summary.get('synthetic_benchmark_result_count', 0)} generated benchmark-result families, "
        f"{summary.get('proof_priority_candidate_count', 0)} proof-priority candidates, and "
        f"{summary.get('test_spec_ready_no_result_count', 0)} test-spec-ready families still awaiting "
        "full benchmark execution.\n\n"
        "I am looking for serious technical reviewers, agency-aligned collaborators, and pilot partners "
        "who care about reproducible evidence, bounded claims, and practical transition paths."
    )
    featured = (
        "Featured proof packet: LumenCore geometry synthetic/live coverage audit. "
        "It separates controlled benchmark discovery from live replay and field validation, so reviewers "
        "can see exactly what has been ranked, what has been tested, and what still needs validation."
    )
    return {"headline": headline, "about": about, "featured_link_caption": featured}


def build_posts(summary: dict[str, Any]) -> list[dict[str, str]]:
    geometry_post = (
        "I published a bounded LumenCore geometry coverage audit.\n\n"
        f"Current state: {summary.get('registered_family_count', 0)} route/path families ranked across "
        f"{summary.get('lane_count', 0)} lanes; "
        f"{summary.get('synthetic_benchmark_result_count', 0)} have generated benchmark-result evidence; "
        f"{summary.get('proof_priority_candidate_count', 0)} are proof-priority candidates; "
        f"{summary.get('field_validated_family_count', 0)} are field validated.\n\n"
        "The core rule is: synthetic discovers, live proves, field validation wins trust.\n\n"
        "This is not a claim of field validation, realized savings, trading profit, or universal superiority. "
        "It is a public evidence map showing what has been ranked, what needs live replay, and what should "
        "be tested next."
    )
    grant_post = (
        "LumenCore is being built around evidence before claims: source manifests, held-out splits, "
        "bounded benchmark results, dashboard feeds, and explicit non-claim boundaries.\n\n"
        "The latest public-safe work turns a broad geometry universe into a reviewer-readable proof queue: "
        "which families are synthetic winners, which are proof-priority candidates, which are only "
        "test-spec-ready, and which still need field validation.\n\n"
        "I am looking for reviewers and pilot partners who can help turn reproducible replay evidence into "
        "independent validation."
    )
    return [
        {
            "channel": "linkedin",
            "name": "Geometry coverage audit post",
            "status": "draft_needs_user_approval",
            "copy": geometry_post,
        },
        {
            "channel": "linkedin",
            "name": "Evidence-before-claims post",
            "status": "draft_needs_user_approval",
            "copy": grant_post,
        },
    ]


def build_channel_plan() -> list[dict[str, Any]]:
    return [
        {
            "channel": "GitHub",
            "priority": 1,
            "action": "Open pull request for the public-safe audit branch.",
            "url": GITHUB_PR_URL,
            "approval_required": False,
            "why": "Shows reproducible code, tests, and public-safe documentation.",
        },
        {
            "channel": "lumen-core.ai",
            "priority": 2,
            "action": "Add a public proof note linking to the geometry coverage audit and PR.",
            "url": PUBLIC_SITE_URL,
            "approval_required": True,
            "why": "Gives reviewers a stable landing page before social traffic.",
        },
        {
            "channel": "LinkedIn",
            "priority": 3,
            "action": "Publish one bounded proof post and update Featured link after user approval.",
            "url": "https://www.linkedin.com/",
            "approval_required": True,
            "why": "Best current professional surface for reviewers, collaborators, and agency-aligned network reach.",
        },
        {
            "channel": "Reviewer email/DM",
            "priority": 4,
            "action": "Send short reviewer note to selected technical reviewers or program-aligned contacts.",
            "url": "",
            "approval_required": True,
            "why": "Targeted review is more valuable than broad posting for grant deadlines.",
        },
        {
            "channel": "Evidence archive",
            "priority": 5,
            "action": "Stage only public-safe, non-secret proof packets after claim review.",
            "url": "",
            "approval_required": True,
            "why": "Useful later for citable artifacts, but too easy to over-publish private grant material today.",
        },
    ]


def build_reviewer_email(summary: dict[str, Any]) -> dict[str, str]:
    subject = "LumenCore public proof audit: geometry coverage and validation boundaries"
    body = (
        "Hello,\n\n"
        "I am sharing a public-safe LumenCore proof artifact for technical review. The new geometry "
        f"coverage audit ranks {summary.get('registered_family_count', 0)} route/path families across "
        f"{summary.get('lane_count', 0)} lanes and separates generated benchmark evidence from live replay "
        "and field validation.\n\n"
        "The purpose is not to claim final performance. The purpose is to make the evidence boundary "
        "auditable: what has been ranked, what has synthetic benchmark evidence, what is queued for live "
        "replay, and what still requires independent/field validation.\n\n"
        f"Public branch: {GITHUB_BRANCH}\n"
        f"Pull request draft URL: {GITHUB_PR_URL}\n"
        f"Public repo: {PUBLIC_REPO_URL}\n\n"
        "I would value review focused on reproducibility, baseline fairness, claim discipline, and which "
        "lane should be prioritized for live replay or pilot validation.\n\n"
        "Best,\n"
        "Robert Ashworth"
    )
    return {"subject": subject, "body": body}


def build_payload() -> dict[str, Any]:
    summary = geometry_summary()
    profile = build_linkedin_profile(summary)
    posts = build_posts(summary)
    payload = {
        "generated_utc": now_utc(),
        "schema": "publication_approval_packet_v1",
        "purpose": "Prepare exact public-safe publishing copy for user approval before LinkedIn/site/email actions.",
        "publication_policy": {
            "approval_required_before_live_profile_or_social_changes": True,
            "no_auto_posting": True,
            "no_private_grant_uploads": True,
            "no_secret_material": True,
            "claim_boundary": (
                "Public copy may discuss ranked families, generated benchmark evidence, proof queues, "
                "and validation requirements. It must not claim field validation, realized savings, trading "
                "profit, funding guarantees, agency endorsement, or award certainty."
            ),
        },
        "github": {
            "branch": GITHUB_BRANCH,
            "pr_url": GITHUB_PR_URL,
            "public_repo": PUBLIC_REPO_URL,
            "status": "public_branch_pushed_pr_not_opened",
        },
        "geometry_audit_summary": summary,
        "source_artifacts": {
            "geometry_audit_markdown": str(GEOMETRY_AUDIT_MD.relative_to(ROOT)),
            "public_visibility_packet": str(PUBLIC_VISIBILITY_MD.relative_to(ROOT)),
            "generated_json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "channel_plan": build_channel_plan(),
        "linkedin_profile_draft": profile,
        "social_posts": posts,
        "reviewer_email": build_reviewer_email(summary),
        "do_not_publish": [
            "API keys, registry secrets, Kraken/Alpaca credentials, or account screenshots.",
            "Grant portal drafts that include private representations or budget details without review.",
            "Claims of field validation, realized savings, trading profit, CMMC certification, or award certainty.",
            "Statements implying agency, partner, customer, or investor endorsement without written confirmation.",
        ],
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["geometry_audit_summary"]
    lines = [
        "# Publication Approval Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Status",
        "",
        f"- Public branch: `{payload['github']['branch']}`",
        f"- PR URL: {payload['github']['pr_url']}",
        f"- Approval required before LinkedIn/site/email changes: `{payload['publication_policy']['approval_required_before_live_profile_or_social_changes']}`",
        "",
        "## Evidence Summary",
        "",
        f"- Registered geometry families: `{summary.get('registered_family_count', 0)}`",
        f"- Lanes: `{summary.get('lane_count', 0)}`",
        f"- Generated benchmark-result families: `{summary.get('synthetic_benchmark_result_count', 0)}`",
        f"- Proof-priority candidates: `{summary.get('proof_priority_candidate_count', 0)}`",
        f"- Field-validated families: `{summary.get('field_validated_family_count', 0)}`",
        "",
        "## Channel Plan",
        "",
    ]
    for row in payload["channel_plan"]:
        url = f" ({row['url']})" if row.get("url") else ""
        lines.append(
            f"- P{row['priority']} {row['channel']}: {row['action']}{url} "
            f"Approval required: `{row['approval_required']}`"
        )
    lines.extend(
        [
            "",
            "## LinkedIn Profile Draft",
            "",
            "### Headline",
            "",
            payload["linkedin_profile_draft"]["headline"],
            "",
            "### About",
            "",
            payload["linkedin_profile_draft"]["about"],
            "",
            "### Featured Link Caption",
            "",
            payload["linkedin_profile_draft"]["featured_link_caption"],
            "",
            "## Social Post Drafts",
            "",
        ]
    )
    for row in payload["social_posts"]:
        lines.extend([f"### {row['name']}", "", row["copy"], ""])
    email = payload["reviewer_email"]
    lines.extend(
        [
            "## Reviewer Email Draft",
            "",
            f"Subject: {email['subject']}",
            "",
            email["body"],
            "",
            "## Do Not Publish",
            "",
        ]
    )
    for item in payload["do_not_publish"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Claim Boundary", "", payload["publication_policy"]["claim_boundary"]])
    return "\n".join(lines)


def main() -> dict[str, Any]:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    return payload


if __name__ == "__main__":
    result = main()
    print(json.dumps({"schema": result["schema"], "github": result["github"]}, indent=2))

