#!/usr/bin/env python3
"""Build a review-only SOW prefill from qualified facts. Never signs or sends."""
from __future__ import annotations
import hashlib
import json
from typing import Any

def build_sow_prefill(opportunity:dict[str,Any],decision:dict[str,Any],evidence:dict[str,Any])->dict[str,Any]:
    digest=hashlib.sha256(json.dumps(opportunity,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    if decision.get("schema")!="lumencore_revenue_decision_v1" or decision.get("input_sha256")!=digest:
        raise ValueError("decision must bind the exact opportunity facts")
    oid=opportunity.get("opportunity_id")
    if not isinstance(oid,str) or not oid.strip() or decision.get("opportunity_id")!=oid.strip() or evidence.get("opportunity_id")!=oid.strip():
        raise ValueError("opportunity, decision and evidence identities must match")
    if evidence.get("schema")!="lumencore_revenue_evidence_map_v1":
        raise ValueError("evidence map schema required")
    if decision.get("outcome")!="scope_candidate": raise ValueError("scope_candidate required")
    if evidence.get("promotion_prohibited") is not True: raise ValueError("evidence map must prohibit promotion")
    fields=("organization","decision","candidate","baseline","primary_metric","source_rights","decision_owner","useful_by","commercial_route")
    if any(not str(opportunity.get(k,"")).strip() for k in fields): raise ValueError("required SOW fact missing")
    return {
      "schema":"lumencore_revenue_sow_prefill_v1",
      "status":"DRAFT_FOUNDER_REVIEW_ONLY",
      "buyer":opportunity["organization"],
      "decision":opportunity["decision"],
      "candidate":opportunity["candidate"],
      "accepted_baseline":opportunity["baseline"],
      "primary_metric":opportunity["primary_metric"],
      "source_rights":opportunity["source_rights"],
      "decision_owner":opportunity["decision_owner"],
      "useful_by":opportunity["useful_by"],
      "commercial_route":opportunity["commercial_route"],
      "requested_tier":decision.get("requested_tier","launch_replay"),
      "evidence_node_ids":[n.get("id") for n in evidence.get("evidence_nodes",[])],
      "must_use_canonical_template":"docs/LUMENCORE_BOUNDED_VALIDATION_SPRINT_SOW_TEMPLATE.md",
      "pricing_source":"config/bounded_validation_sprint_v1.json",
      "signature_authority":"Robert Ashworth",
      "ready_to_sign":False,
      "ready_to_send":False,
      "claim_boundary":"No favorable outcome, savings, ROI, validation, customer status, endorsement, award, or production authorization is promised or established."
    }
