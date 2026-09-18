from code.revenue.revenue_engine import evaluate, SCHEMA

def base():
    return {
      "schema":SCHEMA,"opportunity_id":"OP-1","organization":"Example Buyer",
      "decision":"Does candidate beat accepted baseline?","candidate":"Candidate A v1",
      "baseline":"Buyer accepted incumbent","primary_metric":"MAE, lower is better",
      "source_rights":"buyer_authorized","decision_owner":"Engineering lead",
      "useful_by":"2026-10-31","commercial_route":"Budget/procurement owner identified",
      "handling_restrictions":[],"fair_comparison_possible":True,
      "requested_tier":"launch_replay"
    }

def test_scope_candidate():
    r=evaluate(base())
    assert r["outcome"]=="scope_candidate"
    assert r["external_action_requires_founder_approval"] is True
    assert len(r["input_sha256"])==64

def test_unknown_fails_closed():
    p=base(); p["baseline"]="UNKNOWN"
    r=evaluate(p)
    assert r["outcome"]=="needs_facts"
    assert "baseline" in r["missing_facts"]

def test_sensitive_requires_controls():
    p=base(); p["handling_restrictions"]=["CUI"]
    assert evaluate(p)["outcome"]=="needs_separate_controls"

def test_unfair_comparison_is_no_fit():
    p=base(); p["fair_comparison_possible"]=False
    assert evaluate(p)["outcome"]=="no_fit"
