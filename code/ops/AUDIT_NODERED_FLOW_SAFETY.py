"""Static, fail-closed Node-RED safety audit. Never starts Node-RED or makes calls."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config" / "node_red_flow_safety_policy_v1.json"
DEFAULT_FLOWS = sorted((ROOT / "code" / "node_red").glob("*.json"))
ENSURE = ROOT / "code" / "ENSURE_NODERED_LUMA_FLOWS.py"
SEVERITY = "BLOCKER"

def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)

def finding(rule: str, path: Path, detail: str, node_id: str | None = None) -> dict[str, Any]:
    item = {"severity": SEVERITY, "rule": rule, "path": display_path(path), "detail": detail}
    if node_id:
        item["node_id"] = node_id
    return item

def _secret_hits(value: str, patterns: list[str]) -> list[str]:
    return [p for p in patterns if re.search(r"(?i)(?:^|[^a-z])" + p + r"(?:$|[^a-z])", value)]

def _literal_http_host(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    return parsed.hostname.lower()

def _is_loopback_host(host: str) -> bool:
    return host in {"localhost", "127.0.0.1", "::1"}

def audit_flow(path: Path, patterns: list[str]) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [finding("FLOW_PARSE", path, f"cannot parse JSON: {exc}")]
    if not isinstance(data, list):
        return [finding("FLOW_SCHEMA", path, "flow document must be a JSON list")]
    findings: list[dict[str, Any]] = []
    ids = {n.get("id") for n in data if isinstance(n, dict)}
    for node in data:
        if not isinstance(node, dict):
            findings.append(finding("FLOW_SCHEMA", path, "node must be an object")); continue
        nid = str(node.get("id", "<missing>"))
        ntype = node.get("type")
        if ntype == "inject" and (node.get("once") is True or str(node.get("repeat", "")).strip() or str(node.get("crontab", "")).strip()):
            findings.append(finding("AUTO_FIRE_INJECT", path, "inject fires automatically via once, repeat, or crontab", nid))
        if ntype == "debug" and node.get("active", True) is not False and str(node.get("complete", "payload")).strip() not in {"", "false", "none"}:
            findings.append(finding("DEBUG_PAYLOAD_EXPOSURE", path, f"active debug emits {node.get('complete', 'payload')!r}", nid))
        if ntype == "http request":
            timeout = node.get("timeout")
            try: timeout_ok = float(timeout) > 0
            except (TypeError, ValueError): timeout_ok = False
            if not timeout_ok:
                findings.append(finding("HTTP_TIMEOUT", path, "http request has no positive timeout", nid))
            outgoing = [x for wire in node.get("wires", []) if isinstance(wire, list) for x in wire]
            if not any(x not in ids or (isinstance(x, str) and any(n.get("id") == x and n.get("type") in {"catch", "status"} for n in data if isinstance(n, dict))) for x in outgoing):
                findings.append(finding("HTTP_ERROR_PATH", path, "no statically connected catch/status error path", nid))
            url = str(node.get("url", ""))
            host = _literal_http_host(url)
            if host is not None and not _is_loopback_host(host):
                findings.append(finding("NON_LOOPBACK_HTTP_ENDPOINT", path, f"HTTP URL is not loopback-bound: {host}", nid))
        serialized = json.dumps(node, sort_keys=True)
        hits = _secret_hits(serialized, patterns)
        if hits and ntype != "tab":
            findings.append(finding("SECRET_LIKE_LITERAL", path, "secret-like key/name appears in flow node: " + ", ".join(hits), nid))
    return findings

def audit_ensure(path: Path, patterns: list[str]) -> list[dict[str, Any]]:
    try: text = path.read_text(encoding="utf-8")
    except Exception as exc: return [finding("ENSURE_READ", path, f"cannot read script: {exc}")]
    findings = []
    if re.search(r"(?i)POST", text) and re.search(r"['\"]?/flows", text):
        findings.append(finding("REPLACE_ALL_FLOWS_POST", path, "ensure script can POST /flows, a replace-all deployment endpoint"))
    for url in re.findall(r"https?://[^\s'\"]+", text, flags=re.IGNORECASE):
        host = _literal_http_host(url)
        if host is not None and not _is_loopback_host(host):
            findings.append(finding("NON_LOOPBACK_HTTP_ENDPOINT", path, f"ensure script URL is not loopback-bound: {host}"))
    if re.search(r"(?i)(api[_-]?key|secret|token|password|bearer|private[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]", text):
        findings.append(finding("SECRET_LIKE_LITERAL", path, "ensure script contains a secret-like literal assignment"))
    return findings

def run(flow_paths: list[Path] | None = None, ensure_path: Path = ENSURE, policy_path: Path = POLICY) -> dict[str, Any]:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    patterns = policy.get("secret_patterns", [])
    paths = flow_paths if flow_paths is not None else DEFAULT_FLOWS
    findings = [f for p in paths for f in audit_flow(p, patterns)]
    findings.extend(audit_ensure(ensure_path, patterns))
    return {"policy_id": policy["policy_id"], "fail_closed": True, "targets": [display_path(p) for p in paths] + [display_path(ensure_path)], "findings": findings, "decision": "BLOCK" if findings else "PASS"}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out: args.json_out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if result["decision"] == "BLOCK" else 0

if __name__ == "__main__": sys.exit(main())
