from __future__ import annotations

import ast
import copy
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from booth_public_contract import (  # noqa: E402
    public_booth_contains_forbidden_value,
    public_booth_projection,
)


SYNTHETIC_TRANSACTION = "OABCDE-FGHIJK-LMNOPQ"
SYNTHETIC_PATH = r"C:\SyntheticPrivate\execution.jsonl"
SYNTHETIC_TAX_ID = "12-3456789"
SYNTHETIC_PATENT_ID = "12/345,678"
SYNTHETIC_EMAIL = "private.person@example.invalid"


def _raw_payload() -> dict:
    trade = {
        "timestamp": "2026-01-01T00:00:00Z",
        "txid": SYNTHETIC_TRANSACTION,
        "symbol": "SYNTH",
        "pair": "SYNTHUSD",
        "side": "buy",
        "status": "placed",
        "size_usd": 123.45,
    }
    return {
        "founder_profile": {
            "founder": "Synthetic Founder",
            "ein": SYNTHETIC_TAX_ID,
            "uspto_non_provisional_application": SYNTHETIC_PATENT_ID,
        },
        "indexing": {"files_indexed": 7},
        "live_execution": {
            "heartbeat": {
                "status": "running",
                "reason": f"private {SYNTHETIC_TAX_ID}",
                "symbol": "SYNTH",
                "universe_candidate_count": 5,
                "timestamp_utc": "2026-01-01T00:30:00Z",
            },
            "latest_trade": copy.deepcopy(trade),
            "recent_trade_count": 1,
            "recent_trades": [copy.deepcopy(trade)],
        },
        "premium_mirror": {"destination_root": SYNTHETIC_PATH},
        "autonomous_grant_win": {
            "master_valuation_proxy_usd": 456789.0,
            "event_id": "synthetic-event",
        },
        "artifacts": {"live_trade_ledger_jsonl": SYNTHETIC_PATH},
        "private_notes": {
            "tax_reference": SYNTHETIC_TAX_ID,
            "patent_reference": SYNTHETIC_PATENT_ID,
            "transaction_reference": SYNTHETIC_TRANSACTION,
            "contact": SYNTHETIC_EMAIL,
            "api_key": "synthetic-not-a-real-key",
        },
    }


def test_public_projection_redacts_operational_details_and_claims() -> None:
    raw = _raw_payload()
    original = copy.deepcopy(raw)
    projected = public_booth_projection(raw)
    serialized = json.dumps(projected, sort_keys=True)

    for forbidden in (
        SYNTHETIC_TRANSACTION,
        SYNTHETIC_PATH,
        SYNTHETIC_TAX_ID,
        SYNTHETIC_PATENT_ID,
        SYNTHETIC_EMAIL,
    ):
        assert forbidden not in serialized
        assert public_booth_contains_forbidden_value(forbidden) is True

    assert raw == original
    assert projected["indexing"] == {
        "files_indexed": 7,
        "roots_present": 0,
        "roots_total": 0,
        "scan_capped": False,
    }
    assert projected["catalog"] == {
        "engine_count": 0,
        "assets_source_rows": 0,
    }
    assert set(projected) == {
        "schema",
        "generated_utc",
        "brand",
        "indexing",
        "catalog",
        "supported_maturity_level",
        "details_redacted",
        "public_claim_allowed",
        "profit_claim_allowed",
        "live_execution_authority",
        "level_5_attained",
        "claim_boundary",
    }
    assert projected["supported_maturity_level"] == 3
    assert projected["details_redacted"] is True
    assert projected["public_claim_allowed"] is False
    assert projected["profit_claim_allowed"] is False
    assert projected["live_execution_authority"] is False
    assert projected["level_5_attained"] is False
    assert "Level 3" in projected["claim_boundary"]
    assert public_booth_contains_forbidden_value(projected) is False
    assert public_booth_projection(projected) == projected


def test_public_contract_module_is_syntax_valid_and_fixed_schema() -> None:
    source = (CODE / "booth_public_contract.py").read_text(encoding="utf-8")
    ast.parse(source)
    projected = public_booth_projection({})
    assert projected["schema"] == "lumencore.public_booth_contract.v2"
    assert projected["supported_maturity_level"] == 3
    assert projected["public_claim_allowed"] is False


EXPECTED_GATEWAY_CLOSURE = {
    "application_context_resolver.py",
    "autonomous_agent_manifest.py",
    "booth_public_contract.py",
    "execution/__init__.py",
    "execution/order_safety_gate.py",
    "forecast_api.py",
    "grant_application_factory.py",
    "grant_hunter_v2.py",
    "grant_submission_kit.py",
    "grants_api.py",
    "linkedin_oauth.py",
    "linkedin_router.py",
    "luma_experience_gateway.py",
    "luma_experience_gateway_legacy.py",
    "master_universe_benchmark.py",
    "master_universe_benchmark_v2.py",
    "meta_router.py",
    "operator_api_access.py",
    "opportunities_api.py",
    "universe_v2_fetchers.py",
}


def _repair_script() -> str:
    return (
        ROOT / "code" / "ops" / "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh"
    ).read_text(encoding="utf-8")


def _declared_gateway_closure(script: str) -> set[str]:
    match = re.search(
        r"^BUNDLE_FILES=\(\n(?P<body>.*?)^\)\n",
        script,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None
    return set(re.findall(r'^\s+"([^"]+)"$', match.group("body"), re.MULTILINE))


def test_deployment_repairs_the_exact_gateway_dependency_closure() -> None:
    script = _repair_script()

    assert "Inspect-only by default" in script
    assert "--apply" in script
    assert "--print-files" in script
    assert "--bundle-sha" in script
    assert "LUMENCORE_HUMAN_UNLOCK_FILE" in script
    assert "LUMA_HUMAN_UNLOCK_TOKEN" not in script
    assert '[[ "$HUMAN_UNLOCK_FILE" =~ ^/tmp/lumencore-gateway-repair-' in script
    assert '[[ "$(stat -c \'%U:%a\' "$HUMAN_UNLOCK_FILE")" == "opc:600" ]]' in script
    assert "${#human_unlock_token} -lt 32" in script
    assert "unset human_unlock_token" in script
    for marker in (
        '[[ "$TARGET_ROOT" == "/opt/lumencore/code"',
        '&& "$STACK_ROOT" == "/opt/lumencore"',
        '&& "$PYTHON_BIN" == "/opt/lumencore/.venv/bin/python"',
        '&& "$SERVICE" == "luma-gateway"',
        '&& "$LOCK_FILE" == "/opt/lumencore/run/luma_experience_gateway.lock"',
        '&& "$LOCAL_HEALTH_URL" == "http://127.0.0.1:8787/health"',
        '&& "$PUBLIC_HEALTH_URL" == "https://lumen-core.ai/health"',
        '&& "$LOCAL_STATUS_URL" == "http://127.0.0.1:8787/api/public/status"',
        '&& "$PUBLIC_STATUS_URL" == "https://lumen-core.ai/api/public/status"',
    ):
        assert marker in script
    assert _declared_gateway_closure(script) == EXPECTED_GATEWAY_CLOSURE
    assert "LUMENCORE_EXPECTED_GATEWAY_BUNDLE_SHA256" in script
    assert "source closure does not match the approved bundle SHA-256" in script
    assert '[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]]' in script
    assert "PYTHONDONTWRITEBYTECODE=1" in script
    assert 'PYTHONPATH="$STAGE_DIR:$TARGET_ROOT"' in script
    assert "blocked_live_order" in script
    assert "luma-gateway" in script
    assert 'systemctl stop "$SERVICE"' in script
    assert 'systemctl start "$SERVICE"' in script
    assert "Rolling back the complete gateway dependency closure" in script
    assert "/opt/lumencore/code" in script
    assert "singleton lock owner is still alive; refusing removal" in script
    assert "Removed verified dead-PID gateway singleton lock" in script
    assert "POST_APPLY_SOURCE_SHA256" in script
    assert "POST_APPLY_TARGET_SHA256" in script
    assert "POST_APPLY_HASH_PARITY=" in script
    assert "post-apply source/target SHA-256 mismatch" in script
    assert "GATEWAY_DEPENDENCY_CLOSURE_REPAIR_OK" in script
    assert "rm -rf -- \"$TARGET_ROOT\"" not in script
    assert '[[ "$STAGE_DIR" =~ ^/tmp/lumencore-gateway-stage\\.' in script
    assert '[[ "$BACKUP_DIR" =~ ^/tmp/lumencore-gateway-rollback\\.' in script
    assert "systemctl restart" not in script


def test_declared_gateway_closure_covers_recursive_local_imports() -> None:
    declared = _declared_gateway_closure(_repair_script())
    local_modules: dict[str, str] = {}
    for path in CODE.rglob("*.py"):
        relative = path.relative_to(CODE).as_posix()
        if path.name == "__init__.py":
            module = ".".join(path.relative_to(CODE).parent.parts)
        else:
            module = ".".join(path.relative_to(CODE).with_suffix("").parts)
        local_modules[module] = relative

    pending = ["luma_experience_gateway.py"]
    visited: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        visited.add(relative)
        tree = ast.parse((CODE / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported = [node.module]
            for module in imported:
                candidate = local_modules.get(module)
                if candidate and candidate not in visited:
                    pending.append(candidate)

    assert visited <= declared


def test_gateway_service_restart_policy_is_bounded() -> None:
    deploy = (ROOT / "code" / "deploy" / "deploy_vps.sh").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"cat > \"\$GATEWAY_SERVICE\" <<EOF\n(?P<body>.*?)\nEOF",
        deploy,
        flags=re.DOTALL,
    )
    assert match is not None
    service = match.group("body")
    assert "Restart=on-failure" in service
    assert "Restart=always" not in service
    assert "StartLimitIntervalSec=300" in service
    assert "StartLimitBurst=10" in service


def test_health_probe_classifies_static_and_dynamic_surfaces() -> None:
    health = (ROOT / ".github" / "workflows" / "health-probe.yml").read_text(
        encoding="utf-8"
    )
    static_function = re.search(
        r"check_static_endpoint\(\) \{(?P<body>.*?)\n\s+\}\n\n\s+check_json_endpoint",
        health,
        flags=re.DOTALL,
    )
    assert static_function is not None
    static_body = static_function.group("body")
    assert '--output "$body"' in static_body
    assert "--output /dev/null" not in static_body
    assert '--max-filesize "$STATIC_MAX_BYTES"' in static_body
    assert '"${content_type,,}" == text/html*' in static_body
    assert 'grep -Fq -- "$marker" "$body"' in static_body
    assert "contract_ok:$contract_ok" in static_body
    assert "http_ok:$http_ok" in static_body
    assert health.count("check_static_endpoint ") == 13
    for marker in (
        "proof-to-pilot-home-v1",
        "bounded-validation-offer-v1",
        "external-replication-docket-v1",
        "proof-to-pilot-evidence-v1",
        "<title>ProofLock Console</title>",
        "legacy-public-route-hold-v1",
    ):
        assert marker in health
    for retired_path in (
        "mission_control.html",
        "quant_lab.html",
        "kraken_execution_dashboard.html",
        "grants.html",
        "forecast.html",
        "anomalies.html",
        "explain.html",
        "lab.html",
    ):
        assert f"https://lumen-core.ai/{retired_path}" in health
    assert "agent_approval_hub.html" not in health
    assert "https://lumen-core.ai/api/public/status" in health
    assert "https://lumen-core.ai/health" in health
    assert "https://lumen-core.ai/api/snapshot" not in health
    assert "static_surface_state" in health
    assert "dynamic_gateway_state" in health
    assert "contract_ok" in health
    assert "luma-experience-gateway" in health
    assert "operator_api_v1" in health


def test_health_probe_repository_writer_is_path_and_contract_bounded() -> None:
    health = (ROOT / ".github" / "workflows" / "health-probe.yml").read_text(
        encoding="utf-8"
    )

    assert "allowed_path()" in health
    assert "data/site_health.json|data/uptime_badge.json" in health
    assert "out-of-scope path" in health
    assert "git diff --name-only -z" in health
    assert "git ls-files --others --exclude-standard -z" in health
    assert "sort -zu" in health
    assert "git diff --check -- data/site_health.json data/uptime_badge.json" in health
    assert "git diff --cached --name-only -z" in health
    assert "git diff-tree --no-commit-id --name-only -r -z HEAD" in health
    assert "rebased health snapshot contains an out-of-scope path" in health
    assert 'git ls-remote origin "refs/heads/${GITHUB_REF_NAME}"' in health
    assert "remote health-snapshot receipt does not match local HEAD" in health
    assert "Health snapshot publication receipt" in health
    assert "(.endpoints | keys | sort)" in health
    assert '(.url | type == "string" and startswith("https://lumen-core.ai/"))' in health
    assert '(.ok | type == "boolean")' in health
    assert ".healthy_count == ([.endpoints[] | select(.ok == true)] | length)" in health
    assert ".cacheSeconds == 3600" in health


def test_health_probe_static_contract_fails_closed() -> None:
    if not Path("/bin/bash").is_file():
        return

    health = (ROOT / ".github" / "workflows" / "health-probe.yml").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"check_static_endpoint\(\) \{(?P<body>.*?)\n\s+\}\n\n\s+check_json_endpoint",
        health,
        flags=re.DOTALL,
    )
    assert match is not None
    function_source = "check_static_endpoint() {" + match.group("body") + "\n}"
    harness = (
        """
set -euo pipefail
CURL_TIMEOUT_SECONDS=10
STATIC_MAX_BYTES=1048576
curl() {
  local output=""
  while (( $# )); do
    if [[ "$1" == "--output" ]]; then
      output=$2
      shift 2
    else
      shift
    fi
  done
  [[ -n "$output" ]]
  printf '%s' "$FAKE_BODY" > "$output"
  printf '200\\t%s' "$FAKE_CONTENT_TYPE"
}
"""
        + function_source
        + "\ncheck_static_endpoint fixture https://example.invalid/ home\n"
    )

    cases = (
        ("<meta content='proof-to-pilot-home-v1'>", "text/html; charset=utf-8", True),
        ("<html>wrong release</html>", "text/html; charset=utf-8", False),
        ("proof-to-pilot-home-v1", "text/plain", False),
    )
    for body, content_type, expected_contract in cases:
        completed = subprocess.run(
            ["/bin/bash", "-c", harness],
            check=True,
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "FAKE_BODY": body,
                "FAKE_CONTENT_TYPE": content_type,
            },
        )
        row = json.loads(completed.stdout)["value"]
        assert row["http_ok"] is True
        assert row["reachable"] is True
        assert row["contract_ok"] is expected_contract
        assert row["ok"] is expected_contract


def test_gateway_recovery_workflow_requires_exact_main_commit_and_gate() -> None:
    workflow = (
        ROOT / ".github" / "workflows" / "repair-gateway-dependency-closure.yml"
    ).read_text(encoding="utf-8")
    assert "REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE" in workflow
    assert '[[ "$APPROVAL" == "REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE" ]]' in workflow
    assert '[[ "$RELEASE_COMMIT" == "$WORKFLOW_COMMIT" ]]' in workflow
    assert '[[ "$(git rev-parse origin/main)" == "$RELEASE_COMMIT" ]]' in workflow
    assert "VPS_KNOWN_HOSTS" in workflow
    assert "StrictHostKeyChecking=yes" in workflow
    assert "secrets.LUMA_HUMAN_UNLOCK_TOKEN" in workflow
    assert "Repository secret LUMA_HUMAN_UNLOCK_TOKEN is missing" in workflow
    assert "no VPS change was attempted" in workflow
    assert "LUMENCORE_HUMAN_UNLOCK_FILE='$REMOTE_STAGE/human-unlock'" in workflow
    assert 'LUMA_HUMAN_UNLOCK_TOKEN="$(cat' not in workflow
    assert "LUMENCORE_EXPECTED_GATEWAY_BUNDLE_SHA256" in workflow
    assert "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh" in workflow
    assert "--apply" in workflow
    assert "Remove remote repair staging" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in workflow
    assert "shimataro/ssh-key-action@87a8f067114a8ce263df83e9ed5c849953548bc3 # v2.8.1" in workflow
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1" in workflow

    workflow = (
        ROOT / ".github" / "workflows" / "gateway-public-contract-ci.yml"
    ).read_text(
        encoding="utf-8"
    )
    assert "Gateway Public Contract Gate" in workflow
    assert "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh" in workflow
    assert "WRONG_HASH_FAIL_CLOSED_OK" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0" in workflow
