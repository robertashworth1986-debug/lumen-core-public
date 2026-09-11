"""Adversarial synthetic tests; not independent validation or trading results."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "code" / "ops" / (name + ".py"))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result
forecast = module("audit_forecast_denominators")
paper = module("audit_paper_accounting")


def test_outcome_conditional_coverage_cannot_hide_half_missing():
    y = np.array([1., np.nan] * 100); predictions = np.ones(200)
    r = forecast.audit_cell(y, predictions, {k: predictions for k in forecast.REQUIRED_BASELINES}, np.ones(200, bool))
    assert r["common_over_observed"] == 1
    assert r["common_over_scheduled"] == .5 and r["observed_over_scheduled"] == .5
    assert not r["all_baseline_descriptive_screen"]


def test_both_baselines_compared_on_exact_same_rows():
    y = np.zeros(200); c = np.ones(200); p = np.ones(200) * 10; s = np.ones(200) * 2
    p[:50] = np.nan; s[50:100] = np.nan
    r = forecast.audit_cell(y, c, {"persistence": p, "seasonal": s}, np.ones(200, bool))
    assert r["common_pairs"] == 100
    assert r["comparisons"]["persistence"]["candidate_mae"] == r["comparisons"]["seasonal"]["candidate_mae"] == 1
    assert r["common_over_scheduled"] == .5
    assert not r["all_baseline_descriptive_screen"]


def test_losing_stronger_baseline_blocks_screen():
    y = np.zeros(200); c = np.ones(200)
    r = forecast.audit_cell(y, c, {"persistence": c * 2, "seasonal": c / 2}, np.ones(200, bool))
    assert r["comparisons"]["persistence"]["descriptive_screen"]
    assert not r["all_baseline_descriptive_screen"]


def test_reference_equivalence_is_visible_not_two_independent_baselines():
    y = np.zeros(200); c = np.ones(200)
    r = forecast.audit_cell(y, c, {k: c * 2 for k in forecast.REQUIRED_BASELINES}, np.ones(200, bool))
    assert r["baselines_identical_on_common_rows"] and r["all_baseline_descriptive_screen"]
    assert r["decision"] == "RESEARCH_ONLY_NO_PROMOTION"


def test_zero_baseline_has_no_infinite_skill():
    y = np.zeros(200)
    r = forecast.audit_cell(y, y, {k: y for k in forecast.REQUIRED_BASELINES}, np.ones(200, bool))
    assert r["comparisons"]["seasonal"]["mae_improvement_pct"] is None
    assert not r["all_baseline_descriptive_screen"]


@pytest.mark.parametrize("truth,mask", [([np.nan] * 200, [True] * 200), ([1.] * 200, [False] * 200), ([], np.array([], bool))])
def test_empty_or_missing_evidence_stays_hold(truth, mask):
    values = np.ones(len(truth))
    r = forecast.audit_cell(truth, values, {k: values for k in forecast.REQUIRED_BASELINES}, mask)
    assert r["common_pairs"] == 0 and not r["all_baseline_descriptive_screen"]
    assert r["decision"] == "RESEARCH_ONLY_NO_PROMOTION"


@pytest.mark.parametrize("truth,candidate,baselines,mask", [
    ([1], [1], {"persistence": [1]}, [True]),
    ([1], [1], {"persistence": [1], "seasonal": [1], "other": [1]}, [True]),
    ([1, 2], [1], {"persistence": [1], "seasonal": [1]}, [True]),
    ([1], [1], {"persistence": [1], "seasonal": [1]}, [1]),
    ([float("inf")], [1], {"persistence": [1], "seasonal": [1]}, [True]),
    ([1], [float("inf")], {"persistence": [1], "seasonal": [1]}, [True]),
    ([1], [1], {"persistence": [1], "seasonal": [float("inf")]}, [True]),
    (["1"], [1], {"persistence": [1], "seasonal": [1]}, [True]),
    ([[1]], [1], {"persistence": [1], "seasonal": [1]}, [True]),
])
def test_bad_array_contracts(truth, candidate, baselines, mask):
    with pytest.raises(ValueError): forecast.audit_cell(truth, candidate, baselines, mask)


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e309}'])
def test_strict_json_rejects_nonfinite_and_duplicate(tmp_path, text):
    p = tmp_path / 'x.json'; p.write_text(text)
    with pytest.raises(ValueError): forecast.read_json(p)


def tiny_manifest(root):
    (root / 'x.txt').write_text('intact')
    (root / 'MANIFEST.json').write_text(json.dumps({'files': {'x.txt': forecast.digest(root / 'x.txt')}}))
    return forecast.digest(root / 'MANIFEST.json')


def test_manifest_positive_and_tamper(tmp_path):
    expected = tiny_manifest(tmp_path)
    assert forecast.verify_tree(tmp_path, expected)['verified_files'] == 1
    (tmp_path / 'x.txt').write_text('modified')
    with pytest.raises(ValueError): forecast.verify_tree(tmp_path, expected)


def test_extra_file_and_wrong_manifest_fail(tmp_path):
    expected = tiny_manifest(tmp_path)
    with pytest.raises(ValueError): forecast.verify_tree(tmp_path, '0' * 64)
    (tmp_path / 'extra').write_text('unbound')
    with pytest.raises(ValueError): forecast.verify_tree(tmp_path, expected)


@pytest.mark.parametrize('name', ['../x', '/x', 'a\\b', 'a//b', './x', 'MANIFEST.json'])
def test_manifest_path_defenses(tmp_path, name):
    (tmp_path / 'MANIFEST.json').write_text(json.dumps({'files': {name: 'a' * 64}}))
    with pytest.raises(ValueError): forecast.verify_tree(tmp_path, forecast.digest(tmp_path / 'MANIFEST.json'))


def test_symlink_rejected(tmp_path):
    expected = tiny_manifest(tmp_path)
    (tmp_path / 'x.txt').unlink(); (tmp_path / 'x.txt').symlink_to('/etc/hosts')
    with pytest.raises(ValueError): forecast.verify_tree(tmp_path, expected)


def ledger():
    return {'schema': 'lumencore.paper_accounting.v1', 'mode': 'paper', 'currency': 'USD',
        'initial_cash': '1000', 'as_of_utc': '2026-09-11T12:05:00Z', 'max_mark_age_seconds': 3600,
        'events': [
            {'id': 'd1', 'time_utc': '2026-09-11T12:00:00Z', 'type': 'deposit', 'amount': '500'},
            {'id': 'b1', 'time_utc': '2026-09-11T12:01:00Z', 'type': 'buy', 'instrument': 'TEST', 'quantity': '2', 'price': '100', 'fee': '1'},
            {'id': 's1', 'time_utc': '2026-09-11T12:02:00Z', 'type': 'sell', 'instrument': 'TEST', 'quantity': '1', 'price': '110', 'fee': '1'}],
        'marks': {'TEST': {'price': '105', 'time_utc': '2026-09-11T12:05:00Z'}}, 'reported_cash': '1408'}


def test_deposits_are_not_profit_and_fees_are_charged():
    r = paper.audit_paper_ledger(ledger())
    assert r['net_external_flows'] == '500' and r['net_paper_pnl'] == '13'
    assert r['cash'] == '1408' and r['equity'] == '1513' and r['fees'] == '2'
    assert r['live_authorized'] is False and r['broker_reconciled'] is False


@pytest.mark.parametrize('key,value', [('mode', 'live'), ('currency', 'EUR'), ('initial_cash', 1000),
    ('initial_cash', '-1'), ('initial_cash', 'NaN'), ('initial_cash', '1e9'),
    ('max_mark_age_seconds', True), ('max_mark_age_seconds', -1), ('reported_cash', '1409'),
    ('as_of_utc', '2026-09-11T12:05:00'), ('as_of_utc', '2026-09-11T13:05:00+01:00')])
def test_bad_ledger_headers(key, value):
    d = ledger(); d[key] = value
    with pytest.raises(ValueError): paper.audit_paper_ledger(d)


@pytest.mark.parametrize('key,value', [('fee', '-1'), ('fee', 'Infinity'), ('quantity', '0'),
    ('quantity', '3'), ('price', '0'), ('id', 'b1'), ('type', 'order'),
    ('instrument', '../bad'), ('time_utc', '2026-09-11T12:00:30Z'), ('time_utc', '2026-09-11T13:00:00Z')])
def test_bad_fill_or_chronology(key, value):
    d = ledger(); d['events'][2][key] = value
    with pytest.raises(ValueError): paper.audit_paper_ledger(d)


@pytest.mark.parametrize('marks', [{}, {'TEST': {'price': '105', 'time_utc': '2026-09-10T12:05:00Z'}},
    {'TEST': {'price': '105', 'time_utc': '2026-09-11T12:06:00Z'}},
    {'TEST': {'price': '-105', 'time_utc': '2026-09-11T12:05:00Z'}},
    {'TEST': {'price': '105', 'time_utc': '2026-09-11T12:05:00Z'}, 'EXTRA': {}}])
def test_invalid_marks(marks):
    d = ledger(); d['marks'] = marks
    with pytest.raises(ValueError): paper.audit_paper_ledger(d)


def test_ledger_overdraft_and_unknown_fields():
    d = ledger(); d['events'][0]['type'] = 'withdrawal'; d['events'][0]['amount'] = '1001'
    with pytest.raises(ValueError): paper.audit_paper_ledger(d)
    d = ledger(); d['unexpected_field'] = 'not-supported'
    with pytest.raises(ValueError): paper.audit_paper_ledger(d)


def test_fractional_accounting_and_separate_fees():
    d = ledger(); d['events'] = [
        {'id':'b', 'time_utc':'2026-09-11T12:00:00Z', 'type':'buy','instrument':'TEST','quantity':'0.1','price':'0.2','fee':'0.001'},
        {'id':'f', 'time_utc':'2026-09-11T12:01:00Z', 'type':'fee','amount':'0.002'}]
    d['reported_cash'] = '999.977'; d['marks']['TEST']['price'] = '0.2'
    assert paper.audit_paper_ledger(d)['net_paper_pnl'] == '-0.003'
