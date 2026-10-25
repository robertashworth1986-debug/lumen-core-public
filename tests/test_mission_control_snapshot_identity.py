"""Exercise the delivered meeting view against real and mixed-version snapshots."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
REVIEW_COMMIT = "2022d0c319c7585ab4d35fbe97f1ba48e6f0e37d"
HISTORICAL_COMMIT = "e706e91de133e039cc16ed25ec5021a293edbf2b"
PATHS = {
    "packet": "dashboard/data/external_technical_review_packet.json",
    "audit": "dashboard/data/lumencore_engine_portfolio_audit.json",
    "catalogue": "dashboard/portfolio/data/portfolio.json",
}

HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Node {
  constructor(id = '') {
    this.id = id; this.children = []; this.dataset = {}; this.style = {};
    this.attributes = {}; this.events = {}; this.textContent = '';
    this.value = id === 'comparison-window' ? 'original' : '';
    this.classList = {add() {}, remove() {}, toggle() {}, contains() {return false;}};
  }
  append(...nodes) {this.children.push(...nodes);}
  replaceChildren(...nodes) {this.children = nodes;}
  get lastElementChild() {return this.children.at(-1);}
  setAttribute(key, value) {this.attributes[key] = value;}
  removeAttribute(key) {delete this.attributes[key];}
  addEventListener(name, fn) {this.events[name] = fn;}
  focus() {}
  querySelectorAll() {return [];}
}
const elements = new Map();
const pathLink = new Node(); pathLink.dataset.sourcePath = 'code/forecast_evaluation_v2.py';
const document = {
  getElementById(id) {
    if (!elements.has(id)) {
      const node = new Node(id);
      if (['evidence-count', 'lane-count', 'catalogue-count'].includes(id)) node.textContent = '—';
      elements.set(id, node);
    }
    return elements.get(id);
  },
  createElement() {return new Node();},
  createDocumentFragment() {return new Node();},
  querySelectorAll(selector) {return selector === '[data-source-path]' ? [pathLink] : [];},
  addEventListener() {}, body: new Node(), documentElement: new Node()
};
const requests = [];
async function fetch(path) {
  requests.push(path);
  const file = path === './data/external_technical_review_packet.json' ? 'packet'
    : path === './data/lumencore_engine_portfolio_audit.json' ? 'audit' : 'catalogue';
  let bytes = Buffer.from(input.sources[file], 'base64');
  if (input.changed === file) bytes = Buffer.concat([bytes, Buffer.from('\n')]);
  return {ok: input.missing !== file, status: input.missing === file ? 404 : 200,
    async arrayBuffer() {return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);},
    async json() {return JSON.parse(bytes.toString('utf8'));}};
}
const crypto = input.noCrypto ? undefined : require('node:crypto').webcrypto;
['evidence-count', 'lane-count', 'catalogue-count', 'packet-assets', 'engine-list', 'portfolio-results'].forEach(id => document.getElementById(id));
vm.runInNewContext(fs.readFileSync(input.script, 'utf8'), {
  document, fetch, crypto, TextDecoder, URL, Uint8Array,
  window: {addEventListener() {}}, location: {hash: ''}, history: {replaceState() {}}
});
function links(node) {return [...(node.href ? [node.href] : []), ...node.children.flatMap(links)];}
(async () => {
  const deadline = Date.now() + 3000;
  while (!document.getElementById('snapshot-status').textContent) {
    if (Date.now() > deadline) throw new Error('Snapshot tasks did not settle');
    await new Promise(resolve => setTimeout(resolve, 5));
  }
  const comparison = document.getElementById('comparison-window');
  const original = document.getElementById('baseline-improvement').textContent;
  comparison.value = 'later'; comparison.events.change();
  process.stdout.write(JSON.stringify({
    displayed: Object.fromEntries([...elements].map(([id, node]) => [id, node.textContent])),
    packetLinks: links(document.getElementById('packet-assets')),
    auditLinks: links(document.getElementById('engine-list')),
    sourceLink: pathLink.href, comparisonLink: document.getElementById('comparison-source').href,
    original, requests,
    childCounts: Object.fromEntries(['packet-assets', 'engine-list', 'portfolio-results'].map(id => [id, document.getElementById(id).children.length]))
  }));
})().catch(error => {console.error(error); process.exitCode = 1;});
"""


def review(**options):
    import base64

    if shutil.which("node") is None:
        pytest.skip("Node.js is required to exercise the delivered browser script")
    payload = {
        "script": str(ROOT / "dashboard/assets/mission_control_review.js"),
        "sources": {name: base64.b64encode((ROOT / path).read_bytes()).decode("ascii") for name, path in PATHS.items()},
        **options,
    }
    result = subprocess.run(["node", "-e", HARNESS], input=json.dumps(payload),
                            text=True, capture_output=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_current_snapshots_render_with_their_exact_source_commit():
    result = review()
    assert result["displayed"]["evidence-count"] == "44"
    assert result["displayed"]["lane-count"] == "15"
    assert result["displayed"]["catalogue-count"] == "64"
    assert len(result["packetLinks"]) == 44
    assert all(f"/blob/{REVIEW_COMMIT}/" in url for url in result["packetLinks"] + result["auditLinks"])
    assert f"/blob/{REVIEW_COMMIT}/code/forecast_evaluation_v2.py" in result["sourceLink"]
    assert REVIEW_COMMIT in result["displayed"]["snapshot-status"]
    assert result["original"] == "10.60%"
    assert result["displayed"]["baseline-improvement"] == "18.51%"
    assert f"/blob/{HISTORICAL_COMMIT}/" in result["comparisonLink"]
    assert set(result["requests"]) == {"./data/external_technical_review_packet.json", "./data/lumencore_engine_portfolio_audit.json", "./portfolio/data/portfolio.json"}


@pytest.mark.parametrize("name,count_id,container", [
    ("packet", "evidence-count", "packet-assets"),
    ("audit", "lane-count", "engine-list"),
    ("catalogue", "catalogue-count", "portfolio-results"),
])
def test_valid_json_from_another_snapshot_cannot_create_counts_or_source_links(name, count_id, container):
    # A newline preserves every JSON field but changes the served bytes.
    result = review(changed=name)
    assert result["displayed"][count_id] == "—"
    assert result["childCounts"][container] == 0
    assert "unavailable" in result["displayed"]["snapshot-status"]


def test_unavailable_digest_support_does_not_render_unverified_snapshot_counts():
    result = review(noCrypto=True)
    for key in ("evidence-count", "lane-count", "catalogue-count"):
        assert result["displayed"][key] == "—"
    assert all(value == 0 for value in result["childCounts"].values())


def test_missing_packet_keeps_other_verified_snapshots_and_historical_comparison():
    result = review(missing="packet")
    assert result["displayed"]["evidence-count"] == "—"
    assert result["packetLinks"] == []
    assert result["displayed"]["lane-count"] == "15"
    assert result["displayed"]["catalogue-count"] == "64"
    assert result["displayed"]["baseline-improvement"] == "18.51%"
