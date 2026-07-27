from __future__ import annotations

import ast
import copy
import json
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
    assert projected["indexing"] == raw["indexing"]
    assert projected["founder_profile"] == {
        "founder": "Synthetic Founder",
        "private_identifiers_embedded": False,
    }
    assert projected["live_execution"]["heartbeat"]["status"] == "running"
    assert projected["live_execution"]["heartbeat"]["reason"] == ""
    assert projected["live_execution"]["heartbeat"]["symbol"] == ""
    assert projected["live_execution"]["recent_trade_count"] == 1
    assert projected["live_execution"]["recent_trades"] == []
    assert projected["live_execution"]["latest_trade"]["txid"] == ""
    assert projected["live_execution"]["latest_trade"]["size_usd"] is None
    assert projected["autonomous_grant_win"]["master_valuation_proxy_usd"] is None
    assert projected["premium_mirror"]["destination_root"] == ""
    assert projected["supported_maturity_level"] == 3
    assert projected["details_redacted"] is True
    assert projected["public_claim_allowed"] is False
    assert projected["profit_claim_allowed"] is False
    assert projected["live_execution_authority"] is False
    assert projected["level_5_attained"] is False
    assert "Level 3" in projected["claim_boundary"]
    assert public_booth_contains_forbidden_value(projected) is False
    assert public_booth_projection(projected) == projected


def test_gateway_projects_both_prebuilt_and_fallback_booth_payloads() -> None:
    source = (CODE / "luma_experience_gateway_legacy.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "master_booth_brief"
    )
    projection_calls = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "public_booth_projection"
    ]

    assert len(projection_calls) == 2
    assert {ast.unparse(call.args[0]) for call in projection_calls} == {
        "payload",
        "_build_booth_explainer_brief_payload()",
    }


def test_deployment_repairs_only_the_public_contract_dependency() -> None:
    script = (
        ROOT / "code" / "ops" / "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh"
    ).read_text(encoding="utf-8")

    assert "Inspect-only by default" in script
    assert "--apply" in script
    assert "booth_public_contract.py" in script
    assert "LUMENCORE_EXPECTED_PUBLIC_CONTRACT_SHA256" in script
    assert "PYTHONDONTWRITEBYTECODE=1" in script
    assert "luma-gateway" in script
    assert "systemctl restart \"$SERVICE\"" in script
    assert "Rolling back gateway public-contract dependency" in script
    assert "/opt/lumencore/code/booth_public_contract.py" in script
    assert "luma_experience_gateway.py" not in script
    assert "luma_experience_gateway_legacy.py" not in script

    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )
    assert "Apply bounded gateway dependency repair" in workflow
    assert "Classify bounded deployment scope" in workflow
    assert "deploy_site:" in workflow
    assert "deploy_gateway:" in workflow
    assert "deploy_evidence:" in workflow
    assert "steps.scope.outputs.site_changed == 'true'" in workflow
    assert "steps.scope.outputs.gateway_changed == 'true'" in workflow
    assert "steps.scope.outputs.evidence_changed == 'true'" in workflow
    assert "https://lumen-core.ai/health?deploy=${GITHUB_SHA}" in workflow
    assert '[[ "$HEALTH" == "200" ]]' in workflow
    assert 'python3 -m json.tool "$tmp_health"' in workflow
