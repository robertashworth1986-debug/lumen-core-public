import importlib.util
import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_revenue_script(name):
    # Avoid treating the standard-library `code` module as a package.
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "code" / "revenue" / f"{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


map_evidence = _load_revenue_script("evidence_mapper").map_evidence
build_sow_prefill = _load_revenue_script("sow_builder").build_sow_prefill
evaluate = _load_revenue_script("revenue_engine").evaluate

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

def bound_records():
    o={"schema":"lumencore_revenue_opportunity_v1","opportunity_id":"OP-1",
       "organization":"Buyer","decision":"Q","candidate":"C","baseline":"B","primary_metric":"MAE",
       "source_rights":"buyer_authorized","decision_owner":"Lead","useful_by":"2026-10-01","commercial_route":"PO",
       "fair_comparison_possible":True,"handling_restrictions":[]}
    d=evaluate(o)
    e=map_evidence(d,{"nodes":[]})
    return o,d,e


def test_sow_prefill_is_never_send_ready():
    o,d,e=bound_records()
    r=build_sow_prefill(o,d,e)
    assert r["ready_to_sign"] is False and r["ready_to_send"] is False


def test_sow_rejects_changed_facts_and_cross_opportunity_evidence():
    o,d,e=bound_records()
    o["baseline"]="Changed incumbent"
    with pytest.raises(ValueError,match="exact opportunity"):
        build_sow_prefill(o,d,e)
    o,d,e=bound_records()
    e["opportunity_id"]="OP-2"
    with pytest.raises(ValueError,match="identities"):
        build_sow_prefill(o,d,e)


def test_mapper_excludes_unknown_state_and_missing_boundaries():
    _,d,_=bound_records()
    g={"nodes":[{"state":"unknown","supports":["claims"],"does_not_support":["limits"]},
                {"state":"merged_capability","supports":["claims"]}]}
    assert map_evidence(d,g)["node_count"]==0
