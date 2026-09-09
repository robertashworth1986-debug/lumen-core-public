"""Assemble one immutable reviewer bundle with three measured domain packets.

Rechecks the pinned file manifest and successful verification receipt before
assembly. ZIP bytes are read back; undeclared members and symlinks are refused.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import zipfile

import run_stage8 as run
from verify_stage8 import check_manifest, require


def packet_documents(results):
    index = run.strict_json(results / "INDEX.json")
    rows = [r for entry in index for r in run.strict_json(results / "metrics" / (Path(entry["array_file"]).stem + ".json"))]
    domains = {}
    for family in ("grid", "marine", "geothermal"):
        selected = [r for r in rows if r["family"] == family]
        clean = [r for r in selected if r["scenario"] == "clean" and r["slice"] == "all" and r["baseline"] == "persistence"]
        domains[family] = dict(schema="lumencore.domain_delta_packet.v1", family=family,
            measured=True, independent_validation=False, status="HISTORICAL_RESEARCH_ONLY",
            series=sorted({r["series"] for r in selected}), metric_records=len(selected),
            clean_vs_persistence_counts=dict(collections.Counter(r["status"] for r in clean)),
            primitive_array_files=sorted({r["array_file"] for r in selected}),
            all_metric_shards=sorted({"metrics/" + Path(r["array_file"]).stem + ".json" for r in selected}),
            interpretation={"grid":"Daily demand in native MWh; archived revised values, not attested day-ahead production inputs.",
                            "marine":"Hourly mean WVHT²×APD activity proxy in m²s; not electrical output or calibrated wave power.",
                            "geothermal":"Five-minute sensor means in gpm, psi, degF and bpm; each channel scored separately."}[family])
    clean_groups = collections.defaultdict(list)
    for r in rows:
        if r["scenario"] == "clean" and r["slice"] == "all":
            clean_groups[(r["series"], r["horizon_steps"], r["candidate"])].append(r)
    shortlist = [dict(series=k[0], horizon_steps=k[1], candidate=k[2], comparisons=v,
                      status="DESCRIPTIVE_SHORTLIST_REQUIRES_FRESH_EXTERNAL_TEST")
                 for k, v in sorted(clean_groups.items())
                 if len(v) == 2 and all(r["status"] == "DESCRIPTIVE_CANDIDATE_ONLY" for r in v)]
    return domains, shortlist


def build(results, inputs, receipt, out, expected):
    require(not out.exists(), "Refusing to replace a frozen packet")
    check_manifest(results, expected)
    verification = run.strict_json(receipt)
    require(verification["status"] == "PASS" and verification["manifest_sha256"] == expected,
            "Matching successful verification receipt required")
    protocol = run.strict_json(results / "PROTOCOL.json")
    members = {}
    def add(name, path):
        require(name not in members and not path.is_symlink() and path.is_file(), "Unsafe/duplicate packet member")
        members[name] = path
    for path in sorted(results.rglob("*")):
        if path.is_file(): add("results/" + path.relative_to(results).as_posix(), path)
    for name, digest in protocol["sources"].items():
        require(run.sha(inputs / name) == digest, "Source changed before packaging")
        add("inputs/" + name, inputs / name)
    add("VERIFICATION.json", receipt)
    for name in ("run_stage8.py", "verify_stage8.py", "verify_stage8_cached.py", "test_stage8.py", "test_cache_stage8.py", "package_stage8.py", "report_data.py", "report_queries.sql", "REPORT_QA.json", "PROTOCOL.json", "README.md", "FINDINGS.md", "TRANSFER_CONTRACTS.json"):
        add("source/experiments/energy_multisource/stage8/" + name, run.HERE / name)
    add("source/experiments/energy_multisource/stage3/run_stage3.py", run.HERE.parent / "stage3/run_stage3.py")
    for name in ("requirements-institutional-ubuntu-py311.lock", "LICENSE"):
        if (run.REPO / name).exists(): add("source/" + name, run.REPO / name)
    add("START_HERE.md", run.HERE / "README.md")
    add("FINDINGS.md", run.HERE / "FINDINGS.md")
    add("TRANSFER_CONTRACTS.json", run.HERE / "TRANSFER_CONTRACTS.json")
    domains, shortlist = packet_documents(results)
    generated = {"domain_packets/" + family + "/PACKET.json": (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
                 for family, value in domains.items()}
    generated["DESCRIPTIVE_SHORTLIST.json"] = (json.dumps(shortlist, indent=2, allow_nan=False) + "\n").encode()
    generated["RESULT_MANIFEST_SHA256.txt"] = (expected + "\n").encode()
    inventory = {name: run.sha(path) for name, path in members.items()}
    inventory.update({name: hashlib.sha256(data).hexdigest() for name, data in generated.items()})
    generated["BUNDLE_MANIFEST.json"] = (json.dumps({"schema":"lumencore.delta_bundle.v1", "files":inventory}, indent=2) + "\n").encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, path in sorted(members.items()): z.write(path, name)
        for name, data in sorted(generated.items()): z.writestr(name, data)
    # Check the transported representation, not just the source directory.
    with zipfile.ZipFile(out) as z:
        require(len(z.namelist()) == len(set(z.namelist())) and set(z.namelist()) == set(inventory) | {"BUNDLE_MANIFEST.json"}, "ZIP inventory mismatch")
        require(z.testzip() is None, "ZIP CRC failure")
        for name, digest in inventory.items():
            h = hashlib.sha256()
            with z.open(name) as f:
                for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
            require(h.hexdigest() == digest, "ZIP byte mismatch: " + name)
    return dict(status="PACKAGED_AND_READ_BACK", bytes=out.stat().st_size, sha256=run.sha(out),
                members=len(inventory)+1, measured_domain_packets=3, transfer_contracts=6,
                result_manifest_sha256=expected, descriptive_shortlist_cells=len(shortlist))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("results", "inputs", "receipt", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--expected-manifest-sha256", required=True)
    p.add_argument("--package-receipt", type=Path, required=True)
    a = p.parse_args()
    require(not a.package_receipt.exists(), "Receipt already exists")
    r = build(a.results, a.inputs, a.receipt, a.out, a.expected_manifest_sha256)
    run.write_json(a.package_receipt, r)
    print(json.dumps(r, indent=2))
