#!/usr/bin/env python3
"""Offline, post-hoc coverage/common-mask audit. Never authorizes promotion.

Consume the unchanged Stage 8 packet with its externally supplied manifest hash.
This adds a diagnostic, not a forecaster, new trial, or independent validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any
import numpy as np

MAX_FILES = 5000
MAX_BYTES = 2_000_000_000
REQUIRED_BASELINES = ("persistence", "seasonal")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    require(path.stat().st_size <= 2 * 1024 * 1024, "JSON exceeds bounded size")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def number(text):
        value = float(text)
        require(math.isfinite(value), "Nonfinite JSON number")
        return value
    def invalid(text):
        raise ValueError("Invalid JSON numeric constant")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_float=number, parse_constant=invalid)


def verify_tree(root: Path, expected: str) -> dict:
    require(bool(re.fullmatch(r"[0-9a-f]{64}", expected)), "Expected SHA-256 required")
    require(root.is_dir() and not root.is_symlink(), "Packet directory required")
    manifest = root / "MANIFEST.json"
    require(not manifest.is_symlink() and digest(manifest) == expected, "Manifest hash mismatch")
    data = read_json(manifest)
    entries = data.get("files")
    require(isinstance(entries, dict) and 0 < len(entries) <= MAX_FILES, "Invalid inventory")
    total = 0
    for name, wanted in entries.items():
        require(isinstance(name, str) and name not in ("", "MANIFEST.json") and
                "\\" not in name and "\x00" not in name and
                not Path(name).is_absolute() and
                all(part not in ("", ".", "..") for part in name.split("/")), "Unsafe manifest path")
        require(isinstance(wanted, str) and bool(re.fullmatch(r"[0-9a-f]{64}", wanted)), "Invalid file hash")
        target = root / name
        require(all(not p.is_symlink() for p in [target, *target.parents] if p != root.parent), "Symlink forbidden")
        require(target.is_file() and target.resolve().is_relative_to(root.resolve()), "Missing or escaped file")
        total += target.stat().st_size
        require(total <= MAX_BYTES, "Packet exceeds byte budget")
        require(digest(target) == wanted, "Content hash mismatch: " + name)
    actual = set()
    for path in root.rglob("*"):
        require(not path.is_symlink(), "Symlink in packet")
        if path.is_file() and path != manifest:
            actual.add(path.relative_to(root).as_posix())
        require(len(actual) <= MAX_FILES, "Too many files")
    require(actual == set(entries), "Undeclared or missing file")
    return {"manifest_sha256": expected, "verified_files": len(entries), "verified_bytes": total}


def vector(value: Any, name: str) -> np.ndarray:
    a = np.asarray(value)
    require(a.ndim == 1 and a.dtype.kind in "fiu", name + " must be a numeric vector")
    a = a.astype(float)
    require(not np.isinf(a).any(), name + " contains infinity")
    return a


def ratio(n: int, d: int) -> float | None:
    return n / d if d else None


def audit_cell(truth: Any, candidate: Any, baselines: dict, mask: Any) -> dict:
    y = vector(truth, "truth"); c = vector(candidate, "candidate")
    require(set(baselines) == set(REQUIRED_BASELINES), "Both named baselines are required")
    b = {k: vector(v, k) for k, v in baselines.items()}
    m = np.asarray(mask)
    require(m.ndim == 1 and m.dtype.kind == "b", "Slice mask must be Boolean")
    require(all(len(v) == len(y) for v in [c, m, *b.values()]), "Length mismatch")
    observed = m & np.isfinite(y)
    common = observed & np.isfinite(c)
    for values in b.values():
        common &= np.isfinite(values)
    scheduled = int(m.sum()); outcomes = int(observed.sum()); pairs = int(common.sum())
    result = {"scheduled_targets": scheduled, "observed_targets": outcomes,
              "common_pairs": pairs,
              "observed_over_scheduled": ratio(outcomes, scheduled),
              "common_over_observed": ratio(pairs, outcomes),
              "common_over_scheduled": ratio(pairs, scheduled),
              "prediction_available_over_scheduled": ratio(int((m & np.isfinite(c)).sum()), scheduled),
              "comparisons": {}, "baselines_identical_on_common_rows": None,
              "all_baseline_descriptive_screen": False,
              "decision": "RESEARCH_ONLY_NO_PROMOTION"}
    if not pairs:
        return result
    with np.errstate(over="raise", invalid="raise"):
        ce = np.abs(c[common] - y[common])
        cm = float(np.mean(ce)); cp = float(np.quantile(ce, .95))
        require(math.isfinite(cm) and math.isfinite(cp), "Metric overflow")
        for name, values in b.items():
            be = np.abs(values[common] - y[common])
            bm = float(np.mean(be)); bp = float(np.quantile(be, .95))
            quartiles = []
            for indices in np.array_split(np.flatnonzero(m), 4):
                selected = indices[common[indices]]
                quartiles.append(float(np.mean(np.abs(values[selected] - y[selected]) -
                                                np.abs(c[selected] - y[selected]))) if len(selected) >= 20 else None)
            improvement = 100 * (bm - cm) / bm if bm > 0 else None
            result["comparisons"][name] = {
                "baseline_mae": bm, "candidate_mae": cm, "mae_delta_native": bm - cm,
                "mae_improvement_pct": improvement, "baseline_p95": bp, "candidate_p95": cp,
                "quartile_mae_delta_native": quartiles,
                "descriptive_screen": bool(pairs >= 100 and pairs / scheduled >= .90 and
                     improvement is not None and improvement >= 5 and cp <= bp and
                     sum(v is not None and v > 0 for v in quartiles) >= 3)}
    result["baselines_identical_on_common_rows"] = bool(np.array_equal(b["persistence"][common], b["seasonal"][common]))
    result["all_baseline_descriptive_screen"] = all(v["descriptive_screen"] for v in result["comparisons"].values())
    return result


def audit_packet(root: Path, expected: str) -> tuple[dict, list[dict]]:
    custody = verify_tree(root, expected)
    protocol = read_json(root / "PROTOCOL.json")
    methods = protocol["methods"]
    require(methods == ["persistence", "seasonal", "median5", "damped_trend", "robust_blend"], "Unexpected method identities")
    index = read_json(root / "INDEX.json"); rows = []; identities = set()
    bound_files = read_json(root / "MANIFEST.json")["files"]
    require(isinstance(index, list) and 0 < len(index) <= 2000, "Invalid array index")
    for entry in index:
        name = entry["array_file"]
        require(name not in identities and name in bound_files, "Duplicate or unbound array")
        identities.add(name)
        # Hash-bound archives only; object arrays/pickle remain forbidden.
        with np.load(root / name, allow_pickle=False) as a:
            n = len(a["truth"])
            require(n <= 1_000_000 and a["predictions"].shape == (n, 5), "Invalid prediction matrix")
            issue = a["issue"]; target = a["target_index"]
            require(issue.shape == target.shape == (n,) and issue.dtype.kind in "iu" and target.dtype.kind in "iu", "Invalid target identity")
            require(bool(np.all(np.diff(issue) > 0)) and bool(np.all(target - issue == entry["horizon_steps"])), "Unordered or mismatched horizon")
            masks = {"all": np.ones(n, bool), "high_at_issue": a["high"], "ramp_at_issue": a["ramp"]}
            predictions = a["predictions"]
            for j, candidate_name in enumerate(methods[2:], 2):
                for slice_name, mask in masks.items():
                    row = audit_cell(a["truth"], predictions[:, j], {k: predictions[:, i] for i, k in enumerate(methods[:2])}, mask)
                    row.update(entry, candidate=candidate_name, slice=slice_name)
                    rows.append(row)
    require(verify_tree(root, expected) == custody, "Source changed during audit")
    summary = {"schema": "lumencore.denominator_common_mask_audit.v1", **custody,
        "arrays": len(index), "audit_cells": len(rows),
        "all_baseline_descriptive_screen_count": sum(r["all_baseline_descriptive_screen"] for r in rows),
        "conditional_90pct_but_scheduled_below_90pct_cells": sum(
            (r["common_over_observed"] or 0) >= .9 and (r["common_over_scheduled"] or 0) < .9 for r in rows),
        "independent_validation": False, "production_authorized": False,
        "policy_timing": "Post-hoc diagnostic designed after historical outcomes were examined; not preregistered.",
        "boundary": "Common-mask comparisons and explicit scheduled/observed denominators. No forecasts changed, no new observations or financial conversion. Reused cells are not independent trials."}
    return summary, rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "Refusing to overwrite outputs")
    require(not args.out.resolve().is_relative_to(args.packet.resolve()), "Output must be outside immutable packet")
    summary, rows = audit_packet(args.packet, args.expected_manifest_sha256)
    args.out.mkdir(parents=True)
    (args.out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    with (args.out / "CELLS.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2))
