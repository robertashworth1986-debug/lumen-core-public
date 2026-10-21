"""Synthetic configurations and temp files only; no production or network calls."""
from contextlib import nullcontext
import importlib.util
import json
import os
from pathlib import Path
import stat
import time
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location("mime_repair", Path(__file__).resolve().parents[1] / "code/ops/repair_public_mjs_mime.py")
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)
RAW = b"# preserve exact bytes\r\ntypes {\r\n text/html html;\r\n application/javascript  js; # comment mjs\r\n}\r\n"


def dump(*, table=RAW.decode(), server_extra="", http_extra="", locations="location / { try_files $uri $uri/ =404; }"):
    return ("# configuration file /etc/nginx/nginx.conf:\n"
            "events {}\nhttp { include /etc/nginx/tables.types; " + http_extra +
            " server { listen 443 ssl; server_name lumen-core.ai; root /opt/lumencore/dashboard; " + server_extra + locations + " } }\n"
            "# configuration file /etc/nginx/tables.types:\n" + table)


def test_exact_candidate_bytes_and_idempotent_proposal():
    candidate, status = repair.propose(RAW)
    assert candidate == RAW.replace(b"js;", b"js mjs;", 1)
    assert len(candidate) == len(RAW) + 4 and status == "CANDIDATE"
    assert repair.propose(candidate) == (candidate, "ALREADY_MAPPED")


@pytest.mark.parametrize("raw", [b"types { application/javascript js; text/javascript js; }",
    b"types { text/plain js; }", b"types { application/javascript js; text/plain mjs; }",
    b"types { application/javascript js; } server {}", b"types { application/javascript js }", b"\x00"])
def test_candidate_refuses_ambiguous_or_unsupported_tables(raw):
    with pytest.raises(repair.RepairError):
        repair.propose(raw)


def test_discovers_actual_included_table_instead_of_guessing():
    assert repair.discover(dump()) == Path("/etc/nginx/tables.types")


@pytest.mark.parametrize("options", [
    {"server_extra": "types {}"},
    {"server_extra": "root /different;"},
    {"locations": "location /portfolio { proxy_pass http://backend; }"},
    {"locations": "location ~ \\.mjs$ { types {} }"},
    {"locations": "location / { try_files $uri /index.html; }"},
    {"locations": "location / { location /portfolio {} }"},
    {"locations": "location / { rewrite ^ /index.html; }"},
    {"server_extra": "error_page 404 /index.html;"},
])
def test_route_override_or_ambiguity_fails_closed(options):
    with pytest.raises(repair.RepairError):
        repair.discover(dump(**options))


def test_unrelated_api_proxy_does_not_prevent_static_proof():
    value = dump(locations="location /api/ { proxy_pass http://backend; } location / { try_files $uri =404; }")
    assert repair.discover(value) == Path("/etc/nginx/tables.types")


def test_regex_precedence_catches_proxy_override():
    value = dump(locations="location /portfolio/ { try_files $uri =404; } location ~* \\.mjs$ { proxy_pass http://backend; }")
    with pytest.raises(repair.RepairError, match="not_simple_static"):
        repair.discover(value)


def test_nested_irrelevant_prefix_does_not_affect_approved_static_routes():
    value = dump(locations=r"location /api/ { location ~ \.mjs$ { proxy_pass http://backend; } } location / { try_files $uri =404; }")
    assert repair.discover(value) == Path("/etc/nginx/tables.types")


@pytest.mark.parametrize("locations", [
    r"location / { location /portfolio/ { types {} } }",
    r"location /portfolio/ { location ~ \.mjs$ { proxy_pass http://backend; } }",
    r"location ~ \.mjs$ { location ~ math { types {} } }",
])
def test_relevant_nested_location_retains_diagnostic_and_refuses(locations):
    with pytest.raises(repair.RepairError, match="unsupported_relevant_nested_location") as failure:
        repair.discover(dump(locations=locations))
    facts = failure.value.route_diagnostics
    assert facts["diagnostic_only"] is True
    assert facts["locations"][1]["parent_id"] == facts["locations"][0]["id"]
    assert facts["locations"][0]["candidate_uris_with_ancestors"]


@pytest.mark.parametrize("first", ["$uri", "$uri $uri/"])
def test_named_fallback_checks_existing_file_first(first):
    value = dump(locations=f"location / {{ try_files {first} @gateway_fallback; }} location @gateway_fallback {{ proxy_pass http://backend; }}")
    assert repair.discover(value, verified_static_sha256=dict(repair.EXPECTED)) == Path("/etc/nginx/tables.types")


@pytest.mark.parametrize("proof", [None, {}, {"portfolio/math-models.mjs": "0" * 64}])
def test_named_fallback_discovery_requires_all_exact_static_hashes(proof):
    value = dump(locations="location / { try_files $uri @gateway_fallback; } location @gateway_fallback { proxy_pass http://backend; }")
    with pytest.raises(repair.RepairError, match="named_fallback_requires_verified_static_files"):
        repair.discover(value, verified_static_sha256=proof)


@pytest.mark.parametrize("fallback", ["$uri /index.html", "$uri @missing", "$uri/ @gateway_fallback", "/other $uri @gateway_fallback", "$uri $uri/ $args @gateway_fallback"])
def test_changed_uri_missing_name_or_non_file_first_fallback_refuses(fallback):
    value = dump(locations=f"location / {{ try_files {fallback}; }} location @gateway_fallback {{ proxy_pass http://backend; }}")
    with pytest.raises(repair.RepairError, match="unsupported_static_fallback"):
        repair.discover(value)


def test_route_diagnostics_redact_unknown_paths_headers_and_credentials():
    value = dump(server_extra='proxy_set_header Authorization "Bearer private-secret-fixture";',
                 locations='location / { location /private-secret-fixture { alias /private-secret-fixture; } try_files $uri @private-secret-fixture; }')
    with pytest.raises(repair.RepairError) as failure:
        repair.discover(value)
    encoded = json.dumps(failure.value.route_diagnostics)
    assert "private-secret-fixture" not in encoded
    assert "Authorization" not in encoded
    assert "Bearer" not in encoded
    assert '"redacted": true' in encoded
    assert '"kind": "alias"' in encoded


def test_route_diagnostic_count_is_bounded():
    nested = " ".join(f"location /private-{index} {{}}" for index in range(100))
    with pytest.raises(repair.RepairError) as failure:
        repair.discover(dump(locations="location / { " + nested + " }"))
    assert len(failure.value.route_diagnostics["locations"]) == 64
    assert failure.value.route_diagnostics["truncated"] is True


def test_route_diagnostic_encoded_size_is_bounded_and_tokens_stay_redacted():
    children = [{"args": ["try_files", *(["private-token-fixture"] * 8)], "children": None, "source": "/etc/nginx/public.conf"} for _ in range(24)]
    server = [{"args": ["location", f"/private-{index}"], "children": children, "source": "/etc/nginx/public.conf"} for index in range(64)]
    facts = repair.bounded_route_facts([], server)
    encoded = json.dumps(facts)
    assert len(encoded.encode()) <= 65536
    assert facts["truncated"] is True
    assert "private-token-fixture" not in encoded


def test_missing_and_duplicate_dump_sections_rejected():
    with pytest.raises(repair.RepairError):
        repair.discover(dump().split("# configuration file /etc/nginx/tables.types:")[0])
    with pytest.raises(repair.RepairError):
        repair.discover(dump() + "# configuration file /etc/nginx/tables.types:\n" + RAW.decode())


@pytest.fixture
def backend(tmp_path, monkeypatch):
    target = tmp_path / "active.types"
    target.write_bytes(RAW)
    backups = tmp_path / "rollback"
    backups.mkdir()
    directory = backups / ("20261021T010203Z-" + "a" * 32)
    directory.mkdir()
    meta = {"uid": 0, "gid": 0, "mode": 0o644, "atime_ns": 123, "mtime_ns": 456, "xattrs": {}}
    calls = []
    flags = {"fail_test_after": False, "fail_reload": False, "fail_http": False, "concurrent": False,
             "fail_install": False, "interrupted": False, "fail_restore": False, "fail_receipt": False,
             "config_drift": False, "probe_timeout": False}
    tests = [0]
    def checked(path, root, limit=4_000_000):
        mode = 0o600 if path.name == "execution.json" else 0o644
        return path.read_bytes(), SimpleNamespace(st_uid=0, st_gid=0, st_mode=stat.S_IFREG | mode,
                                                  st_dev=1, st_ino=1, st_size=path.stat().st_size, st_mtime_ns=456, st_ctime_ns=456)
    def install(path, raw, _meta, **kwargs):
        if path == target and raw != RAW and flags["fail_install"]:
            raise OSError("synthetic")
        if path == target and raw == RAW and flags["fail_restore"]:
            raise OSError("synthetic")
        path.write_bytes(raw)
        calls.append(("install", path.name, repair.digest(raw)))
        if path == target and raw != RAW and flags["interrupted"]:
            raise KeyboardInterrupt()
    def command(args, **kwargs):
        calls.append(tuple(args))
        if "-T" in args:
            if flags["config_drift"] and len([row for row in calls if "-T" in row]) > 1:
                return "changed unrelated route"
            return "not printed"
        if "-t" in args:
            tests[0] += 1
            if tests[0] == 2 and flags["fail_test_after"]:
                raise repair.RepairError("synthetic_test_failure")
        if "reload" in args and flags["fail_reload"]:
            flags["fail_reload"] = False
            raise repair.RepairError("synthetic_reload_failure")
        return {"passed": True}
    def probe(relative, expected, local, token):
        calls.append(("probe", relative, local))
        if flags["probe_timeout"]:
            raise repair.RepairError("https_probe_total_deadline")
        if flags["concurrent"]:
            target.write_bytes(b"unrelated edit")
        return {"path": relative, "route": "local" if local else "public", "passed": not flags["fail_http"]}
    monkeypatch.setattr(repair, "require_root", lambda: None)
    monkeypatch.setattr(repair, "exclusive_lock", nullcontext)
    monkeypatch.setattr(repair, "nginx_binary", lambda: "/nginx")
    monkeypatch.setattr(repair, "discover", lambda value, **kwargs: target)
    monkeypatch.setattr(repair, "checked_file", checked)
    monkeypatch.setattr(repair, "metadata", lambda *_: meta.copy())
    monkeypatch.setattr(repair, "create_rollback", lambda: directory)
    monkeypatch.setattr(repair, "secure_directory", lambda *_: None)
    monkeypatch.setattr(repair, "install_bytes", install)
    monkeypatch.setattr(repair, "fsync_directory", lambda *_: None)
    monkeypatch.setattr(repair, "command", command)
    monkeypatch.setattr(repair, "verify_static", lambda: [{"path": path, "sha256": sha, "expected_sha256": sha, "passed": True} for path, sha in repair.EXPECTED.items()])
    monkeypatch.setattr(repair, "probe", probe)
    monkeypatch.setattr(repair, "ROLLBACK_ROOT", backups)
    monkeypatch.setattr(repair.signal, "signal", lambda *_: None)
    # Windows lacks SIGHUP; only synthetic signal wiring is exercised here.
    monkeypatch.setattr(repair.signal, "SIGHUP", 1, raising=False)
    return target, directory, calls, flags


def test_inspect_has_no_install_or_reload(backend):
    target, directory, calls, flags = backend
    result = repair.execute("inspect")
    assert result["status"] == "INSPECTED" and target.read_bytes() == RAW
    assert not any("reload" in row or "install" in row for row in calls)
    assert list(directory.iterdir()) == []


def test_pre_mutation_discovery_refusal_keeps_facts_and_known_unchanged_state(backend, monkeypatch):
    target, directory, calls, flags = backend
    def refused(_dump, **kwargs):
        error = repair.RepairError("unsupported_relevant_nested_location")
        error.route_diagnostics = {"diagnostic_only": True, "locations": [{"id": 0, "parent_id": None}]}
        raise error
    monkeypatch.setattr(repair, "discover", refused)
    result = repair.execute("inspect")
    assert result["phase"] == "STATIC_ROUTE_DISCOVERY"
    assert result["configuration_modified"] is False and result["service_reloaded"] is False
    assert result["route_diagnostics"]["locations"]
    assert not any("reload" in row or "install" in row for row in calls)
    assert list(directory.iterdir()) == [] and target.read_bytes() == RAW


def test_missing_immutable_file_prevents_discovery_or_any_install(backend, monkeypatch):
    target, directory, calls, flags = backend
    discoveries = []
    monkeypatch.setattr(repair, "discover", lambda value, **kwargs: discoveries.append(value))
    def missing():
        raise repair.RepairError("static_release_hash_mismatch")
    monkeypatch.setattr(repair, "verify_static", missing)
    with pytest.raises(repair.RepairError, match="static_release_hash_mismatch"):
        repair.execute("apply", repair.digest(RAW))
    assert discoveries == [] and target.read_bytes() == RAW
    assert not any("reload" in row or "install" in row for row in calls)


def test_apply_requires_observed_original_hash(backend):
    target, directory, calls, flags = backend
    with pytest.raises(repair.RepairError, match="approved_original_hash_mismatch"):
        repair.execute("apply", "0" * 64)
    assert target.read_bytes() == RAW and list(directory.iterdir()) == []


def test_success_checks_all_three_local_and_public_and_retains_backup(backend):
    target, directory, calls, flags = backend
    result = repair.execute("apply", repair.digest(RAW))
    assert result["status"] == "REPAIRED_THREE_FILES_VERIFIED"
    assert target.read_bytes() == repair.propose(RAW)[0]
    assert (directory / "original.mime").read_bytes() == RAW
    assert len([row for row in calls if row[0] == "probe"]) == 6
    assert json.loads((directory / "execution.json").read_text())["status"] == result["status"]
    assert "not printed" not in json.dumps(result)


@pytest.mark.parametrize("failure", ["fail_test_after", "fail_reload", "fail_http", "fail_install", "interrupted", "probe_timeout"])
def test_failure_restores_original_and_revalidates_reload(backend, failure):
    target, directory, calls, flags = backend
    flags[failure] = True
    result = repair.execute("apply", repair.digest(RAW))
    assert result["status"] == "FAILED"
    assert result["rollback"] == "RESTORED_VALIDATED_RELOADED"
    assert target.read_bytes() == RAW
    assert any("reload" in row for row in calls)


def test_concurrent_edit_is_never_overwritten_by_rollback(backend):
    target, directory, calls, flags = backend
    flags.update(concurrent=True, fail_http=True)
    result = repair.execute("apply", repair.digest(RAW))
    assert result["rollback"] == "FAILED_MANUAL_REVIEW_REQUIRED"
    assert result["rollback_error_code"] == "concurrent_edit_rollback_refused"
    assert target.read_bytes() == b"unrelated edit"


def test_failed_restore_is_reported_without_claiming_success(backend):
    target, directory, calls, flags = backend
    flags.update(fail_http=True, fail_restore=True)
    result = repair.execute("apply", repair.digest(RAW))
    assert result["rollback"] == "FAILED_MANUAL_REVIEW_REQUIRED"
    assert target.read_bytes() == repair.propose(RAW)[0]


def test_other_configuration_drift_refuses_mime_install(backend):
    target, directory, calls, flags = backend
    flags["config_drift"] = True
    result = repair.execute("apply", repair.digest(RAW))
    assert result["status"] == "FAILED"
    assert result["error_code"] == "active_configuration_changed_before_install"
    assert result["configuration_modified"] is False and target.read_bytes() == RAW
    assert not any("reload" in row for row in calls)


def test_explicit_rollback_for_full_gate_failure_restores_only_mime(backend):
    target, directory, calls, flags = backend
    applied = repair.execute("apply", repair.digest(RAW))
    original_receipt = (directory / "execution.json").read_bytes()
    result = repair.explicit_rollback(directory.name, applied["original_sha256"], applied["candidate_sha256"])
    assert result["status"] == "MIME_ROLLBACK_VALIDATED_RELOADED"
    assert result["scope"] == "MIME_TABLE_ONLY" and result["full_release_rollback_claimed"] is False
    assert target.read_bytes() == RAW
    assert (directory / "execution.json").read_bytes() == original_receipt


@pytest.mark.parametrize("mismatch", ["id", "original", "candidate", "current", "backup", "target"])
def test_explicit_rollback_requires_exact_receipt_hashes_and_active_file(backend, mismatch, monkeypatch):
    target, directory, calls, flags = backend
    applied = repair.execute("apply", repair.digest(RAW))
    runid, original, candidate = directory.name, applied["original_sha256"], applied["candidate_sha256"]
    if mismatch == "id":
        runid = "../unrelated"
    elif mismatch == "original":
        original = "0" * 64
    elif mismatch == "candidate":
        candidate = "1" * 64
    elif mismatch == "current":
        target.write_bytes(b"different writer")
    elif mismatch == "backup":
        (directory / "original.mime").write_bytes(b"damaged backup")
    elif mismatch == "target":
        monkeypatch.setattr(repair, "discover", lambda _, **kwargs: target.with_name("other.types"))
    before = target.read_bytes()
    with pytest.raises(repair.RepairError):
        repair.explicit_rollback(runid, original, candidate)
    assert target.read_bytes() == before


def test_explicit_rollback_reload_failure_reports_actual_mutation(backend):
    target, directory, calls, flags = backend
    applied = repair.execute("apply", repair.digest(RAW))
    flags["fail_reload"] = True
    result = repair.explicit_rollback(directory.name, applied["original_sha256"], applied["candidate_sha256"])
    assert result["status"] == "MIME_ROLLBACK_FAILED_MANUAL_REVIEW_REQUIRED"
    assert result["configuration_modified"] is True and target.read_bytes() == RAW


def test_explicit_rollback_rejects_backup_metadata_drift(backend, monkeypatch):
    target, directory, calls, flags = backend
    applied = repair.execute("apply", repair.digest(RAW))
    real_metadata = repair.metadata
    def drifted(path, info):
        return {**real_metadata(path, info), "mode": 0o600}
    monkeypatch.setattr(repair, "metadata", drifted)
    with pytest.raises(repair.RepairError, match="rollback_backup_metadata_mismatch"):
        repair.explicit_rollback(directory.name, applied["original_sha256"], applied["candidate_sha256"])
    assert target.read_bytes() == repair.propose(RAW)[0]


def test_explicit_rollback_refuses_prior_metadata_only_edit(backend, monkeypatch):
    target, directory, calls, flags = backend
    applied = repair.execute("apply", repair.digest(RAW))
    real_metadata = repair.metadata
    def drifted(path, info):
        value = real_metadata(path, info)
        return {**value, "mode": 0o600} if path == target else value
    monkeypatch.setattr(repair, "metadata", drifted)
    with pytest.raises(repair.RepairError, match="concurrent_metadata_edit_rollback_refused"):
        repair.explicit_rollback(directory.name, applied["original_sha256"], applied["candidate_sha256"])
    assert target.read_bytes() == repair.propose(RAW)[0]


def test_internal_rollback_refuses_prior_metadata_only_edit(backend, monkeypatch):
    target, directory, calls, flags = backend
    real_metadata = repair.metadata
    drift = []
    def drifted(path, info):
        value = real_metadata(path, info)
        return {**value, "mode": 0o600} if path == target and drift else value
    def failed_probe(*args):
        drift.append(True)
        raise repair.RepairError("synthetic_probe_failure")
    monkeypatch.setattr(repair, "metadata", drifted)
    monkeypatch.setattr(repair, "probe", failed_probe)
    result = repair.execute("apply", repair.digest(RAW))
    assert result["rollback"] == "FAILED_MANUAL_REVIEW_REQUIRED"
    assert result["rollback_error_code"] == "concurrent_metadata_edit_rollback_refused"
    assert target.read_bytes() == repair.propose(RAW)[0]


@pytest.mark.skipif(os.name != "posix", reason="POSIX metadata install needs Linux")
def test_atomic_installer_preserves_mode_times_and_bytes(tmp_path):
    path = tmp_path / "table"
    path.write_bytes(RAW)
    os.chmod(path, 0o600)
    before = path.stat()
    meta = repair.metadata(path, before)
    repair.install_bytes(path, repair.propose(RAW)[0], meta)
    after = path.stat()
    assert stat.S_IMODE(after.st_mode) == 0o600
    assert after.st_mtime_ns == before.st_mtime_ns
    assert path.read_bytes() == repair.propose(RAW)[0]
    assert not list(tmp_path.glob(".*.mime-repair-*"))


@pytest.mark.skipif(os.name != "posix", reason="POSIX staging race test needs Linux")
def test_atomic_installer_rechecks_source_after_staging(tmp_path, monkeypatch):
    path = tmp_path / "table"
    path.write_bytes(RAW)
    monkeypatch.setattr(repair, "CONFIG_ROOT", tmp_path)
    monkeypatch.setattr(repair, "secure_directory", lambda *_: None)
    info = path.stat()
    meta = repair.metadata(path, info)
    version = repair.file_version(RAW, info, meta)
    original_fsync = repair.os.fsync
    injected = []
    def racing_fsync(fd):
        original_fsync(fd)
        if not injected:
            path.write_bytes(b"concurrent source edit")
            injected.append(True)
    monkeypatch.setattr(repair.os, "fsync", racing_fsync)
    with pytest.raises(repair.RepairError, match="changed_during_staging"):
        repair.install_bytes(path, repair.propose(RAW)[0], meta, expected_current=version)
    assert path.read_bytes() == b"concurrent source edit"
    assert not list(tmp_path.glob(".*.mime-repair-*"))


def test_untracked_exception_never_claims_configuration_unchanged(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["repair", "apply", "--expected-sha256", "0" * 64])
    monkeypatch.setattr(repair.signal, "signal", lambda *_: None)
    def fail(*args):
        raise KeyboardInterrupt()
    monkeypatch.setattr(repair, "execute", fail)
    assert repair.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["configuration_modified"] is None
    assert result["status"] == "FAILED_STATE_REVIEW_REQUIRED"


@pytest.mark.skipif(os.name != "posix", reason="POSIX total deadline test needs Linux")
def test_total_deadline_bounds_slow_trickle_equivalent_wait():
    start = time.monotonic()
    with pytest.raises(repair.RepairError, match="https_probe_total_deadline"):
        with repair.total_deadline(0.03):
            time.sleep(1)
    assert time.monotonic() - start < 0.5
