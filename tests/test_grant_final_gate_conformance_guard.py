from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "code"))

MODULE_PATH = REPO_ROOT / "code" / "ops" / "RUN_GRANT_FINAL_GATE.py"
SPEC = importlib.util.spec_from_file_location("run_grant_final_gate_conformance_test", MODULE_PATH)
assert SPEC and SPEC.loader
final_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(final_gate)

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


def _write_final_gate_workspace(
    repo_root: Path,
    *,
    opp_num: str = "TEST-001",
    lane_id: str = "test_technical_lane",
    approval_state: str = "approved",
) -> tuple[Path, Path]:
    app_packets = repo_root / "out" / "grants" / "application_packets"
    approved_root = repo_root / "out" / "grants" / "_approved"
    app_packets.mkdir(parents=True, exist_ok=True)
    run_dir = approved_root / "live_test_001" / "20260725T120000Z"
    run_dir.mkdir(parents=True, exist_ok=True)

    packet = {
        "opportunity": {
            "opp_num": opp_num,
            "close_date": "12/31/2099",
        },
        "organization": {
            "uei": "TESTUEI",
            "ein": "TESTEIN",
            "sam_registered": True,
        },
    }
    (app_packets / f"GRANT-TICKET_{opp_num}.json").write_text(
        json.dumps(packet),
        encoding="utf-8",
    )

    application = {
        "opp_num": opp_num,
        "submission_conformance_lane_id": lane_id,
    }
    files = {
        "application.json": json.dumps(application),
        "application.md": "complete\n",
        "technical_volume.md": "complete\n",
        "commercialization_plan.md": "complete\n",
        "cover_letter.md": "complete\n",
        "budget.json": "{}",
        "eligibility_report.json": "{}",
        "evidence_manifest.json": "{}",
        "approval_state.json": json.dumps({"state": approval_state}),
        "submission_packet.json": json.dumps(
            {
                "approval_state": approval_state,
                "submission_conformance": {"lane_id": lane_id},
            }
        ),
        "SUBMIT_HOWTO.md": "human review and portal action required\n",
    }
    for name, content in files.items():
        (run_dir / name).write_text(content, encoding="utf-8")
    manifest = {
        "files": {
            name: {"sha256": _sha256(run_dir / name)}
            for name in files
        }
    }
    (run_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return app_packets, approved_root


def _build(
    repo_root: Path,
    monkeypatch,
    *,
    gate_path: Path,
    lane_id: str = "test_technical_lane",
    approval_state: str = "approved",
) -> dict[str, object]:
    app_packets, approved_root = _write_final_gate_workspace(
        repo_root,
        lane_id=lane_id,
        approval_state=approval_state,
    )
    monkeypatch.setattr(final_gate, "ROOT", repo_root)
    monkeypatch.setattr(final_gate, "OUT_OPS", repo_root / "out" / "ops")
    monkeypatch.setattr(final_gate, "APP_PACKETS", app_packets)
    monkeypatch.setattr(final_gate, "APPROVED_ROOT", approved_root)
    monkeypatch.setattr(final_gate, "CONFORMANCE_GATE_PATH", gate_path)
    return final_gate.build_gate("TEST-001")


def test_approved_files_and_hashes_cannot_bypass_absent_conformance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _build(
        tmp_path,
        monkeypatch,
        gate_path=tmp_path / "missing_conformance.json",
    )

    assert payload["approval_state"]["state"] == "approved"
    assert payload["manifest_verification"]["status"] == "PASS"
    assert payload["content_unlock"] is False
    assert payload["action_unlock"] is False
    assert payload["decision"] == "BLOCKED"
    assert any("gate is absent" in item for item in payload["content_blockers"])


def test_unmapped_stale_and_blocked_lane_conformance_fail_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    unmapped_root = tmp_path / "unmapped"
    unmapped_gate = _write_conformance_gate(unmapped_root)
    unmapped = _build(
        unmapped_root,
        monkeypatch,
        gate_path=unmapped_gate,
        lane_id="different_lane",
    )
    assert unmapped["decision"] == "BLOCKED"
    assert any("unmapped" in item for item in unmapped["content_blockers"])

    stale_root = tmp_path / "stale"
    stale_gate = _write_conformance_gate(
        stale_root,
        as_of=datetime.now(timezone.utc) - timedelta(hours=25),
    )
    stale = _build(stale_root, monkeypatch, gate_path=stale_gate)
    assert stale["decision"] == "BLOCKED"
    assert any("is stale" in item for item in stale["content_blockers"])

    blocked_root = tmp_path / "blocked"
    blocked_gate = _write_conformance_gate(blocked_root, argument_pass=False)
    blocked = _build(blocked_root, monkeypatch, gate_path=blocked_gate)
    assert blocked["decision"] == "BLOCKED"
    assert blocked["approval_state"]["state"] == "approved"
    assert any(
        "has no argument_conformance_pass" in item
        for item in blocked["content_blockers"]
    )
    assert "TECHNICAL_DRAFT_PASS" not in json.dumps(blocked)


def test_content_pass_does_not_grant_action_unlock(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gate_path = _write_conformance_gate(tmp_path)
    payload = _build(
        tmp_path,
        monkeypatch,
        gate_path=gate_path,
        approval_state="draft",
    )

    assert payload["content_unlock"] is True
    assert payload["submission_conformance"]["independent_red_team_pass"] is True
    assert payload["action_unlock"] is False
    assert payload["decision"] == "BLOCKED"
    assert payload["external_action_allowed_without_human"] is False
    assert any("approval_state must be approved" in item for item in payload["action_blockers"])


def test_approved_decision_requires_independent_red_team_receipt(
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
    assert payload["decision"] == "BLOCKED"


def test_approved_decision_requires_current_lane_specific_argument_pass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gate_path = _write_conformance_gate(tmp_path)
    payload = _build(tmp_path, monkeypatch, gate_path=gate_path)

    assert payload["schema"] == "grant_final_gate_v2"
    assert payload["content_unlock"] is True
    assert payload["action_unlock"] is True
    assert payload["decision"] == "APPROVED"
    assert payload["external_action_allowed_without_human"] is False


def test_cli_without_explicit_opportunity_fails_closed_without_writing(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    conformance_path = tmp_path / "submission_conformance_gate_latest.json"
    conformance_path.write_text(
        json.dumps(
            {
                "lanes": [
                    {
                        "lane_id": "nsf_project_pitch",
                        "disposition": "ACTIVE_SUBMISSION_CANDIDATE",
                        "submission_candidate_active": True,
                        "status": "BLOCKED_UNASSESSED_CRITERIA",
                        "candidate_artifact": {
                            "path": "grant_submissions/NSF_Project_Pitch/portal_fields.md"
                        },
                    },
                    {
                        "lane_id": "closed_lane",
                        "disposition": "CLOSED",
                        "submission_candidate_active": False,
                        "status": "CLOSED",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(final_gate, "CONFORMANCE_GATE_PATH", conformance_path)

    def unexpected_call(*_args, **_kwargs):
        raise AssertionError("No gate may be built or written without an explicit target.")

    monkeypatch.setattr(final_gate, "build_gate", unexpected_call)
    monkeypatch.setattr(final_gate, "write_outputs", unexpected_call)

    result = final_gate.main([])
    output = capsys.readouterr().out

    assert result == 1
    assert "BLOCKED_NO_EXPLICIT_OPPORTUNITY" in output
    assert "nsf_project_pitch|BLOCKED_UNASSESSED_CRITERIA" in output
    assert "closed_lane" not in output
    assert "DE-FOA-0003539" not in output
