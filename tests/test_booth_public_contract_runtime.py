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
        "generated_utc": "2026-01-01T00:00:00+00:00",
        "founder_profile": {
            "founder": "Synthetic Founder",
            "ein": SYNTHETIC_TAX_ID,
            "uspto_non_provisional_application": SYNTHETIC_PATENT_ID,
        },
        "indexing": {
            "files_indexed": 7,
            "roots_present": 2,
            "roots_total": 3,
            "scan_capped": True,
            "private_path": SYNTHETIC_PATH,
        },
        "catalog": {
            "engine_count": 4,
            "assets_source_rows": 9,
            "top_engines": [{"secret": SYNTHETIC_TAX_ID}],
        },
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
    assert projected["schema"] == "lumencore.public_booth_contract.v2"
    assert projected["generated_utc"] == "2026-01-01T00:00:00Z"
    assert projected["brand"] == {"company_system": "LumenCore"}
    assert projected["indexing"] == {
        "files_indexed": 7,
        "roots_present": 2,
        "roots_total": 3,
        "scan_capped": True,
    }
    assert projected["catalog"] == {
        "engine_count": 4,
        "assets_source_rows": 9,
    }
    assert "founder_profile" not in projected
    assert "live_execution" not in projected
    assert "premium_mirror" not in projected
    assert "autonomous_grant_win" not in projected
    assert "artifacts" not in projected
    assert "private_notes" not in projected
    assert projected["supported_maturity_level"] == 3
    assert projected["details_redacted"] is True
    assert projected["public_claim_allowed"] is False
    assert projected["profit_claim_allowed"] is False
    assert projected["live_execution_authority"] is False
    assert projected["level_5_attained"] is False
    assert "Level 3" in projected["claim_boundary"]
    assert public_booth_contains_forbidden_value(projected) is False
    assert public_booth_projection(projected) == projected


def test_public_projection_rejects_unbounded_or_malformed_counts() -> None:
    projected = public_booth_projection(
        {
            "generated_utc": "not-a-timestamp",
            "indexing": {
                "files_indexed": -5,
                "roots_present": float("inf"),
                "roots_total": 10**30,
                "scan_capped": "yes",
            },
            "catalog": {
                "engine_count": "4.9",
                "assets_source_rows": None,
            },
        }
    )
    assert projected["generated_utc"] == ""
    assert projected["indexing"] == {
        "files_indexed": 0,
        "roots_present": 0,
        "roots_total": 1_000_000_000,
        "scan_capped": False,
    }
    assert projected["catalog"] == {
        "engine_count": 4,
        "assets_source_rows": 0,
    }


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


def test_deployment_repairs_the_fixed_contract_and_gateway_runtime() -> None:
    script = (
        ROOT / "code" / "ops" / "REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh"
    ).read_text(encoding="utf-8")

    assert "Inspect-only by default" in script
    assert "--apply" in script
    assert "booth_public_contract.py" in script
    assert "luma_experience_gateway.py" in script
    assert "luma_experience_gateway_legacy.py" in script
    assert "LUMENCORE_EXPECTED_PUBLIC_CONTRACT_SHA256" in script
    assert "LUMENCORE_EXPECTED_GATEWAY_FACADE_SHA256" in script
    assert "LUMENCORE_EXPECTED_GATEWAY_LEGACY_SHA256" in script
    assert "PYTHONDONTWRITEBYTECODE=1" in script
    assert "luma-gateway" in script
    assert "systemctl restart \"$SERVICE\"" in script
    assert "Rolling back gateway facade, legacy provider, and public contract" in script
    assert "/opt/lumencore/code/booth_public_contract.py" in script
    assert "/opt/lumencore/code/luma_experience_gateway.py" in script
    assert "/opt/lumencore/code/luma_experience_gateway_legacy.py" in script
    assert "/api/master/approval-queue" in script
    assert "probe_until_status" in script
    assert "LUMENCORE_GATEWAY_PROBE_ATTEMPTS" in script
    assert "LUMENCORE_GATEWAY_PROBE_DELAY_SECONDS" in script
    assert 'dirname -- "$LEGACY_TARGET"' in script

    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )
    assert "Apply public edge guard" in workflow
    assert "Apply bounded gateway dependency repair" in workflow
    assert "Classify bounded deployment scope" in workflow
    assert "deploy_site:" in workflow
    assert "deploy_gateway:" in workflow
    assert "deploy_evidence:" in workflow
    assert "steps.scope.outputs.site_changed == 'true'" in workflow
    assert "steps.scope.outputs.gateway_changed == 'true'" in workflow
    assert "steps.scope.outputs.evidence_changed == 'true'" in workflow
    assert "DEPLOY_BOUNDED_LUMENCORE_TO_PRODUCTION" in workflow
    assert "https://lumen-core.ai/health?deploy=${GITHUB_SHA}" in workflow
    assert "LUMENCORE_GATEWAY_LEGACY_SOURCE=" in workflow
    assert "LUMENCORE_EXPECTED_GATEWAY_LEGACY_SHA256=" in workflow
    assert '[[ "$HEALTH" == "200" ]]' in workflow
    assert 'health["schema"] == "lumencore.public_gateway_health.v1"' in workflow
    assert 'booth["schema"] == "lumencore.public_booth_contract.v2"' in workflow
