from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "code" / "ops" / "BUILD_PUBLIC_SITE_DEPLOYMENT_TRANSACTION_RECEIPT.py"
SPEC = importlib.util.spec_from_file_location("public_site_transaction", BUILDER_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

COMMIT = "a" * 40
RUN_ID = 123456789
RUN_ATTEMPT = 2


def canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
        newline="\n",
    )
    return path


def manifest_payload() -> dict[str, object]:
    rows = []
    for index, (repo_path, name) in enumerate(
        zip(builder.RELEASE_PATHS, builder.RELEASE_ARCHIVE_NAMES, strict=True)
    ):
        rows.append(
            {
                "archive_name": name,
                "bytes": index + 1,
                "git_blob_oid": f"{index + 1:040x}",
                "install_mode": "0644",
                "repo_path": repo_path,
                "sha256": hashlib.sha256(name.encode("ascii")).hexdigest(),
            }
        )
    return {
        "archive_sha256": "c" * 64,
        "file_count": len(rows),
        "files": rows,
        "schema": builder.MANIFEST_SCHEMA,
        "source_commit": COMMIT,
        "target_directory": builder.TARGET,
    }


def component_paths(tmp_path: Path) -> dict[str, Path]:
    manifest = manifest_payload()
    manifest_path = write_json(tmp_path / "manifest.json", manifest)
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    authority: dict[str, object] = {
        "authority_scope": builder.AUTHORITY_SCOPE,
        "created_at_utc": "2026-08-31T12:00:00Z",
        "deployment_approval": builder.DEPLOYMENT_APPROVAL,
        "directory_state_sha256": "1" * 64,
        "post_deploy_sha256": "2" * 64,
        "pre_deploy_sha256": "d" * 64,
        "python_version": "3.11.9",
        "release_manifest_sha256": manifest_sha,
        "repository": builder.REPOSITORY,
        "rollback_capability_sha256": "3" * 64,
        "rollback_capture_id": f"20260831T120000Z-{COMMIT[:12]}",
        "run_attempt": RUN_ATTEMPT,
        "run_id": RUN_ID,
        "schema": builder.AUTHORITY_SCHEMA,
        "source_commit": COMMIT,
        "target_directory": builder.TARGET,
        "workflow": builder.WORKFLOW,
    }
    authority["receipt_sha256"] = canonical_hash(authority)
    return {
        "manifest": manifest_path,
        "package": write_json(tmp_path / "package.json", manifest),
        "apply": tmp_path / "apply.txt",
        "authority": write_json(tmp_path / "authority.json", authority),
        "live": tmp_path / "live.json",
        "compensation": tmp_path / "compensation.json",
    }


def write_apply(
    path: Path, authority_path: Path, *, duplicate_authority: bool = False
) -> Path:
    authority_hash = json.loads(authority_path.read_text(encoding="ascii"))[
        "receipt_sha256"
    ]
    lines = [
        f"PUBLIC_SITE_SOURCE_COMMIT={COMMIT}",
        f"PUBLIC_SITE_RUN_ID={RUN_ID}",
        f"PUBLIC_SITE_RUN_ATTEMPT={RUN_ATTEMPT}",
        f"PUBLIC_SITE_ROLLBACK_DIR=/opt/lumencore/rollbacks/public-site/20260831T120000Z-{COMMIT[:12]}",
        f"PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256={authority_hash}",
    ]
    if duplicate_authority:
        lines.append(f"PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256={authority_hash}")
    lines.append("PUBLIC_SITE_DEPLOYMENT_OK")
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    return path


def authority_hash(paths: dict[str, Path]) -> str:
    return json.loads(paths["authority"].read_text(encoding="ascii"))["receipt_sha256"]


def live_payload(manifest: dict[str, object], *, verified: bool) -> dict[str, object]:
    rows = []
    for index, manifest_row in enumerate(manifest["files"]):
        match = verified or index > 0
        actual = manifest_row["sha256"] if match else "f" * 64
        rows.append(
            {
                "actual_sha256": actual,
                "archive_name": manifest_row["archive_name"],
                "bytes": manifest_row["bytes"],
                "content_type": "text/html" if index == 0 else "text/plain",
                "content_type_allowed": True,
                "expected_sha256": manifest_row["sha256"],
                "http_status": 200,
                "status": "MATCH" if match else "MISMATCH",
                "url": builder._expected_live_url(manifest_row["archive_name"], COMMIT),
            }
        )
    matched = sum(row["status"] == "MATCH" for row in rows)
    return {
        "base_url": "https://lumen-core.ai",
        "checked_at_utc": "2026-08-31T12:01:00Z",
        "expected_file_count": len(rows),
        "matched_file_count": matched,
        "release_verified": verified,
        "results": rows,
        "schema": builder.LIVE_SCHEMA,
        "source_commit": COMMIT,
    }


def compensation_payload(
    *, manifest_sha: str, live_sha: str | None, authority_hash: str
) -> dict[str, object]:
    payload: dict[str, object] = {
        "authority_receipt_sha256": authority_hash,
        "claim_boundary": "ALLOWLISTED_LOCAL_BYTES_UID_GID_MODE_ONLY",
        "completed_at_utc": "2026-08-31T12:02:00Z",
        "live_gate_receipt_sha256": live_sha,
        "release_manifest_sha256": manifest_sha,
        "repository": builder.REPOSITORY,
        "restored_file_count": builder.EXPECTED_FILE_COUNT,
        "restored_pre_deploy_sha256": "d" * 64,
        "rollback_verified": True,
        "run_attempt": RUN_ATTEMPT,
        "run_id": RUN_ID,
        "schema": builder.COMPENSATION_SCHEMA,
        "source_commit": COMMIT,
        "trigger": "LIVE_GATE_REJECTED" if live_sha else "LIVE_GATE_ERROR_OR_MISSING",
        "verified_directory_count": builder.EXPECTED_DIRECTORY_COUNT,
        "workflow": builder.WORKFLOW,
    }
    payload["receipt_sha256"] = canonical_hash(payload)
    return payload


def build(
    paths: dict[str, Path],
    *,
    apply_outcome: str,
    live_outcome: str,
    compensation_outcome: str,
    apply: bool,
    live: bool,
    compensation: bool,
):
    return builder.build_receipt(
        source_commit=COMMIT,
        run_id=RUN_ID,
        run_attempt=RUN_ATTEMPT,
        manifest_path=paths["manifest"],
        package_receipt_path=paths["package"],
        apply_receipt_path=paths["apply"] if apply else None,
        authority_receipt_path=paths["authority"] if apply else None,
        live_gate_path=paths["live"] if live else None,
        compensation_path=paths["compensation"] if compensation else None,
        apply_outcome=apply_outcome,
        live_outcome=live_outcome,
        compensation_outcome=compensation_outcome,
    )


def test_verified_candidate_is_the_only_green_transaction(tmp_path):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(paths["apply"], paths["authority"])
    write_json(paths["live"], live_payload(manifest, verified=True))
    receipt = build(
        paths,
        apply_outcome="success",
        live_outcome="success",
        compensation_outcome="skipped",
        apply=True,
        live=True,
        compensation=False,
    )
    assert receipt["final_state"] == "CANDIDATE_VERIFIED"
    assert receipt["candidate_live_verified"] is True
    assert receipt["compensation_required"] is False
    assert receipt["compensation_verified"] is False
    assert receipt["workflow_should_succeed"] is True
    assert receipt["receipt_sha256"] == canonical_hash(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )


def test_rejected_candidate_with_verified_restore_remains_red(tmp_path):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(paths["apply"], paths["authority"])
    write_json(paths["live"], live_payload(manifest, verified=False))
    live_sha = hashlib.sha256(paths["live"].read_bytes()).hexdigest()
    manifest_sha = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    write_json(
        paths["compensation"],
        compensation_payload(
            manifest_sha=manifest_sha,
            live_sha=live_sha,
            authority_hash=authority_hash(paths),
        ),
    )
    receipt = build(
        paths,
        apply_outcome="success",
        live_outcome="failure",
        compensation_outcome="success",
        apply=True,
        live=True,
        compensation=True,
    )
    assert receipt["final_state"] == "PRIOR_STATE_RESTORED"
    assert receipt["candidate_live_verified"] is False
    assert receipt["compensation_required"] is True
    assert receipt["compensation_verified"] is True
    assert receipt["workflow_should_succeed"] is False
    assert "incident closure" in " ".join(receipt["claim_boundaries"]).lower()


def test_failed_compensation_is_indeterminate_and_red(tmp_path):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(paths["apply"], paths["authority"])
    write_json(paths["live"], live_payload(manifest, verified=False))
    receipt = build(
        paths,
        apply_outcome="success",
        live_outcome="failure",
        compensation_outcome="failure",
        apply=True,
        live=True,
        compensation=False,
    )
    assert receipt["final_state"] == "INDETERMINATE_FAIL_CLOSED"
    assert receipt["compensation_required"] is True
    assert receipt["compensation_verified"] is False
    assert receipt["workflow_should_succeed"] is False


def test_apply_failure_skips_downstream_and_is_indeterminate(tmp_path):
    paths = component_paths(tmp_path)
    receipt = build(
        paths,
        apply_outcome="failure",
        live_outcome="skipped",
        compensation_outcome="skipped",
        apply=False,
        live=False,
        compensation=False,
    )
    assert receipt["final_state"] == "INDETERMINATE_FAIL_CLOSED"
    assert receipt["workflow_should_succeed"] is False


def test_missing_live_receipt_can_bind_verified_same_attempt_restore(tmp_path):
    paths = component_paths(tmp_path)
    write_apply(paths["apply"], paths["authority"])
    manifest_sha = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    write_json(
        paths["compensation"],
        compensation_payload(
            manifest_sha=manifest_sha,
            live_sha=None,
            authority_hash=authority_hash(paths),
        ),
    )
    receipt = build(
        paths,
        apply_outcome="success",
        live_outcome="failure",
        compensation_outcome="success",
        apply=True,
        live=False,
        compensation=True,
    )
    assert receipt["final_state"] == "PRIOR_STATE_RESTORED"
    assert receipt["live_gate_receipt_sha256"] is None
    assert receipt["workflow_should_succeed"] is False


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("duplicate_apply_key", "exactly one PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256"),
        ("wrong_run", "run ID mismatch"),
        ("unknown_compensation_field", "fields or schema"),
        ("altered_compensation_hash", "self-hash mismatch"),
        ("package_manifest_drift", "does not equal"),
    ],
)
def test_cross_component_tampering_fails_closed(tmp_path, mutation, match):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(
        paths["apply"],
        paths["authority"],
        duplicate_authority=mutation == "duplicate_apply_key",
    )
    write_json(paths["live"], live_payload(manifest, verified=False))
    live_sha = hashlib.sha256(paths["live"].read_bytes()).hexdigest()
    manifest_sha = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    compensation = compensation_payload(
        manifest_sha=manifest_sha,
        live_sha=live_sha,
        authority_hash=authority_hash(paths),
    )
    if mutation == "wrong_run":
        compensation["run_id"] = RUN_ID + 1
        compensation["receipt_sha256"] = canonical_hash(
            {key: value for key, value in compensation.items() if key != "receipt_sha256"}
        )
    elif mutation == "unknown_compensation_field":
        compensation["unexpected"] = True
    elif mutation == "altered_compensation_hash":
        compensation["receipt_sha256"] = "e" * 64
    elif mutation == "package_manifest_drift":
        package = json.loads(paths["package"].read_text(encoding="ascii"))
        package["target_directory"] = "/tmp/not-production"
        write_json(paths["package"], package)
    write_json(paths["compensation"], compensation)
    with pytest.raises(builder.TransactionReceiptError, match=match):
        build(
            paths,
            apply_outcome="success",
            live_outcome="failure",
            compensation_outcome="success",
            apply=True,
            live=True,
            compensation=True,
        )


def test_compensation_cannot_run_after_verified_live_gate(tmp_path):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(paths["apply"], paths["authority"])
    write_json(paths["live"], live_payload(manifest, verified=True))
    with pytest.raises(builder.TransactionReceiptError, match="invalid predecessor"):
        build(
            paths,
            apply_outcome="success",
            live_outcome="success",
            compensation_outcome="success",
            apply=True,
            live=True,
            compensation=False,
        )


def test_duplicate_json_key_is_rejected(tmp_path):
    paths = component_paths(tmp_path)
    paths["package"].write_text(
        '{"schema":"first","schema":"second"}\n', encoding="ascii"
    )
    with pytest.raises(builder.TransactionReceiptError, match="duplicate JSON key"):
        build(
            paths,
            apply_outcome="failure",
            live_outcome="skipped",
            compensation_outcome="skipped",
            apply=False,
            live=False,
            compensation=False,
        )


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("reorder", "order or manifest binding"),
        ("unknown", "observed row fields"),
        ("contradict_status", "status contradicts"),
        ("wrong_aggregate", "did not match every file"),
    ],
)
def test_malformed_live_result_rows_are_rejected(tmp_path, mutation, match):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(paths["apply"], paths["authority"])
    live = live_payload(manifest, verified=True)
    if mutation == "reorder":
        live["results"][0], live["results"][1] = live["results"][1], live["results"][0]
    elif mutation == "unknown":
        live["results"][0]["unexpected"] = True
    elif mutation == "contradict_status":
        live["results"][0]["status"] = "MISMATCH"
        live["matched_file_count"] -= 1
        live["release_verified"] = False
    else:
        live["matched_file_count"] -= 1
    write_json(paths["live"], live)
    with pytest.raises(builder.TransactionReceiptError, match=match):
        build(
            paths,
            apply_outcome="success",
            live_outcome="success" if live["release_verified"] else "failure",
            compensation_outcome="skipped" if live["release_verified"] else "failure",
            apply=True,
            live=True,
            compensation=False,
        )


@pytest.mark.parametrize("mutation", ["substitute", "reorder"])
def test_canonical_manifest_identity_and_order_are_required(tmp_path, mutation):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    if mutation == "substitute":
        manifest["files"][-1]["archive_name"] = "assets/substitute.txt"
        manifest["files"][-1]["repo_path"] = "dashboard/assets/substitute.txt"
    else:
        manifest["files"][0], manifest["files"][1] = (
            manifest["files"][1],
            manifest["files"][0],
        )
    write_json(paths["manifest"], manifest)
    write_json(paths["package"], manifest)
    with pytest.raises(builder.TransactionReceiptError, match="allowlist or order"):
        build(
            paths,
            apply_outcome="failure",
            live_outcome="skipped",
            compensation_outcome="skipped",
            apply=False,
            live=False,
            compensation=False,
        )


def test_compensation_predeploy_digest_must_match_authority(tmp_path):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(paths["apply"], paths["authority"])
    write_json(paths["live"], live_payload(manifest, verified=False))
    compensation = compensation_payload(
        manifest_sha=hashlib.sha256(paths["manifest"].read_bytes()).hexdigest(),
        live_sha=hashlib.sha256(paths["live"].read_bytes()).hexdigest(),
        authority_hash=authority_hash(paths),
    )
    compensation["restored_pre_deploy_sha256"] = "e" * 64
    compensation["receipt_sha256"] = canonical_hash(
        {key: value for key, value in compensation.items() if key != "receipt_sha256"}
    )
    write_json(paths["compensation"], compensation)
    with pytest.raises(builder.TransactionReceiptError, match="does not match the rollback authority"):
        build(
            paths,
            apply_outcome="success",
            live_outcome="failure",
            compensation_outcome="success",
            apply=True,
            live=True,
            compensation=True,
        )


def test_component_bound_final_verifier_accepts_only_exact_green_receipt(tmp_path):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_apply(paths["apply"], paths["authority"])
    write_json(paths["live"], live_payload(manifest, verified=True))
    receipt = build(
        paths,
        apply_outcome="success",
        live_outcome="success",
        compensation_outcome="skipped",
        apply=True,
        live=True,
        compensation=False,
    )
    receipt_path = write_json(tmp_path / "transaction.json", receipt)
    loaded = builder._load_json(receipt_path)
    assert builder.verify_receipt(
        loaded,
        source_commit=COMMIT,
        run_id=RUN_ID,
        run_attempt=RUN_ATTEMPT,
        manifest_path=paths["manifest"],
        package_receipt_path=paths["package"],
        apply_receipt_path=paths["apply"],
        authority_receipt_path=paths["authority"],
        live_gate_path=paths["live"],
    ) == receipt

    forged = dict(receipt)
    forged["unexpected"] = True
    forged["receipt_sha256"] = canonical_hash(
        {key: value for key, value in forged.items() if key != "receipt_sha256"}
    )
    with pytest.raises(builder.TransactionReceiptError, match="fields or schema"):
        builder.verify_receipt(
            forged,
            source_commit=COMMIT,
            run_id=RUN_ID,
            run_attempt=RUN_ATTEMPT,
            manifest_path=paths["manifest"],
            package_receipt_path=paths["package"],
            apply_receipt_path=paths["apply"],
            authority_receipt_path=paths["authority"],
            live_gate_path=paths["live"],
        )

    paths["live"].write_text("{}\n", encoding="ascii")
    with pytest.raises(builder.TransactionReceiptError):
        builder.verify_receipt(
            receipt,
            source_commit=COMMIT,
            run_id=RUN_ID,
            run_attempt=RUN_ATTEMPT,
            manifest_path=paths["manifest"],
            package_receipt_path=paths["package"],
            apply_receipt_path=paths["apply"],
            authority_receipt_path=paths["authority"],
            live_gate_path=paths["live"],
        )


def test_invalid_direct_outcome_is_rejected(tmp_path):
    paths = component_paths(tmp_path)
    with pytest.raises(builder.TransactionReceiptError, match="apply outcome is invalid"):
        build(
            paths,
            apply_outcome="cancelled",
            live_outcome="skipped",
            compensation_outcome="skipped",
            apply=False,
            live=False,
            compensation=False,
        )


def test_rejected_live_classifier_accepts_only_strict_authoritative_receipt(tmp_path):
    paths = component_paths(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="ascii"))
    write_json(paths["live"], live_payload(manifest, verified=False))
    assert builder.validate_rejected_live_receipt(
        manifest_path=paths["manifest"],
        live_gate_path=paths["live"],
        source_commit=COMMIT,
    )["release_verified"] is False
    paths["live"].write_text(
        '{"schema":"first","schema":"second"}\n', encoding="ascii"
    )
    with pytest.raises(builder.TransactionReceiptError, match="duplicate JSON key"):
        builder.validate_rejected_live_receipt(
            manifest_path=paths["manifest"],
            live_gate_path=paths["live"],
            source_commit=COMMIT,
        )
