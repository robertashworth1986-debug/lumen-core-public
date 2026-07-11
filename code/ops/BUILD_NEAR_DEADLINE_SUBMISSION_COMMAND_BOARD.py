from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

SAM_BOARD = OUT_OPS / "sam_rush_submission_board_latest.json"
GRANTS_RANKED = ROOT / "out" / "grants" / "grants_ranked_v2.json"
ZERO_FRICTION = OUT_OPS / "funding_reviewer_zero_friction_pack_latest.json"

OUT_JSON = OUT_OPS / "near_deadline_submission_command_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "near_deadline_submission_command_board.json"
OUT_MD = SPRINT_DIR / "NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-11.md"

SCAN_DATE = date(2026, 7, 11)

SENSITIVE_MARKERS = [
    "password",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def deadline_bucket(days: int | None) -> str:
    if days is None:
        return "unknown"
    if days < 0:
        return "past_due"
    if days <= 2:
        return "48_hour_sprint"
    if days <= 7:
        return "seven_day_sprint"
    if days <= 14:
        return "two_week_sprint"
    if days <= 31:
        return "thirty_day_sprint"
    return "later"


def sam_lookup(sam_board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("solicitation_number")): row
        for row in sam_board.get("opportunities", [])
        if row.get("solicitation_number")
    }


def grant_lookup(grants: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in grants.get("ranked", []):
        opp_num = str(row.get("opp_num") or "")
        if opp_num:
            rows[opp_num] = row
    return rows


def base_sources() -> dict[str, Any]:
    sources = {}
    for key, path in {
        "sam_rush_board": SAM_BOARD,
        "grants_ranked": GRANTS_RANKED,
        "funding_reviewer_zero_friction_pack": ZERO_FRICTION,
    }.items():
        if path.exists():
            data = path.read_bytes()
            sources[key] = {
                "path": rel(path),
                "present": True,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        else:
            sources[key] = {"path": rel(path), "present": False}
    return sources


def build_command_lanes(sam_board: dict[str, Any], grants_ranked: dict[str, Any]) -> list[dict[str, Any]]:
    sam = sam_lookup(sam_board)
    grants = grant_lookup(grants_ranked)

    nasa = sam.get("80TECH26RFI0020", {})
    fhwa = sam.get("693JJ326R000012", {})
    erdc = sam.get("W912HZ26SC005", {})
    bop = sam.get("15BCMS26Q70000005", {})
    nsf = grants.get("26-511", {})
    hud = grants.get("PDR-2600-DC-029Q", {})
    hhs_child = grants.get("HHS-2026-ACF-ACYF-CA-0037", {})

    lanes: list[dict[str, Any]] = [
        {
            "rank": 1,
            "lane_id": "nasa_data_center_rfi",
            "source_system": "SAM.gov",
            "opportunity_number": "80TECH26RFI0020",
            "title": nasa.get("title", "Strategic Partnerships for NASA Data Center Infrastructure"),
            "agency": nasa.get("agency", "NASA IT Procurement Office"),
            "deadline_utc": nasa.get("deadline_utc", "2026-07-17T21:00:00Z"),
            "days_to_close_from_2026_07_11": 6,
            "deadline_bucket": "seven_day_sprint",
            "command": "STAGE_NOW",
            "submission_route": nasa.get("submission_route", "Email response per RFI instructions"),
            "official_url": nasa.get("official_url", "https://sam.gov/opp/312af51a7fc14110b1239bdd32252213/view"),
            "package_files": nasa.get(
                "package_files",
                [
                    "NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
                    "NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md",
                ],
            ),
            "why_now": "Fastest clean federal market-research lane: no pricing needed, response can be bounded to capability, proof-to-decision validation, and no agency-validation claims.",
            "today_work": [
                "Confirm official RFI email recipients, page cap, attachments, and amendments.",
                "Promote the NASA outline/stub into a reviewer-ready RFI response.",
                "Stage email subject/body and attachment list for human approval.",
            ],
            "human_gate": [
                "Robert approves final capability language and any past-performance statement.",
                "Robert approves the final email send.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 2,
            "lane_id": "fhwa_tsmo_data_initiative",
            "source_system": "SAM.gov",
            "opportunity_number": "693JJ326R000012",
            "title": fhwa.get("title", "Transportation Systems Management and Operations Data Initiative"),
            "agency": fhwa.get("agency", "Federal Highway Administration"),
            "deadline_utc": fhwa.get("deadline_utc", "2026-08-03T13:00:00Z"),
            "days_to_close_from_2026_07_11": 23,
            "deadline_bucket": "thirty_day_sprint",
            "command": "BUILD_PRIMARY_VOLUME",
            "submission_route": fhwa.get("submission_route", "SAM.gov / official solicitation instructions"),
            "official_url": fhwa.get("official_url", "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view"),
            "package_files": fhwa.get(
                "package_files",
                [
                    "FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
                    "LUMENCORE_FHWA_TSMO_CAPABILITY_NOTE_693JJ326R000012_2026-07-09.pdf",
                    "FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md",
                ],
            ),
            "why_now": "Best fit for LumenCore's measured-source validation story: TSMO data barriers, prototype algorithms, use-case prioritization, and evidence-backed evaluation.",
            "today_work": [
                "Download/review official attachments and amendments.",
                "Add a compliance matrix to the Phase I outline.",
                "Stage SAM.gov upload packet and hold at final preview.",
            ],
            "human_gate": [
                "Robert approves Phase I volume, reps/certs, and any price/cost language.",
                "Robert approves final SAM.gov submission preview.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 3,
            "lane_id": "nsf_sbir_scientific_instrumentation",
            "source_system": "Grants.gov / NSF Seed Fund",
            "opportunity_number": "26-511",
            "title": nsf.get(
                "title",
                "SBIR/STTR Pilot Emphasis on Scientific Instrumentation",
            ),
            "agency": nsf.get("raw", {}).get("agency", "U.S. National Science Foundation"),
            "deadline_utc": "2026-07-27T23:59:59Z",
            "days_to_close_from_2026_07_11": 16,
            "deadline_bucket": "thirty_day_sprint",
            "command": "STAGE_PROJECT_PITCH",
            "submission_route": "NSF Seed Fund Project Pitch / Grants.gov full proposal if invited",
            "official_url": "https://www.grants.gov/search-results-detail/362551",
            "secondary_url": "https://seedfund.nsf.gov/project-pitch/",
            "package_files": [
                "NSF_PROJECT_PITCH_DRAFT_2026-07-09.md",
                "FUNDING_REVIEWER_ZERO_FRICTION_PACK_2026-07-10.md",
            ],
            "why_now": "Strongest grants-side fit: small business, SBIR/STTR, Phase I, instrumentation emphasis. This is a better match than most broad human-services grants.",
            "today_work": [
                "Open NSF Seed Fund Project Pitch and confirm account state.",
                "Use the existing NSF draft as the base pitch.",
                "Frame LumenCore as a scientific instrumentation and validation platform for measured-source AI/data systems.",
            ],
            "human_gate": [
                "Robert confirms company profile, PI/ownership eligibility, and any budget facts.",
                "Robert approves final pitch submit.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 4,
            "lane_id": "hud_robotics_ai_home_construction",
            "source_system": "Grants.gov / HUD",
            "opportunity_number": "PDR-2600-DC-029Q",
            "title": hud.get(
                "title",
                "Mass Market Solutions for Leveraging Robotics and AI Technologies for Home Construction Demonstration",
            ),
            "agency": hud.get("raw", {}).get("agency", "Department of Housing and Urban Development"),
            "deadline_utc": "2026-07-13T23:59:59Z",
            "days_to_close_from_2026_07_11": 2,
            "deadline_bucket": "48_hour_sprint",
            "command": "ELIGIBILITY_AND_PARTNER_GATE",
            "submission_route": "Grants.gov Workspace package if eligibility and demonstration facts are supportable",
            "official_url": "https://www.grants.gov/search-results-detail/362360",
            "package_files": [
                "NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-11.md",
                "FUNDING_REVIEWER_ZERO_FRICTION_PACK_2026-07-10.md",
            ],
            "why_now": "Deadline is closest and the title matches robotics/AI, but it likely needs a credible construction demonstration plan, budget, and project facts. Treat as emergency only if eligibility passes.",
            "today_work": [
                "Open Grants.gov package and confirm eligible applicant categories, required forms, and attachments.",
                "If eligible, draft a narrow AI/robotics validation-and-instrumentation demonstration narrative.",
                "Stop before budget, certifications, and final submission.",
            ],
            "human_gate": [
                "Robert confirms eligible applicant status and real project/demonstration facts.",
                "Robert approves all Grants.gov certifications and final submission.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 5,
            "lane_id": "erdc_sovereign_cloud_cso",
            "source_system": "SAM.gov / ERDCWERX",
            "opportunity_number": "W912HZ26SC005",
            "title": erdc.get("title", "Sovereign Defense Cloud for High-Performance Computing CSO"),
            "agency": erdc.get("agency", "ERDC Information Technology Laboratory / HPCMP"),
            "deadline_utc": erdc.get("deadline_utc", "2026-08-07T21:00:00Z"),
            "days_to_close_from_2026_07_11": 27,
            "deadline_bucket": "thirty_day_sprint",
            "command": "STAGE_CONCEPT_PAPER",
            "submission_route": erdc.get("submission_route", "ERDCWERX Commercial Solutions Opening portal"),
            "official_url": erdc.get("official_url", "https://sam.gov/opp/8e32f0dfcdee42eeb3b2b03819a6ed25/view"),
            "secondary_url": erdc.get("secondary_url", "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/"),
            "package_files": erdc.get("package_files", ["ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md"]),
            "why_now": "Good concept-paper lane if LumenCore is framed as a proof fabric module, not a full sovereign cloud prime.",
            "today_work": [
                "Open ERDCWERX and confirm form fields.",
                "Stage concept title, problem, modular solution, and data-rights boundary.",
            ],
            "human_gate": [
                "Robert approves title, commercial item framing, data rights, and any price.",
                "Robert approves final portal submit.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 6,
            "lane_id": "doj_bop_medical_claims_quote",
            "source_system": "SAM.gov",
            "opportunity_number": "15BCMS26Q70000005",
            "title": bop.get("title", "Historical Medical Claims Data Analysis"),
            "agency": bop.get("agency", "Federal Bureau of Prisons"),
            "deadline_utc": bop.get("deadline_utc", "2026-07-23T15:00:00Z"),
            "days_to_close_from_2026_07_11": 12,
            "deadline_bucket": "two_week_sprint",
            "command": "PRICE_AND_COMPLIANCE_GATE",
            "submission_route": bop.get("submission_route", "Email quote per solicitation instructions"),
            "official_url": bop.get("official_url") or "https://sam.gov/search/?index=opp&keywords=15BCMS26Q70000005&sort=-modifiedDate&sfm%5Bstatus%5D%5Bis_active%5D=true",
            "package_files": bop.get("package_files", ["DOJ_BOP_MEDICAL_CLAIMS_ANALYSIS_QUOTE_STUB_2026-07-10.md"]),
            "why_now": "Bounded analytics quote with small-business set-aside, but price, deliverable capacity, clauses, and data handling must be confirmed before any quote email.",
            "today_work": [
                "Open official notice and download solicitation.",
                "Draft technical quote and AI-use disclosure.",
                "Hold until price and compliance are approved.",
            ],
            "human_gate": [
                "Robert approves price and responsibility/past-performance statements.",
                "Robert approves final quote email.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 7,
            "lane_id": "hhs_predictive_analytics_child_welfare",
            "source_system": "Grants.gov",
            "opportunity_number": "HHS-2026-ACF-ACYF-CA-0037",
            "title": hhs_child.get("title", "Predictive Analytics in Child Welfare Demonstration Grants"),
            "agency": hhs_child.get("raw", {}).get("agency", "Administration for Children and Families"),
            "deadline_utc": "2026-07-13T23:59:59Z",
            "days_to_close_from_2026_07_11": 2,
            "deadline_bucket": "48_hour_sprint",
            "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
            "submission_route": "Partner with eligible public/tribal child-welfare agency only",
            "official_url": "https://www.grants.gov/search-results-detail/361912",
            "package_files": [],
            "why_now": "The title is relevant, but it is not a safe solo submission lane unless an eligible agency partner controls the application.",
            "today_work": [
                "Do not spend the sprint here unless an eligible agency partner is already available.",
                "Keep as a future proof-to-pilot target for predictive analytics ethics and validation.",
            ],
            "human_gate": [
                "Eligible agency partner identified and approves participation.",
                "Robert approves partner outreach or subrecipient role.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
    ]

    for lane in lanes:
        lane["lane_sha256"] = stable_sha256(lane)
    return lanes


def build_payload() -> dict[str, Any]:
    sam_board = read_json(SAM_BOARD)
    grants_ranked = read_json(GRANTS_RANKED)
    zero = read_json(ZERO_FRICTION)
    lanes = build_command_lanes(sam_board, grants_ranked)
    stage_now = [row for row in lanes if row["command"] in {"STAGE_NOW", "BUILD_PRIMARY_VOLUME", "STAGE_PROJECT_PITCH", "STAGE_CONCEPT_PAPER"}]
    emergency_gate = [row for row in lanes if row["command"] == "ELIGIBILITY_AND_PARTNER_GATE"]
    human_gated = [row for row in lanes if row["human_gate"]]

    payload: dict[str, Any] = {
        "schema": "near_deadline_submission_command_board_v1",
        "generated_utc": now_utc(),
        "scan_date": SCAN_DATE.isoformat(),
        "status": "NEAR_DEADLINE_COMMAND_BOARD_READY_HUMAN_SUBMIT_REQUIRED",
        "source_ledgers": base_sources(),
        "summary": {
            "lane_count": len(lanes),
            "stage_now_count": len(stage_now),
            "emergency_eligibility_gate_count": len(emergency_gate),
            "human_gated_count": len(human_gated),
            "strongest_today_action": "Promote NASA RFI response first, then NSF Project Pitch and FHWA TSMO volume.",
            "closest_deadline_lane": "PDR-2600-DC-029Q HUD robotics/AI home construction demonstration, due 2026-07-13, eligibility/project gate required.",
            "best_grants_lane": "26-511 NSF SBIR/STTR scientific instrumentation, due 2026-07-27.",
            "best_contract_lane": "693JJ326R000012 FHWA TSMO Data Initiative, due 2026-08-03.",
            "fastest_low_friction_lane": "80TECH26RFI0020 NASA Data Center Infrastructure RFI, due 2026-07-17.",
            "all_final_actions_blocked_without_human": True,
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
            "pricing_allowed_without_human": False,
            "legal_certification_allowed_without_human": False,
        },
        "lanes": lanes,
        "stage_now": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_utc": row["deadline_utc"],
                "official_url": row["official_url"],
                "package_files": row["package_files"],
            }
            for row in stage_now
        ],
        "emergency_gate": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_utc": row["deadline_utc"],
                "official_url": row["official_url"],
                "human_gate": row["human_gate"],
            }
            for row in emergency_gate
        ],
        "zero_friction_pack_status": zero.get("status", "UNKNOWN"),
        "submission_boundary": {
            "can_open_pages": True,
            "can_stage_drafts": True,
            "can_fill_nonfinal_routine_fields_after_user_login": True,
            "can_final_submit_without_human": False,
            "must_stop_before": [
                "final Grants.gov submit",
                "final SAM.gov submit",
                "final email send",
                "legal certification",
                "signature",
                "terms acceptance",
                "pricing or quote amount",
                "claim of agency validation, award, realized savings, or customer ROI",
            ],
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["command_board_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Near-Deadline Submission Command Board - 2026-07-11",
        "",
        "This is the action board for getting the closest credible grants and federal contract responses fully staged.",
        "",
        "Direct answer: stage NASA first for speed, NSF and FHWA next for strongest fit, HUD only if the live Grants.gov package confirms eligibility and we can support a real construction-demonstration narrative.",
        "",
        "## Control Line",
        "",
        f"- Status: `{payload['status']}`",
        f"- Scan date: `{payload['scan_date']}`",
        f"- Lane count: `{summary['lane_count']}`",
        f"- Stage-now lanes: `{summary['stage_now_count']}`",
        f"- Emergency eligibility gates: `{summary['emergency_eligibility_gate_count']}`",
        f"- Human-gated lanes: `{summary['human_gated_count']}`",
        f"- Strongest today action: {summary['strongest_today_action']}",
        f"- Closest deadline lane: {summary['closest_deadline_lane']}",
        f"- Best grants lane: {summary['best_grants_lane']}",
        f"- Best contract lane: {summary['best_contract_lane']}",
        f"- Fastest low-friction lane: {summary['fastest_low_friction_lane']}",
        f"- Final submit without human: `{str(summary['final_submit_allowed_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Pricing without human: `{str(summary['pricing_allowed_without_human']).lower()}`",
        f"- Legal certification without human: `{str(summary['legal_certification_allowed_without_human']).lower()}`",
        f"- Command board SHA-256: `{payload['command_board_sha256']}`",
        "",
        "## Stage Now",
        "",
    ]
    for row in payload["stage_now"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline UTC: `{row['deadline_utc']}`",
                f"- Official URL: {row['official_url']}",
                "- Package files:",
            ]
        )
        for file in row["package_files"]:
            lines.append(f"  - `{file}`")
        lines.append("")

    lines.extend(["## Emergency Gate", ""])
    for row in payload["emergency_gate"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline UTC: `{row['deadline_utc']}`",
                f"- Official URL: {row['official_url']}",
                "- Human gate:",
            ]
        )
        for gate in row["human_gate"]:
            lines.append(f"  - {gate}")
        lines.append("")

    lines.extend(["## Full Lane Detail", ""])
    for lane in payload["lanes"]:
        lines.extend(
            [
                f"### {lane['rank']}. {lane['opportunity_number']} - {lane['title']}",
                "",
                f"- Source: `{lane['source_system']}`",
                f"- Agency: `{lane['agency']}`",
                f"- Deadline UTC: `{lane['deadline_utc']}`",
                f"- Days to close from 2026-07-11: `{lane['days_to_close_from_2026_07_11']}`",
                f"- Deadline bucket: `{lane['deadline_bucket']}`",
                f"- Command: `{lane['command']}`",
                f"- Route: {lane['submission_route']}",
                f"- Official URL: {lane['official_url']}",
            ]
        )
        if lane.get("secondary_url"):
            lines.append(f"- Secondary URL: {lane['secondary_url']}")
        lines.extend(
            [
                f"- Why now: {lane['why_now']}",
                "- Today work:",
            ]
        )
        for item in lane["today_work"]:
            lines.append(f"  - {item}")
        lines.append("- Human gate:")
        for gate in lane["human_gate"]:
            lines.append(f"  - {gate}")
        if lane["package_files"]:
            lines.append("- Package files:")
            for file in lane["package_files"]:
                lines.append(f"  - `{file}`")
        lines.extend(
            [
                f"- External send without human: `{str(lane['external_send_allowed_without_human']).lower()}`",
                f"- Final submit without human: `{str(lane['final_submit_allowed_without_human']).lower()}`",
                f"- Lane SHA-256: `{lane['lane_sha256']}`",
                "",
            ]
        )

    lines.extend(["## Submission Boundary", ""])
    boundary = payload["submission_boundary"]
    for key, value in boundary.items():
        if isinstance(value, list):
            lines.append(f"- {key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(["", "## Source Ledgers", ""])
    for key, source in payload["source_ledgers"].items():
        lines.append(f"- `{key}`: `{source.get('path')}` present=`{str(source.get('present')).lower()}` sha256=`{source.get('sha256', '')}`")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    rendered = render_markdown(payload)
    hits = scan_sensitive_text(rendered)
    if hits:
        raise SystemExit(f"Refusing to write sensitive markers: {hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, rendered)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "stage_now": payload["summary"]["stage_now_count"],
                "emergency_gates": payload["summary"]["emergency_eligibility_gate_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
