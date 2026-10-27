"""Offline regressions for the existing local dashboard's evidence labels."""

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

HELMIER_HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const elements = new Map();
const document = {getElementById(id) {
  if (!elements.has(id)) elements.set(id, {className: '', innerHTML: '', textContent: ''});
  return elements.get(id);
}};
const window = {LUMA_API_BASE: 'https://offline.invalid'};
async function fetch(url) {
  const pathname = new URL(url, 'https://offline.invalid/dashboard/').pathname;
  const key = pathname === '/api/snapshot' ? 'snapshot' : pathname.split('/').pop();
  const supplied = Object.prototype.hasOwnProperty.call(input.routes, key);
  const value = input.routes[key];
  return {ok: supplied, async json() {
    return value && Object.prototype.hasOwnProperty.call(value, 'rawJson')
      ? JSON.parse(value.rawJson) : value;
  }, async text() {return typeof value === 'string' ? value : '';}};
}
vm.runInNewContext(fs.readFileSync(input.source, 'utf8'), {
  window, document, fetch, location: {protocol: 'https:', hostname: 'offline.invalid', origin: 'https://offline.invalid'},
  setInterval() {return 1;}
});
(async () => {
  window.LumaDS.mountHelmier('proof');
  const report = await window.LumaDS.refreshHelmier('proof');
  process.stdout.write(JSON.stringify({report, html: elements.get('proof').innerHTML,
    displayed: Object.fromEntries([...elements].map(([id, element]) => [id, element.textContent]))}));
})().catch(error => {console.error(error); process.exitCode = 1;});
"""


def helmier(routes):
    if shutil.which('node') is None:
        pytest.skip('Node.js is required for the offline dashboard behavior check')
    result = subprocess.run(
        ['node', '-e', HELMIER_HARNESS],
        input=json.dumps({'source': str(ROOT / 'dashboard/js/luma_design_system.js'), 'routes': routes}, allow_nan=False),
        text=True, capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_missing_helmier_sources_never_invent_performance_money_or_verification():
    result = helmier({})
    report = result['report']
    for key in ('sharpe', 'improvement', 'opportunity', 'closedTrades'):
        assert report[key] == 'n/a — unverified'
    assert 'unverified' in report['chain']
    assert report['txid'] == 'n/a — execution unverified'
    assert not any(value in json.dumps(report) for value in ('4.277', '458.2', '35,116', '35116'))
    assert 'Live Answers' not in result['html'] and 'Investor Proof' not in result['html']
    assert 'Did it execute live?' not in result['html'] and 'Measured opportunity' not in result['html']
    assert result['displayed']['proof-sharpe'] == report['sharpe']


@pytest.mark.parametrize('invalid', ['', '   ', True, False, [], {}, 'Infinity', '-Infinity', 'NaN', 'unknown', '0x10', '1e309'])
def test_malformed_helmier_numbers_remain_unknown(invalid):
    report = helmier({
        'cross_sector_optimization_report.json': {
            'best_strategy_sharpe': invalid, 'improvement_pct': invalid,
            'rolling_opportunity_per_hour': invalid,
        },
        'CHAIN_OF_CUSTODY_SHA256.json': {'artifact_count': invalid},
        'snapshot': {'paper': {'closed_trades': invalid}, 'packages': {'usage_pct': invalid}},
    })['report']
    for key in ('sharpe', 'improvement', 'opportunity', 'closedTrades'):
        assert report[key] == 'n/a — unverified'
    assert report['chain'] == 'hash listings n/a — unverified'


def test_nonfinite_json_numbers_cannot_become_dashboard_metrics():
    report = helmier({'cross_sector_optimization_report.json': {
        'rawJson': '{"best_strategy_sharpe":1e309,"improvement_pct":-1e309,"rolling_opportunity_per_hour":1e309}'
    }})['report']
    assert report['sharpe'] == report['improvement'] == report['opportunity'] == 'n/a — unverified'


@pytest.mark.parametrize('value,sharpe,delta,money', [
    (-2, '-2.000', '-2.0%', '$-2/hr'),
    (0, '0.000', '0.0%', '$0/hr'),
    ('3.5', '3.500', '+3.5%', '$3.5/hr'),
])
def test_reported_metrics_preserve_negative_zero_and_positive_values(value, sharpe, delta, money):
    result = helmier({
        'cross_sector_optimization_report.json': {
            'best_strategy_sharpe': value, 'improvement_pct': value,
            'rolling_opportunity_per_hour': value,
        },
        'CHAIN_OF_CUSTODY_SHA256.json': {'artifact_count': 0},
        'snapshot': {'paper': {'closed_trades': 0}},
    })
    report = result['report']
    assert report['sharpe'] == f'reported {sharpe} (historical, unverified)'
    assert report['improvement'] == f'reported {delta} | baseline unverified'
    assert report['opportunity'] == f'estimated {money} | unverified'
    assert report['closedTrades'] == 'reported 0 | unverified'
    assert report['chain'] == '0 hashes listed | unverified'
    assert 'luma-helmier-a green' not in result['html']


def test_gateway_zero_and_adverse_reports_do_not_fall_back_to_better_numbers():
    report = helmier({
        'snapshot': {'edge': {'top_test_sharpe': 0}, 'packages': {'usage_pct': 0},
                     'evidence': {'derived': {'stacker_router_delta_pct': -5}}},
        'cross_sector_optimization_report.json': {
            'best_strategy_sharpe': 9, 'improvement_pct': 100, 'rolling_opportunity_per_hour': 500,
        },
    })['report']
    assert report['sharpe'] == 'reported 0.000 (historical, unverified)'
    assert report['improvement'] == 'reported -5.0% | baseline unverified'
    assert report['opportunity'] == 'reported 0.0% pkg usage | unverified'


@pytest.mark.parametrize('flag,expected', [(True, 'reported PASS | unverified'), (False, 'reported FAIL | unverified'), ('false', 'n/a — unverified')])
def test_validation_status_is_reported_without_promoting_truthy_strings(flag, expected):
    report = helmier({'seed_validation_readout.json': {'passed': flag}})['report']
    assert report['walkForward'] == expected


def test_order_ids_hash_listings_and_old_timestamps_do_not_prove_live_execution():
    report = helmier({
        'execution_events.jsonl': '{"order_id":"reported-order-123"}\n',
        'CHAIN_OF_CUSTODY_SHA256.json': {'verified': True, 'files': [{'sha256': 'unverified-entry'}]},
        'federal_brief_daemon_heartbeat.json': {'generated_utc': '2020-01-01T00:00:00Z'},
    })['report']
    assert report['txid'] == 'reported reported-order-123 | execution unverified'
    assert report['chain'] == '1 hashes listed | unverified'
    assert report['reliability'] == 'reported heartbeat 2020-01-01 00:00:00 | freshness unverified'
