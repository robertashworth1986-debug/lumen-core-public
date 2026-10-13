from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard/build_week/prooflock_console"
FIXTURES = json.loads((ROOT / "tests/fixtures/prooflock_canonicalization_v2.json").read_text())
NODE_RUNNER = r"""
const fs = require('node:fs'), path = require('node:path');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const core = require(path.resolve(input.app, 'prooflock_core.js'));
(async () => {
 const output = [];
 for (const item of input.cases) {
  try {
   const parsed = core.parseStrictJson(item.raw, item.profile ? {profile:item.profile} : {});
   if (item.operation === 'verify') output.push({ok:true,report:await core.verifyReceipt(parsed,{loadArtifact:p=>fs.readFileSync(path.join(input.artifactRoot,p))})});
   else {const canonical=core.canonicalize(parsed,item.profile);output.push({ok:true,canonical,hash:await core.sha256Text(canonical)});}
  } catch(error) {output.push({ok:false,error:String(error.message || error)});}
 }
 process.stdout.write(JSON.stringify(output));
})().catch(error=>{process.stderr.write(String(error));process.exitCode=1;});
"""


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("prooflock_parity_verifier", APP / "verify_receipt.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def node(cases: list[dict], artifact_root: Path | None = None) -> list[dict]:
    completed = subprocess.run(
        ["node", "-e", NODE_RUNNER], input=json.dumps({"app":str(APP),"cases":cases,"artifactRoot":str(artifact_root or ROOT / "dashboard")}),
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    return json.loads(completed.stdout)


def artifact_root(tmp_path: Path, receipt: dict) -> Path:
    for row in receipt["artifacts"]:
        target = tmp_path / row["repo_relative_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.run(["git","cat-file","blob",f"HEAD:dashboard/{row['repo_relative_path']}"],cwd=ROOT,check=True,capture_output=True).stdout)
    return tmp_path


def sample(verifier, v2=False) -> dict:
    receipt = verifier.strict_json_loads((APP / "sample_receipt.json").read_text())
    if v2:
        receipt["schema"] = verifier.RECEIPT_SCHEMA_V2
        receipt["canonicalization"] = verifier.CANONICALIZATION_V2
    return receipt


def test_shared_v2_vectors_produce_identical_text_and_sha256(verifier):
    profile = verifier.CANONICALIZATION_V2
    results = node([dict(row,profile=profile) for row in FIXTURES["accepted"]])
    for row, result in zip(FIXTURES["accepted"],results,strict=True):
        parsed = verifier.strict_json_loads(row["raw"],profile)
        canonical = verifier.canonical_json(parsed,profile)
        assert result["ok"], (row["id"],result)
        assert result["canonical"] == canonical, row["id"]
        assert result["hash"] == hashlib.sha256(canonical.encode()).hexdigest(), row["id"]
    assert verifier.canonical_json({"measurement":1.0},profile) == '{"measurement":N3ff0000000000000;}'
    assert verifier.canonical_json({"measurement":-0.0},profile) == '{"measurement":N0000000000000000;}'


def test_shared_v2_invalid_vectors_are_rejected_by_both_raw_parsers(verifier):
    results = node([dict(row,profile=verifier.CANONICALIZATION_V2) for row in FIXTURES["rejected"]])
    for row,result in zip(FIXTURES["rejected"],results,strict=True):
        assert not result["ok"], row["id"]
        with pytest.raises(ValueError):
            verifier.strict_json_loads(row["raw"],verifier.CANONICALIZATION_V2)


def test_v1_portable_sample_keeps_its_historical_hash_and_bytes(verifier,tmp_path):
    raw = (APP / "sample_receipt.json").read_bytes()
    receipt = sample(verifier)
    assert receipt["receipt_sha256"] == "a7509f90f65dfc024e1918b984a0c963811512c040df47ab22d9ea2b51195576"
    assert verifier.stable_hash(verifier.receipt_payload(receipt)) == receipt["receipt_sha256"]
    root = artifact_root(tmp_path,receipt)
    py = verifier.verify_receipt(receipt,root)
    js = node([{"raw":raw.decode(),"operation":"verify"}],root)[0]
    assert js["ok"]
    assert py["integrity_valid"] and js["report"]["integrity_valid"]
    assert py["receipt_hash"] == js["report"]["receipt_hash"]
    assert not py["promotion_allowed"] and not js["report"]["promotion_allowed"]
    assert (APP / "sample_receipt.json").read_bytes() == raw


@pytest.mark.parametrize("metadata",[1.0,1e-6,-0.0,{"Ｚ":"BMP","😀":"astral"},"\x7f\n😀"])
def test_full_v2_receipts_match_across_runtime_and_resealed_promote_stays_blocked(verifier,tmp_path,metadata):
    receipt = sample(verifier,True)
    receipt["measurement"] = metadata
    receipt["decision"] = "PROMOTE"
    for gate in receipt["gates"]:
        gate["status"] = "PASS"
    receipt["receipt_sha256"] = verifier.stable_hash(verifier.receipt_payload(receipt))
    root = artifact_root(tmp_path,receipt)
    py = verifier.verify_receipt(receipt,root)
    js = node([{"raw":json.dumps(receipt,ensure_ascii=True),"operation":"verify"}],root)[0]
    assert js["ok"],js
    report = js["report"]
    assert py["integrity_valid"] and report["integrity_valid"]
    assert py["receipt_hash"] == report["receipt_hash"]
    assert py["artifact_hash_match_count"] == report["artifact_hash_match_count"] == 2
    assert not py["policy_valid"] and not report["policy_valid"]
    assert not py["promotion_allowed"] and not report["promotion_allowed"]


@pytest.mark.parametrize("raw_value",["1.0","1e-6","-0.0","-0",'{"Ｚ":1,"😀":2}','"\\u007f"'])
def test_nonportable_v1_text_is_rejected_instead_of_reinterpreted(verifier,raw_value):
    raw = '{"schema":"lumencore.prooflock_receipt.v1","measurement":'+raw_value+'}'
    assert not node([{"raw":raw}])[0]["ok"]
    with pytest.raises(ValueError):
        verifier.strict_json_loads(raw)


def test_v1_unicode_string_values_and_ascii_control_escapes_remain_portable(verifier):
    raw = '{"schema":"lumencore.prooflock_receipt.v1","text":"é😀\\n\\t\\u0001"}'
    parsed = verifier.strict_json_loads(raw)
    result = node([{"raw":raw}])[0]
    assert result["ok"]
    assert result["canonical"] == verifier.canonical_json(parsed)
    assert result["hash"] == verifier.stable_hash(parsed)


def test_duplicate_decoded_manifest_keys_cannot_pass_lineage(verifier,tmp_path):
    receipt = sample(verifier)
    root = artifact_root(tmp_path,receipt)
    current = next(a for a in receipt["artifacts"] if a["role"] == "current_protocol_manifest")
    path = root / current["repo_relative_path"]
    old = path.read_text()
    path.write_text('{"asset_id":"contradiction",'+old.strip()[1:])
    current["expected_sha256"] = verifier.file_sha256(path)
    receipt["receipt_sha256"] = verifier.stable_hash(verifier.receipt_payload(receipt))
    py = verifier.verify_receipt(receipt,root)
    js = node([{"raw":json.dumps(receipt),"operation":"verify"}],root)[0]["report"]
    for report in (py,js):
        lineage = next(g for g in report["gates"] if g["gate_id"] == "lineage_manifest")
        assert lineage["effective_status"] == "FAIL"
        assert not report["promotion_allowed"]


@pytest.mark.parametrize("profile",["missing","wrong"])
def test_v2_profile_is_required_and_unknown_profiles_fail_closed(verifier,tmp_path,profile):
    receipt = sample(verifier,True)
    if profile == "missing":
        receipt.pop("canonicalization")
    else:
        receipt["canonicalization"] = "unrecognized"
    report = verifier.verify_receipt(receipt,artifact_root(tmp_path,receipt))
    js = node([{"raw":json.dumps(receipt),"operation":"verify"}],tmp_path)[0]
    assert not report["integrity_valid"]
    assert not report["promotion_allowed"]
    assert not js["report"]["integrity_valid"]
    assert not js["report"]["promotion_allowed"]


def test_write_hash_rejects_ambiguous_v1_and_never_changes_original_bytes(verifier,tmp_path):
    receipt = sample(verifier)
    receipt["measurement"] = 1.0
    path = tmp_path / "historical_v1.json"
    path.write_text(json.dumps(receipt))
    before = path.read_bytes()
    with pytest.raises(ValueError,match="integer lexemes"):
        verifier.write_receipt_hash(path)
    assert path.read_bytes() == before
    result = subprocess.run([sys.executable,str(APP / "verify_receipt.py"),str(path),"--write-hash"],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)["promotion_allowed"] is False
    assert "Traceback" not in result.stderr
    assert path.read_bytes() == before


def test_raw_json_text_and_nesting_budgets_reject_before_verification(verifier):
    deep = "["*102 + "0" + "]"*102
    large = '"' + "x"*2_000_000 + '"'
    for raw in (deep,large):
        with pytest.raises(ValueError):
            verifier.strict_json_loads(raw)
        assert not node([{"raw":raw}])[0]["ok"]


def test_browser_raw_receipt_entrypoints_use_the_strict_parser():
    source = (APP / "app.js").read_text()
    assert "receipt: Core.parseStrictJson(text)" in source
    assert "receipt = Core.parseStrictJson(elements.editor.value)" in source
    assert "JSON.parse(elements.editor.value)" not in source
    assert "--directory dashboard" in (APP / "README.md").read_text()
