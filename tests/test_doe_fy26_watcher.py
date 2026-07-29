from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "watchers" / "doe_fy26_watcher.py"


def load_module():
    spec = importlib.util.spec_from_file_location("doe_fy26_watcher", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_html(*, portal_link: bool = False, include_topic_4: bool = True) -> str:
    topic_4 = (
        "<p>4. Achieving AI-Driven Autonomous Laboratories</p>"
        if include_topic_4
        else ""
    )
    portal = (
        '<a href="https://amp.connectwerx.org/genesis">Application Management Portal</a>'
        if portal_link
        else "<p>AMP application portal (application link coming soon).</p>"
    )
    return f"""
        <html>
          <head><title>FY26 Phase I - Genesis Mission</title></head>
          <body>
            <h1>FY26 Phase I - Genesis Mission</h1>
            <p>Active Solicitation</p>
            <p>Submission Deadline: September 10, 2026 at 2 PM ET</p>
            <p>1. Scaling the Biotechnology Revolution</p>
            <p>2. AI for Quantum Computing and Networking</p>
            <p>3. Designing Materials with Predictable Functionality</p>
            {topic_4}
            {portal}
          </body>
        </html>
    """


def test_detects_active_genesis_and_fail_closed_portal_state():
    module = load_module()
    state = module.detect_state(
        sample_html(),
        now=datetime(2026, 7, 29, 12, tzinfo=timezone.utc),
    )

    assert state["active_solicitation"] is True
    assert state["deadline_literal"] == "September 10, 2026 at 2 PM ET"
    assert state["deadline_iso"] == "2026-09-10T14:00:00-04:00"
    assert state["topic_4_present"] is True
    assert len(state["topics"]) == 4
    assert state["application_portal_state"] == "COMING_SOON"
    assert state["application_portal_url"] is None
    assert state["urgency"] == "OPEN_NOT_DUE_WITHIN_14_DAYS"
    assert state["parse_complete"] is True
    assert len(state["source_fingerprint_sha256"]) == 64


def test_detects_application_portal_transition_and_alerts_once():
    module = load_module()
    state = module.detect_state(
        sample_html(portal_link=True),
        now=datetime(2026, 8, 15, 12, tzinfo=timezone.utc),
    )
    previous = {
        "schema": module.SCHEMA,
        "status": "ok",
        "parse_complete": True,
        "application_portal_state": "COMING_SOON",
        "deadline_iso": state["deadline_iso"],
        "topics": state["topics"],
        "active_solicitation": True,
    }

    assert state["application_portal_state"] == "LINKED"
    assert state["application_portal_url"] == (
        "https://amp.connectwerx.org/genesis"
    )
    assert module.alert_reasons(state, previous) == [
        "APPLICATION_PORTAL_BECAME_LINKED"
    ]


def test_due_window_and_source_changes_are_alerted():
    module = load_module()
    state = module.detect_state(
        sample_html(),
        now=datetime(2026, 9, 1, 18, tzinfo=timezone.utc),
    )
    previous = {
        "schema": module.SCHEMA,
        "status": "ok",
        "parse_complete": True,
        "application_portal_state": "COMING_SOON",
        "deadline_iso": "2026-09-09T14:00:00-04:00",
        "topics": ["old topic set"],
        "active_solicitation": False,
    }

    assert state["urgency"] == "DUE_WITHIN_14_DAYS"
    assert module.alert_reasons(state, previous) == [
        "DUE_WITHIN_14_DAYS",
        "DEADLINE_CHANGED",
        "TOPIC_TEXT_CHANGED",
        "ACTIVE_STATUS_CHANGED",
    ]


def test_missing_required_topic_fails_closed():
    module = load_module()
    with pytest.raises(module.GenesisParseError, match="Required topic text"):
        module.detect_state(sample_html(include_topic_4=False))


def test_unknown_portal_state_fails_closed():
    module = load_module()
    html = sample_html().replace(
        "<p>AMP application portal (application link coming soon).</p>",
        "<p>Application details will be posted later.</p>",
    )
    with pytest.raises(module.GenesisParseError, match="portal state"):
        module.detect_state(html)
