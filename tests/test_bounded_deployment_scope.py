from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "classify_bounded_deployment_scope.py"
SPEC = importlib.util.spec_from_file_location("classify_bounded_deployment_scope", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_gateway_only_change_does_not_select_site_or_evidence() -> None:
    payload = MODULE.classify_deployment_scope(
        mode="push",
        changed_paths=[
            "code/booth_public_contract.py",
            "code/ops/REPAIR_GATEWAY_PUBLIC_CONTRACT_ON_VPS.sh",
            ".github/workflows/deploy.yml",
            "tests/test_booth_public_contract_runtime.py",
        ],
    )

    assert payload["gateway_changed"] is True
    assert payload["site_changed"] is False
    assert payload["evidence_changed"] is False
    assert payload["mutation_requested"] is True
    assert payload["scope_summary"] == "gateway"
    assert payload["control_paths"] == [".github/workflows/deploy.yml"]
    assert payload["ignored_paths"] == ["tests/test_booth_public_contract_runtime.py"]


def test_evidence_only_change_selects_only_evidence() -> None:
    payload = MODULE.classify_deployment_scope(
        mode="push",
        changed_paths=[
            "code/ops/repair_evidence_route.py",
            "code/ops/REPAIR_EVIDENCE_ROUTE_ON_VPS.sh",
        ],
    )

    assert payload["evidence_changed"] is True
    assert payload["site_changed"] is False
    assert payload["gateway_changed"] is False
    assert payload["scope_summary"] == "evidence"


def test_site_patterns_select_site_without_runtime_mutations() -> None:
    for path in (
        "dashboard/proof_to_pilot.html",
        "dashboard/js/app.js",
        "dashboard/assets/app.css",
        "dashboard/master_dashboard.json",
        "data/site_health.json",
    ):
        payload = MODULE.classify_deployment_scope(mode="push", changed_paths=[path])
        assert payload["site_changed"] is True
        assert payload["gateway_changed"] is False
        assert payload["evidence_changed"] is False
        assert payload["scope_summary"] == "site"

    for path in (
        "assets/equity_card.svg",
        "dashboard_analytics.html",
        "dashboard/data/generated.json",
        "dashboard/dashboard_analytics.py",
    ):
        payload = MODULE.classify_deployment_scope(mode="push", changed_paths=[path])
        assert payload["mutation_requested"] is False
        assert payload["ignored_paths"] == [path]


def test_control_and_unrelated_changes_are_inspect_only() -> None:
    payload = MODULE.classify_deployment_scope(
        mode="push",
        changed_paths=[
            ".github/workflows/deploy.yml",
            "code/ops/classify_bounded_deployment_scope.py",
            "config/order_submission_path_policy.json",
        ],
    )

    assert payload["mutation_requested"] is False
    assert payload["scope_summary"] == "inspect_only"
    assert payload["control_paths"] == [
        ".github/workflows/deploy.yml",
        "code/ops/classify_bounded_deployment_scope.py",
    ]
    assert payload["ignored_paths"] == ["config/order_submission_path_policy.json"]


def test_manual_dispatch_is_inspect_only_unless_scopes_are_explicit() -> None:
    inspect_only = MODULE.classify_deployment_scope(mode="manual")
    selected = MODULE.classify_deployment_scope(
        mode="manual",
        manual_scopes=["gateway", "evidence", "gateway"],
    )

    assert inspect_only["mutation_requested"] is False
    assert inspect_only["scope_summary"] == "inspect_only"
    assert selected["site_changed"] is False
    assert selected["gateway_changed"] is True
    assert selected["evidence_changed"] is True
    assert selected["scope_summary"] == "gateway,evidence"


def test_classifier_rejects_escaping_or_absolute_paths() -> None:
    for path in ("../deploy.yml", "/etc/nginx/nginx.conf", r"C:\private\file"):
        try:
            MODULE.classify_deployment_scope(mode="push", changed_paths=[path])
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe path was accepted: {path}")


def test_cli_writes_machine_readable_receipt_and_github_outputs() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        changed = root / "changed.txt"
        receipt = root / "scope.json"
        github_output = root / "github-output.txt"
        changed.write_text(
            "code/booth_public_contract.py\ndashboard/js/app.js\n",
            encoding="utf-8",
        )

        result = MODULE.main(
            [
                "--mode",
                "push",
                "--changed-path-file",
                str(changed),
                "--output",
                str(receipt),
                "--github-output",
                str(github_output),
            ]
        )
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        outputs = github_output.read_text(encoding="utf-8")

        assert result == 0
        assert payload["schema"] == "lumencore.bounded_deployment_scope.v1"
        assert payload["scope_summary"] == "site,gateway"
        assert len(payload["classification_sha256"]) == 64
        assert "site_changed=true" in outputs
        assert "gateway_changed=true" in outputs
        assert "evidence_changed=false" in outputs
        assert "mutation_requested=true" in outputs


def test_every_vps_mutation_step_has_the_matching_scope_guard() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )

    def step_block(name: str) -> str:
        marker = f"      - name: {name}\n"
        start = workflow.index(marker)
        end = workflow.find("\n      - name:", start + len(marker))
        return workflow[start:] if end < 0 else workflow[start:end]

    expected_guards = {
        "Ensure remote transfer dependencies": "mutation_requested",
        "Verify VPS disk capacity": "mutation_requested",
        "Prepare site content directories": "site_changed",
        "Prepare gateway code directory": "gateway_changed",
        "Prepare writable repair staging directory": "evidence_changed",
        "Prepare writable gateway dependency staging directory": "gateway_changed",
        "Sync dashboard assets": "site_changed",
        "Sync data snapshots": "site_changed",
        "Upload bounded repair tools": "evidence_changed",
        "Upload bounded gateway dependency repair": "gateway_changed",
        "Apply bounded gateway dependency repair": "gateway_changed",
        "Apply bounded evidence route repair": "evidence_changed",
    }
    for name, output in expected_guards.items():
        block = step_block(name)
        assert f"if: steps.scope.outputs.{output} == 'true'" in block

    assert "--delete" not in step_block("Apply bounded gateway dependency repair")
    assert "--delete" not in step_block("Apply bounded evidence route repair")
    assert "- 'dashboard/**/*.js'" in workflow
    assert "- 'dashboard/**/*.css'" in workflow
    assert "- 'dashboard/*.json'" in workflow
    assert "- 'assets/**'" not in workflow
    assert "\n      - '*.html'\n" not in workflow


def test_deployment_workflow_captures_deletions_and_verifies_ssh_hosts() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )

    assert "--diff-filter=ACDMRT" in workflow
    assert "StrictHostKeyChecking=no" not in workflow
    assert "StrictHostKeyChecking=yes" in workflow
    assert "BatchMode=yes" in workflow
    assert "ConnectTimeout=15" in workflow
