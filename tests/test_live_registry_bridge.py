"""Exercise the delivered browser bridge with deterministic DOM/fetch fixtures."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "dashboard/js/live_registry_bridge.js"
NOW = "2026-10-14T12:00:10.000Z"
GENERATED = "2026-10-14T12:00:00+00:00"
HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const RealDate = Date;
class Clock extends RealDate {
  constructor(...args) { super(...(args.length ? args : [input.now])); }
  static now() { return RealDate.parse(input.now); }
}
const ids = new Map();
const calls = [];
let index = 0;
const context = {
  Date: Clock, window: {},
  document: {getElementById(id) {
    if (!ids.has(id)) ids.set(id, {textContent: '', title: ''});
    return ids.get(id);
  }},
  fetch: async (url, options) => {
    calls.push({url, options});
    const response = input.responses[index++];
    if (!response || response.network_error) throw new Error('offline');
    return {ok: response.ok !== false, json: async () => {
      if (response.parse_error) throw new Error('invalid JSON');
      return Object.hasOwn(response, 'raw') ? JSON.parse(response.raw) : response.payload;
    }};
  },
  setInterval() { throw new Error('refresh must not start a worker'); },
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
context.window.LumaLiveBridge.refresh().then(() => {
  process.stdout.write(JSON.stringify({elements: Object.fromEntries(ids), calls}));
}).catch(error => { console.error(error); process.exitCode = 1; });
"""


def reports():
    return [
        {"generated_utc": GENERATED, "count": 1,
         "rows": [{"pick": "Research candidate", "edge_pct": -1.25}]},
        {"generated_utc": GENERATED, "installed_count": 0, "total_checked": 3},
        {"generated_utc": GENERATED, "regime": "normal", "vix": 0},
        {"generated_utc": GENERATED, "execution_mode": "paper", "status": "healthy"},
        {"generated_utc": GENERATED, "health": "degraded"},
    ]


@pytest.fixture
def bridge():
    if shutil.which("node") is None:
        pytest.skip("requires Node.js for the real browser-source VM fixture")

    def run(payloads=None, *, responses=None):
        if responses is None:
            responses = [{"payload": row} for row in (payloads or reports())]
        completed = subprocess.run(
            ["node", "-e", HARNESS, str(BRIDGE)],
            input=json.dumps({"now": NOW, "responses": responses}),
            cwd=ROOT, text=True, capture_output=True, check=True, timeout=10,
        )
        return json.loads(completed.stdout)

    return run


def text(result, element):
    return result["elements"][element]["textContent"]


def test_failed_polls_are_not_current_source_observations_or_zero_picks(bridge):
    result = bridge(responses=[{"network_error": True}] * 5)
    assert text(result, "livePicksCount") == "n/a"
    for element in ("liveTopPick", "liveTopEdge", "liveStackHealth", "liveVix",
                    "liveExecMode", "liveInfraHealth"):
        assert text(result, element) == "n/a"
    assert text(result, "liveRegime") == "unknown"
    stamp = text(result, "liveRegistryStamp")
    assert "Poll attempted: " + NOW in stamp
    assert "Source observation: unknown" in stamp
    assert "Freshness: unknown" in stamp


def test_recent_reports_stay_reported_without_becoming_source_freshness(bridge):
    result = bridge()
    for element, expected in {
        "livePicksCount": "Reported: 1", "liveTopPick": "Reported: Research candidate",
        "liveTopEdge": "Reported: -1.25%", "liveStackHealth": "Reported: 0/3",
        "liveRegime": "Reported: normal", "liveVix": "Reported: 0.00",
        "liveExecMode": "Reported: paper", "liveInfraHealth": "Reported: degraded",
    }.items():
        assert text(result, element) == expected
        assert "Report generated: 2026-10-14T12:00:00.000Z" in result["elements"][element]["title"]
        assert "source observation/freshness unknown" in result["elements"][element]["title"]
    assert len(result["calls"]) == 5
    assert all(call["options"]["cache"] == "no-store" for call in result["calls"])
    assert "Source observation: unknown" in text(result, "liveRegistryStamp")


@pytest.mark.parametrize("timestamp", [
    None, "", "2026-10-14", "invalid", "2026-02-31T12:00:00Z",
    "2026-10-14T12:00:11Z", "2026-10-14T11:55:09Z", "2020-01-01T00:00:00Z",
])
def test_missing_invalid_future_or_old_report_times_suppress_numbers(bridge, timestamp):
    payloads = reports()
    for row in payloads:
        row["generated_utc"] = timestamp
    result = bridge(payloads)
    assert text(result, "livePicksCount") == "n/a"
    assert text(result, "liveVix") == "n/a"
    assert text(result, "liveExecMode") == "n/a"
    assert text(result, "liveInfraHealth") == "n/a"
    assert "Freshness: unknown" in text(result, "liveRegistryStamp")


def test_empty_valid_board_is_zero_but_missing_or_inconsistent_board_is_unknown(bridge):
    payloads = reports()
    payloads[0] = {"generated_utc": GENERATED, "count": 0, "rows": []}
    assert text(bridge(payloads), "livePicksCount") == "Reported: 0"
    for board in [None, [], {}, {"generated_utc": GENERATED, "count": 0},
                  {"generated_utc": GENERATED, "rows": [], "count": 2},
                  {"generated_utc": GENERATED, "rows": [None]},
                  {"generated_utc": GENERATED, "rows": [], "count": "0"}]:
        payloads[0] = board
        result = bridge(payloads)
        assert text(result, "livePicksCount") == "n/a"
        assert text(result, "liveTopPick") == "n/a"


@pytest.mark.parametrize("invalid", ["", " ", "1", "NaN", "Infinity", None, True, [], {}])
def test_numeric_fields_do_not_coerce_placeholders_or_booleans(bridge, invalid):
    payloads = reports()
    payloads[0]["rows"][0]["edge_pct"] = invalid
    payloads[1]["installed_count"] = invalid
    payloads[2]["vix"] = invalid
    result = bridge(payloads)
    assert text(result, "liveTopEdge") == "n/a"
    assert text(result, "liveStackHealth") == "n/a"
    assert text(result, "liveVix") == "n/a"


def test_json_numeric_overflow_and_impossible_stack_counts_are_unknown(bridge):
    responses = [{"payload": row} for row in reports()]
    responses[0] = {"raw": '{"generated_utc":"' + GENERATED + '","rows":[{"pick":"x","edge_pct":1e999}]}'}
    responses[2] = {"raw": '{"generated_utc":"' + GENERATED + '","vix":-1e999,"regime":"normal"}'}
    result = bridge(responses=responses)
    assert text(result, "liveTopEdge") == "n/a"
    assert text(result, "liveVix") == "n/a"
    for installed, total in [(4, 3), (-1, 3), (0.5, 3), (1, -1), (1, 3.5), (1, 0)]:
        payloads = reports()
        payloads[1].update(installed_count=installed, total_checked=total)
        assert text(bridge(payloads), "liveStackHealth") == "n/a"


def test_failed_sources_never_borrow_health_or_macro_from_other_reports(bridge):
    payloads = reports()
    payloads[0]["macro"] = {"regime": "calm", "vix": 10}
    payloads[2] = {"generated_utc": GENERATED, "error": "upstream failed", "vix": 20, "regime": "normal"}
    payloads[4] = {"generated_utc": GENERATED}
    result = bridge(payloads)
    assert text(result, "liveRegime") == "unknown"
    assert text(result, "liveVix") == "n/a"
    assert text(result, "liveInfraHealth") == "n/a"
    responses = [{"ok": False}, {"parse_error": True}, {"payload": []},
                 {"payload": "paper"}, {"payload": None}]
    result = bridge(responses=responses)
    assert text(result, "livePicksCount") == "n/a"
    assert text(result, "liveExecMode") == "n/a"


def test_report_age_boundary_is_not_an_underlying_observation_claim(bridge):
    payloads = reports()
    payloads[0]["generated_utc"] = "2026-10-14T11:55:10Z"
    result = bridge(payloads)
    assert text(result, "livePicksCount") == "Reported: 1"
    assert "300s maximum report age" in result["elements"]["livePicksCount"]["title"]
    assert "Freshness: unknown" in text(result, "liveRegistryStamp")
