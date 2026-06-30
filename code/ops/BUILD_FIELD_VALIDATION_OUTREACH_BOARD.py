from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

CONTROL_ROOM_JSON = OUT_OPS / "field_validation_control_room_latest.json"
GAUNTLET_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
REVENUE_JSON = OUT_OPS / "proof_to_revenue_engine_latest.json"

OUT_JSON = OUT_OPS / "field_validation_outreach_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validation_outreach_board.json"
OUT_MD = DOCS / "FIELD_VALIDATION_OUTREACH_BOARD_2026-06-29.md"

BOUNDARY = (
    "Field-validation outreach board. This artifact identifies people and organizations that could unlock external "
    "validation by supplying or approving held-out operational data, incumbent baselines, acceptance metrics, and "
    "economic conversion factors. It creates local draft language only. It does not authorize sending email, bulk "
    "outreach, contact scraping, field-validation claims, realized-savings claims, fixed-dollar frozen-delta claims, "
    "live trading, or autonomous operational execution."
)


SOURCE_REFS: dict[str, dict[str, str]] = {
    "epri_iel": {
        "url": "https://epri.brightidea.com/community/iel",
        "fact": "Incubatenergy Labs, powered by EPRI, is a collaborative model for quick paid utility demonstrations of early-stage innovations.",
    },
    "epri_ai_power": {
        "url": "https://epri.brightidea.com/AIforPower2026",
        "fact": "AI for Power Challenge facilitates rapid demonstrations with technology providers and energy companies to de-risk AI solutions.",
    },
    "openpower_ai": {
        "url": "https://openpowerai.org/",
        "fact": "OpenPOWER AI describes a power-sector AI ecosystem with utilities, technology providers, datasets, models, and challenge paths for collaboration, testing, validation, and de-risking.",
    },
    "epb_automated_grid": {
        "url": "https://epb.com/energy/automated-grid/",
        "fact": "EPB describes an automated grid that reroutes power in seconds and reports nearly 19 million outage minutes avoided yearly.",
    },
    "tva_future_grid": {
        "url": "https://www.tva.com/energy/technology-innovation/future-grid-performance",
        "fact": "TVA identifies future-grid challenges from renewables, storage, weather-dependent resources, and inverter-based resources.",
    },
    "spark_accelerator": {
        "url": "https://www.tnresearchpark.org/spark/accelerator/",
        "fact": "Spark Accelerator offers mentorship, prototyping, customer and partner connections, and TVA/ORNL partnership pathways.",
    },
    "launchtn_sbir": {
        "url": "https://launchtn.org/sbir-sttr/",
        "fact": "LaunchTN provides SBIR/STTR support, matching fund pathways, and institutional partnership help for Tennessee companies.",
    },
    "launchtn_match": {
        "url": "https://launchtn.org/sbir-sttr-matching-fund/",
        "fact": "LaunchTN's SBIR/STTR Matching Fund supports commercialization by matching successful Tennessee federal SBIR/STTR awards.",
    },
    "nashville_ec": {
        "url": "https://ec.co/",
        "fact": "Nashville Entrepreneur Center exists to help make Nashville a strong place to start and grow a business.",
    },
    "nashville_ec_accelerators": {
        "url": "https://ec.co/accelerators/",
        "fact": "Nashville EC accelerators offer mentorship, curriculum, community, and go-to-market support.",
    },
    "taebc": {
        "url": "https://www.tnadvancedenergy.com/",
        "fact": "TAEBC champions advanced energy as a Tennessee job creation and economic development strategy.",
    },
    "taebc_contact": {
        "url": "https://www.tnadvancedenergy.com/get-involved/contact-us/",
        "fact": "TAEBC provides a direct contact path for advanced-energy ecosystem inquiries.",
    },
    "nes_business": {
        "url": "https://www.nespower.com/programs-and-services/business-solutions/",
        "fact": "NES business solutions and economic-development pages provide a local Nashville utility entry point.",
    },
    "vanderbilt_wondry": {
        "url": "https://www.vanderbilt.edu/the-wondry/",
        "fact": "The Wond'ry is Vanderbilt's Center for Innovation and Design.",
    },
    "vanderbilt_wondry_entrepreneurship": {
        "url": "https://www.vanderbilt.edu/the-wondry/entrepreneurship/",
        "fact": "The Wond'ry entrepreneurship practice area supports venture growth for Nashville-area university communities.",
    },
    "vanderbilt_isis": {
        "url": "https://www.isis.vanderbilt.edu/",
        "fact": "Vanderbilt ISIS conducts basic and applied research in systems and information science and engineering.",
    },
    "vanderbilt_cps": {
        "url": "https://engineering.vanderbilt.edu/departments/electrical-computer-engineering/cps/",
        "fact": "Vanderbilt's Cyber-Physical Systems program focuses on networked interaction of computational and physical components.",
    },
    "tntech_cesr": {
        "url": "https://www.tntech.edu/engineering/research/cesr/index.php",
        "fact": "Tennessee Tech's Center for Energy Systems Research is funded by state/federal agencies and the private sector.",
    },
    "tntech_smart_grid": {
        "url": "https://www.tntech.edu/engineering/research/cesr/smartgrid/index.php",
        "fact": "Tennessee Tech CESR smart-grid research uses a scale model grid with in-house SCADA and controls.",
    },
    "ornl_partnerships": {
        "url": "https://www.ornl.gov/partnerships",
        "fact": "ORNL partnerships connect strategic partnerships, commercialization, and technology-transfer pathways.",
    },
    "ornl_tech_transfer": {
        "url": "https://www.ornl.gov/technology-transfer/contact",
        "fact": "ORNL Technology Transfer lists staff and contact routes for commercialization engagement.",
    },
}


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


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def dollars(value: float) -> str:
    return f"${value:,.0f}"


def proof_snapshot() -> dict[str, Any]:
    control = read_json(CONTROL_ROOM_JSON)
    gauntlet = read_json(GAUNTLET_JSON)
    revenue = read_json(REVENUE_JSON)

    control_summary = as_dict(control.get("summary"))
    gauntlet_summary = as_dict(gauntlet.get("summary"))
    source_breadth = as_dict(gauntlet.get("source_breadth_universe"))
    champion_replay = as_dict(source_breadth.get("champion_replay"))
    fresh = as_dict(source_breadth.get("fresh_provider_measurement"))
    manifest = as_dict(source_breadth.get("geometry_manifest"))
    revenue_summary = as_dict(revenue.get("summary"))

    return {
        "champion_family": control_summary.get("strongest_current_family")
        or gauntlet_summary.get("champion_family")
        or "kuramoto_phase_coupling",
        "named_baseline": revenue_summary.get("named_baseline") or "kalman_filter",
        "champion_wins": as_int(control_summary.get("kuramoto_holdout_wins_vs_kalman")),
        "champion_holdouts": as_int(control_summary.get("kuramoto_holdout_count")),
        "champion_estimated_rows_replayed": as_int(
            champion_replay.get("estimated_rows_replayed") or control_summary.get("kuramoto_estimated_rows_replayed")
        ),
        "champion_replay_source_system_count": as_int(
            champion_replay.get("source_system_count") or control_summary.get("kuramoto_source_system_count")
        ),
        "champion_replay_source_systems": champion_replay.get("source_systems", []),
        "broader_measured_provider_count": as_int(
            fresh.get("measured_provider_count") or control_summary.get("broader_measured_provider_count")
        ),
        "broader_enabled_provider_count": as_int(fresh.get("enabled_provider_count")),
        "fresh_rows_returned": as_int(fresh.get("fresh_measured_rows")),
        "fresh_estimated_annual_value_surface_usd": float(fresh.get("estimated_annual_value_surface_usd") or 0),
        "manifest_unique_source_count": as_int(
            manifest.get("unique_source_count") or control_summary.get("manifest_unique_source_count")
        ),
        "manifest_ready_for_benchmark_row_count": as_int(manifest.get("ready_for_benchmark_row_count")),
        "manifest_estimated_rows_total": as_int(manifest.get("estimated_rows_mapped")),
        "safe_estimated_hourly_value_usd": float(revenue_summary.get("safe_estimated_hourly_value_usd") or 0),
        "safe_estimated_annual_value_usd": float(revenue_summary.get("safe_estimated_annual_value_usd") or 0),
        "live_domain_hash_verified": bool(revenue_summary.get("live_domain_hash_verified")),
        "stress_matrix_feed": "https://lumen-core.ai/data/champion_stress_test_matrix.json",
        "champion_gauntlet_feed": "https://lumen-core.ai/data/champion_metric_gauntlet.json",
        "mission_control": "https://lumen-core.ai/mission_control.html",
        "claim_boundary": (
            "The 24/24 result is the strongest champion replay core. The broader live-breadth universe is larger "
            "and ready for promotion, but it is not automatically part of the champion win until each source is "
            "run through locked benchmarks."
        ),
    }


def value_ladder(snapshot: dict[str, Any]) -> dict[str, Any]:
    safe_annual = float(snapshot["safe_estimated_annual_value_usd"])
    broad_surface = float(snapshot["fresh_estimated_annual_value_surface_usd"])
    return {
        "claimable_today": {
            "status": "paid_evidence_review_or_buyer_authorized_replay_only",
            "paid_evidence_review_range_usd": {"low": 5000, "high": 15000},
            "why": (
                "This is a service/review price posture for curated proof, not a claim that each frozen delta is worth "
                "a fixed amount."
            ),
        },
        "bounded_internal_scenario": {
            "safe_estimated_hourly_value_usd": snapshot["safe_estimated_hourly_value_usd"],
            "safe_estimated_annual_value_usd": safe_annual,
            "status": "estimated_value_signal_not_realized_savings",
            "plain_english": (
                f"The current safe scenario value signal is about {dollars(safe_annual)} per year under stated "
                "assumptions, but it becomes buyer-facing dollar language only after an external owner accepts the "
                "baseline, metric, and conversion factor."
            ),
        },
        "broader_live_breadth_surface": {
            "estimated_annual_value_surface_usd": broad_surface,
            "status": "opportunity_surface_not_claim",
            "plain_english": (
                f"The broader live-breadth scan surfaces about {dollars(broad_surface)} per year of possible "
                "addressable value, but it is a targeting map until promoted through source-specific benchmarks."
            ),
        },
        "what_unlocks_real_dollars": [
            "external owner supplies or approves held-out operational data",
            "external owner names the incumbent baseline",
            "acceptance metric is locked before replay",
            "economic conversion factor is approved before replay",
            "result artifact is signed, logged, or otherwise traceable",
        ],
    }


def target(
    rank: int,
    name: str,
    lane: str,
    locality: str,
    category: str,
    fit_score: int,
    why: str,
    first_ask: str,
    source_keys: list[str],
    likely_unlock: list[str],
) -> dict[str, Any]:
    row = {
        "rank": rank,
        "organization": name,
        "validation_lane": lane,
        "locality": locality,
        "category": category,
        "fit_score": fit_score,
        "why_this_matters": why,
        "first_ask": first_ask,
        "likely_unlock": likely_unlock,
        "source_refs": [SOURCE_REFS[key] for key in source_keys],
        "manual_review_required": True,
        "send_now_allowed": False,
        "send_without_user_review_allowed": False,
    }
    row["target_sha256"] = stable_sha256(row)
    return row


def targets() -> list[dict[str, Any]]:
    return [
        target(
            1,
            "OpenPOWER AI / EPRI AI for Power / Incubatenergy Labs",
            "utility_ai_paid_demonstration",
            "national_utility_channel",
            "field_validation_unlocker",
            100,
            "Best first unlock because it directly connects power-sector AI validation, EPRI/utility collaboration, public datasets/models, and paid demonstration-style pathways.",
            "Ask for a technical fit review or route into an OpenPOWER AI / AI for Power / Incubatenergy validation or paid demonstration path.",
            ["openpower_ai", "epri_iel", "epri_ai_power"],
            ["utility-approved holdout data", "incumbent baseline", "demo sponsor", "pass/fail metric"],
        ),
        target(
            2,
            "EPB Chattanooga / ORNL grid resilience path",
            "grid_reliability_replay",
            "tennessee_regional",
            "field_validation_unlocker",
            97,
            "EPB has automated-grid, real-time usage, microgrid, and research-partnership context suited to replay validation.",
            "Ask for a no-control historical replay on outage, reroute, or microgrid windows.",
            ["epb_automated_grid", "ornl_partnerships"],
            ["historical event windows", "operator metric", "reroute/outage baseline", "data-rights boundary"],
        ),
        target(
            3,
            "TVA / Spark Cleantech Accelerator",
            "future_grid_performance",
            "tennessee_regional",
            "funder_and_partner_bridge",
            95,
            "TVA's future-grid concerns match phase/timing, inverter, storage, and forecasting claims; Spark can route to mentors and partners.",
            "Ask Spark/TVA for a mentor review and one path to a buyer-approved replay dataset.",
            ["tva_future_grid", "spark_accelerator"],
            ["mentor route", "pilot sponsor", "future-grid KPI", "TVA/ORNL bridge"],
        ),
        target(
            4,
            "Tennessee Tech Center for Energy Systems Research",
            "grid_hardware_bench",
            "tennessee_lab",
            "lab_validation_unlocker",
            93,
            "CESR has an energy systems focus and smart-grid research with scale-model grid, SCADA, and controls.",
            "Ask for a small external lab protocol review for grid replay and hardware-bench feasibility.",
            ["tntech_cesr", "tntech_smart_grid"],
            ["scale-model grid bench", "SCADA/control baseline", "lab acceptance metric", "independent memo"],
        ),
        target(
            5,
            "Vanderbilt ISIS / Cyber-Physical Systems",
            "cyber_physical_systems_validation",
            "nashville_local",
            "research_validation_unlocker",
            91,
            "ISIS/CPS research aligns with software-integrated, cyber-physical, human/system, and resilient engineered systems.",
            "Ask for a research fit review on DICE/MissionWeave style controlled-emergence validation.",
            ["vanderbilt_isis", "vanderbilt_cps"],
            ["CPS evaluation frame", "baseline methodology", "reviewer credibility", "grant partner route"],
        ),
        target(
            6,
            "Vanderbilt Wond'ry",
            "startup_validation_and_pitch",
            "nashville_local",
            "local_startup_bridge",
            88,
            "The Wond'ry can help frame the venture and route to local mentors without overclaiming field validation.",
            "Ask for venture mentor feedback and a warm intro to grid/AI validation reviewers.",
            ["vanderbilt_wondry", "vanderbilt_wondry_entrepreneurship"],
            ["mentor review", "pitch refinement", "local university network", "founder support"],
        ),
        target(
            7,
            "LaunchTN SBIR/STTR support and Matching Fund",
            "grant_and_non_dilutive_funding",
            "tennessee_statewide",
            "funder",
            87,
            "LaunchTN is the best Tennessee-specific route for SBIR/STTR support, matching fund awareness, and institutional partnerships.",
            "Ask for SBIR/STTR support, matching fund guidance, and a Tennessee research-institution partner route.",
            ["launchtn_sbir", "launchtn_match"],
            ["proposal coaching", "matching fund path", "STTR partner route", "state commercialization support"],
        ),
        target(
            8,
            "Nashville Entrepreneur Center",
            "startup_acceleration",
            "nashville_local",
            "funder_and_operator_support",
            84,
            "Nashville EC is a practical local founder support path for mentorship, accelerator help, and investor/operator introductions.",
            "Apply or request advisor guidance for validating and selling a proof-to-pilot platform.",
            ["nashville_ec", "nashville_ec_accelerators"],
            ["mentor network", "accelerator path", "go-to-market feedback", "capital introductions"],
        ),
        target(
            9,
            "Tennessee Advanced Energy Business Council",
            "advanced_energy_network",
            "tennessee_statewide",
            "ecosystem_connector",
            82,
            "TAEBC can connect the work to Tennessee advanced-energy policy, business, and partnership channels.",
            "Ask who in the Tennessee advanced-energy ecosystem reviews grid AI validation pilots.",
            ["taebc", "taebc_contact"],
            ["industry network", "advanced-energy credibility", "partner referrals", "event visibility"],
        ),
        target(
            10,
            "Nashville Electric Service business/economic development route",
            "local_utility_entry",
            "nashville_local",
            "local_utility_connector",
            78,
            "NES is the local utility door, but the safest first ask is a route to the right technical/economic-development contact.",
            "Ask for the correct person for grid analytics, reliability innovation, or TVA-connected pilot routing.",
            ["nes_business"],
            ["local utility route", "economic-development contact", "TVA bridge", "problem-owner discovery"],
        ),
        target(
            11,
            "ORNL Technology Transfer / Partnerships",
            "national_lab_partnership",
            "tennessee_lab",
            "lab_and_commercialization_bridge",
            76,
            "ORNL is a high-credibility lab pathway, but it needs a focused ask and likely a partner program rather than a cold technical proof dump.",
            "Ask for the right partnership or technical assistance route for grid/RF/PLL validation.",
            ["ornl_partnerships", "ornl_tech_transfer"],
            ["lab partnership path", "technical assistance route", "commercialization review", "validation credibility"],
        ),
    ]


def draft_email(kind: str, recipient_label: str, snapshot: dict[str, Any]) -> dict[str, str]:
    proof_line = (
        f"Our strongest current internal champion is `{snapshot['champion_family']}` vs "
        f"`{snapshot['named_baseline']}` with {snapshot['champion_wins']}/{snapshot['champion_holdouts']} "
        f"source-conditioned holdout wins and {snapshot['champion_estimated_rows_replayed']:,} estimated rows replayed."
    )
    breadth_line = (
        f"Separate from that core replay, the broader live-breadth estate currently shows "
        f"{snapshot['broader_measured_provider_count']} measured providers, "
        f"{snapshot['manifest_unique_source_count']} mapped source files/feeds, and "
        f"{snapshot['manifest_ready_for_benchmark_row_count']} ready-for-benchmark rows."
    )

    if kind == "utility_or_lab":
        subject = "Request for buyer-authorized field replay: LumenCore grid timing proof"
        body = f"""Hello,

I am Robert Ashworth, founder/inventor of LumenCore. I am looking for the right technical owner or lab reviewer to evaluate a narrow, controlled field-replay protocol.

{proof_line}

{breadth_line}

Important boundary: I am not claiming field validation or realized savings yet. The request is to run or scope a buyer-authorized replay using your held-out data, your incumbent baseline, your acceptance metric, and your approved economic conversion.

Reviewer feed: {snapshot['champion_gauntlet_feed']}
Mission console: {snapshot['mission_control']}

Would you be open to a 20-minute technical fit call, or could you route me to the person who owns AI/grid analytics validation pilots?

Respectfully,
Robert Ashworth
[physical mailing address]

To stop further outreach, reply "remove."
"""
    elif kind == "nashville_connector":
        subject = "Nashville validation partner request for grid/RF/PLL proof stack"
        body = f"""Hello,

I am Robert Ashworth, a Nashville-area founder building LumenCore, a hash-verified benchmark and proof stack for infrastructure, grid timing, RF/PLL-style signal stability, and AI-assisted validation.

{proof_line}

{breadth_line}

I am looking for a local Tennessee path to an external reviewer, lab, utility, or partner who can help lock the held-out data, baseline, acceptance metric, and economic conversion needed for real field validation.

Could you point me to the right mentor, lab, utility innovation contact, or funding path?

Respectfully,
Robert Ashworth
[physical mailing address]

To stop further outreach, reply "remove."
"""
    else:
        subject = "Funding path for external validation of LumenCore proof stack"
        body = f"""Hello,

I am Robert Ashworth, building LumenCore, a proof-to-pilot platform for controlled benchmark evidence across grid, infrastructure, signal, and AI validation lanes.

{proof_line}

{breadth_line}

The honest next funding need is external validation: a buyer/lab/agency-controlled replay using held-out data, an incumbent baseline, pre-registered metrics, and agreed economics. I am seeking non-dilutive funding, a paid evidence review, or an accelerator/partner path that can help turn this into a credible field replay.

Would you be open to a short fit call or route me to the right program/contact?

Respectfully,
Robert Ashworth
[physical mailing address]

To stop further outreach, reply "remove."
"""

    return {
        "kind": kind,
        "recipient_label": recipient_label,
        "subject": subject,
        "body": body,
        "send_mode": "manual_review_only",
        "send_without_user_review_allowed": "false",
    }


def build_payload() -> dict[str, Any]:
    snapshot = proof_snapshot()
    ranked_targets = targets()
    payload = {
        "schema": "field_validation_outreach_board_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "summary": {
            "target_count": len(ranked_targets),
            "nashville_or_tennessee_targets": sum(
                1 for row in ranked_targets if row["locality"] in {"nashville_local", "tennessee_regional", "tennessee_statewide", "tennessee_lab"}
            ),
            "field_validation_unlockers": sum(1 for row in ranked_targets if "validation_unlocker" in row["category"]),
            "funder_or_connector_targets": sum(
                1 for row in ranked_targets if row["category"] in {"funder", "funder_and_partner_bridge", "funder_and_operator_support", "ecosystem_connector"}
            ),
            "champion_replay_source_system_count": snapshot["champion_replay_source_system_count"],
            "broader_measured_provider_count": snapshot["broader_measured_provider_count"],
            "manifest_unique_source_count": snapshot["manifest_unique_source_count"],
            "manifest_ready_for_benchmark_row_count": snapshot["manifest_ready_for_benchmark_row_count"],
            "local_drafts_created": 3,
            "manual_reviewed_outreach_allowed": True,
            "send_without_user_review_allowed": False,
            "bulk_email_allowed": False,
            "contact_scraping_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
        },
        "proof_snapshot": snapshot,
        "value_ladder": value_ladder(snapshot),
        "ranked_targets": ranked_targets,
        "draft_emails": [
            draft_email("utility_or_lab", "OpenPOWER AI / EPRI / EPB / TVA / Tennessee Tech / ORNL technical reviewer", snapshot),
            draft_email("nashville_connector", "Vanderbilt Wond'ry / Nashville EC / local mentor", snapshot),
            draft_email("funder", "LaunchTN / Spark / TAEBC / non-dilutive funding path", snapshot),
        ],
        "send_gate": {
            "send_without_user_review_allowed": False,
            "bulk_email_allowed": False,
            "contact_scraping_allowed": False,
            "requires_exact_recipient": True,
            "requires_physical_mailing_address": True,
            "requires_opt_out_language": True,
            "requires_final_human_approval_at_send_time": True,
        },
        "next_10_actions": [
            "Send one manually reviewed OpenPOWER AI / EPRI / Incubatenergy inquiry if the recipient and footer are approved.",
            "Prepare EPB/ORNL-specific one-page field replay request using historical outage/reroute windows.",
            "Ask Spark/TVA for a technical mentor route and future-grid pilot sponsor path.",
            "Ask Tennessee Tech CESR whether a scale-model grid or SCADA replay protocol review is possible.",
            "Ask Vanderbilt ISIS/CPS for DICE/MissionWeave methodology review, not dollar validation.",
            "Ask LaunchTN about SBIR/STTR support, matching fund timing, and STTR partner routes.",
            "Ask Nashville EC for accelerator/advisor routing and investor/operator feedback.",
            "Keep all outreach language on buyer-authorized replay, not field-validated savings.",
            "Promote the 17-provider broader live-breadth universe through locked benchmarks before broad claims.",
            "Only convert deltas to dollars after an external owner approves the economic conversion.",
        ],
    }
    payload["outreach_board_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "proof_snapshot": payload["proof_snapshot"],
            "ranked_targets": payload["ranked_targets"],
            "draft_emails": payload["draft_emails"],
            "send_gate": payload["send_gate"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    snapshot = payload["proof_snapshot"]
    value = payload["value_ladder"]
    lines = [
        "# Field Validation Outreach Board",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Live Breadth Correction",
        "",
        f"- Champion replay core: `{snapshot['champion_wins']}/{snapshot['champion_holdouts']}` wins vs `{snapshot['named_baseline']}` across `{snapshot['champion_replay_source_system_count']}` source systems.",
        f"- Champion replay estimated rows: `{snapshot['champion_estimated_rows_replayed']}`",
        f"- Broader measured providers: `{snapshot['broader_measured_provider_count']}/{snapshot['broader_enabled_provider_count']}`",
        f"- Fresh rows returned by broader live pull: `{snapshot['fresh_rows_returned']}`",
        f"- Mapped source files/feeds: `{snapshot['manifest_unique_source_count']}`",
        f"- Ready-for-benchmark manifest rows: `{snapshot['manifest_ready_for_benchmark_row_count']}`",
        f"- Boundary: {snapshot['claim_boundary']}",
        "",
        "## Dollar Posture",
        "",
        f"- Claimable today: `{value['claimable_today']['status']}`",
        f"- Paid evidence review range: `{dollars(value['claimable_today']['paid_evidence_review_range_usd']['low'])}` to `{dollars(value['claimable_today']['paid_evidence_review_range_usd']['high'])}` after scope.",
        f"- Safe internal scenario value signal: `{dollars(value['bounded_internal_scenario']['safe_estimated_annual_value_usd'])}/year` under stated assumptions.",
        f"- Broader live-breadth opportunity surface: `{dollars(value['broader_live_breadth_surface']['estimated_annual_value_surface_usd'])}/year`, not a claim.",
        "- What unlocks real dollars: " + "; ".join(value["what_unlocks_real_dollars"]),
        "",
        "## Send Gate",
        "",
        f"- Send without user review allowed: `{str(summary['send_without_user_review_allowed']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Contact scraping allowed: `{str(summary['contact_scraping_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Realized-savings claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        "",
        "## Ranked Targets",
        "",
    ]
    for row in payload["ranked_targets"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['organization']}",
                "",
                f"- Category: `{row['category']}`",
                f"- Locality: `{row['locality']}`",
                f"- Validation lane: `{row['validation_lane']}`",
                f"- Fit score: `{row['fit_score']}`",
                f"- Why: {row['why_this_matters']}",
                f"- First ask: {row['first_ask']}",
                f"- Likely unlock: {', '.join(row['likely_unlock'])}",
                f"- Send now allowed: `{str(row['send_now_allowed']).lower()}`",
                "- Sources:",
            ]
        )
        for source in row["source_refs"]:
            lines.append(f"  - {source['url']} - {source['fact']}")
        lines.append("")
    lines.extend(["## Draft Emails", ""])
    for draft in payload["draft_emails"]:
        lines.extend(
            [
                f"### `{draft['kind']}`",
                "",
                f"Recipient lane: {draft['recipient_label']}",
                f"Subject: {draft['subject']}",
                "",
                "```text",
                draft["body"].rstrip(),
                "```",
                "",
            ]
        )
    lines.extend(["## Next 10 Actions", ""])
    lines.extend([f"{idx}. {item}" for idx, item in enumerate(payload["next_10_actions"], start=1)])
    lines.extend(["", f"Outreach board SHA-256: `{payload['outreach_board_sha256']}`"])
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_MD}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
