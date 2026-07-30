from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_PUBLIC_RELEASE_STAGE_BUNDLE.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "public_release_stage_bundle",
        MODULE_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_plan(tmp_path: Path) -> tuple[Path, Path, Path]:
    module = load_module()
    root = tmp_path / "repo"
    source = root / "output" / "pdf" / "current.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"bounded reviewer artifact")
    plan_path = root / "out" / "ops" / "PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.json"
    plan_path.parent.mkdir(parents=True)
    source_sha = sha256(source)
    plan = {
        "schema": module.PLAN_SCHEMA,
        "mode": "DRY_RUN_ONLY",
        "human_gate": module.HUMAN_GATE,
        "network_actions": {
            action: module.HUMAN_GATE
            for action in ("deploy", "email", "post", "publish", "push")
        },
        "items": [
            {
                "id": "current_pdf",
                "source_path": "output/pdf/current.pdf",
                "source_sha256": source_sha,
                "target_path": "dashboard/evidence/current_ABC123.pdf",
                "mime_type": "application/pdf",
                "planned_action": "PLAN_NEW_LOCAL_STAGE_COPY",
                "copy_performed": False,
                "network_action_performed": False,
                "blockers": [],
                "public_url_verification": {
                    "url": "https://example.test/evidence/current_ABC123.pdf",
                    "expected_sha256": source_sha,
                    "network_request_performed": False,
                    "state": "PENDING_HUMAN_UNLOCK_AND_PUBLICATION",
                },
            }
        ],
        "summary": {
            "item_count": 1,
            "blocked_count": 0,
            "plan_state": "DRY_RUN_READY_HUMAN_UNLOCK_REQUIRED",
            "local_copy_performed": False,
            "network_action_performed": False,
            "public_release_completed": False,
        },
    }
    plan["plan_sha256"] = module.stable_sha256(plan)
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return root, plan_path, source


def test_check_builds_contract_without_copying_any_file(tmp_path: Path) -> None:
    module = load_module()
    root, plan_path, _ = fixture_plan(tmp_path)

    contract = module.build_stage_contract(
        plan_path,
        root=root,
        deploy_stage=root / ".deploy_stage",
    )

    assert contract["stage_state"] == "CHECK_READY_NOT_STAGED"
    assert contract["summary"]["stage_ready"] is True
    assert contract["summary"]["files_staged_locally"] is False
    assert contract["summary"]["public_root_copy_performed"] is False
    assert contract["summary"]["network_action_performed"] is False
    assert contract["authority"]["credentials_required_for_local_stage"] is False
    assert not (root / ".deploy_stage").exists()
    assert not (root / "dashboard").exists()


def test_stage_copies_only_beneath_deploy_stage_and_verifies_hashes(
    tmp_path: Path,
) -> None:
    module = load_module()
    root, plan_path, source = fixture_plan(tmp_path)
    contract = module.build_stage_contract(
        plan_path,
        root=root,
        deploy_stage=root / ".deploy_stage",
    )

    manifest = module.stage_bundle(contract, root=root)
    stage_root = root / manifest["stage_root"]
    staged = stage_root / "dashboard" / "evidence" / "current_ABC123.pdf"

    assert manifest["stage_state"] == "LOCAL_STAGE_READY"
    assert manifest["summary"]["files_staged_locally"] is True
    assert manifest["summary"]["public_root_copy_performed"] is False
    assert manifest["summary"]["network_action_performed"] is False
    assert manifest["authority"]["external_action_authorized_by_stage"] is False
    assert staged.read_bytes() == source.read_bytes()
    assert sha256(staged) == sha256(source)
    assert not (root / "dashboard").exists()
    assert (stage_root / "manifest.json").is_file()


def test_exact_existing_stage_is_a_verified_noop(tmp_path: Path) -> None:
    module = load_module()
    root, plan_path, _ = fixture_plan(tmp_path)
    contract = module.build_stage_contract(
        plan_path,
        root=root,
        deploy_stage=root / ".deploy_stage",
    )

    first = module.stage_bundle(contract, root=root)
    second = module.stage_bundle(contract, root=root)

    assert first == second


def test_plan_hash_tamper_is_rejected(tmp_path: Path) -> None:
    module = load_module()
    root, plan_path, _ = fixture_plan(tmp_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["summary"]["item_count"] = 2
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(module.StageError, match="plan SHA-256"):
        module.build_stage_contract(
            plan_path,
            root=root,
            deploy_stage=root / ".deploy_stage",
        )


def test_source_drift_is_rejected(tmp_path: Path) -> None:
    module = load_module()
    root, plan_path, source = fixture_plan(tmp_path)
    source.write_bytes(b"changed")

    with pytest.raises(module.StageError, match="source drifted"):
        module.build_stage_contract(
            plan_path,
            root=root,
            deploy_stage=root / ".deploy_stage",
        )


def test_current_plan_is_safe_for_local_stage_check() -> None:
    module = load_module()

    contract = module.build_stage_contract(
        module.DEFAULT_PLAN,
        root=ROOT,
        deploy_stage=ROOT / ".deploy_stage",
    )

    assert contract["summary"]["item_count"] == 6
    assert contract["summary"]["stage_ready"] is True
    assert all(
        row["staged_relative_path"].startswith("dashboard/")
        for row in contract["files"]
    )
    assert contract["authority"] == {
        "human_unlock_required_for_vps_or_publication": True,
        "external_action_authorized_by_stage": False,
        "credentials_required_for_local_stage": False,
    }
