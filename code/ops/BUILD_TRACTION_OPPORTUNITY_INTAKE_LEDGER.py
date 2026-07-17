from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

OUT_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "traction_opportunity_intake_ledger.json"
OUT_MD = SPRINT_DIR / "TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md"
CURRENT_RESPONSE_JSON = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json"
MISSIONWEAVE_ACTION_GATE_JSON = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
)

RELATED_CURRENT_RESPONSE_LANES: dict[str, tuple[str, ...]] = {
    "fhwa_tsmo_qualified_partner_outreach": ("fhwa_tsmo_data_initiative",),
    "georgia_patents_pro_bono_intake": (
        "uspto_georgia_patents_route",
        "patent_deadline_counsel",
    ),
    "lvlup_optional_paid_event": ("lvlup_first_check",),
    "sam_public_credential_rotation": ("sam_registration_external_validation_watch",),
    "terry_vynetic_followup": ("evtit_blackdog_inkind",),
}

RELATED_EFFECTIVE_OVERLAY_LANES: dict[str, tuple[str, ...]] = {
    "fhwa_tsmo_qualified_partner_outreach": ("fhwa_tsmo_data_initiative",),
    "georgia_patents_pro_bono_intake": (
        "uspto_georgia_patents_route",
        "patent_deadline_counsel",
    ),
    "lvlup_optional_paid_event": ("lvlup_first_check",),
    "terry_vynetic_followup": ("evtit_blackdog_inkind",),
}

SENSITIVE_MARKERS = [
    "password",
    "zoom.us",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

PUBLIC_SOURCES = {
    "sam_fhwa_tsmo": "https://sam.gov/opp/0ebbe1e43167440ebb111f80fd065ed4/view",
    "sam_nasa_data_center": "https://sam.gov/workspace/contract/opp/b6d14a4b9eac476b997894d0c5a47a27/view",
    "sam_epa_icpoes": "https://sam.gov/opp/d9cebf54026d4eae918897e0c34d5a28/view",
    "sam_fhwa_baa_call_3": "https://sam.gov/opp/99e6bba615c746e9af27e1527a05a897/view",
    "darpa_dice": "https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence",
    "sbir_topics": "https://www.sbir.gov/topics",
    "nsf_project_pitch": "https://seedfund.nsf.gov/project-pitch/",
    "nsf_project_pitch_apply": "https://seedfund.nsf.gov/apply/project-pitch/",
    "uspto_provisional": "https://www.uspto.gov/patents/basics/apply/provisional-application",
    "uspto_utility": "https://www.uspto.gov/patents/basics/apply/utility-patent",
    "uspto_probono": "https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program",
    "georgia_patents": "https://glarts.org/georgia-patents/",
    "lvlup_first_check": "https://www.lvlup.vc/fund/first-check-fund",
    "black_dog": "https://blackdogceo.com/",
    "evtit_event": "https://www.eventbrite.com/e/the-equity-for-code-revolution-evtits-10m-in-kind-venture-fund-tickets-1993026582158",
    "openai_contact_sales": "https://openai.com/contact-sales/",
    "protecnium_its_georgia": "https://protecnium.viterbit.site/its-engineer-highway-infrastructure-project-georgia-usa-rvXJvh2d6fuH/",
}

CONNECTED_EVIDENCE = {
    "gmail_profile": "Robert Ashworth mailbox confirmed through Gmail connector.",
    "gmail_window": "Gmail searched in:anywhere after 2026-04-09 for funding, SBIR, RFI/RFP, deadline, calendar, and application terms.",
    "gmail_latest_response_window": "Gmail reconciled the July 16, 2026 response window for EPRI, CDC, LANL, NASA, Army, SAM, Terry/EVTit, USPTO, LinkedIn, venture, and account-notice updates.",
    "calendar_window": "Google Calendar located the July 9 EVTit discovery meeting; public artifacts intentionally exclude meeting access details.",
    "sweetspot_window": "Sweetspot federal contracts searched for active opportunities after 2026-07-09 and before 2026-08-31 across AI validation, lab data QA, data center, and transportation operations lanes.",
}

LANES: list[dict[str, Any]] = [
    {
        "lane_id": "sam_registration_external_validation_watch",
        "name": "SAM.gov registration external validation watch",
        "channel": "federal_registration",
        "source_kind": "gmail_system_confirmation",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "SAM confirmation says the entity registration remains Submitted until IRS TIN validation and DLA CAGE validation complete; DLA may contact the Government Business POC.",
        "status": "SUBMITTED_EXTERNAL_VALIDATION_PENDING",
        "fit_score": 100,
        "priority": 0,
        "traction_evidence": [
            "SAM.gov confirmed the entity registration was successfully submitted.",
            "The confirmation states IRS validation can take two business days.",
            "The confirmation states DLA CAGE validation averages two business days and can take up to ten business days or longer in peak periods.",
            "The confirmation warns that DLA questions must be answered promptly or the registration can return to Work in Progress.",
        ],
        "reviewer_action": "Monitor SAM status and any DLA email; prepare notarized Entity Administrator letter if required.",
        "human_gate": "Human handles any DLA response, notarized letter, registration correction, or federal certification.",
        "claim_boundary": "Submitted is not Active; no award eligibility, active registration, or CAGE validation is claimed until SAM confirms it.",
        "source_refs": ["gmail:19f48d20c59295b2"],
    },
    {
        "lane_id": "lanl_vision_licensing_followup",
        "name": "LANL VISION licensing opportunity follow-up",
        "channel": "federal_lab_tech_transfer",
        "source_kind": "gmail_lab_response",
        "evidence_date": "2026-07-08",
        "deadline_or_gate": "LANL reply says Mike Erickson is the main point of contact and is out until next week.",
        "status": "WAITING_POC_RETURN",
        "fit_score": 88,
        "priority": 2,
        "traction_evidence": [
            "LANL replied to the VISION licensing opportunity outreach.",
            "The reply identified Mike Erickson as the main point of contact.",
            "The reply indicates follow-up is expected after the POC returns next week.",
        ],
        "reviewer_action": "Prepare a short licensing-fit note, evidence-replay boundary, and technical questions for Mike Erickson.",
        "human_gate": "Human approves any LANL reply, NDA, licensing discussion, export-control response, or disclosure package.",
        "claim_boundary": "This is a POC routing response only; no LANL license, partnership, endorsement, or technical validation is claimed.",
        "source_refs": ["gmail:19f43fa33e165230"],
    },
    {
        "lane_id": "uspto_georgia_patents_route",
        "name": "USPTO / Georgia PATENTS pro bono routing",
        "channel": "ip_readiness",
        "source_kind": "gmail_uspto_response_plus_public_program",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "USPTO Pro Bono response says Georgia PATENTS serves Tennessee inventors; counsel must verify actual patent deadlines and filing posture.",
        "status": "PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED",
        "fit_score": 100,
        "priority": 3,
        "traction_evidence": [
            "USPTO Pro Bono replied to the urgent patent routing request.",
            "The reply points Tennessee inventors to Georgia PATENTS, sponsored by Georgia Lawyers for the Arts.",
            "The route gives LumenCore a concrete counsel-intake path instead of a generic legal search.",
        ],
        "reviewer_action": "Prepare Georgia PATENTS intake packet: filed materials, invention timeline, public disclosure map, claim boundary, and counsel questions.",
        "human_gate": "Human and licensed counsel decide any filing, claim, continuation, PCT, disclosure, or legal strategy.",
        "claim_boundary": "This is not legal advice and does not assert patentability, ownership, deadline sufficiency, or filing entitlement.",
        "source_refs": ["gmail:19f47bc2564305ae", "public:uspto_probono", "public:georgia_patents"],
    },
    {
        "lane_id": "protecnium_its_infrastructure_signal",
        "name": "Protecnium ITS infrastructure signal",
        "channel": "infrastructure_market_signal",
        "source_kind": "linkedin_recruiter_inmail_plus_public_role",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Recruiter asked Robert to apply for an ITS Engineer role on a Georgia highway infrastructure project if interested.",
        "status": "CUSTOMER_DISCOVERY_SIGNAL_ONLY",
        "fit_score": 66,
        "priority": 8,
        "traction_evidence": [
            "LinkedIn recruiter message indicates external recognition of Robert's infrastructure systems profile.",
            "The role maps to highway infrastructure, ITS, and Georgia deployment context.",
            "The signal can inform customer-discovery language for FHWA/TSMO and infrastructure validation, without reframing LumenCore as a job search.",
        ],
        "reviewer_action": "Use as market-context evidence; optionally respond only if it supports partner/customer-discovery.",
        "human_gate": "Human decides whether to reply, apply, or use it only as a customer-discovery clue.",
        "claim_boundary": "This is not a customer commitment, contract, employment acceptance, or pilot demand signal.",
        "source_refs": ["gmail:19f485d99c69a63a", "public:protecnium_its_georgia"],
    },
    {
        "lane_id": "evtit_blackdog_inkind",
        "name": "EVTit / Black Dog in-kind engineering fund",
        "channel": "venture_engineering",
        "source_kind": "gmail_plus_public_program",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Discovery call window occurred July 9, 2026; reset note sent after the timing mix-up; public launch event July 22, 2026.",
        "status": "RESET_NOTE_SENT_TECH_REVIEW_PENDING",
        "fit_score": 92,
        "priority": 1,
        "traction_evidence": [
            "EVTit internal process form requested by Terry Anderton.",
            "LumenCore reply indicates the EVTit application form was submitted.",
            "EVTit email indicated Bruno and Aron were reviewing the materials already sent.",
            "Robert sent a same-day reset note after the meeting-time confusion.",
            "Latest thread evidence shows Terry sent a 4 PM invite after the reset note.",
        ],
        "reviewer_action": "Prepare a concise follow-up packet, technical walkthrough, build-scope menu, and proof-card appendix.",
        "human_gate": "Human approves any follow-up send, scheduling, equity-for-services discussion, or services terms.",
        "claim_boundary": "Meeting and application evidence only; no investment, services award, or partnership has been accepted.",
        "source_refs": [
            "gmail:19f43c8a4ba9346e",
            "gmail:19f44a3d4a48d2c6",
            "gmail:19f47e797960c0cd",
            "gmail:19f4822c21a4a861",
            "gmail:19f484a1fe4aea3b",
            "gmail:19f485a69ba2410d",
            "public:evtit_event",
            "public:black_dog",
        ],
    },
    {
        "lane_id": "lvlup_first_check",
        "name": "LvlUp Ventures First Check Fund",
        "channel": "venture_cash",
        "source_kind": "gmail_plus_public_program",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Submitted July 9, 2026; Gmail reply acknowledged the update.",
        "status": "WAITING_REVIEW",
        "fit_score": 86,
        "priority": 2,
        "traction_evidence": [
            "LumenCore application submitted with proof-to-pilot public proof link.",
            "Jackson Hellmann replied positively to the submitted-update email.",
            "Public program describes first-check funding and startup perks for early founders.",
        ],
        "reviewer_action": "Keep investor brief and short walkthrough ready for under-one-week review.",
        "human_gate": "Human approves any diligence reply or investor terms.",
        "claim_boundary": "Submission and acknowledgement only; no funding decision is represented.",
        "source_refs": ["gmail:19f44c59a4189d31", "public:lvlup_first_check"],
    },
    {
        "lane_id": "darpa_dice_full_submission",
        "name": "DARPA DICE full proposal sprint",
        "channel": "federal_baa",
        "source_kind": "gmail_plus_official_program",
        "evidence_date": "2026-07-08",
        "deadline_or_gate": "Abstract ID HR001126S0010-DICE-PA-052 recorded; full proposal instructions must be confirmed against the controlling BAA before upload.",
        "status": "FULL_PROPOSAL_SPRINT",
        "fit_score": 90,
        "priority": 3,
        "traction_evidence": [
            "Gmail sent follow-up records receipt of the abstract and the assigned identifying number.",
            "Official DARPA DICE page aligns with decentralized coordination and local inference control.",
        ],
        "reviewer_action": "Build full submission matrix, compute plan, performer/team map, and acceptance-test narrative.",
        "human_gate": "Human confirms BAA requirements, reps, budgets, and submission package before any portal action.",
        "claim_boundary": "Abstract receipt is not award selection and not permission to skip BAA instructions.",
        "source_refs": ["gmail:19f4332ca917d603", "public:darpa_dice"],
    },
    {
        "lane_id": "fhwa_tsmo_data_initiative",
        "name": "FHWA TSMO Data Initiative",
        "channel": "federal_contract",
        "source_kind": "sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-08-03 13:00 UTC per Sweetspot search; official SAM notice ID 693JJ326R000012 located.",
        "status": "PHASE_I_TECH_VOLUME",
        "fit_score": 95,
        "priority": 4,
        "traction_evidence": [
            "Sweetspot matched prototype algorithms/models for AI-enabled TSMO data barriers.",
            "Existing LumenCore sprint already contains a Phase I technical capability outline.",
        ],
        "reviewer_action": "Convert the existing outline into a compliance matrix, capability volume, and teaming decision.",
        "human_gate": "Human verifies SAM attachments, terms, pricing, reps/certs, and final submission authority.",
        "claim_boundary": "Prepared capability material only; no FHWA field result, safety benefit, or deployment claim.",
        "source_refs": ["public:sam_fhwa_tsmo", "sweetspot:693JJ326R000012"],
    },
    {
        "lane_id": "nasa_data_center_rfi",
        "name": "NASA Data Center Infrastructure RFI",
        "channel": "federal_rfi",
        "source_kind": "sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-17 21:00 UTC per Sweetspot search; official RFI number 80TECH26RFI0020 located.",
        "status": "RFI_RESPONSE_PREP",
        "fit_score": 89,
        "priority": 5,
        "traction_evidence": [
            "Sweetspot describes NASA interest in modernization, AI-driven operations, resilience, efficiency, and mission continuity.",
            "Existing LumenCore sprint already contains a response outline.",
        ],
        "reviewer_action": "Package the RFI response as architecture, evidence manifest, and operations-risk framing.",
        "human_gate": "Human verifies official response instructions, page limits, contacts, and final send.",
        "claim_boundary": "RFI response only; no NASA partnership, contract, or infrastructure result is represented.",
        "source_refs": ["public:sam_nasa_data_center", "sweetspot:80TECH26RFI0020"],
    },
    {
        "lane_id": "dla_missionweave_sbir",
        "name": "DLA MissionWeave DSIP SBIR",
        "channel": "federal_sbir",
        "source_kind": "existing_sprint_plus_public_sbir",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Current sprint records July 22, 2026 as the active DSIP gate; verify DSIP before final action.",
        "status": "DSIP_PACKAGE_PREP",
        "fit_score": 87,
        "priority": 6,
        "traction_evidence": [
            "Existing sprint contains a MissionWeave fast submission plan.",
            "SBIR.gov topic framework confirms SBIR/STTR topics define the response rules.",
        ],
        "reviewer_action": "Prepare DSIP technical volume, cost notes, and Firm PIN handoff checklist.",
        "human_gate": "Human-only Firm PIN, certifications, cost approval, and final submit.",
        "claim_boundary": "No DLA integration, procurement, or certified readiness claim.",
        "source_refs": ["public:sbir_topics", "local:DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md"],
    },
    {
        "lane_id": "nsf_project_pitch",
        "name": "NSF SBIR/STTR Project Pitch",
        "channel": "federal_sbir",
        "source_kind": "official_public_program",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Rolling pitch gate; NSF requires waiting if a Project Pitch, open invitation, or full proposal is already pending.",
        "status": "PITCH_READY_HUMAN_CHECK",
        "fit_score": 78,
        "priority": 7,
        "traction_evidence": [
            "Existing sprint contains an NSF Project Pitch draft.",
            "NSF public guidance confirms the Project Pitch is the gate before invited full proposal submission.",
        ],
        "reviewer_action": "Check the one-pending-pitch rule and submit only if no conflicting NSF item is pending.",
        "human_gate": "Human approves pitch content and submission.",
        "claim_boundary": "No NSF invitation or full-proposal eligibility is represented unless NSF issues it.",
        "source_refs": ["public:nsf_project_pitch", "public:nsf_project_pitch_apply", "local:NSF_PROJECT_PITCH_DRAFT_2026-07-09.md"],
    },
    {
        "lane_id": "epa_r10_icpoes_route",
        "name": "EPA Region 10 ICP-OES RFI route",
        "channel": "federal_market_research",
        "source_kind": "gmail_plus_sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-21 21:30 UTC per Sweetspot search; official notice ID 68HE0726Q0027 located.",
        "status": "ROUTE_ONLY_LOW_FIT",
        "fit_score": 42,
        "priority": 8,
        "traction_evidence": [
            "LumenCore already sent a boundary-safe email clarifying it is not an ICP-OES OEM/reseller.",
            "The only viable angle is routing to lab data QA or audit-ready reporting needs.",
        ],
        "reviewer_action": "Wait for agency routing response; do not prepare a hardware quote.",
        "human_gate": "Human approves any further agency contact.",
        "claim_boundary": "No instrument supply, OEM, reseller, or lab-services qualification claim.",
        "source_refs": ["gmail:19f4332fa2615bd6", "public:sam_epa_icpoes", "sweetspot:68HE0726Q0027"],
    },
    {
        "lane_id": "epa_ucmr6_partner_only",
        "name": "EPA UCMR 6 analytical chemistry lab services",
        "channel": "federal_sources_sought",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-21 20:00 UTC per Sweetspot search.",
        "status": "PARTNER_ONLY",
        "fit_score": 46,
        "priority": 9,
        "traction_evidence": [
            "Scope is analytical chemistry laboratory services, not a software-only proof-to-pilot lane.",
            "Possible fit only as a data QA, anomaly review, or reporting subcontractor to a qualified lab.",
        ],
        "reviewer_action": "Hold for qualified lab partner; do not chase as prime.",
        "human_gate": "Human approves partner outreach.",
        "claim_boundary": "No testing lab, contaminant monitoring, or regulated lab-services claim.",
        "source_refs": ["sweetspot:68HERW26R0020"],
    },
    {
        "lane_id": "fhwa_infrastructure_baa_call3",
        "name": "FHWA Infrastructure R&D BAA Call 3.0",
        "channel": "federal_baa",
        "source_kind": "sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-24 17:00 UTC per Sweetspot search; official SAM call located.",
        "status": "SCOUT_TOPIC_MATCH",
        "fit_score": 64,
        "priority": 10,
        "traction_evidence": [
            "Could fit if a topic supports evidence replay, digital asset validation, or nondestructive-evaluation data workflows.",
            "Requires topic-by-topic Appendix C fit check before effort.",
        ],
        "reviewer_action": "Download official attachments and score each Appendix C topic before drafting.",
        "human_gate": "Human approves topic selection and submission.",
        "claim_boundary": "No claim that LumenCore fits all BAA topics.",
        "source_refs": ["public:sam_fhwa_baa_call_3", "sweetspot:693JJ3-23-BAA-0002-3"],
    },
    {
        "lane_id": "hhs_ai_power_user_pilot",
        "name": "HHS AI Power User Advanced Models and Features Pilot",
        "channel": "federal_contract",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-14 21:00 UTC per Sweetspot search.",
        "status": "DO_NOT_PRIME_SOLO",
        "fit_score": 38,
        "priority": 11,
        "traction_evidence": [
            "Attractive AI governance language, but Sweetspot indicates a strict security/authorization pathway.",
            "Solo-prime posture is not reviewer-safe unless a qualified platform partner leads.",
        ],
        "reviewer_action": "Do not chase solo; use as partner-target intelligence only.",
        "human_gate": "Human approves any partner route.",
        "claim_boundary": "No FedRAMP, ATO, HHS pilot, or government production-access claim.",
        "source_refs": ["sweetspot:7571TE26R00004"],
    },
    {
        "lane_id": "csosa_public_safety_analytics",
        "name": "CSOSA Public Safety Data Analytics Platform",
        "channel": "federal_contract",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-14 16:00 UTC per Sweetspot search.",
        "status": "DO_NOT_PRIME_SOLO",
        "fit_score": 35,
        "priority": 12,
        "traction_evidence": [
            "Analytics platform language is relevant, but Sweetspot indicates an active FedRAMP Moderate gate at quote submission.",
            "LumenCore should not represent qualification for this without a compliant platform partner.",
        ],
        "reviewer_action": "Park as a partner-only signal; do not spend proposal time as prime.",
        "human_gate": "Human approves any partner route.",
        "claim_boundary": "No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.",
        "source_refs": ["sweetspot:9594CS26Q0053"],
    },
    {
        "lane_id": "defense_energy_consortium",
        "name": "Defense Energy Consortium CMO",
        "channel": "federal_contract",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-30 19:00 UTC per Sweetspot search.",
        "status": "PARTNER_INTRO_ONLY",
        "fit_score": 58,
        "priority": 13,
        "traction_evidence": [
            "Energy resilience and facility-management language can map to proof-to-pilot evidence workflows.",
            "The prime role appears to require consortium management and private-capital mobilization beyond current solo posture.",
        ],
        "reviewer_action": "Use as investor/strategic-partner conversation material, not immediate solo proposal.",
        "human_gate": "Human approves any partner or investor intro.",
        "claim_boundary": "No consortium management, energy project financing, or installation-performance claim.",
        "source_refs": ["sweetspot:FA8003-26-R-0023"],
    },
    {
        "lane_id": "openai_api_continuity",
        "name": "OpenAI API continuity request",
        "channel": "vendor_credit_or_partner_route",
        "source_kind": "gmail_plus_official_page",
        "evidence_date": "2026-07-08",
        "deadline_or_gate": "No deadline found; request should be submitted through official contact-sales path if still needed.",
        "status": "HUMAN_FORM_READY",
        "fit_score": 80,
        "priority": 14,
        "traction_evidence": [
            "Self-sent packet frames API continuity as a blocker for grant factory and proof-stack maintenance.",
            "Official contact-sales page is the clean route for enterprise/startup routing.",
        ],
        "reviewer_action": "Submit or update the official contact request with conservative proof-to-pilot framing.",
        "human_gate": "Human submits the vendor form and approves any billing or credit terms.",
        "claim_boundary": "No credit, free account, or vendor approval is represented.",
        "source_refs": ["gmail:19f43a156bcf0ab6", "public:openai_contact_sales"],
    },
    {
        "lane_id": "openai_build_week_prooflock",
        "name": "OpenAI Build Week - ProofLock Console",
        "channel": "developer_challenge",
        "source_kind": "gmail_plus_official_rules_plus_git_commit",
        "evidence_date": "2026-07-17",
        "deadline_or_gate": "Final submission deadline is 2026-07-21 17:00 Pacific / 19:00 Central / 2026-07-22 00:00 UTC per the official Devpost overview and rules.",
        "status": "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN",
        "fit_score": 93,
        "priority": 2,
        "traction_evidence": [
            "Official OpenAI email announced the challenge, deadline, and $100,000 total prize pool.",
            "Official rules allow a meaningfully extended pre-existing project when post-start work is clearly documented.",
            "ProofLock Console was added after the submission period opened in commit 1578504204c429d7f05779897dc3d5430038f681.",
            "The browser and Python verifiers both match 4/4 public V2/V3 artifacts and keep four engineering/release gates open.",
        ],
        "reviewer_action": "Confirm GPT-5.6 provenance and the /feedback Session ID, deploy the public demo, record the public under-three-minute YouTube demo, then populate and review the Devpost draft.",
        "human_gate": "Human logs in or registers with Devpost, reviews publicity/IP terms and every populated field, and approves the final submission action.",
        "claim_boundary": "This is a verified project-readiness lane, not proof of Devpost registration, model identity, final submission, eligibility acceptance, judging outcome, OpenAI endorsement, prize entitlement, external validation, or commercial value.",
        "source_refs": [
            "gmail:19f71ed715ce0c9f",
            "public:https://openai.devpost.com/",
            "public:https://openai.devpost.com/rules",
            "github:1578504204c429d7f05779897dc3d5430038f681",
        ],
    },
    {
        "lane_id": "patent_deadline_counsel",
        "name": "Patent counsel / IP deadline defense",
        "channel": "ip_readiness",
        "source_kind": "gmail_plus_uspto_public_guidance",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Dossier email states a July 25, 2025 filing date; USPTO Pro Bono routed Tennessee inventors to Georgia PATENTS; counsel must verify all actual patent deadlines before action.",
        "status": "PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED",
        "fit_score": 100,
        "priority": 15,
        "traction_evidence": [
            "Patent counsel outreach was sent with application number, title, and requested limited-scope/pro bono routing.",
            "USPTO Pro Bono response identified Georgia PATENTS as the Tennessee inventor route.",
            "USPTO public guidance confirms provisional-to-nonprovisional timing is deadline-sensitive when applicable.",
        ],
        "reviewer_action": "Prepare Georgia PATENTS intake packet, monitor counsel replies, and avoid public claim expansion until counsel reviews.",
        "human_gate": "Human and licensed counsel decide any filing, claim, continuation, PCT, or disclosure action.",
        "claim_boundary": "This ledger is not legal advice and does not assert patentability, ownership, or filing sufficiency.",
        "source_refs": [
            "gmail:19f43b89dd51e2fd",
            "gmail:19f47bc2564305ae",
            "public:uspto_provisional",
            "public:uspto_utility",
            "public:uspto_probono",
            "public:georgia_patents",
        ],
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def lane_hash(lane: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(lane, sort_keys=True).encode("utf-8")).hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def public_safe_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return value.replace("one-time-password", "one-time verification code").replace(
        "password", "credential secret"
    )


def current_response_overlay() -> dict[str, Any]:
    payload = read_json(CURRENT_RESPONSE_JSON)
    if payload.get("schema") != "lumencore.external_engagement_response_register.v1":
        raise ValueError("Current external-engagement register is missing or has the wrong schema")
    records = payload.get("records")
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise ValueError("Current external-engagement register records are malformed")
    lane_ids = [str(row.get("lane_id", "")) for row in records]
    if any(not lane_id for lane_id in lane_ids) or len(set(lane_ids)) != len(lane_ids):
        raise ValueError("Current external-engagement register lane IDs are missing or duplicated")
    if payload.get("summary", {}).get("record_count") != len(records):
        raise ValueError("Current external-engagement register record count is inconsistent")
    for row in records:
        recorded_hash = row.get("record_sha256")
        unhashed = dict(row)
        unhashed.pop("record_sha256", None)
        if not isinstance(recorded_hash, str) or canonical_hash(unhashed) != recorded_hash:
            raise ValueError(
                f"Current response record hash mismatch: {row.get('lane_id', 'UNKNOWN')}"
            )
    recorded_register_hash = payload.get("register_sha256")
    unhashed_register = dict(payload)
    unhashed_register.pop("register_sha256", None)
    if (
        not isinstance(recorded_register_hash, str)
        or canonical_hash(unhashed_register) != recorded_register_hash
    ):
        raise ValueError("Current external-engagement register hash mismatch")
    return payload


def missionweave_action_gate_overlay() -> dict[str, Any]:
    payload = read_json(MISSIONWEAVE_ACTION_GATE_JSON)
    if payload.get("schema") != "lumencore.missionweave_dsip_action_gate.v1":
        raise ValueError("MissionWeave action gate is missing or has the wrong schema")
    recorded_hash = payload.get("gate_sha256")
    unhashed = dict(payload)
    unhashed.pop("gate_sha256", None)
    if not isinstance(recorded_hash, str) or canonical_hash(unhashed) != recorded_hash:
        raise ValueError("MissionWeave action-gate hash mismatch")
    gate_summary = payload.get("gate_summary", {})
    required = gate_summary.get("required_private_gate_count")
    passed = gate_summary.get("passed_private_gate_count")
    open_count = gate_summary.get("open_gate_count")
    if not all(isinstance(value, int) for value in (required, passed, open_count)):
        raise ValueError("MissionWeave action-gate counts are malformed")
    if passed + open_count != required:
        raise ValueError("MissionWeave action-gate counts are inconsistent")
    return payload


def compact_current_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "lane_id": row.get("lane_id"),
        "organization": row.get("organization"),
        "state": row.get("state"),
        "decision": row.get("decision"),
        "deadline": row.get("deadline"),
        "no_send_before": row.get("no_send_before"),
        "send_now": row.get("send_now"),
        "do_not_duplicate_send": row.get("do_not_duplicate_send"),
        "response_channel": row.get("response_channel"),
        "response_ready": row.get("response_ready"),
        "action_gate": public_safe_text(row.get("action_gate")),
        "next_action": public_safe_text(row.get("next_action")),
        "claim_boundary": public_safe_text(row.get("claim_boundary")),
        "response_artifact": row.get("response_artifact"),
        "supporting_artifacts": row.get("supporting_artifacts", []),
        "related_legacy_lane_ids": list(
            RELATED_CURRENT_RESPONSE_LANES.get(str(row.get("lane_id")), ())
        ),
        "record_sha256": row.get("record_sha256"),
    }


def build_payload() -> dict[str, Any]:
    response_control = current_response_overlay()
    missionweave_gate = missionweave_action_gate_overlay()
    response_records = {
        str(row.get("lane_id")): row
        for row in response_control.get("records", [])
        if isinstance(row, dict) and row.get("lane_id")
    }
    current_response_queue = [
        compact_current_response(row) for row in response_control["records"]
    ]
    legacy_lane_ids = {str(lane["lane_id"]) for lane in LANES}
    related_response_records: dict[str, list[dict[str, Any]]] = {}
    for current in current_response_queue:
        for related_lane_id in current["related_legacy_lane_ids"]:
            related_response_records.setdefault(related_lane_id, []).append(current)

    mission_summary = missionweave_gate["gate_summary"]
    mission_deadline = missionweave_gate["deadline"]
    lanes = []
    for lane in LANES:
        row = dict(lane)
        current = response_records.get(str(row.get("lane_id")))
        effective_status = row["status"]
        effective_deadline_or_gate = row["deadline_or_gate"]
        effective_reviewer_action = row["reviewer_action"]
        effective_claim_boundary = row["claim_boundary"]
        effective_source = "legacy_intake_baseline"
        if current:
            row["current_response_control"] = {
                "as_of_date": response_control.get("as_of_date"),
                **compact_current_response(current),
            }
            effective_status = str(current.get("state"))
            effective_deadline_or_gate = str(
                current.get("deadline") or current.get("action_gate") or "No current deadline recorded"
            )
            effective_reviewer_action = str(current.get("next_action"))
            effective_claim_boundary = str(current.get("claim_boundary"))
            effective_source = rel(CURRENT_RESPONSE_JSON)
        related = related_response_records.get(str(row.get("lane_id")), [])
        if related:
            row["related_current_response_controls"] = related
        effective_related = next(
            (
                related_row
                for related_row in related
                if row.get("lane_id")
                in RELATED_EFFECTIVE_OVERLAY_LANES.get(
                    str(related_row.get("lane_id")), ()
                )
            ),
            None,
        )
        if current is None and effective_related is not None:
            effective_status = str(effective_related["state"])
            effective_deadline_or_gate = str(
                effective_related.get("deadline")
                or effective_related.get("action_gate")
                or "No current deadline recorded"
            )
            effective_reviewer_action = str(effective_related["next_action"])
            effective_claim_boundary = str(effective_related["claim_boundary"])
            effective_source = (
                f"{rel(CURRENT_RESPONSE_JSON)}#related:{effective_related['lane_id']}"
            )
        if row.get("lane_id") == "dla_missionweave_sbir":
            row["current_action_gate"] = {
                "status": missionweave_gate["status"],
                "deadline_expected_local": mission_deadline["expected_local"],
                "deadline_expected_utc": mission_deadline["expected_utc"],
                "live_dsip_recheck_required": mission_deadline[
                    "live_dsip_recheck_required"
                ],
                "passed_gate_count": mission_summary["passed_private_gate_count"],
                "open_gate_count": mission_summary["open_gate_count"],
                "required_gate_count": mission_summary[
                    "required_private_gate_count"
                ],
                "submission_ready_for_human_click": missionweave_gate[
                    "submission_ready_for_human_click"
                ],
                "claim_boundary": missionweave_gate["claim_boundary"],
                "source": rel(MISSIONWEAVE_ACTION_GATE_JSON),
                "gate_sha256": missionweave_gate["gate_sha256"],
            }
            effective_status = str(missionweave_gate["status"])
            effective_deadline_or_gate = (
                f"{mission_deadline['expected_local']} "
                f"({mission_deadline['expected_utc']}); live DSIP recheck required"
            )
            effective_reviewer_action = (
                f"Resolve the {mission_summary['open_gate_count']} open gates out of "
                f"{mission_summary['required_private_gate_count']}, review the complete portal "
                "preview, and retain the human-only final-submit boundary."
            )
            effective_claim_boundary = str(missionweave_gate["claim_boundary"])
            effective_source = rel(MISSIONWEAVE_ACTION_GATE_JSON)
        row["effective_status"] = effective_status
        row["effective_deadline_or_gate"] = effective_deadline_or_gate
        row["effective_reviewer_action"] = effective_reviewer_action
        row["effective_claim_boundary"] = effective_claim_boundary
        row["effective_source"] = effective_source
        row["lane_sha256"] = lane_hash(row)
        row["human_gate_required"] = True
        lanes.append(row)

    status_counts: dict[str, int] = {}
    effective_status_counts: dict[str, int] = {}
    channel_counts: dict[str, int] = {}
    source_kind_counts: dict[str, int] = {}
    for lane in lanes:
        status_counts[lane["status"]] = status_counts.get(lane["status"], 0) + 1
        effective_status = str(lane["effective_status"])
        effective_status_counts[effective_status] = (
            effective_status_counts.get(effective_status, 0) + 1
        )
        channel_counts[lane["channel"]] = channel_counts.get(lane["channel"], 0) + 1
        source_kind_counts[lane["source_kind"]] = source_kind_counts.get(lane["source_kind"], 0) + 1

    public_ref_count = sum(
        1
        for lane in lanes
        for ref in lane["source_refs"]
        if str(ref).startswith("public:")
    )
    gmail_ref_count = sum(
        1
        for lane in lanes
        for ref in lane["source_refs"]
        if str(ref).startswith("gmail:")
    )
    sweetspot_ref_count = sum(
        1
        for lane in lanes
        for ref in lane["source_refs"]
        if str(ref).startswith("sweetspot:")
    )

    payload = {
        "generated_utc": now_utc(),
        "schema": "traction_opportunity_intake_ledger_v1",
        "status": "TRACTION_INTAKE_READY_HUMAN_ACTION_REQUIRED",
        "summary": {
            "lane_count": len(lanes),
            "top_priority_count": sum(1 for lane in lanes if int(lane["priority"]) <= 7),
            "gmail_reference_count": gmail_ref_count,
            "sweetspot_reference_count": sweetspot_ref_count,
            "public_reference_count": public_ref_count,
            "status_counts": dict(sorted(status_counts.items())),
            "effective_status_counts": dict(sorted(effective_status_counts.items())),
            "channel_counts": dict(sorted(channel_counts.items())),
            "source_kind_counts": dict(sorted(source_kind_counts.items())),
            "human_action_required": True,
            "final_submission_allowed_without_human": False,
            "external_send_allowed_without_human": False,
            "current_response_record_count": response_control["summary"]["record_count"],
            "current_immediate_human_action_count": response_control["summary"]["immediate_human_action_count"],
            "current_do_not_duplicate_send_count": response_control["summary"]["do_not_duplicate_send_count"],
            "current_state_supersedes_legacy_when_present": True,
            "current_response_queue_count": len(current_response_queue),
            "current_response_exact_overlay_count": sum(
                1 for row in current_response_queue if row["lane_id"] in legacy_lane_ids
            ),
            "current_response_related_control_count": sum(
                1 for row in current_response_queue if row["related_legacy_lane_ids"]
            ),
            "missionweave_passed_gate_count": mission_summary[
                "passed_private_gate_count"
            ],
            "missionweave_open_gate_count": mission_summary["open_gate_count"],
            "missionweave_required_gate_count": mission_summary[
                "required_private_gate_count"
            ],
            "missionweave_submission_ready_for_human_click": missionweave_gate[
                "submission_ready_for_human_click"
            ],
        },
        "connected_evidence": {
            **CONNECTED_EVIDENCE,
            "external_engagement_response_register": (
                f"Tracked current-state register reconciled through {response_control['as_of_date']}; its state and response decision "
                "supersede legacy July 9 lane status where both are present."
            ),
            "missionweave_dsip_action_gate": (
                f"Integrity-checked action gate reports {mission_summary['passed_private_gate_count']}/"
                f"{mission_summary['required_private_gate_count']} gates passed and "
                f"{mission_summary['open_gate_count']} open; final submission remains human-only."
            ),
        },
        "current_response_control": {
            "as_of_date": response_control["as_of_date"],
            "status": response_control["status"],
            "direct_answer": response_control["direct_answer"],
            "source": rel(CURRENT_RESPONSE_JSON),
            "register_sha256": response_control["register_sha256"],
            "records": current_response_queue,
            "claim_boundary": response_control["claim_boundary"],
        },
        "missionweave_action_gate": {
            "status": missionweave_gate["status"],
            "deadline": mission_deadline,
            "gate_summary": mission_summary,
            "submission_ready_for_human_click": missionweave_gate[
                "submission_ready_for_human_click"
            ],
            "source": rel(MISSIONWEAVE_ACTION_GATE_JSON),
            "gate_sha256": missionweave_gate["gate_sha256"],
            "claim_boundary": missionweave_gate["claim_boundary"],
        },
        "public_sources": PUBLIC_SOURCES,
        "lanes": sorted(lanes, key=lambda item: int(item["priority"])),
        "next_actions": [
            "Complete the Nashville EC founder-fact gate and reviewed portal workflow well before 2026-07-17T23:59:00-05:00; do not duplicate the deadline-support email.",
            "Do not duplicate-send NASA, Army, CDC, LANL, EPRI, Georgia PATENTS, FHWA, Terry/Vynetic, or LvlUp packets already controlled by the current register.",
            f"Resolve MissionWeave's {mission_summary['open_gate_count']} open gates and recheck the live DSIP deadline before the expected July 22, 2026 noon Eastern close.",
            "Monitor the existing FHWA referral thread; no fit check, partner commitment, or additional send is currently supported.",
            "Build DICE full-proposal compliance matrix after confirming controlling BAA instructions.",
            "Submit or refresh OpenAI API continuity request through official contact route if still needed.",
            "Monitor patent counsel replies and prepare filed-materials packet for licensed review.",
        ],
        "sanitization": {
            "public_packet_excludes_meeting_links": True,
            "public_packet_excludes_phone_numbers": True,
            "public_packet_excludes_financial_account_data": True,
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["ledger_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    current = payload["current_response_control"]
    lines = [
        (
            "# Traction Opportunity Intake Ledger - Current Control "
            f"{current['as_of_date']} (Legacy Intake 2026-07-09)"
        ),
        "",
        "Purpose: turn connected Gmail evidence, federal contract search, and official public sources into a reviewer-safe action queue.",
        "",
        "This ledger does not authorize portal submissions, email sends, certifications, calendar edits, IP filings, trading, or capital movement. It is an intake and prioritization artifact for human review.",
        "",
        "## Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lanes tracked: `{summary['lane_count']}`",
        f"- Top priority lanes: `{summary['top_priority_count']}`",
        f"- Gmail references: `{summary['gmail_reference_count']}`",
        f"- Sweetspot references: `{summary['sweetspot_reference_count']}`",
        f"- Public references: `{summary['public_reference_count']}`",
        f"- Current response records: `{summary['current_response_record_count']}`",
        f"- Current immediate human actions: `{summary['current_immediate_human_action_count']}`",
        f"- Current do-not-duplicate sends: `{summary['current_do_not_duplicate_send_count']}`",
        f"- Current response queue records: `{summary['current_response_queue_count']}`",
        f"- Exact legacy-lane overlays: `{summary['current_response_exact_overlay_count']}`",
        f"- Related current controls: `{summary['current_response_related_control_count']}`",
        (
            "- MissionWeave gates: "
            f"`{summary['missionweave_passed_gate_count']}/"
            f"{summary['missionweave_required_gate_count']}` passed; "
            f"`{summary['missionweave_open_gate_count']}` open"
        ),
        (
            "- MissionWeave ready for human final click: "
            f"`{str(summary['missionweave_submission_ready_for_human_click']).lower()}`"
        ),
        f"- Current state supersedes legacy when present: `{str(summary['current_state_supersedes_legacy_when_present']).lower()}`",
        f"- Human action required: `{str(summary['human_action_required']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Ledger SHA-256: `{payload['ledger_sha256']}`",
        "",
        "## Source Coverage",
        "",
    ]
    for key, value in payload["connected_evidence"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Current Response Overlay",
            "",
            current["direct_answer"],
            "",
            "This overlay is authoritative through the stated as-of date and supersedes a legacy lane status where the two differ. Historical status remains visible below for provenance.",
            "",
            f"- As of: `{current['as_of_date']}`",
            f"- Source: `{current['source']}`",
            f"- Register SHA-256: `{current['register_sha256']}`",
            "",
            "| Organization | Current state | Current decision | Deadline | Send now | Duplicate send |",
            "|---|---|---|---|---:|---:|",
        ]
    )
    for row in current["records"]:
        lines.append(
            f"| {row['organization']} | `{row['state']}` | `{row['decision']}` | "
            f"{row['deadline'] or 'None recorded'} | "
            f"`{str(row['send_now']).lower()}` | "
            f"`{str(row['do_not_duplicate_send']).lower()}` |"
        )
    lines.extend(["", "## Current Response Queue", ""])
    for row in current["records"]:
        lines.extend(
            [
                f"### {row['organization']}",
                "",
                f"- Lane ID: `{row['lane_id']}`",
                f"- State: `{row['state']}`",
                f"- Decision: `{row['decision']}`",
                f"- Deadline: {row['deadline'] or 'None recorded'}",
                f"- Send now: `{str(row['send_now']).lower()}`",
                f"- Do not duplicate: `{str(row['do_not_duplicate_send']).lower()}`",
                f"- Next action: {row['next_action']}",
                f"- Action gate: {row['action_gate']}",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Record SHA-256: `{row['record_sha256']}`",
                "",
            ]
        )
    lines.extend(["## Legacy Intake Queue With Effective-State Controls", ""])
    for lane in payload["lanes"]:
        lines.extend(
            [
                f"### {lane['priority']}. {lane['name']}",
                "",
                f"- Lane ID: `{lane['lane_id']}`",
                f"- Channel: `{lane['channel']}`",
                f"- Legacy intake status: `{lane['status']}`",
                f"- Effective current status: `{lane['effective_status']}`",
                f"- Fit score: `{lane['fit_score']}`",
                f"- Legacy intake gate: {lane['deadline_or_gate']}",
                f"- Effective current gate: {lane['effective_deadline_or_gate']}",
                f"- Effective reviewer action: {lane['effective_reviewer_action']}",
                f"- Effective state source: `{lane['effective_source']}`",
                f"- Human gate: {lane['human_gate']}",
                f"- Effective claim boundary: {lane['effective_claim_boundary']}",
                f"- Evidence hash: `{lane['lane_sha256']}`",
            ]
        )
        current_lane = lane.get("current_response_control")
        if isinstance(current_lane, dict):
            lines.extend(
                [
                    f"- Current response state: `{current_lane['state']}`",
                    f"- Current response decision: `{current_lane['decision']}`",
                    f"- Current do-not-duplicate send: `{str(current_lane['do_not_duplicate_send']).lower()}`",
                    f"- Current next action: {current_lane['next_action']}",
                ]
            )
        current_gate = lane.get("current_action_gate")
        if isinstance(current_gate, dict):
            lines.extend(
                [
                    (
                        "- Current action-gate progress: "
                        f"`{current_gate['passed_gate_count']}/"
                        f"{current_gate['required_gate_count']}` passed; "
                        f"`{current_gate['open_gate_count']}` open"
                    ),
                    (
                        "- Ready for human final click: "
                        f"`{str(current_gate['submission_ready_for_human_click']).lower()}`"
                    ),
                    f"- Current action-gate source: `{current_gate['source']}`",
                    f"- Current action-gate SHA-256: `{current_gate['gate_sha256']}`",
                ]
            )
        related_controls = lane.get("related_current_response_controls", [])
        for related in related_controls:
            lines.extend(
                [
                    (
                        f"- Related current control `{related['lane_id']}`: "
                        f"`{related['state']}` / `{related['decision']}`"
                    ),
                    f"- Related current next action: {related['next_action']}",
                    (
                        "- Related current do-not-duplicate send: "
                        f"`{str(related['do_not_duplicate_send']).lower()}`"
                    ),
                ]
            )
        lines.append("- Evidence:")
        for item in lane["traction_evidence"]:
            lines.append(f"  - {item}")
        lines.append("- Sources:")
        for ref in lane["source_refs"]:
            lines.append(f"  - `{ref}`")
        lines.append("")
    lines.extend(["## Public Source Map", ""])
    for key, value in sorted(payload["public_sources"].items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Immediate Next Actions", ""])
    for item in payload["next_actions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Human-Only Boundary",
            "",
            "No final portal action, email send, certification, legal filing, pricing approval, account authorization, or investor term acceptance is authorized by this ledger.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(
        markdown + "\n" + json.dumps(payload, sort_keys=True)
    )
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public ledger markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
