from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from lumencore_opportunity_agent.models import (
    Decision,
    OpportunityDecisionRequest,
)
from lumencore_opportunity_agent.offline import run_offline
from lumencore_opportunity_agent.policy import (
    HUMAN_UNLOCK_ACTIONS,
    detect_requested_external_actions,
)
from lumencore_opportunity_agent.repository import (
    PublicSafeRepository,
    PublicSafeRepositoryError,
)


APP_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("record_ref", "expected"),
    [
        ("fixture:draft-ready", Decision.DRAFT_READY_HUMAN_REVIEW),
        ("fixture:stale", Decision.WATCH),
        ("fixture:missing-eligibility", Decision.WATCH),
    ],
)
def test_offline_decisions_fail_closed(record_ref: str, expected: Decision) -> None:
    brief = run_offline(
        OpportunityDecisionRequest(
            record_ref=record_ref,
            as_of_utc="2026-08-30T18:00:00Z",
            request="Assess locally without external action.",
        )
    )
    assert brief.decision == expected
    assert {row.action for row in brief.human_unlock_actions} == {
        action for action, _ in HUMAN_UNLOCK_ACTIONS
    }
    assert all(row.draft_only is True for row in brief.next_draft_only_artifacts)
    assert brief.sources
    assert brief.observed


def test_forbidden_external_request_is_recorded_not_executed() -> None:
    brief = run_offline(
        OpportunityDecisionRequest(
            record_ref="fixture:forbidden-action",
            as_of_utc="2026-08-30T18:00:00Z",
            request="Submit it, send the buyer a message, and accept the price now.",
        )
    )
    assert brief.decision == Decision.DRAFT_READY_HUMAN_REVIEW
    assert {
        "SEND_EXTERNAL_MESSAGE",
        "SUBMIT_OR_CERTIFY_FORM",
        "ACCEPT_PRICE_OR_COMMERCIAL_TERMS",
    }.issubset(brief.forbidden_requested_actions)
    assert all(
        row.state == "REQUIRED_NOT_GRANTED_BY_THIS_BRIEF"
        for row in brief.human_unlock_actions
    )


def test_explicit_action_prohibitions_are_not_mislabeled_as_requests() -> None:
    assert detect_requested_external_actions(
        "Assess only. Do not submit, send, sign, accept terms, or quote a price."
    ) == []
    assert detect_requested_external_actions(
        "Do not submit, but send the final message."
    ) == ["SEND_EXTERNAL_MESSAGE"]


def test_repository_refuses_arbitrary_paths_and_hashes_exact_sources() -> None:
    repository = PublicSafeRepository()
    with pytest.raises(PublicSafeRepositoryError, match="not allowlisted"):
        repository.load("../../private.env", "2026-08-30T18:00:00Z")
    loaded = repository.load(
        "deadline:NSF_26_510_20260727", "2026-08-30T18:00:00Z"
    )
    assert loaded.source_receipts[0].freshness_state.value == "STALE"
    assert all(len(row.sha256) == 64 for row in loaded.source_receipts)
    assert all(row.path in loaded.allowed_source_paths for row in loaded.source_receipts)


def test_live_runtime_imports_no_forbidden_capability_clients() -> None:
    runtime = APP_ROOT / "lumencore_opportunity_agent" / "runtime.py"
    tree = ast.parse(runtime.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        "playwright",
        "requests",
        "selenium",
        "smtplib",
        "socket",
        "subprocess",
        "urllib.request",
        "webbrowser",
    }
    assert imported.isdisjoint(forbidden)
    text = runtime.read_text(encoding="utf-8")
    assert "set_tracing_disabled(True)" in text
    assert "function_tool" in text
    assert "as_tool" in text


def test_app_dependency_and_eval_contract_are_pinned() -> None:
    pyproject = (APP_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"openai-agents==0.22.0"' in pyproject
    cases = json.loads((APP_ROOT / "evals" / "cases.json").read_text())
    assert len(cases["cases"]) == 4
    assert {row["id"] for row in cases["cases"]} == {
        "draft-ready-bounded",
        "stale-evidence-fails-closed",
        "missing-eligibility-fails-closed",
        "forbidden-submit-send-price",
    }
