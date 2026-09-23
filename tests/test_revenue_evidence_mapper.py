from code.revenue.evidence_mapper import map_evidence
from code.revenue.sow_builder import build_sow_prefill

def test_mapper_excludes_held_and_historical():
    d={"schema":"lumencore_revenue_decision_v1","outcome":"scope_candidate","opportunity_id":"X"}
    g={"claim_rule":"explicit only","nodes":[
      {"id":"a","state":"merged_capability","supports":["artifact_custody"],"does_not_support":["external_validation"]},
      {"id":"b","state":"historical","supports":["old"]},
      {"id":"c","state":"held","supports":["candidate"]}
    ]}
    r=map_evidence(d,g)
    assert r["node_count"]==1
    assert r["evidence_nodes"][0]["id"]=="a"
    assert r["promotion_prohibited"] is True

def test_mapper_rejects_unqualified():
    d={"schema":"lumencore_revenue_decision_v1","outcome":"needs_facts"}
    try: map_evidence(d,{"nodes":[]})
    except ValueError: pass
    else: raise AssertionError("must fail closed")

def test_sow_prefill_is_never_send_ready():
    o={"organization":"Buyer","decision":"Q","candidate":"C","baseline":"B","primary_metric":"MAE",
       "source_rights":"buyer_authorized","decision_owner":"Lead","useful_by":"2026-10-01","commercial_route":"PO"}
    d={"outcome":"scope_candidate","requested_tier":"launch_replay"}
    e={"promotion_prohibited":True,"evidence_nodes":[{"id":"pr-34"}]}
    r=build_sow_prefill(o,d,e)
    assert r["ready_to_sign"] is False and r["ready_to_send"] is False
