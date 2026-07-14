from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_scheduled_monitors_are_read_only_and_do_not_push() -> None:
    for name in ["equity-card.yml", "health-probe.yml", "live-metrics-sync.yml"]:
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "contents: read" in text
        assert "contents: write" not in text
        assert "git push" not in text
        assert "actions/upload-artifact@v4" in text


def test_deploy_uses_strict_ssh_host_verification() -> None:
    text = (WORKFLOWS / "deploy.yml").read_text(encoding="utf-8")
    assert "StrictHostKeyChecking=yes" in text
    assert "UserKnownHostsFile=$HOME/.ssh/known_hosts" in text
    assert "StrictHostKeyChecking=no" not in text


def test_reviewer_entrypoint_and_citation_are_present() -> None:
    reviewer = (ROOT / "docs" / "REVIEWER_START_HERE.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "Level 3" in reviewer
    assert "Level 5" in reviewer
    assert "EXTERNAL_EVALUATOR_ACCEPTANCE_HANDOFF_2026-07-14.md" in reviewer
    assert "VERIFY_EXTERNAL_EVALUATOR_ACCEPTANCE.py --expect-template" in reviewer
    assert "Independent Review Roles" in reviewer
    assert "cff-version: 1.2.0" in citation


def test_reviewer_entrypoint_changes_trigger_external_validation_ci() -> None:
    workflow = (WORKFLOWS / "external-validation-docket.yml").read_text(
        encoding="utf-8"
    )
    assert workflow.count('"docs/REVIEWER_START_HERE.md"') == 2
    assert workflow.count('"tests/test_github_workflow_governance.py"') == 2
    assert "tests/test_github_workflow_governance.py" in workflow.split(
        "python -m pytest -q", maxsplit=1
    )[1]
