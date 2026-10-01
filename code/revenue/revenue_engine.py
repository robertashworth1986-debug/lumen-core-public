#!/usr/bin/env python3
"""LumenCore Revenue Engine v1: deterministic, claim-bounded opportunity qualification.

This module never sends outreach, signs scopes, transfers data, or claims revenue.
It converts non-confidential opportunity facts into a reviewable commercial decision.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

SCHEMA="lumencore_revenue_opportunity_v1"
OUTCOMES={"scope_candidate","needs_facts","needs_separate_controls","no_fit"}
REQUIRED=("opportunity_id","organization","decision","candidate","baseline","primary_metric","source_rights","decision_owner","useful_by","commercial_route")
UNKNOWN={"","unknown","tbd","none","n/a"}
SENSITIVE={"classified","cui","phi","payment card","export-controlled","credential","private key","production access"}

def _text(v:Any)->str:
    return str(v).strip() if v is not None else ""

def _known(v:Any)->bool:
    return _text(v).casefold() not in UNKNOWN

def evaluate(p:dict[str,Any])->dict[str,Any]:
    if p.get("schema")!=SCHEMA: raise ValueError(f"schema must be {SCHEMA}")
    missing=[k for k in REQUIRED if not _known(p.get(k))]
    blob=json.dumps(p,sort_keys=True,separators=(",",":")).encode()
    rights=_text(p.get("source_rights")).casefold()
    restrictions=" ".join(map(_text,p.get("handling_restrictions",[]))).casefold()
    sensitive=sorted(x for x in SENSITIVE if x in rights+" "+restrictions)
    fair=bool(p.get("fair_comparison_possible",True))
    if sensitive:
        outcome="needs_separate_controls"
    elif not fair:
        outcome="no_fit"
    elif missing:
        outcome="needs_facts"
    else:
        outcome="scope_candidate"
    offer=p.get("requested_tier","launch_replay")
    return {
      "schema":"lumencore_revenue_decision_v1",
      "opportunity_id":_text(p.get("opportunity_id")),
      "outcome":outcome,
      "missing_facts":missing,
      "separate_control_triggers":sensitive,
      "requested_tier":offer,
      "input_sha256":hashlib.sha256(blob).hexdigest(),
      "allowed_next_action":{
        "scope_candidate":"draft_buyer_specific_sow_for_founder_review",
        "needs_facts":"request_or_research_named_non_confidential_facts",
        "needs_separate_controls":"stop_until_legal_security_data_controls_exist",
        "no_fit":"stop"
      }[outcome],
      "claim_boundary":"This decision is an internal qualification record, not a customer, contract, revenue, validation, savings, endorsement, award, or production-authorization claim.",
      "external_action_requires_founder_approval":True
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("input",type=Path); ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    p=json.loads(a.input.read_text(encoding="utf-8"))
    r=evaluate(p); s=json.dumps(r,indent=2,sort_keys=True)+"\n"
    if a.output: a.output.write_text(s,encoding="utf-8")
    else: print(s,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
