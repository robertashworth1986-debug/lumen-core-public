import importlib.util
import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# `code` is also a standard-library module; load the script by its exact path.
SPEC = importlib.util.spec_from_file_location(
    "revenue_engine", ROOT / "code" / "revenue" / "revenue_engine.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
evaluate, SCHEMA = MODULE.evaluate, MODULE.SCHEMA

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


@pytest.mark.parametrize("value", [None, "false", "true", 0, 1, [], {}])
def test_comparison_fact_requires_explicit_boolean(value):
    p=base(); p["fair_comparison_possible"]=value
    assert evaluate(p)["outcome"]=="needs_facts"


@pytest.mark.parametrize("value", [None, False, 0, [], {}, "tbd"])
def test_required_facts_reject_nontext_placeholders(value):
    p=base(); p["baseline"]=value
    assert evaluate(p)["outcome"]=="needs_facts"


def test_missing_restrictions_is_unknown_and_string_cui_still_stops():
    p=base(); del p["handling_restrictions"]
    assert evaluate(p)["outcome"]=="needs_facts"
    p["handling_restrictions"]="CUI"
    assert evaluate(p)["outcome"]=="needs_separate_controls"
