from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import job_application_factory as factory  # noqa: E402


@pytest.fixture
def profile() -> dict:
    return {
        "company": {
            "email": "candidate@example.com",
            "phone": "555-0100",
            "website": "https://example.com",
            "city": "Nashville",
            "state": "TN",
            "country": "US",
        },
        "pi": {"name": "Example Candidate", "linkedin": "https://linkedin.com/in/example"},
        "identifiers": {
            "uei": "ABCDEF123456",
            "ein": "12-3456789",
            "cage_code": "1AB23",
            "patent_numbers": ["US-1234567-A1"],
            "sam_gov_status": "active",
        },
        "federal_readiness": {"sam_status": "active"},
    }


@pytest.fixture
def role() -> dict:
    return {
        "id": "surge_data_scientist",
        "title": "Data Scientist",
        "employer": "Surge AI",
        "role_url": "https://jobs.example.test/surge/data-scientist",
        "deadline": "2030-08-04T17:00:00",
        "timezone": "America/New_York",
        "hard_requirements": ["Python", "Model evaluation"],
        "channel": "company_careers",
        "priority": "P0",
        "location_mode": "remote_us",
        "fit_keywords": ["Python", "model evaluation"],
        "target_organizations": ["Surge AI"],
        "submission_portal_hints": ["Ashby"],
        "_fit_score": 0.91,
        "_matched_keywords": ["Python", "model evaluation"],
    }


@pytest.fixture
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    jobs_root = tmp_path / "jobs"
    monkeypatch.setattr(factory, "JOBS_ROOT", jobs_root)
    monkeypatch.setattr(factory, "QUEUE_ROOT", jobs_root / "_queue")
    monkeypatch.setattr(factory, "APPROVED_ROOT", jobs_root / "_approved")
    monkeypatch.setattr(factory, "RESUME_PDF_PATH", tmp_path / "unsafe-old-resume.pdf")
    return jobs_root


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_employment_packet_strips_identifiers_and_unsupported_claims(
    isolated_paths: Path, profile: dict, role: dict
) -> None:
    resume = """# Resume
UEI: ABCDEF123456
EIN: 12-3456789
CAGE Code: 1AB23
Patent number: US-1234567-A1
Built institutional-grade systems with investor-ready reporting.
Led a live deployment and claimed external validation.
This is an active role search.
Python and model evaluation are documented here.
"""

    result = factory._build_role_package(role, profile, resume, "20300801T000000Z")

    assert result["built"] is True
    run_dir = Path(result["run_dir"])
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(run_dir.iterdir())
        if path.is_file()
    ).casefold()
    for private_value in ("abcdef123456", "12-3456789", "1ab23", "us-1234567-a1"):
        assert private_value not in combined
    for unsupported in ("institutional-grade", "investor-ready", "live deployment", "external validation"):
        assert unsupported not in combined
    assert "this is an active role search" in combined

    application = _read_json(run_dir / "application.json")
    assert set(application["candidate"]).isdisjoint({"uei", "ein", "cage_code", "patent_numbers"})
    assert "federal_readiness" not in application
    assert not (run_dir / "resume.pdf").exists()


def test_role_metadata_and_truthful_custom_interest_are_preserved(
    isolated_paths: Path, profile: dict, role: dict
) -> None:
    role["role_specific_interest_text"] = (
        "I am interested in this role because it emphasizes careful model evaluation."
    )

    result = factory._build_role_package(role, profile, "Python model evaluation", "20300801T000001Z")
    application = _read_json(Path(result["run_dir"]) / "application.json")

    assert application["employer"] == "Surge AI"
    assert application["role_url"] == "https://jobs.example.test/surge/data-scientist"
    assert application["deadline"] == "2030-08-04T17:00:00"
    assert application["timezone"] == "America/New_York"
    assert application["deadline_utc"] == "2030-08-04T21:00:00+00:00"
    assert application["hard_requirements"] == ["Python", "Model evaluation"]
    assert application["interest_text"] == role["role_specific_interest_text"]


def test_fallback_interest_uses_only_resume_matched_terms(profile: dict, role: dict) -> None:
    interest = factory._role_specific_interest(role, profile, ["Python"])

    assert "Python" in interest
    assert "My resume contains direct references" in interest
    assert "institutional" not in interest.casefold()
    assert "validated" not in interest.casefold()


def test_application_fingerprint_is_deterministic_and_target_specific(
    profile: dict, role: dict
) -> None:
    candidate = factory._candidate_payload(profile)
    reordered = {key: role[key] for key in reversed(list(role))}
    reordered["role_url"] = role["role_url"].upper() + "/"

    first = factory._application_fingerprint(role, candidate)
    second = factory._application_fingerprint(reordered, dict(reversed(list(candidate.items()))))
    changed = copy.deepcopy(role)
    changed["role_url"] = "https://jobs.example.test/surge/another-role"

    assert first == second
    assert first != factory._application_fingerprint(changed, candidate)
    assert len(first) == 64


def test_duplicate_fingerprint_skips_repeat_package_by_default(
    isolated_paths: Path, profile: dict, role: dict
) -> None:
    first = factory._build_role_package(role, profile, "Python model evaluation", "20300801T000002Z")
    second = factory._build_role_package(role, profile, "Python model evaluation", "20300801T000003Z")
    override = factory._build_role_package(
        role,
        profile,
        "Python model evaluation",
        "20300801T000004Z",
        allow_duplicate=True,
    )

    assert first["built"] is True
    assert second["built"] is False
    assert second["reason"] == "duplicate_application_fingerprint"
    assert second["duplicate_of"] == first["run_dir"]
    assert override["built"] is True
    receipt = _read_json(Path(override["run_dir"]) / "receipt.json")
    assert receipt["duplicate_of"] == first["run_dir"]


def test_deadline_ranked_mode_excludes_missing_invalid_and_expired() -> None:
    now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    roles = [
        {"id": "missing", "title": "Missing", "priority": "P0"},
        {
            "id": "naive_missing_timezone",
            "title": "Invalid",
            "priority": "P0",
            "deadline": "2026-08-03T17:00:00",
        },
        {
            "id": "expired",
            "title": "Expired",
            "priority": "P0",
            "deadline": "2026-07-31T17:00:00-05:00",
        },
        {
            "id": "later",
            "title": "Later",
            "priority": "P0",
            "deadline": "2026-08-04T17:00:00",
            "timezone": "America/Chicago",
        },
        {
            "id": "sooner",
            "title": "Sooner",
            "priority": "P0",
            "deadline": "2026-08-02",
            "timezone": "America/New_York",
        },
    ]

    selected, excluded = factory._select_roles(
        roles,
        "",
        min_score=0.0,
        limit=20,
        deadline_ranked=True,
        now=now,
    )

    assert [row["id"] for row in selected] == ["sooner", "later"]
    assert {row["job_id"]: row["deadline_status"] for row in excluded} == {
        "missing": "missing",
        "naive_missing_timezone": "invalid",
        "expired": "expired",
    }


def test_receipt_is_prepared_not_submitted_and_gate_stays_locked_after_approval(
    isolated_paths: Path, profile: dict, role: dict
) -> None:
    built = factory._build_role_package(role, profile, "Python model evaluation", "20300801T000005Z")
    run_dir = Path(built["run_dir"])
    before = _read_json(run_dir / "receipt.json")

    assert before["status"] == "prepared_not_submitted"
    assert before["external_submission"]["status"] == "not_submitted"
    assert before["external_submission"]["confirmation_id"] is None
    assert before["final_submit_gate"] == {
        "required": True,
        "locked": True,
        "instruction": factory.FINAL_SUBMIT_GATE_TEXT,
    }
    assert before["artifact_sha256"]

    approved = factory._approve("surge_data_scientist")
    state = _read_json(run_dir / "approval_state.json")
    after = _read_json(run_dir / "receipt.json")

    assert approved["ok"] is True
    assert state["state"] == "approved"
    assert state["submission_locked"] is True
    assert after["status"] == "approved_not_submitted"
    assert after["external_submission"]["status"] == "not_submitted"
    assert after["external_submission"]["confirmation_id"] is None
    assert after["artifact_sha256"]["approval_state.json"] == factory._sha256(
        run_dir / "approval_state.json"
    )


def test_main_deadline_ranked_mode_returns_error_when_all_deadlines_are_missing(
    isolated_paths: Path,
    profile: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        factory,
        "_load_roles",
        lambda: [{"id": "undated", "title": "Undated Role", "priority": "P0"}],
    )
    monkeypatch.setattr(factory, "load_application_profile", lambda: profile)
    monkeypatch.setattr(factory, "_load_resume_text", lambda: "Python")
    monkeypatch.setattr(factory, "_read_json", lambda path: {})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "job_application_factory.py",
            "--deadline-ranked",
            "--min-score",
            "0",
            "--as-of",
            "2026-08-01T12:00:00Z",
        ],
    )

    assert factory.main() == 2
    assert not any(isolated_paths.glob("undated/*/application.json"))
