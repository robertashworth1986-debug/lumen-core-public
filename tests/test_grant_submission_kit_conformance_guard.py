from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import grant_submission_kit as kit
from submission_conformance_guard import (
    PASS_STATUS,
    REQUIRED_CONTROLS,
    REQUIRED_CRITERIA,
    canonical_sha256,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt(repo_root: Path, path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(repo_root).as_posix(),
        "present": True,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _write_conformance_gate(
    repo_root: Path,
    *,
    lane_id: str = "test_technical_lane",
    as_of: datetime | None = None,
    argument_pass: bool = True,
    red_team_pass: bool | None = None,
) -> Path:
    if red_team_pass is None:
        red_team_pass = argument_pass
    evidence_dir = repo_root / "gate_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    for name in (
        "candidate.md",
        "official_source.txt",
        "criterion_evidence.md",
        "independent_red_team.json",
        "registry.json",
        "traction.json",
        "near_deadline.json",
        "public_leads.json",
        "falcon_gap_map.md",
        "builder.py",
    ):
        path = evidence_dir / name
        path.write_text(f"source-bound fixture: {name}\n", encoding="utf-8")
        artifacts[name] = path

    source_receipt = {
        **_receipt(repo_root, artifacts["criterion_evidence.md"]),
        "anchor": "criterion fixture",
    }
    criteria = [
        {
            "criterion_id": criterion_id,
            "state": "PASS" if argument_pass else "FAIL",
            "finding": "Fixture finding.",
            "missing_evidence": [] if argument_pass else ["required fixture evidence"],
            "source_refs": [dict(source_receipt)],
            "source_refs_all_present": True,
            "passed": argument_pass,
        }
        for criterion_id in REQUIRED_CRITERIA
    ]
    red_team = {
        **_receipt(repo_root, artifacts["independent_red_team.json"]),
        "reviewer_relation": "SEPARATE_REVIEWER",
        "verdict": "PASS" if red_team_pass else "FAIL",
        "passes": red_team_pass,
    }
    lane = {
        "lane_id": lane_id,
        "name": "Test technical submission",
        "disposition": "ACTIVE_SUBMISSION_CANDIDATE",
        "current_state": "Test fixture",
        "technical_argument_required": True,
        "submission_candidate_active": True,
        "status": PASS_STATUS if argument_pass else "BLOCKED_CRITERION_FAILURE",
        "argument_conformance_pass": argument_pass,
        "candidate_artifact": _receipt(repo_root, artifacts["candidate.md"]),
        "official_source": _receipt(repo_root, artifacts["official_source.txt"]),
        "postmortem": None,
        "criterion_count": len(REQUIRED_CRITERIA),
        "criterion_pass_count": len(REQUIRED_CRITERIA) if argument_pass else 0,
        "criterion_partial_count": 0,
        "criterion_fail_count": 0 if argument_pass else len(REQUIRED_CRITERIA),
        "criterion_unassessed_count": 0,
        "criteria": criteria,
        "independent_red_team_receipt": red_team,
        "next_action": "Human action remains required.",
        "claim_boundary": "Fixture only.",
        "final_submission_allowed_without_human": False,
        "external_send_allowed_without_human": False,
    }
    lane["lane_gate_sha256"] = canonical_sha256(lane)

    payload = {
        "schema": "lumencore.submission_conformance_gate.v1",
        "as_of_utc": (as_of or datetime.now(timezone.utc)).isoformat(),
        "registry_as_of_utc": (as_of or datetime.now(timezone.utc)).isoformat(),
        "status": (
            "SUBMISSION_CONFORMANCE_PASS_HUMAN_ACTION_REQUIRED"
            if argument_pass
            else "SUBMISSION_CONFORMANCE_BLOCKED"
        ),
        "summary": {
            "all_current_lanes_covered": True,
            "final_submission_allowed_without_human": False,
            "external_send_allowed_without_human": False,
        },
        "required_criteria": list(REQUIRED_CRITERIA),
        "controls": dict(REQUIRED_CONTROLS),
        "lanes": [lane],
        "source_evidence": {
            "registry": _receipt(repo_root, artifacts["registry.json"]),
            "traction": _receipt(repo_root, artifacts["traction.json"]),
            "near_deadline": _receipt(repo_root, artifacts["near_deadline.json"]),
            "public_leads": _receipt(repo_root, artifacts["public_leads.json"]),
            "falcon_gap_map": _receipt(repo_root, artifacts["falcon_gap_map.md"]),
            "builder": _receipt(repo_root, artifacts["builder.py"]),
        },
    }
    payload["gate_sha256"] = canonical_sha256(payload)
    gate_path = repo_root / "out" / "ops" / "submission_conformance_gate_latest.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return gate_path


def _write_run(
    run_dir: Path,
    *,
    lane_id: str = "test_technical_lane",
    approval_state: str = "approved",
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    app = {
        "agency": "Test Agency",
        "program": "Test Technical Program",
        "deadline_typical": "2099-12-31",
        "current_state": "open",
        "submission_conformance_lane_id": lane_id,
        "applicant": {
            "sam_gov_status": "active",
            "sam_gov_verified_utc": "2026-07-25T00:00:00Z",
            "sam_gov_expiration_date": "2099-12-31",
        },
        "submission_readiness": {
            "grants_gov_account_verified": True,
            "aor_authority_verified": True,
        },
        "eligibility": {"eligible": True},
        "budget": {"ceiling_usd": 100000, "total": 100000},
    }
    files = {
        "application.json": json.dumps(app),
        "application.md": "complete\n",
        "technical_volume.md": "complete\n",
        "commercialization_plan.md": "complete\n",
        "cover_letter.md": "complete\n",
        "HEILMEIER_CATECHISM.md": "complete\n",
        "BENCHMARK_BREADTH_ADDENDUM.md": "complete\n",
        "budget.json": "{}",
        "eligibility_report.json": "{}",
        "evidence_manifest.json": "{}",
        "manifest.sha256.json": "{}",
        "approval_state.json": json.dumps({"state": approval_state}),
    }
    for name, content in files.items():
        (run_dir / name).write_text(content, encoding="utf-8")


def _build(
    tmp_path: Path,
    monkeypatch,
    *,
    gate_path: Path,
    lane_id: str = "test_technical_lane",
    approval_state: str = "approved",
) -> dict[str, object]:
    run_dir = tmp_path / "run"
    _write_run(run_dir, lane_id=lane_id, approval_state=approval_state)
    monkeypatch.setattr(kit, "ROOT", tmp_path)
    monkeypatch.setattr(kit, "CONFORMANCE_GATE_PATH", gate_path)
    return kit.build_preflight(
        "test_technical_program",
        run_dir,
        {
            "deadline_typical": "2099-12-31",
            "current_state": "open",
            "source_verified_utc": "2026-07-25T00:00:00Z",
            "ceiling_usd": 100000,
        },
    )


def test_human_approval_and_complete_artifacts_cannot_unlock_blocked_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gate_path = _write_conformance_gate(tmp_path, argument_pass=False)
    payload = _build(tmp_path, monkeypatch, gate_path=gate_path)

    assert payload["approval_state"] == "approved"
    assert payload["package_complete"] is True
    assert payload["content_unlock"] is False
    assert payload["action_unlock"] is False
    assert payload["ready"] is False
    assert any(
        "has no argument_conformance_pass" in blocker
        for blocker in payload["content_blockers"]
    )
    assert "TECHNICAL_DRAFT_PASS" not in json.dumps(payload)


def test_absent_unmapped_and_stale_conformance_all_fail_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    absent = _build(
        tmp_path / "absent",
        monkeypatch,
        gate_path=tmp_path / "absent" / "missing.json",
    )
    assert absent["content_unlock"] is False
    assert any("gate is absent" in item for item in absent["content_blockers"])

    unmapped_root = tmp_path / "unmapped"
    unmapped_gate = _write_conformance_gate(unmapped_root)
    unmapped = _build(
        unmapped_root,
        monkeypatch,
        gate_path=unmapped_gate,
        lane_id="different_lane",
    )
    assert unmapped["content_unlock"] is False
    assert any("unmapped" in item for item in unmapped["content_blockers"])

    stale_root = tmp_path / "stale"
    stale_gate = _write_conformance_gate(
        stale_root,
        as_of=datetime.now(timezone.utc) - timedelta(hours=25),
    )
    stale = _build(stale_root, monkeypatch, gate_path=stale_gate)
    assert stale["content_unlock"] is False
    assert any("is stale" in item for item in stale["content_blockers"])


def test_content_unlock_does_not_bypass_action_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gate_path = _write_conformance_gate(tmp_path)
    pending = _build(
        tmp_path,
        monkeypatch,
        gate_path=gate_path,
        approval_state="draft",
    )

    assert pending["submission_conformance"]["argument_conformance_pass"] is True
    assert pending["content_unlock"] is True
    assert pending["action_unlock"] is False
    assert pending["ready"] is False
    assert pending["external_action_allowed_without_human"] is False
    assert any("approval_state" in item for item in pending["action_blockers"])


def test_all_criteria_and_human_approval_still_require_independent_red_team(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gate_path = _write_conformance_gate(
        tmp_path,
        argument_pass=True,
        red_team_pass=False,
    )
    payload = _build(tmp_path, monkeypatch, gate_path=gate_path)

    assert payload["submission_conformance"]["all_required_criteria_pass"] is True
    assert payload["submission_conformance"]["independent_red_team_pass"] is False
    assert payload["content_unlock"] is False
    assert payload["action_unlock"] is False
    assert payload["ready"] is False


def test_ready_requires_lane_pass_and_action_checks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gate_path = _write_conformance_gate(tmp_path)
    payload = _build(tmp_path, monkeypatch, gate_path=gate_path)

    assert payload["content_unlock"] is True
    assert payload["action_unlock"] is True
    assert payload["ready"] is True
    assert payload["external_action_allowed_without_human"] is False
