"""Offline custody checks using the real factory and fictional inputs only."""
from __future__ import annotations

import hashlib
import io
import json
import socket
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


CODE = Path(__file__).resolve().parents[1] / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import grant_application_factory as factory  # noqa: E402
import grant_submission_kit as kit  # noqa: E402
import grants_api as api  # noqa: E402


CORE_FILES = {
    "application.md", "technical_volume.md", "commercialization_plan.md",
    "cover_letter.md", "budget.json", "application.json",
    "eligibility_report.json", "approval_state.json", "evidence_manifest.json",
}
KIT_FILES = {"submission_packet.json", "SUBMIT_HOWTO.md"}
MANIFEST = "manifest.sha256.json"


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _bytes(run: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}


def _assert_native_manifest(run: Path, expected: set[str]) -> None:
    """Independently check on-disk bytes, not just the implementation verifier."""
    entries = list(run.iterdir())
    assert all(p.is_file() and not p.is_symlink() for p in entries)
    assert {p.name for p in entries} == expected | {MANIFEST}
    manifest = json.loads((run / MANIFEST).read_text(encoding="utf-8"))
    assert set(manifest["files"]) == expected
    for name, record in manifest["files"].items():
        content = (run / name).read_bytes()
        assert record["size_bytes"] == len(content)
        assert record["sha256"] == hashlib.sha256(content).hexdigest()
    assert factory.verified_bundle_files(run) == {
        name: (run / name).read_bytes() for name in expected | {MANIFEST}
    }


@pytest.fixture
def fictional_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Only storage locations and the network boundary are patched."""
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("fictional custody checks must never connect to a network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    root = tmp_path / "fictional-local-only"
    data = root / "data"
    out = root / "out"
    grants = out / "grants"
    for module in (factory, api):
        for name, value in {"ROOT": root, "DATA": data, "GRANTS": grants}.items():
            monkeypatch.setattr(module, name, value)
    for name, value in {
        "OUT": out,
        "QUEUE_DIR": grants / "_queue",
        "APPROVED_DIR": grants / "_approved",
        "LIVE_SOURCE_REGISTRY": data / "fictional-no-source-registry.json",
        "DATASET_CATALOG_PATH": out / "fictional-no-dataset-catalog.json",
        "DATA_BREADTH_PROBE_PATH": out / "fictional-no-runtime-probe.json",
        "HUNTER_PROFILE_PATH": data / "fictional-no-hunter-profile.json",
    }.items():
        monkeypatch.setattr(factory, name, value)
    for name, value in {
        "QUEUE": grants / "_queue" / "index.json",
        "CATALOG": data / "grant_catalog.json",
        "PROFILE": data / "company_profile.json",
    }.items():
        monkeypatch.setattr(api, name, value)

    now = datetime.now(timezone.utc)
    utc = now.strftime("%Y%m%dT%H%M%SZ")
    program = {
        "id": "FICTIONAL-CUSTODY-ONLY",
        "agency": "FICTIONAL AGENCY — DOES NOT EXIST",
        "program": "FICTIONAL LOCAL TEST — NO FUNDING OFFERED",
        "topic_area": "Fictional software custody rehearsal",
        "current_state": "open",
        "deadline_typical": "2099-12-31",
        "source_verified_utc": now.isoformat(),
        "source_verification_url": "https://example.invalid/fictional",
        "url": "https://example.invalid/fictional",
        "source_metadata": {"source": "FICTIONAL_LOCAL_FIXTURE"},
        "ceiling_usd": 100_000,
        "duration_months": 6,
        "eligibility": {
            "small_business": True, "us_owned_majority": True,
            "employees_lt": 500, "pi_employed_min_pct": 50,
        },
        "fit_keywords": ["workflow", "evidence"],
        "required_sections": ["summary", "technical", "budget"],
        "page_limits": {},
    }
    profile = {
        "company": {
            "legal_name": "FICTIONAL ORGANIZATION — DOES NOT EXIST",
            "dba": "FICTIONAL TEST ONLY",
            "small_business": True, "us_owned_majority": True, "employees": 2,
            "duns_or_uei": "TO_BE_FILLED_FICTIONAL",
            "ein": "TO_BE_FILLED_FICTIONAL",
            "sam_gov_status": "unverified",
            "sam_gov_verified_utc": None, "sam_gov_expiration_date": None,
            "address_line1": "FICTIONAL ADDRESS", "city": "FICTIONAL",
            "state": "FICTIONAL", "zip": "FICTIONAL", "country": "FICTIONAL",
            "email": "fictional@example.invalid", "phone": "FICTIONAL",
            "website": "https://example.invalid/fictional",
        },
        "pi": {
            "name": "FICTIONAL REVIEWER", "title": "FICTIONAL ROLE",
            "employed_pct": 100, "bio_short": "Fictional local test only.",
        },
        "company_capabilities": ["Fictional workflow and evidence rehearsal"],
        "broader_impacts": ["Fictional test only"],
        "differentiators": ["No performance claim"],
        "ip_status": "Fictional; no rights claim", "team_letters_of_support": [],
        "submission_readiness": {
            "grants_gov_account_verified": False, "aor_authority_verified": False,
        },
    }
    evidence = {
        "run_utc": utc, "evidence_type": "synthetic",
        "notice": "Fictional shape values; no benchmark was executed.",
        "layers": {name: {} for name in (
            "benchmark", "meta_router", "ci_calibration", "anomaly_scanner",
            "regime_shift", "hybrid_stacker", "stacking_blender",
        )},
    }
    evidence["layers"]["benchmark"] = {"n_datasets": 0}
    evidence["layers"]["ci_calibration"] = {"mean_cov80": 0.0, "mean_cov95": 0.0}
    _json(data / "grant_catalog.json", {"programs": [program]})
    _json(data / "company_profile.json", profile)
    eligibility = factory.score_eligibility(program, profile, evidence)
    assert eligibility["eligible"] is True
    run = factory.write_bundle(program, profile, evidence, eligibility, utc)
    return SimpleNamespace(
        root=root, program=program, profile=profile, evidence=evidence,
        eligibility=eligibility, run=run, utc=utc, grant_id=program["id"],
    )


def test_real_draft_approval_kit_export_and_repeat_refusal(fictional_bundle: SimpleNamespace) -> None:
    f = fictional_bundle
    _assert_native_manifest(f.run, CORE_FILES)
    before = kit.build_preflight(f.grant_id, f.run, f.program)
    assert before["ready"] is False
    state = factory.approve(f.grant_id)
    assert state["state"] == "approved"
    _assert_native_manifest(f.run, CORE_FILES)
    snapshot = factory.APPROVED_DIR / f.grant_id / f.run.name
    _assert_native_manifest(snapshot, CORE_FILES)
    snapshot_bytes = _bytes(snapshot)

    after = kit.build_preflight(f.grant_id, f.run, f.program)
    assert after["ready"] is False
    assert after["approval_state"] == "approved"
    assert any("TO_BE_FILLED" in str(blocker) for blocker in after["blockers"])
    kit.write_submission_kit(f.grant_id, f.run, after)
    _assert_native_manifest(f.run, CORE_FILES | KIT_FILES)
    response = api.bundle_zip(f.grant_id)
    with zipfile.ZipFile(io.BytesIO(response.body)) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == CORE_FILES | KIT_FILES | {MANIFEST}
        assert {name: archive.read(name) for name in archive.namelist()} == _bytes(f.run)
    assert _bytes(snapshot) == snapshot_bytes
    current_bytes = _bytes(f.run)
    with pytest.raises(SystemExit):
        factory.approve(f.grant_id)
    assert _bytes(f.run) == current_bytes
    assert _bytes(snapshot) == snapshot_bytes


def test_prepare_twice_seals_current_kit(fictional_bundle: SimpleNamespace) -> None:
    f = fictional_bundle
    for _ in range(2):
        response = api.prepare_submission(f.grant_id)
        assert json.loads(response.body)["ready"] is False
        _assert_native_manifest(f.run, CORE_FILES | KIT_FILES)


def test_approval_never_retains_a_packet_describing_draft_state(
    fictional_bundle: SimpleNamespace,
) -> None:
    f = fictional_bundle
    api.prepare_submission(f.grant_id)
    assert json.loads((f.run / "submission_packet.json").read_text())["approval_state"] == "draft"
    factory.approve(f.grant_id)
    snapshot = factory.APPROVED_DIR / f.grant_id / f.run.name
    # The transition may refresh or remove the obsolete derived kit.
    has_kit = (f.run / "submission_packet.json").exists()
    expected = CORE_FILES | KIT_FILES if has_kit else CORE_FILES
    _assert_native_manifest(f.run, expected)
    _assert_native_manifest(snapshot, expected)
    assert _bytes(f.run) == _bytes(snapshot)
    if has_kit:
        packet = json.loads((f.run / "submission_packet.json").read_text())
        assert packet["approval_state"] == "approved"
        assert not any("approval_state is 'draft'" in str(x) for x in packet["blockers"])


def test_regeneration_same_evidence_creates_latest_unapproved_draft(
    fictional_bundle: SimpleNamespace,
) -> None:
    f = fictional_bundle
    factory.approve(f.grant_id)
    snapshot = factory.APPROVED_DIR / f.grant_id / f.run.name
    previous = _bytes(f.run)
    snapshot_bytes = _bytes(snapshot)
    regenerated = factory.write_bundle(
        f.program, f.profile, f.evidence, f.eligibility, f.utc,
    )
    assert regenerated != f.run
    assert api._latest_grant_run(f.grant_id) == regenerated
    assert json.loads((regenerated / "approval_state.json").read_text())["state"] == "draft"
    _assert_native_manifest(regenerated, CORE_FILES)
    assert _bytes(f.run) == previous
    assert _bytes(snapshot) == snapshot_bytes


def _damage_bundle(run: Path, mutation: str) -> None:
    if mutation in {"application", "budget", "state"}:
        name = {"application": "application.md", "budget": "budget.json", "state": "approval_state.json"}[mutation]
        (run / name).write_bytes((run / name).read_bytes() + b"\nTAMPERED")
    elif mutation == "missing":
        (run / "application.md").unlink()
    elif mutation == "extra":
        (run / "unrecorded.txt").write_text("unexpected bytes")
    elif mutation == "nested":
        (run / "unexpected-directory").mkdir()
    elif mutation == "symlink":
        target = run.parent / "outside-fictional.txt"
        target.write_bytes((run / "application.md").read_bytes())
        (run / "application.md").unlink()
        (run / "application.md").symlink_to(target)
    elif mutation == "manifest_missing":
        (run / MANIFEST).unlink()
    elif mutation == "manifest_corrupt":
        (run / MANIFEST).write_text("{invalid JSON")
    else:
        raise AssertionError(mutation)


@pytest.mark.parametrize("mutation", [
    "application", "budget", "state", "missing", "extra", "nested", "symlink",
    "manifest_missing", "manifest_corrupt",
])
def test_custody_mismatch_refuses_before_transition_or_export(
    fictional_bundle: SimpleNamespace, mutation: str,
) -> None:
    f = fictional_bundle
    _damage_bundle(f.run, mutation)
    before = _bytes(f.run)
    with pytest.raises(factory.BundleIntegrityError):
        factory.verified_bundle_files(f.run)
    for operation in (api.bundle_zip, api.prepare_submission, api.grant_diff):
        with pytest.raises(HTTPException) as exc_info:
            operation(f.grant_id)
        assert exc_info.value.status_code == 409
        assert _bytes(f.run) == before
    with pytest.raises(factory.BundleIntegrityError):
        factory.approve(f.grant_id)
    assert _bytes(f.run) == before
    assert not (factory.APPROVED_DIR / f.grant_id / f.run.name).exists()


@pytest.mark.parametrize("mutation", [
    "hash", "negative_size", "boolean_size", "string_size", "missing_record",
    "self_reference", "path_escape", "program_id", "duplicate_key",
    "nonfinite", "invalid_utf8", "manifest_hardlink",
])
def test_malformed_manifest_records_fail_closed(
    fictional_bundle: SimpleNamespace, mutation: str,
) -> None:
    run = fictional_bundle.run
    manifest_path = run / MANIFEST
    manifest = json.loads(manifest_path.read_text())
    record = manifest["files"]["application.md"]
    if mutation == "hash":
        record["sha256"] = "g" * 64
    elif mutation == "negative_size":
        record["size_bytes"] = -1
    elif mutation == "boolean_size":
        record["size_bytes"] = True
    elif mutation == "string_size":
        record["size_bytes"] = str(record["size_bytes"])
    elif mutation == "missing_record":
        manifest["files"].pop("application.md")
    elif mutation == "self_reference":
        manifest["files"][MANIFEST] = dict(record)
    elif mutation == "path_escape":
        manifest["files"]["../outside"] = manifest["files"].pop("application.md")
    elif mutation == "program_id":
        manifest["program_id"] = "DIFFERENT-FICTIONAL-PROGRAM"
    elif mutation == "duplicate_key":
        raw = manifest_path.read_text()
        raw = raw.replace('"program_id": ', '"program_id": "WRONG", "program_id": ', 1)
        manifest_path.write_text(raw)
    elif mutation == "nonfinite":
        manifest["untrusted_value"] = float("nan")
    elif mutation == "invalid_utf8":
        manifest_path.write_bytes(b"\xff\xfe invalid manifest bytes")
    elif mutation == "manifest_hardlink":
        (run.parent / "outside-manifest-alias.json").hardlink_to(manifest_path)
    if mutation not in {"duplicate_key", "invalid_utf8", "manifest_hardlink"}:
        _json(manifest_path, manifest)
    before = _bytes(run)
    with pytest.raises(factory.BundleIntegrityError):
        factory.verified_bundle_files(run)
    with pytest.raises(HTTPException) as exc_info:
        api.bundle_zip(fictional_bundle.grant_id)
    assert exc_info.value.status_code == 409
    assert _bytes(run) == before


def test_refresh_rejects_concurrent_change_to_unchanged_document(
    fictional_bundle: SimpleNamespace,
) -> None:
    run = fictional_bundle.run
    previous = factory.verified_bundle_files(run)
    old_manifest = (run / MANIFEST).read_bytes()
    state = json.loads(previous["approval_state.json"])
    state["state"] = "approved"
    _json(run / "approval_state.json", state)
    (run / "budget.json").write_bytes(previous["budget.json"] + b" ")
    with pytest.raises(factory.BundleIntegrityError):
        factory.refresh_bundle_manifest(run, previous, {"approval_state.json"})
    assert (run / MANIFEST).read_bytes() == old_manifest


def test_diff_checks_snapshot_bytes(fictional_bundle: SimpleNamespace) -> None:
    f = fictional_bundle
    factory.approve(f.grant_id)
    snapshot = factory.APPROVED_DIR / f.grant_id / f.run.name
    _damage_bundle(snapshot, "application")
    current = _bytes(f.run)
    damaged_snapshot = _bytes(snapshot)
    with pytest.raises(HTTPException) as exc_info:
        api.grant_diff(f.grant_id)
    assert exc_info.value.status_code == 409
    assert _bytes(f.run) == current
    assert _bytes(snapshot) == damaged_snapshot


def test_submission_record_refuses_tamper_without_rewriting_kit_or_state(
    fictional_bundle: SimpleNamespace,
) -> None:
    f = fictional_bundle
    factory.approve(f.grant_id)
    api.prepare_submission(f.grant_id)
    snapshot = factory.APPROVED_DIR / f.grant_id / f.run.name
    snapshot_bytes = _bytes(snapshot)
    _damage_bundle(f.run, "application")
    current = _bytes(f.run)
    with pytest.raises(HTTPException) as exc_info:
        api.mark_submitted(f.grant_id, api.SubmittedRequest(
            external_tracking_id="FICTIONAL-TEST-NO-SUBMISSION",
        ))
    assert exc_info.value.status_code == 409
    assert _bytes(f.run) == current
    assert _bytes(snapshot) == snapshot_bytes


def test_refresh_refuses_a_changed_previous_seal(fictional_bundle: SimpleNamespace) -> None:
    run = fictional_bundle.run
    previous = factory.verified_bundle_files(run)
    changed_manifest = previous[MANIFEST] + b"\n"
    (run / MANIFEST).write_bytes(changed_manifest)
    with pytest.raises(factory.BundleIntegrityError):
        factory.refresh_bundle_manifest(run, previous, KIT_FILES)
    assert (run / MANIFEST).read_bytes() == changed_manifest


@pytest.mark.parametrize("aliased_directory", ["run", "program"])
def test_directory_alias_cannot_export_outside_bytes(
    fictional_bundle: SimpleNamespace, aliased_directory: str,
) -> None:
    f = fictional_bundle
    original = f.run if aliased_directory == "run" else f.run.parent
    outside_parent = f.root / "outside-bundle-tree"
    outside_parent.mkdir()
    outside = outside_parent / original.name
    original.rename(outside)
    original.symlink_to(outside, target_is_directory=True)
    with pytest.raises(factory.BundleIntegrityError):
        factory.verified_bundle_files(f.run)
    with pytest.raises(HTTPException) as exc_info:
        api.bundle_zip(f.grant_id)
    assert exc_info.value.status_code == 409


def test_regeneration_sorts_after_a_future_dated_existing_run(
    fictional_bundle: SimpleNamespace,
) -> None:
    f = fictional_bundle
    future_utc = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%dT%H%M%SZ")
    future_run = factory.write_bundle(
        f.program, f.profile, f.evidence, f.eligibility, future_utc,
    )
    future_bytes = _bytes(future_run)
    fresh = factory.write_bundle(f.program, f.profile, f.evidence, f.eligibility, f.utc)
    assert fresh.name > future_run.name
    assert api._latest_grant_run(f.grant_id) == fresh
    assert _bytes(future_run) == future_bytes
    _assert_native_manifest(fresh, CORE_FILES)


@pytest.mark.parametrize("state_name", ["approved", "submitted", "unknown"])
def test_approval_requires_draft_even_without_an_existing_snapshot(
    fictional_bundle: SimpleNamespace, state_name: str,
) -> None:
    f = fictional_bundle
    previous = factory.verified_bundle_files(f.run)
    state = json.loads(previous["approval_state.json"])
    state["state"] = state_name
    _json(f.run / "approval_state.json", state)
    factory.refresh_bundle_manifest(f.run, previous, {"approval_state.json"})
    before = _bytes(f.run)
    with pytest.raises(SystemExit):
        factory.approve(f.grant_id)
    assert _bytes(f.run) == before
    assert not (factory.APPROVED_DIR / f.grant_id / f.run.name).exists()


def test_fictional_submission_record_updates_current_seal_and_kit_only(
    fictional_bundle: SimpleNamespace,
) -> None:
    """Rehearse a local state record; no portal or agency submission takes place."""
    f = fictional_bundle
    f.profile["company"].update({
        "duns_or_uei": "FICTIONAL-UEI-TEST", "ein": "FICTIONAL-EIN-TEST",
        "sam_gov_status": "active",
        "sam_gov_verified_utc": datetime.now(timezone.utc).isoformat(),
        "sam_gov_expiration_date": "2099-12-31",
    })
    f.profile["submission_readiness"].update({
        "grants_gov_account_verified": True, "aor_authority_verified": True,
    })
    f.profile["project"] = {
        "summary": "Fictional local custody test; no funding application exists.",
        "methods": "Compare fictional document bytes with their recorded hashes.",
        "validation_plan": "Reject any changed or unrecorded fictional document.",
        "commercial_plan": "No sale, revenue, price or customer commitment is claimed.",
        "facilities": "Temporary local test storage; no deployed facility is claimed.",
    }
    run = factory.write_bundle(f.program, f.profile, f.evidence, f.eligibility, f.utc)
    factory.approve(f.grant_id)
    snapshot = factory.APPROVED_DIR / f.grant_id / run.name
    snapshot_bytes = _bytes(snapshot)
    preflight = kit.build_preflight(f.grant_id, run, f.program)
    assert preflight["target_stage"] == "full_proposal"
    assert preflight["ready"] is True

    response = api.mark_submitted(f.grant_id, api.SubmittedRequest(
        submitted_by="FICTIONAL LOCAL TEST REVIEWER",
        external_tracking_id="FICTIONAL-RECEIPT-NO-REAL-SUBMISSION",
        notes="Fictional local state transition test only; nothing was sent.",
    ))
    state = json.loads(response.body)["state"]
    assert state["state"] == "submitted"
    _assert_native_manifest(run, CORE_FILES | KIT_FILES)
    packet = json.loads((run / "submission_packet.json").read_text())
    assert packet["approval_state"] == "submitted"
    assert packet["submitted_utc"] == state["submitted_utc"]
    assert packet["external_tracking_id"] == state["external_tracking_id"]
    assert _bytes(snapshot) == snapshot_bytes
    assert json.loads(snapshot_bytes["approval_state.json"])["state"] == "approved"
    export = api.bundle_zip(f.grant_id)
    with zipfile.ZipFile(io.BytesIO(export.body)) as archive:
        assert {name: archive.read(name) for name in archive.namelist()} == _bytes(run)


def test_factory_dispatch_custody_error_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fictional_path = "/fictional/private/grants/DO-NOT-EXPOSE/application.json"

    def fail_dispatch(args: list[str]) -> int:
        raise factory.BundleIntegrityError(f"integrity failure at {fictional_path}")

    monkeypatch.setattr(factory, "main", fail_dispatch)
    with pytest.raises(HTTPException) as exc_info:
        api._run_factory(["--force"])
    assert exc_info.value.status_code == 409
    assert fictional_path not in str(exc_info.value.detail)
    assert "DO-NOT-EXPOSE" not in str(exc_info.value.detail)
