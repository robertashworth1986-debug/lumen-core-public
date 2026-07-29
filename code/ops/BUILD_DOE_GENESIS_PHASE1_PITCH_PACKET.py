"""Build a source-bound DOE Genesis Mission Phase I pitch packet.

This builder prepares a bounded draft and readiness audit only. It has no
email, authentication, upload, certification, signature, or submission path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
SOURCE_DIR = SPRINT_DIR / "source_attachments" / "DOE_FY26_GENESIS"
GUIDE_PATH = SOURCE_DIR / "Pitch-Stage-Key-Questions.docx"
WATCH_PATH = ROOT / "out" / "grants" / "doe_fy26_watch.json"
OUTPUT_JSON = SPRINT_DIR / "DOE_FY26_GENESIS_PHASE1_PITCH_PACKET_2026-07-29.json"
OUTPUT_MD = SPRINT_DIR / "DOE_FY26_GENESIS_PHASE1_PITCH_PACKET_2026-07-29.md"

SCHEMA = "lumencore.doe_genesis_phase1_pitch_packet.v1"
EXPECTED_GUIDE_SHA256 = (
    "06CABDB6F8CAA8BDD80AB5BDE1FFD916DD76DA18CB6DCDF7BDE48AB112196AE4"
)
TOPIC = "Achieving AI-Driven Autonomous Laboratories"
CONCEPT_NAME = "LumenCore Autonomous Experiment Assurance Plane"
WORD_LIMITS = {
    "summary_topic_mission_alignment": 100,
    "technical_promise": 200,
    "commercialization_potential": 200,
    "team_qualifications": 200,
}
OFFICIAL_SOURCES = {
    "opportunity": (
        "https://sbir-sttr.connectwerx.org/portfolio-items/fy26genesismission/"
    ),
    "eligibility": "https://sbir-sttr.connectwerx.org/eligibility-criteria/",
    "registrations": (
        "https://www.energy.gov/technologycommercialization/"
        "required-sbirsttr-registrations"
    ),
    "doe_program": (
        "https://www.energy.gov/technologycommercialization/"
        "doe-small-business-innovation-research-sbir-and-small-business"
    ),
    "faq_and_resources": "https://sbir-sttr.connectwerx.org/resources/",
}
REFERENCE_CANDIDATES = [
    {
        "name": "Bluesky simulated hardware tutorial",
        "url": "https://blueskyproject.io/tutorials/Hello%20Bluesky.html",
        "use": "candidate simulation and orchestration baseline",
        "relationship_claimed": False,
    },
    {
        "name": "Bluesky plan simulation documentation",
        "url": "https://blueskyproject.io/bluesky/main/simulation.html",
        "use": "candidate pre-execution inspection baseline",
        "relationship_claimed": False,
    },
    {
        "name": "HELAO autonomous laboratory framework",
        "url": "https://pubs.rsc.org/en/content/articlehtml/2023/dd/d3dd00166k",
        "use": "candidate distributed-instrument orchestration baseline",
        "relationship_claimed": False,
    },
    {
        "name": "NIST modular and autonomous laboratory ecosystem",
        "url": (
            "https://www.nist.gov/programs-projects/"
            "development-standards-support-modular-and-autonomous-"
            "laboratory-ecosystem"
        ),
        "use": "standards landscape and prior-system boundary",
        "relationship_claimed": False,
    },
    {
        "name": "NREL autonomous experimentation",
        "url": "https://www.nrel.gov/materials-science/autonomous-experimentation",
        "use": "application context and customer-discovery reference",
        "relationship_claimed": False,
    },
]
EVIDENCE_FILES = [
    {
        "path": "build_week/prooflock_console/verify_receipt.py",
        "supports": (
            "deterministic receipt verification and separation of integrity "
            "from promotion"
        ),
        "evidence_level": "BOUNDED_SOFTWARE_IMPLEMENTATION",
    },
    {
        "path": "tests/test_prooflock_console.py",
        "supports": (
            "adversarial tests for tampering, path traversal, missing evidence, "
            "and premature promotion"
        ),
        "evidence_level": "LOCAL_SOFTWARE_TEST",
    },
    {
        "path": "out/ops/source_native_family_baseline_ledger_latest.json",
        "supports": "source-native baseline accounting and claim suppression",
        "evidence_level": "LOCAL_RESEARCH_LEDGER",
    },
    {
        "path": "out/ops/time_series_source_native_prospective_protocol_status.json",
        "supports": "frozen prospective protocol and wait-for-future-data state",
        "evidence_level": "LOCAL_PROTOCOL_RECEIPT",
    },
    {
        "path": "docs/ALPHA_EDGE_EVIDENCE_AUDIT_2026-07-29.md",
        "supports": "preservation and classification of negative results",
        "evidence_level": "LOCAL_SKEPTICAL_AUDIT",
    },
    {
        "path": "docs/FULL_GEOMETRY_PROTOCOL_FIELD_2026-07-29.md",
        "supports": "implemented-versus-unimplemented family accounting",
        "evidence_level": "LOCAL_COVERAGE_AUDIT",
    },
    {
        "path": "code/hardware/lumenshell_safety_state_machine.py",
        "supports": (
            "software-only fail-closed state and fault-lockout patterns; "
            "no physical safety case"
        ),
        "evidence_level": "EXECUTABLE_SOFTWARE_REQUIREMENTS_MODEL",
    },
    {
        "path": "tests/test_autonomous_agent_manifest_security.py",
        "supports": (
            "local tests for authorization, payload filtering, and "
            "human-controlled action gates"
        ),
        "evidence_level": "LOCAL_SOFTWARE_TEST",
    },
]

PITCH_DRAFTS = {
    "summary_topic_mission_alignment": (
        "LumenCore Autonomous Experiment Assurance Plane is proposed middleware "
        "between AI experiment planners and laboratory instruments. It would "
        "convert experiments into machine-checkable contracts defining "
        "authorized actions, parameter bounds, required data and provenance, "
        "stopping rules, and human approvals; block noncompliant commands "
        "before dispatch; and issue replayable evidence capsules linking plans, "
        "inputs, actions, outputs, deviations, and negative results. Phase I "
        "would test only instrument simulators and synthetic workflows; no "
        "laboratory deployment is claimed. The project addresses Achieving "
        "AI-Driven Autonomous Laboratories by targeting repeatability, safer "
        "closed-loop automation, and richer auditable datasets without "
        "replacing laboratory control systems."
    ),
    "technical_promise": (
        "Autonomous laboratories can accelerate discovery, but nondeterministic "
        "AI planners can change hypotheses, parameters, or stopping criteria "
        "mid-run, complicating repeatability and scientific review. Current "
        "workflow engines, experiment trackers, and policy tools address parts "
        "of this problem. The research question is whether an interoperable "
        "assurance layer can bind them into one enforceable experiment contract "
        "without unacceptable latency or false blocks. The proposed innovation "
        "is a policy-compiled contract that binds the hypothesis, design space, "
        "baselines, instrument capabilities, approval points, data schema, and "
        "falsification rules before execution. A runtime mediator would validate "
        "every action against that contract and generate an evidence capsule "
        "linking plans, commands, observations, model versions, deviations, and "
        "preserved null results. This is a proposed integration and control "
        "method, not a deployed laboratory capability. Within 6 to 12 months, "
        "Phase I would implement adapters for three instrument simulators; "
        "compare direct-agent, Bluesky/databroker, HELAO-async, and component "
        "baselines; and run normal, fault-injection, and adversarial scenarios. "
        "Feasibility would require predeclared gates for command containment, "
        "provenance completeness, deterministic decision replay, over-blocking, "
        "and overhead. Failure of any critical safety or reproducibility gate "
        "would be reported as a no-go."
    ),
    "commercialization_potential": (
        "Target users are autonomous-lab developers, DOE user facilities, and "
        "industrial materials or biotechnology R&D teams that need to govern "
        "AI-directed experiments without replacing installed orchestration. "
        "The proposed entry product is an assurance gateway and adapter kit, "
        "sold first through paid evaluations and then annual site or platform "
        "licenses. No customer, revenue, laboratory deployment, or procurement "
        "commitment is claimed. Alternatives include Bluesky/databroker, "
        "HELAO-async, LIMS and ELN systems, MLflow Tracking, Open Policy Agent, "
        "and custom safety interlocks. These address orchestration, records, "
        "model tracking, policy, or instrument safety. The proposed "
        "differentiation is a vendor-neutral, machine-enforced chain from "
        "predeclared scientific intent through command authorization to a "
        "replayable evidence capsule that retains deviations and null results. "
        "Phase I must demonstrate incremental value over named baselines, not "
        "merely repackage logging. Customer discovery would test procurement, "
        "integration, cybersecurity, data rights, and validation through 20 "
        "structured interviews. Phase II readiness targets are two authorized, "
        "nonbinding evaluation commitments and one instrument-integration plan. "
        "Supply-chain planning centers on signed dependencies, adapter "
        "maintenance, and on-premises packages; other barriers are sales "
        "cycles, authorization requirements, vendor APIs, liability, and "
        "resistance to middleware in safety-relevant paths."
    ),
    "team_qualifications": (
        "LumenCore's demonstrated starting point is local evidence-governance "
        "software: hashed source custody, frozen protocols, named-baseline "
        "evaluation, reproducible receipts, retained negative results, and "
        "human approval gates. The current repository supports software-pattern "
        "and source-conditioned replay claims only; it does not establish "
        "autonomous-laboratory experience, independent validation, or field "
        "deployment. A credible Phase I team needs four named functions: "
        "[PI/software assurance lead], [laboratory automation and controls "
        "lead], [scientific-domain experimentalist], and "
        "[commercialization/customer-discovery lead]. Before submission, "
        "replace every bracket with an authorized person, role, relevant "
        "project evidence, availability, and employment status. No partnership "
        "should be implied without consent. The plan should add an authorized "
        "simulator or equipment-vendor collaborator. A laboratory partner would "
        "strengthen the pitch but is not claimed here. SBIR workshare and "
        "PI-employment requirements must be checked against the final team, or "
        "the project should be structured truthfully as STTR with required "
        "research-institution participation. Follow-on funding is contingent: "
        "Phase II only after technical gates and DOE approval, followed by paid "
        "evaluations, strategic platform partnerships, and non-SBIR revenue. "
        "Insert only verified cash, runway, prior awards, commitments, and "
        "matching resources; otherwise state that no committed follow-on "
        "capital is presently claimed."
    ),
}


class PacketError(ValueError):
    """Raised when a source, claim, or readiness invariant fails."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"Unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise PacketError(f"Expected JSON object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str):
        raise PacketError(f"{label} must be a string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PacketError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise PacketError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def word_count(value: str) -> int:
    return len(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", value))


def extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise PacketError(f"Unreadable pitch guide: {path}") from exc
    root = ElementTree.fromstring(xml)
    paragraphs: list[str] = []
    for paragraph in (node for node in root.iter() if node.tag.endswith("}p")):
        text = "".join(
            node.text or ""
            for node in paragraph.iter()
            if node.tag.endswith("}t")
        )
        normalized = re.sub(r"\s+", " ", text).strip()
        if normalized:
            paragraphs.append(normalized)
    return " ".join(paragraphs)


def validate_pitch_guide() -> dict[str, Any]:
    if not GUIDE_PATH.is_file():
        raise PacketError("Official pitch guide is missing")
    digest = sha256_file(GUIDE_PATH)
    if digest != EXPECTED_GUIDE_SHA256:
        raise PacketError("Official pitch guide identity changed; review required")

    text = extract_docx_text(GUIDE_PATH)
    required_text = (
        "Summary, Topic, and Mission Alignment",
        "100 words or less",
        "Technical Promise",
        "Commercialization Potential",
        "Team Qualifications",
        "200 words or less",
    )
    missing = [item for item in required_text if item.lower() not in text.lower()]
    if missing:
        raise PacketError(f"Pitch guide requirements missing: {missing}")
    return {
        "path": GUIDE_PATH.relative_to(ROOT).as_posix(),
        "bytes": GUIDE_PATH.stat().st_size,
        "sha256": digest,
        "requirements_verified": True,
        "word_limits": WORD_LIMITS,
    }


def validate_watcher(as_of: datetime) -> dict[str, Any]:
    watcher = read_json(WATCH_PATH)
    required = {
        "schema": "lumencore.doe_genesis_watch.v2",
        "status": "ok",
        "parse_complete": True,
        "active_solicitation": True,
        "topic_4_present": True,
        "application_portal_state": "COMING_SOON",
    }
    for field, expected in required.items():
        if watcher.get(field) != expected:
            raise PacketError(
                f"DOE watcher {field} is {watcher.get(field)!r}; "
                f"expected {expected!r}"
            )
    if watcher.get("url") != OFFICIAL_SOURCES["opportunity"]:
        raise PacketError("DOE watcher source URL is not the official opportunity")
    checked = parse_utc(watcher.get("checked_utc", ""), "watcher checked_utc")
    if as_of - checked > timedelta(hours=48) or checked - as_of > timedelta(minutes=5):
        raise PacketError("DOE watcher receipt is stale or future-dated")
    return watcher


def build_evidence_snapshot() -> dict[str, Any]:
    ledger = read_json(
        ROOT / "out" / "ops" / "source_native_family_baseline_ledger_latest.json"
    )
    protocol = read_json(
        ROOT
        / "out"
        / "ops"
        / "time_series_source_native_prospective_protocol_status.json"
    )
    summary = ledger.get("summary")
    if not isinstance(summary, dict):
        raise PacketError("Source-native ledger summary is missing")
    required_summary = {
        "registered_family_count": 140,
        "implementation_present_count": 35,
        "implementation_required_count": 105,
        "internal_source_native_promotion_gate_pass_count": 0,
        "public_performance_claim_allowed": False,
    }
    for field, expected in required_summary.items():
        if summary.get(field) != expected:
            raise PacketError(
                f"Current evidence {field} changed; regenerate after review"
            )
    if protocol.get("verification_passed") is not True:
        raise PacketError("Prospective protocol verification is not passing")
    if protocol.get("protocol_status") != "FROZEN_AWAITING_FUTURE_OBSERVATIONS":
        raise PacketError("Prospective protocol is not in the expected waiting state")
    if protocol.get("performance_claim_allowed") is not False:
        raise PacketError("Prospective protocol improperly allows a performance claim")

    receipts: list[dict[str, Any]] = []
    for item in EVIDENCE_FILES:
        path = ROOT / item["path"]
        if not path.is_file():
            raise PacketError(f"Evidence file missing: {item['path']}")
        receipts.append(
            {
                **item,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "registered_family_count": summary["registered_family_count"],
        "implementation_present_count": summary["implementation_present_count"],
        "implementation_required_count": summary["implementation_required_count"],
        "promotion_gate_pass_count": summary[
            "internal_source_native_promotion_gate_pass_count"
        ],
        "public_performance_claim_allowed": summary[
            "public_performance_claim_allowed"
        ],
        "prospective_protocol_id": protocol["protocol_id"],
        "prospective_protocol_status": protocol["protocol_status"],
        "eligible_future_observation_count": protocol[
            "eligible_future_observation_count"
        ],
        "evidence_receipts": receipts,
    }


def build_pitch_sections() -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section_id, limit in WORD_LIMITS.items():
        text = PITCH_DRAFTS[section_id]
        count = word_count(text)
        if count > limit:
            raise PacketError(
                f"{section_id} is {count} words and exceeds the {limit}-word cap"
            )
        sections.append(
            {
                "section_id": section_id,
                "word_limit": limit,
                "word_count": count,
                "within_limit": True,
                "draft": text,
            }
        )
    return sections


def build_packet(*, as_of_utc: str | None = None) -> dict[str, Any]:
    as_of = (
        parse_utc(as_of_utc, "as_of_utc")
        if as_of_utc
        else datetime.now(timezone.utc)
    )
    guide = validate_pitch_guide()
    watcher = validate_watcher(as_of)
    evidence = build_evidence_snapshot()
    pitch_sections = build_pitch_sections()

    open_gates = [
        {
            "gate": "small_business_eligibility",
            "state": "FOUNDER_CONFIRMATION_REQUIRED",
            "required_fact": (
                "U.S. for-profit small business, no more than 500 employees, "
                "and qualifying 51% ownership and control"
            ),
        },
        {
            "gate": "domestic_research",
            "state": "FOUNDER_CONFIRMATION_REQUIRED",
            "required_fact": "all proposed research and development performed in the U.S.",
        },
        {
            "gate": "principal_investigator",
            "state": "FOUNDER_CONFIRMATION_REQUIRED",
            "required_fact": (
                "named PI, relevant qualifications, and primary-employment "
                "commitment at the small business if awarded"
            ),
        },
        {
            "gate": "registrations",
            "state": "DIRECT_PORTAL_EVIDENCE_REQUIRED",
            "required_fact": (
                "active SAM/UEI, SBA Company Registry, and DOE SBIR/STTR "
                "Application Hub registration"
            ),
        },
        {
            "gate": "laboratory_domain_credibility",
            "state": "PARTNER_OR_ADVISOR_EVIDENCE_REQUIRED",
            "required_fact": (
                "direct experimental-workflow expertise or a bounded plan to "
                "secure it before a full application"
            ),
        },
        {
            "gate": "commercialization_and_financials",
            "state": "FOUNDER_REVIEW_REQUIRED",
            "required_fact": (
                "truthful customer-discovery plan, pricing hypothesis, "
                "follow-on funding plan, and no invented traction"
            ),
        },
        {
            "gate": "generative_ai_disclosure",
            "state": "TRUTHFUL_DISCLOSURE_REQUIRED",
            "required_fact": (
                "state the extent and use of generative AI in developing both "
                "the pitch and any invited full application"
            ),
        },
        {
            "gate": "action_time_review",
            "state": "HUMAN_REVIEW_REQUIRED",
            "required_fact": (
                "final portal text, bibliography, company facts, "
                "certifications, and submit action reviewed at action time"
            ),
        },
    ]

    proposed_protocol = {
        "phase_i_scope": "SIMULATION_AND_FAULT_INJECTION_NO_LAB_DEPLOYMENT_CLAIM",
        "aims": [
            (
                "Compile experiment contracts that bind hypotheses, action "
                "bounds, models, approvals, stopping rules, data schemas, and "
                "falsification criteria across three simulator families."
            ),
            (
                "Intercept commands before dispatch and test faults, policy "
                "bypasses, stale state, altered plans, and missing observations "
                "while remaining subordinate to physical interlocks."
            ),
            (
                "Validate evidence capsules through blinded replay and compare "
                "trace completeness, reproducibility, diagnosis time, and "
                "overhead against frozen baseline versions."
            ),
        ],
        "named_baselines": [
            "direct agent-to-simulator control with native JSON logs",
            "Bluesky RunEngine with Ophyd and databroker",
            "HELAO-async with native workflow and provenance handling",
            "MLflow Tracking plus Open Policy Agent component baseline",
            "no-assurance pass-through adapter and feature ablations",
        ],
        "fault_set": [
            "stale model or policy version",
            "missing required provenance",
            "out-of-sequence action",
            "threshold or constraint violation",
            "operator override and authority mismatch",
        ],
        "proposed_targets_not_results": [
            {
                "metric": "contract compilation",
                "target": (
                    ">=100 frozen contracts across three simulator families, "
                    ">=95% valid compilation, and 100% seeded malformed or "
                    "out-of-range plans rejected before dispatch"
                ),
            },
            {
                "metric": "critical command containment",
                "target": (
                    "0 critical unauthorized commands delivered in >=1,000 "
                    "seeded trials, with a reported confidence bound and no "
                    "zero-risk claim"
                ),
            },
            {
                "metric": "valid-command admission",
                "target": ">=97%, with Wilson 95% lower bound >=95%",
            },
            {
                "metric": "critical provenance completeness",
                "target": (
                    "100% of critical events bind plan, model, policy, "
                    "instrument, input, and output identifiers"
                ),
            },
            {
                "metric": "tamper detection",
                "target": "100% of >=100 seeded record mutations detected",
            },
            {
                "metric": "decision and trace replay",
                "target": (
                    "100% authorization decisions reproduced from frozen "
                    "inputs and >=95% complete traces reconstructed"
                ),
            },
            {
                "metric": "runtime overhead",
                "target": (
                    "p95 policy latency <=50 ms and median workflow overhead "
                    "<=10% on declared non-hard-real-time simulators"
                ),
            },
            {
                "metric": "diagnosis and market evidence",
                "target": (
                    ">=30% lower median deviation-diagnosis time than the "
                    "strongest baseline, 20 structured interviews, two "
                    "authorized nonbinding evaluation commitments, and one "
                    "instrument-integration plan"
                ),
            },
        ],
        "target_status": "PROPOSED_MUST_BE_FROZEN_BEFORE_EVALUATION",
        "critical_gate_rule": (
            "Any critical containment, tamper-detection, or replay failure is a "
            "no-go and cannot be averaged away."
        ),
    }

    submission_constraints = {
        "pitch_count_cap_per_company": 3,
        "reviewed_pitch_rule": "ONLY_LAST_THREE_SUBMITTED_PITCHES_REVIEWED",
        "topic_change_after_pitch_allowed": False,
        "prime_small_business_change_after_pitch_allowed": False,
        "phase_i_period": "6_TO_12_MONTHS",
        "phase_i_r_and_d_cap_usd": 250000,
        "phase_i_cap_with_max_taba_usd": 256500,
        "optional_references_pdf": {
            "required": False,
            "max_bytes": 5_000_000,
            "print_capable": True,
            "password_allowed": False,
            "special_filename_characters_allowed": False,
        },
        "generative_ai_use_disclosure_required": True,
    }

    red_team = {
        "reviewer_verdict": "BORDERLINE_NOT_INVITE_READY_TODAY",
        "truthful_position": (
            "PRE_DISPATCH_EXPERIMENT_ASSURANCE_MIDDLEWARE_FOR_SIMULATED_WORKFLOWS"
        ),
        "preferred_route": (
            "PRIME_ONLY_AFTER_TEAM_DOMAIN_AND_ELIGIBILITY_GATES_OR_PARTNER_SIDE_ROLE"
        ),
        "novelty_hypothesis": (
            "A policy-compiled experiment contract can bind scientific intent, "
            "command authorization, model and instrument state, falsification "
            "rules, and replayable evidence before dispatch with measurable "
            "incremental value over established orchestration, tracking, and "
            "policy components."
        ),
        "rejection_triggers": [
            "generic governance or compliance wrapper rather than experimental-workflow R&D",
            "post-hoc log inspection without pre-dispatch command mediation",
            "no measurable advantage over Bluesky, HELAO-async, MLflow plus OPA, or native interlocks",
            "no specific simulator family, instrument class, experimental domain, or hazard model",
            "software safety wording that displaces physical interlocks, ES&H controls, or operator authority",
            "blocking every command to manufacture a perfect containment score",
            "repository benchmark counts presented as laboratory validation",
            "invented partnerships, deployments, customers, revenue, capital, or DOE experience",
            "unresolved PI employment, workshare, ownership, registration, or certification gates",
            "failure to disclose generative-AI assistance in an eventual submission",
            "accelerated-discovery claims without direct measurement",
        ],
        "must_not_claim": [
            "autonomous laboratory operation",
            "laboratory instrument integration",
            "physical safety certification",
            "DOE deployment or endorsement",
            "independent field validation",
            "discovery acceleration",
            "customer adoption, savings, or revenue",
        ],
    }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": as_of.isoformat().replace("+00:00", "Z"),
        "status": "CONDITIONAL_TOPIC_FIT_R_AND_D_PROTOCOL_AND_FOUNDER_GATES_OPEN",
        "opportunity": "DOE FY26 Phase I - Genesis Mission",
        "topic": TOPIC,
        "concept_name": CONCEPT_NAME,
        "fit_decision": "CONDITIONAL_FIT_NOT_YET_SUBMISSION_READY",
        "fit_basis": (
            "The current stack supports evidence contracts, provenance, replay, "
            "adversarial testing, and fail-closed promotion. It does not yet "
            "establish laboratory integration or autonomous-lab performance."
        ),
        "official_state": {
            "source_url": watcher["url"],
            "source_checked_utc": watcher["checked_utc"],
            "active_solicitation": watcher["active_solicitation"],
            "deadline_literal": watcher["deadline_literal"],
            "deadline_iso": watcher["deadline_iso"],
            "days_to_deadline_at_generation": watcher["days_to_deadline"],
            "application_portal_state": watcher["application_portal_state"],
            "application_portal_url": watcher["application_portal_url"],
            "full_application_invitation_required": True,
            "pitch_stage_first": True,
        },
        "official_sources": OFFICIAL_SOURCES,
        "official_pitch_guide": guide,
        "pitch_sections": pitch_sections,
        "proposed_phase_i_protocol": proposed_protocol,
        "submission_constraints": submission_constraints,
        "red_team": red_team,
        "current_evidence_snapshot": evidence,
        "reference_candidates": REFERENCE_CANDIDATES,
        "open_gates": open_gates,
        "submission_ready": False,
        "send_now": False,
        "external_action_count": 0,
        "portal_submit_allowed_without_human": False,
        "autonomous_certification_allowed": False,
        "autonomous_upload_allowed": False,
        "claim_boundary": (
            "This packet is a source-bound R&D pitch draft. It does not establish "
            "DOE eligibility, invitation, laboratory integration, autonomous-lab "
            "performance, adoption, savings, field validation, award, or "
            "authority to sign in, certify, upload, or submit."
        ),
        "safest_next_action": (
            "Resolve the company, PI, registration, laboratory-domain, and "
            "commercialization facts; then red-team the bounded pitch before "
            "the AMP portal opens."
        ),
    }
    payload["control_sha256"] = canonical_sha256(
        {
            "official_state": payload["official_state"],
            "official_pitch_guide": payload["official_pitch_guide"],
            "pitch_sections": payload["pitch_sections"],
            "proposed_phase_i_protocol": payload["proposed_phase_i_protocol"],
            "submission_constraints": payload["submission_constraints"],
            "red_team": payload["red_team"],
            "open_gates": payload["open_gates"],
            "claim_boundary": payload["claim_boundary"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    state = payload["official_state"]
    lines = [
        "# DOE FY26 Genesis Mission Phase I Pitch Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Decision: **{payload['fit_decision']}**",
        f"Status: `{payload['status']}`",
        "",
        "## Official Source Lock",
        "",
        f"- Opportunity: [{payload['opportunity']}]({state['source_url']})",
        f"- Topic: `{payload['topic']}`",
        f"- Deadline: **{state['deadline_literal']}**",
        f"- Application portal: `{state['application_portal_state']}`",
        "- Route: pitch first; only invited applicants proceed to a full application.",
        "- External action taken by this builder: `0`.",
        "",
        "## Submission Constraints",
        "",
        "- DOE accepts at most `3` pitches per company and reviews only the last three.",
        "- Topic and prime small business cannot change between pitch and full application.",
        "- Phase I is `6 to 12 months`, with a `$250,000` R&D cap or `$256,500` including maximum TABA.",
        "- The optional references PDF must be print-capable, unencrypted, at most 5 MB, and use no special filename characters.",
        "- Generative-AI use must be truthfully disclosed in the pitch and any invited full application.",
        "",
        "## Fit Decision",
        "",
        payload["fit_basis"],
        "",
        "The concept is an assurance layer for an autonomous experiment workflow, "
        "not a claim that LumenCore already operates a laboratory or controls "
        "physical instruments.",
        "",
        "## Bounded Pitch Draft",
        "",
    ]
    title_by_id = {
        "summary_topic_mission_alignment": "Summary, Topic, and Mission Alignment",
        "technical_promise": "Technical Promise",
        "commercialization_potential": "Commercialization Potential",
        "team_qualifications": "Team Qualifications",
    }
    for section in payload["pitch_sections"]:
        lines.extend(
            [
                f"### {title_by_id[section['section_id']]}",
                "",
                f"Word count: `{section['word_count']} / {section['word_limit']}`",
                "",
                section["draft"],
                "",
            ]
        )

    protocol = payload["proposed_phase_i_protocol"]
    lines.extend(
        [
            "## Proposed Phase I Test",
            "",
            f"Scope: `{protocol['phase_i_scope']}`",
            "",
            "### Aims",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in protocol["aims"])
    lines.extend(["", "### Named Baselines", ""])
    lines.extend(f"- {item}" for item in protocol["named_baselines"])
    lines.extend(["", "### Proposed Targets, Not Results", ""])
    lines.extend(
        f"- {row['metric']}: `{row['target']}`"
        for row in protocol["proposed_targets_not_results"]
    )
    lines.extend(["", f"Critical gate rule: {protocol['critical_gate_rule']}"])

    red_team = payload["red_team"]
    lines.extend(
        [
            "",
            "## Independent Red-Team Decision",
            "",
            f"Reviewer verdict: **{red_team['reviewer_verdict']}**",
            "",
            f"Truthful position: `{red_team['truthful_position']}`",
            "",
            f"Novelty hypothesis: {red_team['novelty_hypothesis']}",
            "",
            "### Rejection Triggers",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in red_team["rejection_triggers"])
    lines.extend(["", "### Claims Not Supported Today", ""])
    lines.extend(f"- {item}" for item in red_team["must_not_claim"])

    lines.extend(["", "## Current Evidence Boundary", ""])
    evidence = payload["current_evidence_snapshot"]
    lines.extend(
        [
            f"- Registered families accounted for: `{evidence['registered_family_count']}`",
            f"- Concrete implementations: `{evidence['implementation_present_count']}`",
            f"- Implementation gaps: `{evidence['implementation_required_count']}`",
            f"- Current source-native promotion gates passed: `{evidence['promotion_gate_pass_count']}`",
            f"- Prospective protocol: `{evidence['prospective_protocol_status']}`",
            "- These are governance and research-readiness facts, not autonomous-lab performance.",
            "",
            "| Evidence | Level | Supports |",
            "| --- | --- | --- |",
        ]
    )
    for receipt in evidence["evidence_receipts"]:
        lines.append(
            f"| `{receipt['path']}` | `{receipt['evidence_level']}` | "
            f"{receipt['supports']} |"
        )

    lines.extend(["", "## Open Gates", ""])
    for gate in payload["open_gates"]:
        lines.append(
            f"- **{gate['gate']}** - `{gate['state']}`: "
            f"{gate['required_fact']}"
        )

    lines.extend(["", "## Candidate References", ""])
    for reference in payload["reference_candidates"]:
        lines.append(
            f"- [{reference['name']}]({reference['url']}) - "
            f"{reference['use']}; no relationship claimed."
        )

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            "## Safest Next Action",
            "",
            payload["safest_next_action"],
            "",
            f"Control SHA-256: `{payload['control_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    as_of_utc = args.as_of_utc
    if args.check and not as_of_utc and OUTPUT_JSON.is_file():
        as_of_utc = read_json(OUTPUT_JSON).get("generated_utc")
    payload = build_packet(as_of_utc=as_of_utc)
    rendered_json = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    rendered_md = render_markdown(payload)
    if args.check:
        if not OUTPUT_JSON.is_file() or not OUTPUT_MD.is_file():
            raise PacketError("Generated outputs are missing")
        if OUTPUT_JSON.read_text(encoding="utf-8") != rendered_json:
            raise PacketError("JSON output is stale")
        if OUTPUT_MD.read_text(encoding="utf-8") != rendered_md:
            raise PacketError("Markdown output is stale")
    else:
        write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "submission_ready": payload["submission_ready"],
                "send_now": payload["send_now"],
                "deadline": payload["official_state"]["deadline_literal"],
                "control_sha256": payload["control_sha256"],
                "output_json": str(OUTPUT_JSON),
                "output_md": str(OUTPUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
