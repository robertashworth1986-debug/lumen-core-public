#!/usr/bin/env python3
"""
LumenCore Architecture Discovery and Validation Engine.

Read-only by design:
- scans one or more roots;
- discovers known architecture names and evidence-bearing artifacts;
- ranks validation readiness;
- proposes bounded experiments and existing-module hybrid tests;
- never modifies source architectures, constants, lexicons, or user data;
- never declares external validation from internal evidence.

Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple


TEXT_EXTENSIONS = {
    ".py", ".ps1", ".psm1", ".sh", ".bash", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".cs", ".cpp", ".c", ".h", ".hpp", ".rs", ".go", ".rb",
    ".md", ".rst", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".csv", ".html", ".htm", ".css", ".sql",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__",
    "node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", "site-packages", ".idea", ".vscode",
}
RISK_PHRASES = (
    "certified aircraft", "certified suit", "field-validated savings",
    "guaranteed roi", "guaranteed performance", "agency endorsement",
    "autonomous physical control", "medical diagnosis", "weapons capability",
    "flight-ready", "field-ready dod", "operational deployment",
    "production customer savings", "audited revenue",
)
BOUNDARY_MARKERS = (
    "not ", "no ", "avoid", "forbidden", "do not", "does not", "doesn't",
    "excluded", "without", "unless", "cannot claim", "not yet",
)
EVIDENCE_MARKERS: Mapping[str, Tuple[str, ...]] = {
    "source": ("source", "dataset", "input data", "sensor data", "stream"),
    "baseline": ("baseline", "comparator", "control group", "control-only"),
    "metric": ("locked metric", "pre-registered metric", "acceptance metric", "scorecard"),
    "manifest": ("manifest", "sha-256", "sha256", "checksum", "content hash"),
    "negative_results": ("negative result", "failure envelope", "failed run", "failure mode"),
    "limitations": ("limitation", "claim boundary", "does not prove", "simulation-only", "simulation only"),
    "seeds": ("random seed", "validation seed", "seed manifest", "disjoint seed"),
    "reproducibility": ("reproducible", "deterministic", "reproduce", "clean checkout"),
    "external_review": ("external technical review", "outside validation", "buyer-authorized"),
}
PATENT_MARKERS = (
    "patent", "patentable", "proprietary", "private inventor",
    "invention disclosure", "trade secret", "claim set",
)


@dataclass
class FileHit:
    path: str
    root: str
    size_bytes: int
    sha256: Optional[str]
    categories: List[str]
    marker_hits: Dict[str, int]
    risk_hits: List[str]
    bounded_risk_hits: List[str]
    patent_hits: List[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def line_is_bounded(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in BOUNDARY_MARKERS)


def iter_files(roots: Sequence[Path], max_file_bytes: int) -> Iterator[Tuple[Path, Path]]:
    seen: set[Path] = set()
    for root in roots:
        try:
            resolved_root = root.expanduser().resolve()
        except OSError:
            continue
        if not resolved_root.exists() or not resolved_root.is_dir():
            continue
        for current, dirs, files in os.walk(resolved_root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".git")]
            current_path = Path(current)
            for name in files:
                path = current_path / name
                if path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                try:
                    if path.stat().st_size > max_file_bytes:
                        continue
                    resolved = path.resolve()
                except OSError:
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield resolved_root, resolved


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def classify_path(path: Path) -> List[str]:
    lower_parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    categories: List[str] = []
    if path.suffix.lower() in {".py", ".ps1", ".psm1", ".sh", ".js", ".ts", ".cpp", ".c", ".rs", ".go"}:
        categories.append("code")
    if any("test" in part for part in lower_parts) or name.startswith("test_"):
        categories.append("test")
    if any(token in lower_parts for token in ("docs", "doc", "documentation")) or path.suffix.lower() in {".md", ".rst"}:
        categories.append("documentation")
    if any(token in lower_parts for token in ("artifacts", "artifact", "results", "result", "evidence", "data", "out")):
        categories.append("evidence_artifact")
    if "benchmark" in name or "validation" in name or "replay" in name:
        categories.append("benchmark_or_validation")
    if "manifest" in name or "checksum" in name or "hash" in name:
        categories.append("manifest")
    if ".github" in lower_parts or "workflow" in lower_parts:
        categories.append("ci")
    return sorted(set(categories))


def architecture_matches(text: str, aliases: Sequence[str]) -> bool:
    lower = text.lower()
    return any(alias.lower() in lower for alias in aliases if alias.strip())


def analyze_file(root: Path, path: Path, text: str, hash_matches: bool) -> FileHit:
    lines = text.splitlines()
    norm = normalized(text)
    marker_hits = {
        marker: sum(norm.count(term) for term in terms)
        for marker, terms in EVIDENCE_MARKERS.items()
    }
    risk_hits: List[str] = []
    bounded_risk_hits: List[str] = []
    for phrase in RISK_PHRASES:
        for line in lines:
            if phrase in line.lower():
                if line_is_bounded(line):
                    bounded_risk_hits.append(phrase)
                else:
                    risk_hits.append(phrase)
    patent_hits = [marker for marker in PATENT_MARKERS if marker in norm]
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    return FileHit(
        path=str(relative).replace("\\", "/"),
        root=str(root),
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path) if hash_matches else None,
        categories=classify_path(relative),
        marker_hits={k: v for k, v in marker_hits.items() if v},
        risk_hits=sorted(set(risk_hits)),
        bounded_risk_hits=sorted(set(bounded_risk_hits)),
        patent_hits=sorted(set(patent_hits)),
    )


def score_architecture(hits: Sequence[FileHit]) -> Dict[str, Any]:
    categories = {cat for hit in hits for cat in hit.categories}
    marker_totals: Dict[str, int] = defaultdict(int)
    for hit in hits:
        for marker, count in hit.marker_hits.items():
            marker_totals[marker] += count

    score = 0
    components: Dict[str, int] = {}
    weights = {
        "code": 12,
        "test": 14,
        "documentation": 5,
        "evidence_artifact": 10,
        "benchmark_or_validation": 12,
        "manifest": 10,
        "ci": 5,
    }
    for category, weight in weights.items():
        if category in categories:
            components[category] = weight
            score += weight

    marker_weights = {
        "source": 5,
        "baseline": 8,
        "metric": 8,
        "manifest": 8,
        "negative_results": 7,
        "limitations": 6,
        "seeds": 5,
        "reproducibility": 6,
        "external_review": 0,
    }
    for marker, weight in marker_weights.items():
        if marker_totals.get(marker, 0):
            components[f"marker:{marker}"] = weight
            score += weight

    score = min(score, 100)
    if score < 20:
        readiness = "conceptual"
    elif score < 40:
        readiness = "model_ready"
    elif score < 60:
        readiness = "simulation_candidate"
    elif score < 80:
        readiness = "reproducibility_candidate"
    else:
        readiness = "external_review_candidate"

    unbounded_risks = sorted({r for hit in hits for r in hit.risk_hits})
    bounded_risks = sorted({r for hit in hits for r in hit.bounded_risk_hits})
    patent_markers = sorted({p for hit in hits for p in hit.patent_hits})
    if unbounded_risks:
        claim_risk = "high"
    elif bounded_risks:
        claim_risk = "controlled"
    else:
        claim_risk = "unknown"

    return {
        "score": score,
        "readiness": readiness,
        "score_components": components,
        "categories": sorted(categories),
        "marker_totals": dict(sorted(marker_totals.items())),
        "claim_risk": claim_risk,
        "unbounded_risk_phrases": unbounded_risks,
        "bounded_risk_phrases": bounded_risks,
        "patent_markers": patent_markers,
    }


def next_experiments(record: Mapping[str, Any]) -> List[Dict[str, str]]:
    markers = record["validation"]["marker_totals"]
    categories = set(record["validation"]["categories"])
    queue: List[Dict[str, str]] = []

    def add(gate: str, action: str, reason: str) -> None:
        queue.append({"gate": gate, "action": action, "reason": reason})

    if "code" not in categories:
        add("implementation", "Build the smallest executable reference model.", "No executable code was detected.")
    if "test" not in categories:
        add("tests", "Add deterministic unit and schema tests.", "No test artifact was detected.")
    if not markers.get("source"):
        add("source", "Name and freeze the source, dataset, simulator, or synthetic generator.", "The evidence source is not explicit.")
    if not markers.get("baseline"):
        add("baseline", "Select a named comparator before tuning.", "No baseline/comparator marker was detected.")
    if not markers.get("metric"):
        add("metric", "Pre-register success, failure, and safety metrics.", "No locked acceptance metric was detected.")
    if not markers.get("seeds"):
        add("validation_split", "Freeze development and validation seeds or disjoint windows.", "No seed/window separation marker was detected.")
    if not markers.get("negative_results"):
        add("failure_capture", "Retain failed runs and construct a failure envelope.", "Negative-result capture is missing.")
    if not markers.get("manifest") or "manifest" not in categories:
        add("manifest", "Generate SHA-256 manifests for inputs, code, configuration, and outputs.", "The evidence chain is incomplete.")
    if not markers.get("limitations"):
        add("claim_boundary", "Write what the result proves and does not prove.", "Limitations are not explicit.")
    if record["validation"]["claim_risk"] == "high":
        add("claim_cleanup", "Quarantine or rewrite unbounded performance language before publication.", "Unbounded high-risk phrases were detected.")
    if record.get("patent_sensitive") or record["validation"]["patent_markers"]:
        add("ip_review", "Route implementation-specific innovation through a private inventor disclosure before public release.", "Potential patent-sensitive material was detected.")
    if not queue and record["validation"]["readiness"] == "external_review_candidate":
        add("outside_validation", "Prepare a bounded validator packet with frozen artifacts and no endorsement request.", "Internal reproducibility gates appear substantially covered.")
    return queue


def build_hybrid_candidates(records: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {record["id"]: record for record in records if record["status"] != "unseen"}
    templates = [
        ("flowform", "echolock", "phase-aware geometry routing", "Compare geometry-only, phase-only, and combined control under identical disturbances."),
        ("etherframe", "lumencore", "constraint-carrying proof orchestration", "Test whether explicit evidence constraints reduce invalid promotion decisions."),
        ("echoform", "aetherreach", "identity-consistent human-in-the-loop interface", "Measure state continuity, operator correction rate, and uncertainty calibration."),
        ("lumajet", "qmpl", "simulation-only coordinated formation and routing", "Compare fixed geometry, continuous phase coupling, and quantized phase coupling using modeled proxies."),
        ("lumasuit_lumaskin", "echoform", "non-actuating state-aware digital twin", "Measure state estimation and risk-score consistency on synthetic or approved bench data."),
        ("harbor_sentinel", "nv065", "source-quality-gated adaptive sensor tasking", "Measure tasking utility and false confidence under missing, delayed, or inconsistent observations."),
        ("hybrid_echo_routing", "dice", "evidence-carrying distributed routing", "Measure safe completion, communication cost, and failure behavior under compromise and monitor shift."),
    ]
    candidates: List[Dict[str, Any]] = []
    for left, right, label, experiment in templates:
        if left not in by_id or right not in by_id:
            continue
        left_record, right_record = by_id[left], by_id[right]
        patent_sensitive = bool(left_record.get("patent_sensitive") or right_record.get("patent_sensitive"))
        candidates.append({
            "left": left,
            "right": right,
            "working_label": label,
            "status": "private_review_first" if patent_sensitive else "experiment_candidate",
            "locked_experiment": experiment,
            "required_baselines": [left, right, "uncoupled_or_naive_control"],
            "promotion_rule": "No public performance claim until the hybrid beats both component baselines on pre-registered validation conditions and retains negative results.",
            "claim_boundary": "Research candidate only; no external validation, universal superiority, field deployment, certification, or agency endorsement.",
        })
    return candidates


def scan(roots: Sequence[Path], seed: Mapping[str, Any], max_file_bytes: int, hash_matches: bool) -> Dict[str, Any]:
    files: List[Tuple[Path, Path, str]] = []
    for root, path in iter_files(roots, max_file_bytes):
        text = read_text(path)
        if text is not None:
            files.append((root, path, text))

    records: List[Dict[str, Any]] = []
    for architecture in seed["architectures"]:
        aliases = architecture.get("aliases", [architecture["name"]])
        hits: List[FileHit] = []
        for root, path, text in files:
            searchable = f"{path.name}\n{text}"
            if architecture_matches(searchable, aliases):
                hits.append(analyze_file(root, path, text, hash_matches))
        validation = score_architecture(hits)
        record = {
            **architecture,
            "status": "detected" if hits else "unseen",
            "matched_file_count": len(hits),
            "matched_files": [asdict(hit) for hit in sorted(hits, key=lambda h: (h.root, h.path))],
            "validation": validation,
        }
        record["next_experiments"] = next_experiments(record)
        records.append(record)

    records.sort(key=lambda r: (-r["validation"]["score"], r["name"].lower()))
    return {
        "schema_version": "1.0",
        "generated_utc": utc_now(),
        "roots": [str(path.expanduser()) for path in roots],
        "files_scanned": len(files),
        "rules": {
            "read_only": True,
            "no_external_validation_inference": True,
            "no_source_mutation": True,
            "no_constants_or_lexicon_mutation": True,
            "negative_results_required": True,
            "patent_sensitive_publication_blocked": True,
        },
        "architectures": records,
        "hybrid_candidates": build_hybrid_candidates(records),
    }


def render_markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# LumenCore Architecture Validation Registry", "",
        f"Generated: `{result['generated_utc']}`  ",
        f"Files scanned: `{result['files_scanned']}`", "",
        "> Internal evidence never equals external validation. The engine is read-only and does not alter canonical lexicons, constants, source architectures, or private inventor disclosures.", "",
        "## Ranked architecture lanes", "",
        "| Score | Architecture | Status | Readiness | Claim risk | Files | Next gate |",
        "|---:|---|---|---|---|---:|---|",
    ]
    for record in result["architectures"]:
        next_gate = record["next_experiments"][0]["gate"] if record["next_experiments"] else "outside_validation"
        lines.append(
            f"| {record['validation']['score']} | {record['name']} | {record['status']} | "
            f"{record['validation']['readiness']} | {record['validation']['claim_risk']} | "
            f"{record['matched_file_count']} | {next_gate} |"
        )
    lines += ["", "## Experiment queue", ""]
    for record in result["architectures"]:
        if record["status"] == "unseen":
            continue
        lines.append(f"### {record['name']}")
        for item in record["next_experiments"]:
            lines.append(f"- **{item['gate']}** — {item['action']} ({item['reason']})")
        if not record["next_experiments"]:
            lines.append("- No internal gap inferred; prepare a bounded outside-review packet.")
        lines.append("")
    lines += ["## Existing-module hybrid candidates", ""]
    for candidate in result["hybrid_candidates"]:
        lines += [
            f"### {candidate['working_label']}",
            f"- Components: `{candidate['left']}` + `{candidate['right']}`",
            f"- Status: `{candidate['status']}`",
            f"- Test: {candidate['locked_experiment']}",
            f"- Promotion rule: {candidate['promotion_rule']}", "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(output: Path, result: Mapping[str, Any], seed_path: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    registry_json = output / "architecture_registry.json"
    registry_md = output / "architecture_registry.md"
    experiment_json = output / "experiment_queue.json"
    hybrid_json = output / "hybrid_candidate_queue.json"
    registry_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    registry_md.write_text(render_markdown(result), encoding="utf-8")
    experiments = [
        {
            "architecture_id": record["id"],
            "architecture": record["name"],
            "score": record["validation"]["score"],
            "readiness": record["validation"]["readiness"],
            "next_experiments": record["next_experiments"],
        }
        for record in result["architectures"] if record["status"] == "detected"
    ]
    experiment_json.write_text(json.dumps(experiments, indent=2, sort_keys=True), encoding="utf-8")
    hybrid_json.write_text(json.dumps(result["hybrid_candidates"], indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "generated_utc": utc_now(),
        "engine_path": str(Path(__file__).resolve()),
        "engine_sha256": sha256_file(Path(__file__).resolve()),
        "seed_path": str(seed_path.resolve()),
        "seed_sha256": sha256_file(seed_path),
        "outputs": {},
    }
    for path in (registry_json, registry_md, experiment_json, hybrid_json):
        manifest["outputs"][path.name] = sha256_file(path)
    (output / "scan_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--extra-root", type=Path, action="append", default=[])
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    parser.add_argument("--hash-matches", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    seed = json.loads(args.seed.read_text(encoding="utf-8"))
    roots = [args.repo_root, *args.extra_root]
    result = scan(roots, seed, args.max_file_bytes, args.hash_matches)
    write_outputs(args.output, result, args.seed)
    print(json.dumps({
        "generated_utc": result["generated_utc"],
        "files_scanned": result["files_scanned"],
        "detected_architectures": sum(1 for r in result["architectures"] if r["status"] == "detected"),
        "external_review_candidates": sum(1 for r in result["architectures"] if r["validation"]["readiness"] == "external_review_candidate"),
        "hybrid_candidates": len(result["hybrid_candidates"]),
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
