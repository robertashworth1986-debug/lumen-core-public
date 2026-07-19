import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ["api[_-]?key", "secret", "token", "password", "bearer", "private[_-]?key"]
SPEC = importlib.util.spec_from_file_location("node_red_safety", ROOT / "code" / "ops" / "AUDIT_NODERED_FLOW_SAFETY.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
audit_flow, audit_ensure, run = AUDIT.audit_flow, AUDIT.audit_ensure, AUDIT.run

def node(**kwargs): return {"id": kwargs.pop("id", "n1"), **kwargs}

def test_real_targets_fail_closed_on_known_controls():
    result = run()
    assert result["decision"] == "BLOCK"
    rules = {item["rule"] for item in result["findings"]}
    assert {"AUTO_FIRE_INJECT", "DEBUG_PAYLOAD_EXPOSURE", "HTTP_TIMEOUT", "HTTP_ERROR_PATH", "REPLACE_ALL_FLOWS_POST"} <= rules
    assert "NON_LOOPBACK_HTTP_ENDPOINT" not in rules

def test_once_false_and_empty_repeat_are_not_auto_fire(tmp_path):
    p = tmp_path / "safe.json"
    p.write_text(json.dumps([node(type="inject", once=False, repeat="", crontab="", wires=[])]), encoding="utf-8")
    assert "AUTO_FIRE_INJECT" not in {x["rule"] for x in audit_flow(p, PATTERNS)}

def test_hidden_inject_repeat_is_blocked(tmp_path):
    p = tmp_path / "evil.json"
    p.write_text(json.dumps([node(type="inject", once=False, repeat=" 5 ", wires=[])]), encoding="utf-8")
    assert any(x["rule"] == "AUTO_FIRE_INJECT" for x in audit_flow(p, PATTERNS))

def test_debug_false_is_allowed_but_payload_debug_is_not(tmp_path):
    p = tmp_path / "debug.json"
    p.write_text(json.dumps([node(id="off", type="debug", active=False, complete="payload"), node(id="on", type="debug", active=True, complete="payload")]));
    assert any(x["rule"] == "DEBUG_PAYLOAD_EXPOSURE" and x["node_id"] == "on" for x in audit_flow(p, PATTERNS))

def test_http_requires_timeout_and_connected_catch(tmp_path):
    p = tmp_path / "http.json"
    p.write_text(json.dumps([node(id="h", type="http request", timeout=10, url="https://service.invalid", wires=[["c"]]), node(id="c", type="catch", wires=[])]), encoding="utf-8")
    assert not {x["rule"] for x in audit_flow(p, PATTERNS)} & {"HTTP_TIMEOUT", "HTTP_ERROR_PATH"}

def test_loopback_http_is_allowed_but_wildcard_or_remote_hosts_are_blocked(tmp_path):
    p = tmp_path / "hosts.json"
    p.write_text(json.dumps([
        node(id="local", type="http request", timeout=10, url="http://127.0.0.1:8787/api", wires=[["catch"]]),
        node(id="wildcard", type="http request", timeout=10, url="http://0.0.0.0:8787/api", wires=[["catch"]]),
        node(id="remote", type="http request", timeout=10, url="https://service.invalid/api", wires=[["catch"]]),
        node(id="catch", type="catch", wires=[]),
    ]), encoding="utf-8")
    findings = audit_flow(p, PATTERNS)
    blocked_ids = {x["node_id"] for x in findings if x["rule"] == "NON_LOOPBACK_HTTP_ENDPOINT"}
    assert blocked_ids == {"wildcard", "remote"}

def test_malformed_flow_is_blocking(tmp_path):
    p = tmp_path / "bad.json"; p.write_text("{not json", encoding="utf-8")
    assert audit_flow(p, PATTERNS)[0]["rule"] == "FLOW_PARSE"

def test_ensure_post_flows_and_secret_literal_are_blocking(tmp_path):
    p = tmp_path / "ensure.py"
    p.write_text('urllib.request.Request("http://localhost:1880/flows", data=b"x", method="POST")\nAPI_KEY = "literal"', encoding="utf-8")
    rules = {x["rule"] for x in audit_ensure(p, PATTERNS)}
    assert {"REPLACE_ALL_FLOWS_POST", "SECRET_LIKE_LITERAL"} <= rules
    assert "NON_LOOPBACK_HTTP_ENDPOINT" not in rules
