"""Offline captured-byte package regressions; no account or runtime invocation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "code/build_investor_evidence_pack.py"
spec = importlib.util.spec_from_file_location("investor_pack_under_test", SOURCE)
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


def setup(tmp_path, names=None):
    root = tmp_path / "source"
    root.mkdir()
    (root / "evidence.json").write_bytes(b'{"claim":"unverified"}\n')
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps(names or ["evidence.json"]))
    return root, selection, tmp_path / "output"


def build(paths):
    return pack.build_pack(source_root=paths[0], artifact_paths=paths[1], output_dir=paths[2])


def test_archive_and_ledger_bind_exact_captured_bytes(tmp_path):
    paths = setup(tmp_path)
    result = build(paths)
    manifest_raw = (paths[2] / pack.MANIFEST_NAME).read_bytes()
    manifest = json.loads(manifest_raw)
    item = manifest["artifacts"][0]
    with zipfile.ZipFile(paths[2] / pack.ARCHIVE_NAME) as z:
        assert len(z.namelist()) == 3
        assert z.read(pack.MANIFEST_NAME) == manifest_raw
        assert z.read(pack.LEDGER_NAME) == (paths[2] / pack.LEDGER_NAME).read_bytes()
        assert z.read(item["archive_path"]) == (paths[0] / item["path"]).read_bytes()
        assert hashlib.sha256(z.read(item["archive_path"])).hexdigest() == item["sha256"]
        assert len(z.read(item["archive_path"])) == item["bytes"]
    assert result["manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest()
    assert result["archive_sha256"] == hashlib.sha256((paths[2] / pack.ARCHIVE_NAME).read_bytes()).hexdigest()
    self_hash = manifest.pop("manifest_sha256")
    assert self_hash == hashlib.sha256(pack._json_bytes(manifest)).hexdigest()
    assert manifest["evidence_class"] == "CAPTURED_SOURCE_BYTES_ONLY"
    assert manifest["content_claims_verified"] is manifest["external_validation"] is False


def test_post_capture_mutation_cannot_change_zip_or_hash(tmp_path, monkeypatch):
    paths = setup(tmp_path)
    original = (paths[0] / "evidence.json").read_bytes()
    capture = pack.capture_file
    def changed(path, limit):
        result = capture(path, limit)
        if path.name == "evidence.json":
            path.write_bytes(b"changed after capture")
        return result
    monkeypatch.setattr(pack, "capture_file", changed)
    build(paths)
    with zipfile.ZipFile(paths[2] / pack.ARCHIVE_NAME) as z:
        assert z.read("sources/evidence.json") == original
        item = json.loads(z.read(pack.MANIFEST_NAME))["artifacts"][0]
        assert item["sha256"] == hashlib.sha256(original).hexdigest()


@pytest.mark.parametrize("names", [[], {}, None, [1], [True], [""], ["/etc/x"],
    ["../x"], ["a/../x"], ["a//b"], ["./x"], ["a\\b"], ["C:/x"], ["x:stream"],
    ["CON.txt"], ["Lpt1"], ["dir./x"], ["dir /x"], ["x\nname"], ["a", "A"],
    ["a", "a"], ["x" * 241], ["a/" * 17 + "b"], [f"a{i}" for i in range(129)],
    ["=1+1"], ["+SUM(1)"], ["-1+1"], ["@SUM(1)"], [" leading"]])
def test_unsafe_selection_rejected_before_output(tmp_path, names):
    paths = setup(tmp_path)
    paths[1].write_text(json.dumps(names))
    with pytest.raises(ValueError):
        build(paths)
    assert not paths[2].exists()


@pytest.mark.parametrize("raw", [b"{", b'[NaN]', b'{"x":1,"x":2}', b'\xff', b"[" * 1100])
def test_malformed_selection_holds(tmp_path, raw):
    paths = setup(tmp_path)
    paths[1].write_bytes(raw)
    assert pack.main(["--source-root", str(paths[0]), "--artifacts-json", str(paths[1]),
                      "--output-dir", str(paths[2])]) == 2
    assert not paths[2].exists()


def test_missing_input_is_not_silently_omitted(tmp_path):
    paths = setup(tmp_path, ["evidence.json", "missing.json"])
    with pytest.raises(OSError):
        build(paths)
    assert not paths[2].exists()


def test_existing_output_preserved(tmp_path):
    paths = setup(tmp_path)
    paths[2].mkdir()
    sentinel = paths[2] / "keep"
    sentinel.write_bytes(b"prior evidence")
    with pytest.raises(ValueError, match="new"):
        build(paths)
    assert sentinel.read_bytes() == b"prior evidence"
    assert len(list(paths[2].iterdir())) == 1


@pytest.mark.parametrize("limit_name,limit", [("MAX_FILE_BYTES", 2), ("MAX_TOTAL_BYTES", 2),
                                              ("MAX_SELECTION_BYTES", 2)])
def test_byte_bounds_before_output(tmp_path, monkeypatch, limit_name, limit):
    paths = setup(tmp_path)
    monkeypatch.setattr(pack, limit_name, limit)
    with pytest.raises(ValueError):
        build(paths)
    assert not paths[2].exists()


def test_aggregate_limit_is_not_just_per_file(tmp_path, monkeypatch):
    paths = setup(tmp_path, ["a", "b"])
    (paths[0] / "a").write_bytes(b"123")
    (paths[0] / "b").write_bytes(b"456")
    monkeypatch.setattr(pack, "MAX_FILE_BYTES", 3)
    monkeypatch.setattr(pack, "MAX_TOTAL_BYTES", 5)
    with pytest.raises(ValueError):
        build(paths)
    assert not paths[2].exists()


def test_directory_source_rejected(tmp_path):
    paths = setup(tmp_path, ["directory"])
    (paths[0] / "directory").mkdir()
    with pytest.raises(ValueError):
        build(paths)
    assert not paths[2].exists()


def test_observed_change_during_capture_holds(tmp_path, monkeypatch):
    path = tmp_path / "x"
    path.write_bytes(b"abc")
    real = pack.os.fstat
    calls = []
    def changed(fd):
        info = real(fd)
        calls.append(fd)
        if len(calls) == 2:
            return SimpleNamespace(st_dev=info.st_dev, st_ino=info.st_ino,
                st_size=info.st_size, st_mtime_ns=info.st_mtime_ns + 1)
        return info
    monkeypatch.setattr(pack.os, "fstat", changed)
    with pytest.raises(ValueError, match="changed"):
        pack.capture_file(path, 4)


def test_observed_windows_reparse_attribute_is_rejected(tmp_path, monkeypatch):
    paths = setup(tmp_path)
    original = Path.lstat
    def reparse(path):
        info = original(path)
        if path.name == "evidence.json":
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(ValueError, match="reparse"):
        build(paths)
    assert not paths[2].exists()


def test_missing_trade_log_does_not_become_zero_or_trigger_reads(monkeypatch):
    def prohibited(*args, **kwargs):
        raise AssertionError("Financial summarization must not read files")
    monkeypatch.setattr(Path, "read_text", prohibited)
    result = pack.summarize_trade_log(Path("not-present"))
    assert all(result[key] is None for key in ("trades", "wins", "losses", "win_rate", "realized_pnl"))
    assert result["broker_reconciled"] is result["investment_ready"] is False


def test_import_and_no_argument_cli_have_no_outputs(tmp_path, monkeypatch):
    source = SOURCE.read_text()
    def prohibited(*args, **kwargs):
        raise AssertionError("Import must not create directories")
    monkeypatch.setattr(Path, "mkdir", prohibited)
    exec(compile(source, str(SOURCE), "exec"), {"__name__": "read_only_import"})
    result = subprocess.run([sys.executable, str(SOURCE)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert not list(tmp_path.iterdir())


def test_implicit_orchestrator_does_not_publish_stale_package():
    source = (ROOT / "code/RUN_ELITE_STACK_OPTIMIZER.ps1").read_text()
    assert "build_investor_evidence_pack.py'" not in source
    assert "institutional_evidence_pack_*.zip" not in source
    assert "evidence packaging remains HOLD" in source
    assert "$LASTEXITCODE -ne 0" in source


@pytest.mark.skipif(not shutil.which("powershell.exe"), reason="Native PowerShell caller check requires Windows")
def test_isolated_native_step_failure_and_location_recovery(tmp_path):
    def literal(value):
        return "'" + str(value).replace("'", "''") + "'"
    source = ROOT / "code/RUN_ELITE_STACK_OPTIMIZER.ps1"
    command = "& " + literal(sys.executable) + " -c "
    script = r"""
$ErrorActionPreference = 'Stop'
$Tokens = $null; $ParseErrors = $null
$Tree = [System.Management.Automation.Language.Parser]::ParseFile(SOURCE, [ref]$Tokens, [ref]$ParseErrors)
if ($ParseErrors.Count) { throw 'parse failed' }
$Function = $Tree.Find({ param($Node) $Node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $Node.Name -eq 'Run-Step' }, $true)
. ([scriptblock]::Create($Function.Extent.Text))
$Before = (Get-Location).Path
$Rejected = $false
try { Run-Step -Label 'failure' -WorkingDirectory WORKING -Command FAILURE } catch {
 if ($_.Exception.Message -notmatch 'failed with native exit code 7') { throw }
 $Rejected = $true
}
if (-not $Rejected -or (Get-Location).Path -ne $Before) { throw 'failed step was not isolated' }
Run-Step -Label 'success' -WorkingDirectory WORKING -Command SUCCESS
if ((Get-Location).Path -ne $Before) { throw 'success location not restored' }
"""
    for key, value in {"SOURCE": literal(source), "WORKING": literal(tmp_path),
                       "FAILURE": literal(command + literal("import sys; sys.exit(7)")),
                       "SUCCESS": literal(command + literal("import sys; sys.exit(0)"))}.items():
        script = script.replace(key, value)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list(tmp_path.iterdir())
