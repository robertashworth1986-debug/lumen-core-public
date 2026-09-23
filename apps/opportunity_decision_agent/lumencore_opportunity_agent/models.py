from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(str, Enum):
    BID = "BID"
    PARTNER = "PARTNER"
    WATCH = "WATCH"
    NO_BID = "NO_BID"
    DRAFT_READY_HUMAN_REVIEW = "DRAFT_READY_HUMAN_REVIEW"


class GateState(str, Enum):
    PASS = "PASS"
    GAP = "GAP"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    FUTURE = "FUTURE"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OpportunityDecisionRequest(StrictModel):
    record_ref: str = Field(min_length=1, max_length=200)
    as_of_utc: str = Field(min_length=20, max_length=40)
    request: str = Field(min_length=1, max_length=4000)

    @field_validator("as_of_utc")
    @classmethod
    def canonical_utc_required(cls, value: str) -> str:
        from datetime import datetime

        if not value.endswith("Z"):
            raise ValueError("as_of_utc must use canonical UTC with a Z suffix")
        try:
            parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError as exc:
            raise ValueError("as_of_utc must be a valid timestamp") from exc
        if parsed.utcoffset() is None or parsed.microsecond:
            raise ValueError("as_of_utc must be timezone-aware and second precision")
        return value


class SourceReceipt(StrictModel):
    path: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    observed_utc: str | None
    freshness_state: FreshnessState
    age_hours: float | None
    evidence_role: str = Field(min_length=1, max_length=200)


class BoundedStatement(StrictModel):
    statement: str = Field(min_length=1, max_length=1200)
    source_paths: list[str] = Field(min_length=1, max_length=12)


class GateAssessment(StrictModel):
    state: GateState
    basis: str = Field(min_length=1, max_length=1600)
    missing_gates: list[str] = Field(max_length=30)
    source_paths: list[str] = Field(min_length=1, max_length=12)


class DraftArtifact(StrictModel):
    artifact: str = Field(min_length=1, max_length=240)
    purpose: str = Field(min_length=1, max_length=600)
    draft_only: Literal[True]


class HumanUnlockAction(StrictModel):
    action: Literal[
        "SEND_EXTERNAL_MESSAGE",
        "SUBMIT_OR_CERTIFY_FORM",
        "ACCEPT_PRICE_OR_COMMERCIAL_TERMS",
        "SIGN_LEGAL_DOCUMENT",
        "MOVE_OR_SPEND_MONEY",
        "PUBLISH_TO_THIRD_PARTY",
        "UPLOAD_PRIVATE_MATERIAL",
        "CHANGE_ACCOUNT_OR_CREDENTIALS",
    ]
    state: Literal["REQUIRED_NOT_GRANTED_BY_THIS_BRIEF"]
    exact_scope_required: str = Field(min_length=1, max_length=500)


class OpportunityDecisionBrief(StrictModel):
    schema_version: Literal["lumencore.opportunity_decision_brief.v1"]
    record_ref: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    organization: str = Field(min_length=1, max_length=500)
    decision: Decision
    decision_rationale: str = Field(min_length=1, max_length=2000)
    observed: list[BoundedStatement] = Field(min_length=1, max_length=30)
    inferred: list[BoundedStatement] = Field(max_length=30)
    modeled: list[BoundedStatement] = Field(max_length=30)
    sources: list[SourceReceipt] = Field(min_length=1, max_length=30)
    eligibility: GateAssessment
    deadline: GateAssessment
    evidence: GateAssessment
    claim_boundary: GateAssessment
    ip_data_rights: GateAssessment
    adversarial_readiness: list[str] = Field(min_length=1, max_length=30)
    unsupported_claims: list[str] = Field(min_length=1, max_length=30)
    forbidden_requested_actions: list[str] = Field(max_length=20)
    next_draft_only_artifacts: list[DraftArtifact] = Field(max_length=20)
    human_unlock_actions: list[HumanUnlockAction] = Field(min_length=8, max_length=8)
    limitations: list[str] = Field(min_length=1, max_length=30)


class SpecialistFinding(StrictModel):
    specialist: Literal[
        "ELIGIBILITY",
        "LICENSING_IP",
        "EVIDENCE_CLAIMS",
        "ADVERSARIAL_READINESS",
    ]
    conclusion: str = Field(min_length=1, max_length=1200)
    state: GateState
    observed: list[BoundedStatement] = Field(min_length=1, max_length=15)
    missing_gates: list[str] = Field(max_length=20)
    source_paths: list[str] = Field(min_length=1, max_length=12)
