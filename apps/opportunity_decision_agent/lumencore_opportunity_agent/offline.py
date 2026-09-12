from __future__ import annotations

from .models import (
    BoundedStatement,
    DraftArtifact,
    GateAssessment,
    GateState,
    OpportunityDecisionBrief,
    OpportunityDecisionRequest,
)
from .policy import (
    detect_requested_external_actions,
    derive_policy_facts,
    deterministic_decision,
    standard_human_unlock_actions,
    validate_decision_brief,
)
from .repository import PublicSafeRepository


UNSUPPORTED_CLAIMS = [
    "No win, selection, award, or funding is established.",
    "No eligibility confirmation exists beyond the exact receipt-backed record.",
    "No submission, customer, contract, partnership, endorsement, or acceptance is established.",
    "No independent validation, field performance, savings, ROI, or production authorization is established.",
    "No patent grant, freedom-to-operate conclusion, or transfer of founder IP is established.",
]


def _gate(
    *,
    state: GateState,
    basis: str,
    missing_gates: list[str],
    source_paths: list[str],
) -> GateAssessment:
    return GateAssessment(
        state=state,
        basis=basis,
        missing_gates=missing_gates,
        source_paths=source_paths,
    )


def run_offline(request: OpportunityDecisionRequest) -> OpportunityDecisionBrief:
    repository = PublicSafeRepository()
    loaded = repository.load(request.record_ref, request.as_of_utc)
    facts = derive_policy_facts(loaded)
    decision = deterministic_decision(facts)
    primary_path = loaded.source_receipts[0].path
    claim_path = repository.claim_boundary_path
    ip_path = repository.ip_boundary_path

    eligibility_pass = facts.eligibility_state in {
        "CONFIRMED",
        "CONFIRMED_FOR_LOCAL_DRAFT_ONLY",
    }
    deadline_pass = not facts.deadline_closed and facts.deadline_state in {
        "EXACT",
        "NONE_STATED",
    }
    evidence_pass = facts.evidence_receipt_backed
    ip_pass = facts.ip_state == "PUBLIC_SAFE_NONCONFIDENTIAL_DRAFT_ONLY"
    freshness_pass = facts.freshness_state.value == "FRESH"

    rationale = {
        "NO_BID": "Current evidence records a closed deadline, ineligibility, or another decisive stop; no external action is authorized.",
        "WATCH": "Official or receipt-backed evidence is stale, missing, or unresolved, so the workflow fails closed to monitoring and source refresh.",
        "PARTNER": "The record requires a documented partner capability or authority before a bounded draft can advance.",
        "BID": "The opportunity may justify bounded pursuit, but named eligibility, evidence, deadline, claim, or IP gates remain before draft readiness.",
        "DRAFT_READY_HUMAN_REVIEW": "Configured local-draft gates are present for this public-safe record; a human must review the draft and separately authorize every consequential action at action time.",
    }[decision.value]

    observed = [
        BoundedStatement(
            statement=(
                f"The allowlisted record identifies {facts.title} for "
                f"{facts.organization}."
            ),
            source_paths=[primary_path],
        ),
        BoundedStatement(
            statement=(
                f"The primary source freshness state is "
                f"{facts.freshness_state.value} at {request.as_of_utc}."
            ),
            source_paths=[primary_path],
        ),
        BoundedStatement(
            statement=f"Recorded eligibility state: {facts.eligibility_state}.",
            source_paths=[primary_path],
        ),
        BoundedStatement(
            statement=(
                f"Recorded deadline state: {facts.deadline_state}; "
                f"closed={str(facts.deadline_closed).lower()}."
            ),
            source_paths=[primary_path],
        ),
    ]
    inferred = [
        BoundedStatement(
            statement=rationale,
            source_paths=[primary_path, claim_path, ip_path],
        )
    ]

    brief = OpportunityDecisionBrief(
        schema_version="lumencore.opportunity_decision_brief.v1",
        record_ref=request.record_ref,
        title=facts.title,
        organization=facts.organization,
        decision=decision,
        decision_rationale=rationale,
        observed=observed,
        inferred=inferred,
        modeled=[],
        sources=list(loaded.source_receipts),
        eligibility=_gate(
            state=GateState.PASS if eligibility_pass else GateState.GAP,
            basis=facts.eligibility_basis,
            missing_gates=(
                []
                if eligibility_pass
                else ["OFFICIAL_ELIGIBILITY_AND_APPLICANT_FACTS_REQUIRED"]
            ),
            source_paths=[primary_path],
        ),
        deadline=_gate(
            state=(
                GateState.BLOCKED
                if facts.deadline_closed
                else GateState.PASS
                if deadline_pass
                else GateState.GAP
            ),
            basis=facts.deadline_basis,
            missing_gates=(
                []
                if deadline_pass
                else ["CURRENT_EXACT_DEADLINE_TIMEZONE_AND_ROUTE_REQUIRED"]
            ),
            source_paths=[primary_path],
        ),
        evidence=_gate(
            state=(
                GateState.PASS
                if evidence_pass and freshness_pass
                else GateState.BLOCKED
                if not freshness_pass
                else GateState.GAP
            ),
            basis=(
                f"Evidence state is {facts.evidence_state}; exact repository bytes "
                f"were hashed, and source freshness is {facts.freshness_state.value}."
            ),
            missing_gates=(
                []
                if evidence_pass and freshness_pass
                else ["FRESH_RECEIPT_BACKED_OFFICIAL_EVIDENCE_REQUIRED"]
            ),
            source_paths=[primary_path],
        ),
        claim_boundary=_gate(
            state=GateState.PASS if facts.claim_boundary_present else GateState.GAP,
            basis=(
                "A record-specific claim boundary and the canonical public claim "
                "register constrain the brief."
                if facts.claim_boundary_present
                else "The canonical register exists, but the record lacks a specific claim boundary."
            ),
            missing_gates=(
                []
                if facts.claim_boundary_present
                else ["RECORD_SPECIFIC_SUPPORTED_AND_UNSUPPORTED_CLAIMS_REQUIRED"]
            ),
            source_paths=[primary_path, claim_path],
        ),
        ip_data_rights=_gate(
            state=GateState.PASS if ip_pass else GateState.GAP,
            basis=(
                "The record is restricted to public-safe, nonconfidential draft work; "
                "private access, reuse, publication, licensing, and derivative rights "
                "require a written founder-protective agreement."
            ),
            missing_gates=(
                []
                if ip_pass
                else ["OPPORTUNITY_SPECIFIC_IP_DATA_RIGHTS_AND_DISCLOSURE_TERMS_REQUIRED"]
            ),
            source_paths=[primary_path, ip_path],
        ),
        adversarial_readiness=[
            "No external-action tool exists in this runtime.",
            "The record path and all evidence paths are immutable allowlist entries, not model-selected file paths.",
            "Stale or missing official evidence cannot produce BID or DRAFT_READY_HUMAN_REVIEW.",
            "A model output is revalidated against hashes, source paths, evidence gates, forbidden requests, and claim boundaries.",
        ],
        unsupported_claims=UNSUPPORTED_CLAIMS,
        forbidden_requested_actions=detect_requested_external_actions(request.request),
        next_draft_only_artifacts=(
            [
                DraftArtifact(
                    artifact="Opportunity-specific compliance and evidence matrix",
                    purpose="Map each requirement to an exact public source, current fact, gap, and owner without submitting it.",
                    draft_only=True,
                ),
                DraftArtifact(
                    artifact="Bounded response or pilot scope draft",
                    purpose="State one buyer-owned baseline, locked metric, failure rules, data-rights boundary, and go/no-go decision for human review.",
                    draft_only=True,
                ),
            ]
            if decision.value in {"BID", "PARTNER", "DRAFT_READY_HUMAN_REVIEW"}
            else [
                DraftArtifact(
                    artifact="Official-source refresh checklist",
                    purpose="Resolve only the named freshness, eligibility, deadline, evidence, claim, and IP gaps before reconsideration.",
                    draft_only=True,
                )
            ]
        ),
        human_unlock_actions=standard_human_unlock_actions(),
        limitations=[
            "This is a first-party software decision aid, not an official-source refresh, legal opinion, eligibility determination, selection forecast, or award-probability model.",
            "Local draft readiness never authorizes login, contact, upload, certification, signature, submission, payment, publication, account change, or production action.",
            "The offline path performs no model or network call; it proves deterministic policy behavior only.",
        ],
    )
    validate_decision_brief(brief, loaded, request.request)
    return brief
