from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .models import (
    Decision,
    FreshnessState,
    HumanUnlockAction,
    OpportunityDecisionBrief,
)
from .repository import LoadedOpportunity, PublicSafeRepositoryError


HUMAN_UNLOCK_ACTIONS: tuple[tuple[str, str], ...] = (
    (
        "SEND_EXTERNAL_MESSAGE",
        "Exact recipient, final text and attachments, existing-thread/duplicate check, and fresh action-time approval.",
    ),
    (
        "SUBMIT_OR_CERTIFY_FORM",
        "Exact portal or submission channel, final artifact set, certifications, deadline, and fresh action-time approval.",
    ),
    (
        "ACCEPT_PRICE_OR_COMMERCIAL_TERMS",
        "Exact price, scope, payment schedule, acceptance criteria, terms, and fresh founder approval.",
    ),
    (
        "SIGN_LEGAL_DOCUMENT",
        "Exact final legal document, named parties, authority, counsel review where appropriate, and fresh founder signature decision.",
    ),
    (
        "MOVE_OR_SPEND_MONEY",
        "Exact amount, destination, purpose, payment terms, and fresh founder approval; the agent never handles payment credentials.",
    ),
    (
        "PUBLISH_TO_THIRD_PARTY",
        "Exact destination, final public bytes, claim and IP review, rollback plan where applicable, and fresh founder approval.",
    ),
    (
        "UPLOAD_PRIVATE_MATERIAL",
        "Exact destination and files, data-rights/privacy review, recipient authority, and fresh founder approval.",
    ),
    (
        "CHANGE_ACCOUNT_OR_CREDENTIALS",
        "Exact account, change, recovery path, least-privilege review, and fresh founder approval; secrets remain outside the brief.",
    ),
)

ACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("SEND_EXTERNAL_MESSAGE", re.compile(r"\b(send|email|message|contact|reply)\b", re.I)),
    (
        "SUBMIT_OR_CERTIFY_FORM",
        re.compile(r"\b(submit|apply|certify|file the (?:grant|form|response))\b", re.I),
    ),
    (
        "ACCEPT_PRICE_OR_COMMERCIAL_TERMS",
        re.compile(r"\b(accept (?:the )?(?:price|rate|offer|terms)|quote a price|set the price)\b", re.I),
    ),
    ("SIGN_LEGAL_DOCUMENT", re.compile(r"\b(sign|execute the agreement)\b", re.I)),
    ("MOVE_OR_SPEND_MONEY", re.compile(r"\b(pay|purchase|spend|transfer money)\b", re.I)),
    ("PUBLISH_TO_THIRD_PARTY", re.compile(r"\b(publish|post it live|release it)\b", re.I)),
    ("UPLOAD_PRIVATE_MATERIAL", re.compile(r"\b(upload|attach private|share private)\b", re.I)),
    (
        "CHANGE_ACCOUNT_OR_CREDENTIALS",
        re.compile(r"\b(change (?:the )?(?:account|password|credential)|rotate (?:the )?key)\b", re.I),
    ),
)

UNSUPPORTED_POSITIVE_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:we|lumencore|the company) (?:has )?won\b", re.I),
    re.compile(r"\b(?:was|has been) awarded\b", re.I),
    re.compile(r"\bindependently validated\b", re.I),
    re.compile(r"\b(?:is|are) eligible\b", re.I),
    re.compile(r"\b(?:was|has been) submitted\b", re.I),
    re.compile(r"\b(?:has|secured|won) (?:a )?contract\b", re.I),
    re.compile(r"\bpatent (?:was )?granted\b", re.I),
    re.compile(r"\b(?:guaranteed|field-validated) savings\b", re.I),
    re.compile(r"\bconfirmed customer\b", re.I),
)


@dataclass(frozen=True)
class PolicyFacts:
    title: str
    organization: str
    freshness_state: FreshnessState
    eligibility_state: str
    eligibility_basis: str
    deadline_state: str
    deadline_closed: bool
    deadline_basis: str
    evidence_state: str
    evidence_receipt_backed: bool
    claim_boundary_present: bool
    ip_state: str
    partner_required: bool
    fit_score: int | None
    draft_ready: bool


def detect_requested_external_actions(request: str) -> list[str]:
    detected: list[str] = []
    for action, pattern in ACTION_PATTERNS:
        if any(
            not _action_is_negated(request, match.start())
            for match in pattern.finditer(request)
        ):
            detected.append(action)
    return detected


def _action_is_negated(request: str, match_start: int) -> bool:
    """Treat explicit prohibitions as boundaries, not requests for execution.

    A negation applies within its current sentence/clause and across a comma-separated
    list (for example, ``Do not submit, send, or sign``). A later ``but`` starts a
    positive clause so ``do not submit, but send`` still surfaces the send request.
    """

    clause_start = max(
        request.rfind(".", 0, match_start),
        request.rfind("!", 0, match_start),
        request.rfind("?", 0, match_start),
        request.rfind(";", 0, match_start),
    ) + 1
    prefix = request[clause_start:match_start]
    negations = list(re.finditer(r"\b(?:do not|don't|never|without)\b", prefix, re.I))
    if not negations:
        return False
    after_negation = prefix[negations[-1].end() :]
    return re.search(r"\bbut\b", after_negation, re.I) is None


def standard_human_unlock_actions() -> list[HumanUnlockAction]:
    return [
        HumanUnlockAction(
            action=action,
            state="REQUIRED_NOT_GRANTED_BY_THIS_BRIEF",
            exact_scope_required=scope,
        )
        for action, scope in HUMAN_UNLOCK_ACTIONS
    ]


def _string(value: Any, fallback: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def derive_policy_facts(loaded: LoadedOpportunity) -> PolicyFacts:
    record = loaded.record
    primary = loaded.source_receipts[0]
    title = _string(record.get("title") or record.get("name"), loaded.record_ref)
    organization = _string(
        record.get("organization") or record.get("portal"), "Unknown organization"
    )

    eligibility = record.get("eligibility")
    if isinstance(eligibility, dict):
        eligibility_state = _string(eligibility.get("state"), "UNKNOWN")
        eligibility_basis = _string(
            eligibility.get("basis"), "No receipt-backed eligibility basis is present."
        )
    else:
        eligibility_state = "UNKNOWN"
        eligibility_basis = "No receipt-backed eligibility object is present."

    deadline = record.get("deadline")
    deadline_state = "UNKNOWN"
    deadline_closed = False
    deadline_basis = "No exact receipt-backed deadline object is present."
    if isinstance(deadline, dict):
        deadline_state = _string(
            deadline.get("state") or deadline.get("precision"), "UNKNOWN"
        )
        deadline_closed = bool(
            deadline.get("closed") is True
            or deadline.get("deadline_passed") is True
            or deadline.get("is_closed") is True
        )
        deadline_basis = _string(
            deadline.get("source_text")
            or deadline.get("local_display")
            or deadline.get("at_utc")
            or deadline.get("iso_utc")
            or deadline.get("date"),
            f"Deadline state is {deadline_state}.",
        )
    state_text = _string(record.get("state"), "")
    if any(token in state_text for token in ("PAST_DEADLINE", "CLOSED_DEADLINE")):
        deadline_closed = True

    evidence = record.get("evidence")
    if isinstance(evidence, dict):
        evidence_state = _string(evidence.get("state"), "UNKNOWN")
        receipt_backed = bool(evidence.get("receipt_backed"))
    else:
        evidence_state = _string(record.get("readiness"), "UNKNOWN")
        receipt_backed = bool(record.get("completion_evidence_present"))

    ip = record.get("ip_data_rights")
    ip_state = (
        _string(ip.get("state"), "UNKNOWN") if isinstance(ip, dict) else "UNKNOWN"
    )
    fit_score = record.get("fit_score")
    if not isinstance(fit_score, int) or isinstance(fit_score, bool):
        fit_score = None

    return PolicyFacts(
        title=title,
        organization=organization,
        freshness_state=primary.freshness_state,
        eligibility_state=eligibility_state,
        eligibility_basis=eligibility_basis,
        deadline_state=deadline_state,
        deadline_closed=deadline_closed,
        deadline_basis=deadline_basis,
        evidence_state=evidence_state,
        evidence_receipt_backed=receipt_backed,
        claim_boundary_present=bool(record.get("claim_boundary_present"))
        or bool(record.get("claim_boundary")),
        ip_state=ip_state,
        partner_required=bool(record.get("partner_required")),
        fit_score=fit_score,
        draft_ready=bool(record.get("draft_ready")),
    )


def deterministic_decision(facts: PolicyFacts) -> Decision:
    if facts.deadline_closed or facts.eligibility_state == "INELIGIBLE":
        return Decision.NO_BID
    if facts.freshness_state in {
        FreshnessState.STALE,
        FreshnessState.FUTURE,
        FreshnessState.MISSING,
    }:
        return Decision.WATCH
    if facts.eligibility_state not in {
        "CONFIRMED",
        "CONFIRMED_FOR_LOCAL_DRAFT_ONLY",
    }:
        return Decision.WATCH
    if facts.partner_required:
        return Decision.PARTNER
    if facts.fit_score is not None and facts.fit_score < 55:
        return Decision.NO_BID
    if (
        facts.draft_ready
        and facts.deadline_state in {"EXACT", "NONE_STATED"}
        and facts.evidence_receipt_backed
        and facts.claim_boundary_present
        and facts.ip_state == "PUBLIC_SAFE_NONCONFIDENTIAL_DRAFT_ONLY"
    ):
        return Decision.DRAFT_READY_HUMAN_REVIEW
    return Decision.BID


def _all_brief_text(brief: OpportunityDecisionBrief) -> Iterable[str]:
    yield brief.decision_rationale
    for statements in (brief.observed, brief.inferred, brief.modeled):
        for item in statements:
            yield item.statement
    for gate in (
        brief.eligibility,
        brief.deadline,
        brief.evidence,
        brief.claim_boundary,
        brief.ip_data_rights,
    ):
        yield gate.basis
    yield from brief.adversarial_readiness
    yield from brief.limitations


def validate_decision_brief(
    brief: OpportunityDecisionBrief,
    loaded: LoadedOpportunity,
    request: str,
) -> None:
    if brief.record_ref != loaded.record_ref:
        raise PublicSafeRepositoryError("brief record_ref does not match the request")
    expected_receipts = {
        receipt.path: receipt for receipt in loaded.source_receipts
    }
    actual_receipts = {receipt.path: receipt for receipt in brief.sources}
    if actual_receipts != expected_receipts:
        raise PublicSafeRepositoryError("brief source receipts do not match exact bytes")
    allowed = loaded.allowed_source_paths
    for statements in (brief.observed, brief.inferred, brief.modeled):
        for statement in statements:
            if not set(statement.source_paths).issubset(allowed):
                raise PublicSafeRepositoryError("brief contains a non-allowlisted source path")
    for gate in (
        brief.eligibility,
        brief.deadline,
        brief.evidence,
        brief.claim_boundary,
        brief.ip_data_rights,
    ):
        if not set(gate.source_paths).issubset(allowed):
            raise PublicSafeRepositoryError("gate contains a non-allowlisted source path")

    facts = derive_policy_facts(loaded)
    if facts.freshness_state != FreshnessState.FRESH and brief.decision in {
        Decision.BID,
        Decision.DRAFT_READY_HUMAN_REVIEW,
    }:
        raise PublicSafeRepositoryError("stale or missing evidence was promoted")
    if facts.eligibility_state not in {
        "CONFIRMED",
        "CONFIRMED_FOR_LOCAL_DRAFT_ONLY",
    } and brief.decision in {Decision.BID, Decision.DRAFT_READY_HUMAN_REVIEW}:
        raise PublicSafeRepositoryError("missing eligibility evidence was promoted")
    if facts.deadline_closed and brief.decision != Decision.NO_BID:
        raise PublicSafeRepositoryError("closed deadline did not fail closed")
    if brief.decision == Decision.DRAFT_READY_HUMAN_REVIEW and (
        deterministic_decision(facts) != Decision.DRAFT_READY_HUMAN_REVIEW
    ):
        raise PublicSafeRepositoryError("draft-ready decision exceeds deterministic gates")

    requested = set(detect_requested_external_actions(request))
    if not requested.issubset(set(brief.forbidden_requested_actions)):
        raise PublicSafeRepositoryError("forbidden requested action was not surfaced")
    expected_unlocks = {action for action, _ in HUMAN_UNLOCK_ACTIONS}
    actual_unlocks = {row.action for row in brief.human_unlock_actions}
    if actual_unlocks != expected_unlocks:
        raise PublicSafeRepositoryError("HumanUnlock action register is incomplete")
    if any(
        pattern.search(text)
        for text in _all_brief_text(brief)
        for pattern in UNSUPPORTED_POSITIVE_CLAIM_PATTERNS
    ):
        raise PublicSafeRepositoryError("unsupported positive claim detected")
