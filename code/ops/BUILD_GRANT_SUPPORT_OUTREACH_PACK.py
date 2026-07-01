from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRANTS = ROOT / "grant_submissions"
OUT = ROOT / "out" / "ops"

ACTION_BOARD_JSON = OUT / "action_time_submission_board_latest.json"
ACTION_BOARD_MD = GRANTS / "ACTION_TIME_SUBMISSION_BOARD_2026-06-20.md"
FREEZE_JSON = OUT / "top_submission_package_freeze_latest.json"
PORTAL_RUNBOOK_MD = GRANTS / "PORTAL_PREVIEW_RUNBOOK_2026-06-20.md"
OUT_JSON = OUT / "grant_support_outreach_pack_latest.json"
OUT_MD = GRANTS / "GRANT_SUPPORT_OUTREACH_PACK_2026-06-20.md"

BOUNDARY = (
    "This pack helps the founder contact support organizations and capture "
    "non-secret readiness facts. It does not authorize upload, certification, "
    "signature, submission, legal representation, trading, or investment claims."
)

DO_NOT_SHARE = [
    "passwords",
    "MFA or one-time codes",
    "API keys or private tokens",
    "TIN/EIN or banking data",
    "private portal screenshots containing identifiers",
    "private registry dumps",
    "unsupported claims of partners, customers, facilities, clearances, CMMC level, field validation, or revenue",
]

OFFICIAL_SUPPORT_LANES: list[dict[str, Any]] = [
    {
        "id": "apex_federal_contracting",
        "label": "APEX Accelerator / federal contracting readiness",
        "source_url": "https://www.sba.gov/local-assistance/federal-contracting-assistance",
        "source_note": (
            "SBA describes APEX Accelerators as technical assistance for businesses "
            "selling to federal, state, and local governments, including readiness, "
            "registration, certifications, and opportunity research."
        ),
        "use_for": [
            "SAM.gov and Grants.gov readiness review",
            "DSIP/BAAT organization and submitter-role questions",
            "small-business certification and set-aside pathway review",
            "basic cost and contracting representation sanity check",
        ],
        "ask": [
            "Can you review my SAM/Grants.gov/DSIP/BAAT readiness without capturing secrets?",
            "Which portal roles or registrations are missing before SBIR/STTR submission?",
            "Can you help me understand required representations without guessing?",
        ],
    },
    {
        "id": "project_spectrum_cyber",
        "label": "DoD OSBP Project Spectrum / CMMC and cybersecurity readiness",
        "source_url": "https://business.defense.gov/Programs/Cyber-Security-Resources/",
        "source_note": (
            "DoD Office of Small Business Programs describes Project Spectrum as a "
            "platform for cybersecurity tools, training, awareness, and compliance "
            "best practices for DoD contracting requirements."
        ),
        "use_for": [
            "CMMC Level 1/2 learning path",
            "NIST SP 800-171 gap planning",
            "SPRS and PIEE role questions",
            "cybersecurity representation boundary before DoD submissions",
        ],
        "ask": [
            "Can you help me determine what CMMC/SPRS facts I can truthfully state now?",
            "What evidence should I collect before I answer any cyber representation?",
            "What is the fastest safe path from unknown status to a documented plan?",
        ],
    },
    {
        "id": "uspto_patent_pro_bono",
        "label": "USPTO Patent Pro Bono / patent legal rescue",
        "source_url": "https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program",
        "source_note": (
            "USPTO describes a nationwide network of regional programs that can "
            "match financially underresourced inventors and small businesses with "
            "volunteer patent attorneys or agents."
        ),
        "use_for": [
            "non-provisional deadline triage",
            "claim-set review",
            "continuation/PCT/new-provisional strategy question routing",
            "public-disclosure and prior-art risk triage",
        ],
        "ask": [
            "I have a provisional approaching its one-year deadline. Can you route me to the correct regional program?",
            "What minimum packet do you need to decide if pro bono patent help is available?",
            "Can counsel advise whether non-provisional, continuation, PCT, or new provisional paths fit?",
        ],
    },
    {
        "id": "sbir_fast_support",
        "label": "SBIR.gov FAST / SBIR-STTR proposal support",
        "source_url": "https://www.sbir.gov/community/fast",
        "source_note": (
            "SBIR.gov describes FAST as a program supporting state and regional "
            "organizations that increase SBIR/STTR proposals and awards from "
            "small businesses in undercapitalized regions."
        ),
        "use_for": [
            "SBIR/STTR agency-fit review",
            "Phase I proposal coaching",
            "NSF Project Pitch path review",
            "state or regional assistance referral",
        ],
        "ask": [
            "Who is my local/regional SBIR/STTR support contact?",
            "Can someone review whether DICE, Navy DSIP, NSF, or NIH paths fit my evidence?",
            "Can you help convert technical proof into reviewer-safe proposal language?",
        ],
    },
    {
        "id": "sbir_program_context",
        "label": "SBIR.gov program context / agency-fit grounding",
        "source_url": "https://www.sbir.gov/about",
        "source_note": (
            "SBIR.gov describes SBIR/STTR as early-stage technology funding for "
            "small businesses across technology areas, federal R&D needs, and "
            "commercialization impact."
        ),
        "use_for": [
            "keeping claims aligned with SBIR/STTR purpose",
            "separating research merit from procurement or investment claims",
            "framing commercialization without guaranteeing awards or revenue",
        ],
        "ask": [
            "Which agencies have the closest fit for a control/evidence/orchestration platform?",
            "What proof level is expected for Phase I feasibility versus Phase II transition?",
        ],
    },
]

SIGN_IN_QUEUE = [
    {
        "site": "DARPA BAAT",
        "why": "DICE is the first local-ready package; BAAT must confirm organization, role, DICE opportunity visibility, accepted file types, and preview behavior.",
        "capture_only": [
            "organization visible",
            "submitter role",
            "opportunity visible",
            "file requirements",
            "preview status",
        ],
    },
    {
        "site": "DSIP",
        "why": "HarborSentinel and later Navy/DLA packages need DSIP topic visibility, organization linkage, forms, and compliance gates.",
        "capture_only": [
            "organization linked",
            "topic visible",
            "volume/form requirements",
            "compliance prompts",
            "preview status",
        ],
    },
    {
        "site": "PIEE / SPRS",
        "why": "CMMC/SPRS/Affirming Official status cannot be guessed. We need the factual status or a documented unknown.",
        "capture_only": [
            "role access present or missing",
            "CAGE hierarchy visible or missing",
            "score/status present or missing",
            "next required role",
        ],
    },
    {
        "site": "NSF Project Pitch",
        "why": "Fastest low-friction non-DoD path if duplicate-pitch status, legal name, PI title, and paste counts are clean.",
        "capture_only": [
            "legal business name",
            "PI/founder title",
            "duplicate/open-invitation status",
            "field paste counts",
        ],
    },
    {
        "site": "USPTO Patent Center / regional Patent Pro Bono intake",
        "why": "Patent deadline is a real legal-risk gate; a patent attorney or agent must advise the correct rescue path.",
        "capture_only": [
            "application number/date if user approves",
            "one-year deadline",
            "regional intake requirements",
            "attorney/agent next step",
        ],
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


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def pick_package_cards(action_board: dict[str, Any]) -> list[dict[str, Any]]:
    cards = action_board.get("cards", action_board.get("packages", []))
    if not isinstance(cards, list):
        return []
    selected = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        selected.append(
            {
                "rank": card.get("rank"),
                "package": card.get("package"),
                "portal": card.get("portal"),
                "readiness": card.get("readiness"),
                "primary_unlock": card.get("primary_unlock"),
                "portal_user_blockers": card.get("portal_user_blockers", []),
                "ready_to_submit": False,
            }
        )
    return selected


def build_outreach_queue(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    package_names = {str(card.get("package")) for card in cards}
    queue = [
        {
            "rank": 1,
            "lane_id": "apex_federal_contracting",
            "target": "Local APEX Accelerator counselor",
            "packages_unblocked": [
                name
                for name in ["DICE", "HarborSentinel", "MissionWeave", "NV065"]
                if name in package_names
            ],
            "request": "Review federal portal readiness, small-business contracting representations, and submitter-role blockers.",
            "share": "A sanitized blocker summary and public-safe one-page capability overview.",
            "do_not_share": DO_NOT_SHARE,
        },
        {
            "rank": 2,
            "lane_id": "project_spectrum_cyber",
            "target": "Project Spectrum / DoD cyber support",
            "packages_unblocked": [
                name
                for name in ["HarborSentinel", "MissionWeave", "NV065"]
                if name in package_names
            ],
            "request": "Clarify CMMC/SPRS/PIEE facts and the safest documented path before answering cyber representations.",
            "share": "Only non-secret company-role questions and a list of representations that need review.",
            "do_not_share": DO_NOT_SHARE,
        },
        {
            "rank": 3,
            "lane_id": "uspto_patent_pro_bono",
            "target": "Regional USPTO Patent Pro Bono intake",
            "packages_unblocked": ["Patent/legal rescue"],
            "request": "Route urgent provisional-to-non-provisional deadline review to a qualified patent attorney or agent.",
            "share": "A sanitized invention summary and deadline facts the user explicitly approves.",
            "do_not_share": DO_NOT_SHARE,
        },
        {
            "rank": 4,
            "lane_id": "sbir_fast_support",
            "target": "Local or regional SBIR/STTR FAST support organization",
            "packages_unblocked": [
                name
                for name in ["DICE", "HarborSentinel", "NSF Project Pitch"]
                if name in package_names
            ],
            "request": "Agency-fit and Phase I proposal coaching for the strongest local-ready packages.",
            "share": "Public-safe abstract, reviewer matrix excerpts, and evidence-boundary summary.",
            "do_not_share": DO_NOT_SHARE,
        },
    ]
    return queue


def build_templates() -> dict[str, str]:
    return {
        "apex": (
            "Subject: Request for SBIR/STTR federal portal readiness review\n\n"
            "Hello,\n\n"
            "I am preparing small-business federal R&D submissions and need help "
            "checking portal readiness, submitter authority, and representation "
            "boundaries before I answer anything in BAAT/DSIP/Grants.gov. I can "
            "share a sanitized blocker list and public-safe capability summary. "
            "I will not send passwords, MFA codes, API keys, tax IDs, banking "
            "details, or private portal screenshots.\n\n"
            "Could you help me identify the fastest safe next step?\n"
        ),
        "project_spectrum": (
            "Subject: CMMC/SPRS factual-status and readiness-plan help\n\n"
            "Hello,\n\n"
            "I am preparing DoD SBIR/STTR submissions and need help determining "
            "what CMMC/SPRS/PIEE facts I can truthfully state today, what remains "
            "unknown, and what evidence should be collected before any cyber "
            "representation is made. I am not asking anyone to certify incomplete "
            "status; I need a safe documented path.\n"
        ),
        "patent_pro_bono": (
            "Subject: Urgent patent pro bono intake request - provisional deadline\n\n"
            "Hello,\n\n"
            "I am an inventor/small-business founder with patent rights that may "
            "need action before a non-provisional deadline. I need routing to a "
            "qualified patent attorney or agent to evaluate the correct path. I "
            "can provide deadline and application details through the intake "
            "process after confirming what is safe to share.\n"
        ),
        "sbir_fast": (
            "Subject: SBIR/STTR proposal support and agency-fit review\n\n"
            "Hello,\n\n"
            "I am preparing early-stage R&D submissions for a control, evidence, "
            "and orchestration platform. I need help matching the proof package "
            "to the right SBIR/STTR agencies and improving reviewer-safe Phase I "
            "language without overstating partners, field validation, or revenue.\n"
        ),
    }


def build_pack(
    action_board: dict[str, Any] | None = None,
    freeze: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action_board = action_board or read_json(ACTION_BOARD_JSON)
    freeze = freeze or read_json(FREEZE_JSON)
    cards = pick_package_cards(action_board)
    return {
        "schema": "grant_support_outreach_pack_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "source_artifacts": {
            "action_board_json": rel(ACTION_BOARD_JSON),
            "action_board_md": rel(ACTION_BOARD_MD),
            "portal_runbook_md": rel(PORTAL_RUNBOOK_MD),
            "freeze_json": rel(FREEZE_JSON),
            "freeze_signature_sha256": freeze.get("freeze_signature_sha256"),
        },
        "official_support_lanes": OFFICIAL_SUPPORT_LANES,
        "sign_in_queue": SIGN_IN_QUEUE,
        "do_not_share": DO_NOT_SHARE,
        "package_blocker_snapshot": cards,
        "outreach_queue": build_outreach_queue(cards),
        "templates": build_templates(),
        "live_breadth_policy": {
            "use_existing_first": True,
            "recommended_paid_data_now": False,
            "reason": (
                "The current blockers are portal authority, compliance facts, cost/domain "
                "review, and evidence boundaries. More live data should be bought only "
                "after a benchmark gate proves that it will test a specific falsifiable edge."
            ),
            "safe_sources_to_expand": [
                "Grants.gov/SAM public opportunity metadata",
                "SBIR.gov agency/topic metadata",
                "public AIS or other representative domain datasets",
                "exchange data through read-only or paper-trading keys until execution proof is reviewed",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Grant Support Outreach Pack",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## What To Sign Into First",
        "",
    ]
    for index, item in enumerate(payload["sign_in_queue"], start=1):
        lines.extend(
            [
                f"### {index}. {item['site']}",
                "",
                f"Why: {item['why']}",
                "",
                "Capture only:",
            ]
        )
        for fact in item["capture_only"]:
            lines.append(f"- {fact}")
        lines.append("")

    lines.extend(["## Official Support Lanes", ""])
    for lane in payload["official_support_lanes"]:
        lines.extend(
            [
                f"### {lane['label']}",
                "",
                f"- Source: {lane['source_url']}",
                f"- Source note: {lane['source_note']}",
                "- Use for:",
            ]
        )
        for use in lane["use_for"]:
            lines.append(f"  - {use}")
        lines.append("- Ask:")
        for ask in lane["ask"]:
            lines.append(f"  - {ask}")
        lines.append("")

    lines.extend(["## Outreach Queue", ""])
    for item in payload["outreach_queue"]:
        packages = ", ".join(item["packages_unblocked"]) or "general readiness"
        lines.extend(
            [
                f"### {item['rank']}. {item['target']}",
                "",
                f"- Packages unblocked: {packages}",
                f"- Request: {item['request']}",
                f"- Share: {item['share']}",
                "",
            ]
        )

    lines.extend(["## Do Not Share", ""])
    lines.append("Do not send passwords, MFA codes, API keys, private tokens, tax IDs, banking data, private registry dumps, or unsupported claims.")
    for item in payload["do_not_share"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.extend(["## Live Breadth Policy", ""])
    policy = payload["live_breadth_policy"]
    lines.extend(
        [
            f"- Use existing data first: {policy['use_existing_first']}",
            f"- Recommended paid data now: {policy['recommended_paid_data_now']}",
            f"- Reason: {policy['reason']}",
            "- Safe sources to expand:",
        ]
    )
    for source in policy["safe_sources_to_expand"]:
        lines.append(f"  - {source}")
    lines.append("")

    lines.extend(["## Message Templates", ""])
    for name, template in payload["templates"].items():
        lines.extend([f"### {name}", "", "```text", template.rstrip(), "```", ""])
    return "\n".join(lines)


def write_pack(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_pack()
    OUT.mkdir(parents=True, exist_ok=True)
    GRANTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_pack()
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"markdown: {rel(OUT_MD)}")
    print(f"json: {rel(OUT_JSON)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
