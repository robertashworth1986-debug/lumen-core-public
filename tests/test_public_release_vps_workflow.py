from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def test_public_release_workflow_is_manual_and_plan_bound() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "release_plan_sha256:" in text
    assert "confirm_publication:" in text
    assert "PUBLISH_PUBLIC_REVIEWER_RELEASE" in text
    assert not re.search(r"(?m)^\s{2}push:\s*$", text)
    assert "environment: production" in text


def test_public_release_workflow_requires_humanunlock_before_ssh() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    gate_at = text.index("LUMA_HUMAN_UNLOCK_TOKEN")
    ssh_at = text.index("Install SSH key")
    sync_at = text.index("Sync staged reviewer release to VPS")

    assert gate_at < ssh_at < sync_at
    assert "secrets.LUMA_HUMAN_UNLOCK_TOKEN" in text
    assert "BUILD_PUBLIC_RELEASE_STAGE_BUNDLE.py --stage" in text
    assert ".deploy_stage/public_reviewer_release_" in text


def test_public_release_workflow_never_broad_deletes_dashboard() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "rsync -avz --delete" not in text
    assert "rsync -avz" not in text
    assert "rsync -rlvz --no-times --omit-dir-times" in text
    assert "dashboard/ \\" not in text
    assert '"$STAGE_ROOT/dashboard/"' in text
    assert "/opt/lumencore/dashboard/" in text


def test_public_release_workflow_runs_complete_post_publish_verification() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'head_status="$(' in text
    assert '"$head_status" != "200"' in text
    assert "observed_mime" in text
    assert '"$observed_mime" != "$expected_mime"' in text
    assert "observed_sha" in text
    assert "release_verify=" in text
    assert "repeat_sha" in text
