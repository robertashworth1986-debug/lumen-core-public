from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_PROOFLOCK_LIVE_RELEASE.py"
RECEIPT = (
    ROOT
    / "docs"
    / "OPENAI_BUILD_WEEK_PROOFLOCK_PREDEPLOYMENT_GATE_2026-07-18.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_prooflock_live_release", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_source(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
    source = tmp_path / "private-source-name"
    source.mkdir()
    bodies = {
        "app.js": b"console.log('bounded');\n",
        "index.html": b"<!doctype html><title>ProofLock</title>\n",
        "verify_receipt.py": b"print('verified')\n",
    }
    for name, body in bodies.items():
        (source / name).write_bytes(body)
    return source, bodies


def fake_fetcher(
    bodies: dict[str, bytes], *, redirect_name: str | None = None
):
    def fetch(url: str, _timeout: float):
        name = unquote(Path(urlsplit(url).path).name)
        final_url = url
        if name == redirect_name:
            final_url = "https://example.test/login"
        return {"status": 200, "body": bodies[name], "final_url": final_url}

    return fetch


def verified_provenance(commit: str, file_count: int) -> dict[str, object]:
    return {
        "checked": True,
        "verified": True,
        "resolved_commit": commit,
        "tracked_file_count": file_count,
        "worktree_file_count": file_count,
        "worktree_match_count": file_count,
        "worktree_matches_commit": True,
        "mismatched_files": [],
        "commit_symlinks_rejected": [],
        "worktree_symlinks_rejected": [],
    }


def test_all_files_matching_opens_only_the_deployment_identity_gate(tmp_path):
    module = load_module()
    source, bodies = make_source(tmp_path)
    commit = "a" * 40

    payload = module.verify_live_release(
        source_dir=source,
        base_url="https://example.test/prooflock/",
        source_commit=commit,
        source_provenance=verified_provenance(commit, len(bodies)),
        fetcher=fake_fetcher(bodies),
        generated_utc="2026-07-18T13:30:00+00:00",
    )

    assert payload["status"] == "CURRENT_HEAD_DEPLOYED"
    assert payload["submission_gate"] == "PASS"
    assert payload["deployment_required"] is False
    assert payload["summary"]["byte_match_count"] == 3
    assert payload["mismatched_files"] == []
    assert payload["controls"]["submission_performed"] is False


def test_one_stale_file_holds_submission_and_names_only_public_file(tmp_path):
    module = load_module()
    source, bodies = make_source(tmp_path)
    commit = "b" * 40
    live_bodies = dict(bodies)
    live_bodies["app.js"] = b"stale\n"

    payload = module.verify_live_release(
        source_dir=source,
        base_url="https://example.test/prooflock/",
        source_commit=commit,
        source_provenance=verified_provenance(commit, len(bodies)),
        fetcher=fake_fetcher(live_bodies),
        generated_utc="2026-07-18T13:30:00+00:00",
    )
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "STALE_OR_INCOMPLETE_DEPLOYMENT_HOLD"
    assert payload["submission_gate"] == "HOLD"
    assert payload["deployment_required"] is True
    assert payload["mismatched_files"] == ["app.js"]
    assert "private-source-name" not in rendered
    assert str(tmp_path) not in rendered


def test_redirect_to_a_different_path_is_rejected_even_when_bytes_match(tmp_path):
    module = load_module()
    source, bodies = make_source(tmp_path)
    commit = "c" * 40

    payload = module.verify_live_release(
        source_dir=source,
        base_url="https://example.test/prooflock/",
        source_commit=commit,
        source_provenance=verified_provenance(commit, len(bodies)),
        fetcher=fake_fetcher(bodies, redirect_name="index.html"),
        generated_utc="2026-07-18T13:30:00+00:00",
    )
    row = next(row for row in payload["files"] if row["file"] == "index.html")

    assert row["redirect_valid"] is False
    assert row["byte_match"] is False
    assert row["state"] == "REDIRECT_REJECTED"
    assert payload["submission_gate"] == "HOLD"


def test_gate_hash_covers_the_complete_public_payload(tmp_path):
    module = load_module()
    source, bodies = make_source(tmp_path)
    commit = "d" * 40
    payload = module.verify_live_release(
        source_dir=source,
        base_url="https://example.test/prooflock/",
        source_commit=commit,
        source_provenance=verified_provenance(commit, len(bodies)),
        fetcher=fake_fetcher(bodies),
        generated_utc="2026-07-18T13:30:00+00:00",
    )

    unhashed = dict(payload)
    recorded = unhashed.pop("gate_sha256")
    assert recorded == module.stable_hash(unhashed)


def test_matching_live_bytes_hold_without_verified_commit_provenance(tmp_path):
    module = load_module()
    source, bodies = make_source(tmp_path)

    payload = module.verify_live_release(
        source_dir=source,
        base_url="https://example.test/prooflock/",
        source_commit="e" * 40,
        fetcher=fake_fetcher(bodies),
        generated_utc="2026-07-18T13:30:00+00:00",
    )

    assert payload["summary"]["byte_match_count"] == len(bodies)
    assert payload["controls"]["source_commit_bytes_verified"] is False
    assert payload["submission_gate"] == "HOLD"


def test_git_snapshot_matches_the_named_deployable_source_commit():
    module = load_module()
    commit = "8c235f587fa748745b67903cda17817c7a344c7d"

    resolved, files, provenance = module.git_source_snapshot(
        root=ROOT,
        source_dir=module.DEFAULT_SOURCE_DIR,
        source_commit=commit,
    )

    assert resolved == commit
    assert provenance["verified"] is True
    assert provenance["tracked_file_count"] == 14
    assert provenance["worktree_file_count"] >= 14
    assert provenance["worktree_matches_commit"] is False
    assert len(files) == 14


def test_checked_in_predeployment_receipt_is_public_safe_and_fail_closed():
    module = load_module()
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    rendered = json.dumps(payload, sort_keys=True).lower()

    assert payload["schema"] == module.SCHEMA
    assert payload["source_commit"] == "8c235f587fa748745b67903cda17817c7a344c7d"
    assert payload["status"] == "STALE_OR_INCOMPLETE_DEPLOYMENT_HOLD"
    assert payload["submission_gate"] == "HOLD"
    assert payload["summary"]["file_count"] == 14
    assert payload["summary"]["byte_match_count"] == 10
    assert payload["controls"]["source_commit_bytes_verified"] is True
    assert payload["source_provenance"]["verified"] is True
    assert "prooflock_core.js" in payload["mismatched_files"]
    assert "verify_receipt.py" in payload["mismatched_files"]
    assert "c:\\users" not in rendered
    assert "e:\\" not in rendered
    assert "@gmail.com" not in rendered

    unhashed = dict(payload)
    recorded = unhashed.pop("gate_sha256")
    assert recorded == module.stable_hash(unhashed)
