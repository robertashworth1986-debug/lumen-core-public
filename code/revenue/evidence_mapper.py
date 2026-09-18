#!/usr/bin/env python3
"""Map a qualified revenue opportunity to existing evidence without claim promotion."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

def map_evidence(decision:dict[str,Any], graph:dict[str,Any])->dict[str,Any]:
    if decision.get("schema")!="lumencore_revenue_decision_v1":
        raise ValueError("invalid revenue decision schema")
    if decision.get("outcome")!="scope_candidate":
        raise ValueError("only scope_candidate may be evidence-mapped")
    nodes=graph.get("nodes")
    if not isinstance(nodes,list): raise ValueError("evidence graph nodes missing")
    useful=[]
    for n in nodes:
        if not isinstance(n,dict): continue
        state=n.get("state","unknown")
        if state in {"held","historical"}: continue
        supports=n.get("supports",[])
        boundaries=n.get("does_not_support",[])
        if supports:
            useful.append({
              "id":n.get("id"),"title":n.get("title"),"state":state,
              "supports":supports,"does_not_support":boundaries,
              "files_of_interest":n.get("files_of_interest",[])
            })
    return {
      "schema":"lumencore_revenue_evidence_map_v1",
      "opportunity_id":decision.get("opportunity_id"),
      "evidence_nodes":useful,
      "node_count":len(useful),
      "promotion_prohibited":True,
      "claim_rule":graph.get("claim_rule"),
      "external_action_requires_founder_approval":True,
      "boundary":"Mapped nodes support only their explicit supports fields. Omitted promotion states remain unproven."
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("decision",type=Path); ap.add_argument("graph",type=Path)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    result=map_evidence(json.loads(a.decision.read_text()),json.loads(a.graph.read_text()))
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if a.output:a.output.write_text(text)
    else:print(text,end="")
    return 0
if __name__=="__main__":raise SystemExit(main())
