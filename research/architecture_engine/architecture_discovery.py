#!/usr/bin/env python3
"""LumenCore Architecture Discovery and Validation Engine.

Public-safe static analysis only. The engine inventories candidate architectures,
creates bounded validation plans, and emits checksummed evidence artifacts. It does
not execute discovered code, modify canonical source, change constants, contact
validators, or promote claims automatically.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

TEXT_EXTENSIONS = {
    ".py", ".ps1", ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".csv", ".js", ".ts", ".tsx", ".jsx", ".html",
}

IGNORE_DIRS = {
    ".git", ".github", ".venv", "venv", "env", "node_modules", "dist",
    "build", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "artifacts", "out", "output", "outputs", "results", "coverage", ".next",
    ".tox", "site-packages", "vendor", "third_party", "third-party", "_worktrees",
    "workspacestorage", "vscode_user_profile", "chat-session-resources",
    "vscode_extensions", "clean_data",
}

ENGINE_DIR = Path(__file__).resolve().parent

ARCHITECTURE_TERMS = {
    "architecture", "engine", "orchestrator", "controller", "control",
    "hybrid", "harmonic", "phase", "locking", "flow", "form", "echo",
    "luma", "lumen", "aether", "ether", "shell", "skin", "suit", "jet",
    "swarm", "dragon", "routing", "router", "optimizer", "optimization",
    "strategy", "model", "digital twin", "simulation", "replay", "evidence",
    "proof", "manifest", "checksum", "provenance", "validation", "consensus",
    "kuramoto", "mesh", "fabric", "resonance", "glyph", "cymatic",
}

EVIDENCE_TERMS = {
    "baseline", "comparator", "locked metric", "acceptance metric", "seed",
    "holdout", "replay", "simulation", "benchmark", "test", "pytest",
    "manifest", "sha256", "checksum", "hash", "result", "negative result",
    "failure", "confidence interval", "uncertainty", "measured", "synthetic",
}

REPRO_TERMS = {
    "argparse", "config", "requirements", "pyproject", "environment",
    "deterministic", "seed", "version", "commit", "manifest", "sha256",
    "docker", "workflow_dispatch", "pytest", "unittest", "main(",
}

CLAIM_RISK_PATTERNS = {
    "certification": r"\b(certified|certification|airworthy|flight[- ]ready)\b",
    "guarantee": r"\b(guaranteed|guarantee|zero[- ]risk|always wins?)\b",
    "field_validation": r"\b(field[- ]validated|proven in the field|realized savings)\b",
    "financial": r"\b(audited revenue|guaranteed roi|guaranteed profit)\b",
    "agency_endorsement": r"\b(approved by|endorsed by)\s+(darpa|doe|dod|nasa|lanl|ornl|epri)\b",
}

PATENT_SENSITIVE_TERMS = {
    "patent", "claim set", "inventor disclosure", "novel embodiment",
    "trade secret", "proprietary", "confidential", "priority date",
}

SAFETY_SENSITIVE_TERMS = {
    "weapon", "targeting", "payload delivery", "engagement logic", "pursuit",
    "evasion", "lethal", "munition", "attack", "intercept",
}

CATEGORY_RULES: Sequence[Tuple[str, Sequence[str]]] = (
    ("phase_control", ("phase", "kuramoto", "oscillator", "locking", "consensus")),
    ("routing_network", ("routing", "router", "path", "mesh", "network", "flowform")),
    ("evidence_provenance", ("evidence", "proof", "manifest", "checksum", "provenance", "replay")),
    ("optimization_ml", ("optimizer", "optimization", "machine learning", " ml ", "model", "ensemble")),
    ("market_analytics", ("trader", "trading", "market", "backtest", "portfolio", "signal")),
    ("digital_twin_simulation", ("digital twin", "simulation", "simulator", "synthetic", "forecast")),
    ("human_interface", ("gesture", "biometric", "human", "suit", "skin", "haptic", "identity")),
    ("opportunity_ops", ("grant", "funding", "sbir", "proposal", "outreach", "opportunity")),
)


@dataclass
class Candidate:
    root_alias: str
    relative_path: str
    extension: str
    sha256: str
    content_hash_status: str
    size_bytes: int
    modified_utc: str
    category: str
    architecture_terms: List[str]
    symbols: List[str]
    headings: List[str]
    executable_score: int
    evidence_score: int
    reproducibility_score: int
    validation_score: int
    disclosure_risk_score: int
    safety_sensitive: bool
    patent_sensitive: bool
    archive_or_backup: bool
    claim_risks: List[str]
    priority_score: float
    recommended_baselines: List[str]
    locked_metrics: List[str]
    proposed_experiments: List[str]
    claim_boundary: str
    scan_mode: str


def sha256_file(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_modified(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def safe_stat(path: Path) -> Optional[os.stat_result]:
    try:
        return path.stat()
    except OSError:
        return None


def ignore_directory(name: str) -> bool:
    lowered = name.lower()
    return lowered in IGNORE_DIRS or lowered.endswith(".worktrees")


def ignore_flattened_generated_file(path: Path) -> bool:
    lowered = path.name.lower()
    return any(
        marker in lowered
        for marker in (
            "site-packages",
            "node_modules",
            "workspacestorage",
            "chat-session-resources",
            "vscode_extensions",
        )
    )


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def iter_files(root: Path, max_files: int) -> Iterable[Path]:
    count = 0
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not ignore_directory(d)]
        for filename in filenames:
            path = Path(directory) / filename
            if ignore_flattened_generated_file(path):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            stat_result = safe_stat(path)
            if stat_result is None or stat_result.st_size > 2_000_000:
                continue
            yield path
            count += 1
            if count >= max_files:
                return


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def python_symbols(text: str) -> List[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    symbols: List[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(node.name)
    return symbols[:80]


def powershell_symbols(text: str) -> List[str]:
    return re.findall(r"(?im)^\s*function\s+([A-Za-z0-9_-]+)", text)[:80]


def markdown_headings(text: str) -> List[str]:
    return [m.strip() for m in re.findall(r"(?m)^#{1,4}\s+(.+)$", text)[:40]]


def count_hits(lowered: str, terms: Iterable[str]) -> Tuple[int, List[str]]:
    hits = sorted({term for term in terms if term in lowered})
    return len(hits), hits


def classify(lowered: str, path_lower: str) -> str:
    joined = f" {path_lower} {lowered[:100_000]} "
    best_name = "generic_architecture"
    best_score = 0
    for name, terms in CATEGORY_RULES:
        score = sum(1 for term in terms if term in joined)
        if score > best_score:
            best_name = name
            best_score = score
    return best_name


def validation_recipe(category: str) -> Tuple[List[str], List[str], List[str]]:
    recipes: Dict[str, Tuple[List[str], List[str], List[str]]] = {
        "phase_control": (
            ["uncoupled local control", "continuous phase coupling", "consensus control"],
            ["phase coherence", "frequency disagreement", "time to lock", "recovery time", "control effort"],
            ["coupling and heterogeneity sweep", "latency/noise/packet-loss sweep", "split/rejoin and disturbance recovery"],
        ),
        "routing_network": (
            ["shortest path", "static routing", "greedy routing"],
            ["path cost", "latency", "throughput", "failure recovery", "constraint violations"],
            ["topology and load sweep", "node/link failure sweep", "cost-versus-resilience Pareto analysis"],
        ),
        "evidence_provenance": (
            ["unsigned output", "timestamp-only record", "single-file checksum"],
            ["tamper detection rate", "manifest completeness", "reproduction success", "verification latency"],
            ["artifact mutation challenge", "dependency/version drift replay", "independent clean-room reproduction"],
        ),
        "optimization_ml": (
            ["naive heuristic", "linear/statistical baseline", "unoptimized model"],
            ["held-out performance", "calibration", "robustness", "compute cost", "drift sensitivity"],
            ["frozen train/validation/test split", "hyperparameter neighborhood sweep", "ablation and leakage audit"],
        ),
        "market_analytics": (
            ["buy-and-hold", "cash", "simple moving average"],
            ["out-of-sample return", "drawdown", "turnover", "cost sensitivity", "stability across periods"],
            ["walk-forward evaluation", "fees/slippage stress test", "survivorship and look-ahead leakage audit"],
        ),
        "digital_twin_simulation": (
            ["static model", "historical mean", "named physical/statistical comparator"],
            ["prediction error", "state divergence", "disturbance response", "uncertainty calibration"],
            ["parameter sensitivity sweep", "held-out disturbance replay", "model-versus-measured residual analysis"],
        ),
        "human_interface": (
            ["manual input", "standard UI", "non-adaptive interface"],
            ["latency", "error rate", "task completion", "user override rate", "privacy/safety violations"],
            ["non-medical usability simulation", "human-review gate test", "privacy and consent audit"],
        ),
        "opportunity_ops": (
            ["manual search", "keyword-only matching", "unranked opportunity list"],
            ["qualified-lead precision", "deadline recall", "false-positive rate", "submission completeness"],
            ["historical opportunity replay", "eligibility-rule audit", "human approval and claim-boundary test"],
        ),
        "generic_architecture": (
            ["current incumbent", "naive baseline", "no-op control"],
            ["primary task metric", "failure rate", "resource cost", "reproducibility"],
            ["deterministic baseline run", "parameter sensitivity sweep", "failure-envelope mapping"],
        ),
    }
    return recipes[category]


def score_candidate(
    path: Path,
    text: str,
    scan_mode: str,
    root_alias: str,
    root: Path,
) -> Candidate:
    stat_result = safe_stat(path)
    if stat_result is None:
        raise FileNotFoundError(path)
    lowered = text.lower()
    path_lower = safe_relative(path, root).lower()
    _, architecture_hits = count_hits(f"{path_lower} {lowered}", ARCHITECTURE_TERMS)
    evidence_count, _ = count_hits(lowered, EVIDENCE_TERMS)
    repro_count, _ = count_hits(lowered, REPRO_TERMS)

    symbols: List[str] = []
    if scan_mode == "content":
        if path.suffix.lower() == ".py":
            symbols = python_symbols(text)
        elif path.suffix.lower() == ".ps1":
            symbols = powershell_symbols(text)
    headings = markdown_headings(text) if scan_mode == "content" else []

    executable = 0
    if path.suffix.lower() in {".py", ".ps1", ".js", ".ts"}:
        executable += 2
    if symbols:
        executable += 2
    if "if __name__" in lowered or "param(" in lowered or "argparse" in lowered:
        executable += 1
    executable = min(5, executable)

    evidence = min(5, evidence_count // 2)
    reproducibility = min(5, repro_count // 2)
    validation = min(5, len(architecture_hits) // 2 + (1 if evidence >= 2 else 0))

    archive_or_backup = any(
        marker in path_lower for marker in ("archive/", "backup", ".bak", "old/", "deprecated")
    )
    claim_risks = [
        name for name, pattern in CLAIM_RISK_PATTERNS.items()
        if re.search(pattern, lowered, flags=re.IGNORECASE)
    ]
    patent_sensitive = any(term in lowered for term in PATENT_SENSITIVE_TERMS)
    safety_sensitive = any(term in lowered for term in SAFETY_SENSITIVE_TERMS)

    disclosure_risk = min(
        5,
        len(claim_risks)
        + (2 if patent_sensitive else 0)
        + (3 if safety_sensitive else 0)
        + (1 if archive_or_backup else 0),
    )

    category = classify(lowered, path_lower)
    baselines, metrics, experiments = validation_recipe(category)

    raw_priority = (
        3.0 * executable
        + 3.0 * evidence
        + 2.0 * reproducibility
        + 2.0 * validation
        - 2.5 * disclosure_risk
        - (3.0 if archive_or_backup else 0.0)
    )
    priority = max(0.0, min(100.0, raw_priority * 2.0))

    if safety_sensitive:
        boundary = (
            "Safety-sensitive content detected. Do not execute operational behavior; "
            "limit work to static review, benign simulation, safety analysis, and qualified oversight."
        )
    elif patent_sensitive:
        boundary = (
            "Potentially patent-sensitive content detected. Preserve hashes and metadata; "
            "route implementation details to a private inventor disclosure before public promotion."
        )
    else:
        boundary = (
            "Candidate architecture only. No performance, field-validation, certification, "
            "revenue, or agency-endorsement claim is supported by discovery alone."
        )

    return Candidate(
        root_alias=root_alias,
        relative_path=safe_relative(path, root),
        extension=path.suffix.lower(),
        sha256=(sha256_file(path) or "") if scan_mode == "content" else "",
        content_hash_status=(
            "computed" if scan_mode == "content" else "not_computed_metadata_only"
        ),
        size_bytes=stat_result.st_size,
        modified_utc=datetime.fromtimestamp(stat_result.st_mtime, timezone.utc).isoformat(),
        category=category,
        architecture_terms=architecture_hits[:30],
        symbols=symbols,
        headings=headings,
        executable_score=executable,
        evidence_score=evidence,
        reproducibility_score=reproducibility,
        validation_score=validation,
        disclosure_risk_score=disclosure_risk,
        safety_sensitive=safety_sensitive,
        patent_sensitive=patent_sensitive,
        archive_or_backup=archive_or_backup,
        claim_risks=claim_risks,
        priority_score=round(priority, 2),
        recommended_baselines=baselines,
        locked_metrics=metrics,
        proposed_experiments=experiments,
        claim_boundary=boundary,
        scan_mode=scan_mode,
    )


def scan_root(
    root: Path,
    root_alias: str,
    scan_mode: str,
    max_files: int,
) -> List[Candidate]:
    candidates: List[Candidate] = []
    for path in iter_files(root, max_files=max_files):
        if root_alias == "repo":
            try:
                path.resolve().relative_to(ENGINE_DIR)
                continue
            except ValueError:
                pass
        text = read_text(path) if scan_mode == "content" else path.name
        lowered = f"{safe_relative(path, root).lower()} {text.lower()}"
        if not any(term in lowered for term in ARCHITECTURE_TERMS):
            continue
        try:
            candidates.append(score_candidate(path, text, scan_mode, root_alias, root))
        except OSError:
            continue
    return candidates


def write_csv(path: Path, candidates: List[Candidate]) -> None:
    rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        row = asdict(candidate)
        for key, value in list(row.items()):
            if isinstance(value, list):
                row[key] = " | ".join(str(item) for item in value)
        rows.append(row)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_backlog(path: Path, candidates: List[Candidate], top_n: int) -> None:
    lines = [
        "# LumenCore Architecture Validation Backlog",
        "",
        "Discovery ranks what deserves controlled testing; it does not prove performance.",
        "",
    ]
    for index, candidate in enumerate(candidates[:top_n], start=1):
        source_hash = candidate.sha256 or "not computed (metadata-only)"
        lines.extend([
            f"## {index}. `{candidate.relative_path}`",
            "",
            f"- Root: `{candidate.root_alias}`",
            f"- Category: `{candidate.category}`",
            f"- Priority score: `{candidate.priority_score}`",
            f"- Source SHA-256: `{source_hash}`",
            f"- Scores: executable `{candidate.executable_score}/5`, evidence `{candidate.evidence_score}/5`, reproducibility `{candidate.reproducibility_score}/5`, validation `{candidate.validation_score}/5`, disclosure risk `{candidate.disclosure_risk_score}/5`",
            f"- Baselines: {', '.join(candidate.recommended_baselines)}",
            f"- Locked metrics: {', '.join(candidate.locked_metrics)}",
            f"- Proposed experiments: {', '.join(candidate.proposed_experiments)}",
            f"- Boundary: {candidate.claim_boundary}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_risk_register(path: Path, candidates: List[Candidate]) -> None:
    risky = [
        candidate for candidate in candidates
        if candidate.disclosure_risk_score > 0 or candidate.claim_risks
    ]
    lines = [
        "# Architecture Claim and Disclosure Risk Register",
        "",
        "This register is a triage aid, not a legal determination.",
        "",
    ]
    for candidate in risky:
        lines.extend([
            f"## `{candidate.relative_path}`",
            "",
            f"- Root: `{candidate.root_alias}`",
            f"- Risk score: `{candidate.disclosure_risk_score}/5`",
            f"- Patent-sensitive signal: `{candidate.patent_sensitive}`",
            f"- Safety-sensitive signal: `{candidate.safety_sensitive}`",
            f"- Claim-risk signals: {', '.join(candidate.claim_risks) or 'none'}",
            f"- Required gate: {candidate.claim_boundary}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def canonical_path_score(candidate: Candidate) -> int:
    path_lower = candidate.relative_path.lower()
    name = Path(candidate.relative_path).name.lower()
    score = 0
    if "lexicon" in name:
        score += 12
    if "constant" in name:
        score += 10
    if "master_context" in path_lower or "master context" in path_lower:
        score += 6
    if "equation_registry" in path_lower or "formula_registry" in path_lower:
        score += 6
    if candidate.root_alias == "repo":
        score += 3
    if candidate.archive_or_backup:
        score -= 8
    if any(
        marker in path_lower
        for marker in (
            ".sha256",
            ".zip",
            "mirror/",
            "packet-clean/",
            "runtime/",
            "vscode",
        )
    ):
        score -= 20
    return score


def write_canonical_path_candidates(path: Path, candidates: List[Candidate]) -> None:
    ranked = [candidate for candidate in candidates if canonical_path_score(candidate) > 0]
    ranked.sort(
        key=lambda item: (
            -canonical_path_score(item),
            -item.priority_score,
            item.root_alias,
            item.relative_path.lower(),
        )
    )
    lines = [
        "# Canonical Lexicon and Constants Path Candidates",
        "",
        "Path metadata is a selection aid only. No external file content was read, and no canonical path is selected automatically.",
        "",
    ]
    for index, candidate in enumerate(ranked[:50], start=1):
        lines.extend(
            [
                f"## {index}. `{candidate.relative_path}`",
                "",
                f"- Root: `{candidate.root_alias}`",
                f"- Scan mode: `{candidate.scan_mode}`",
                f"- Canonical-path score: `{canonical_path_score(candidate)}`",
                f"- Size bytes: `{candidate.size_bytes}`",
                f"- Modified UTC: `{candidate.modified_utc}`",
                f"- Archive/backup signal: `{candidate.archive_or_backup}`",
                "- Required next step: Robert selects the canonical file before any content scan or binding hash.",
                "",
            ]
        )
    if not ranked:
        lines.append("No path-name candidates were found.")
    path.write_text("\n".join(lines), encoding="utf-8")


def normalized_family_name(relative_path: str) -> str:
    stem = Path(relative_path).stem.lower()
    stem = re.sub(
        r"(?:^|[_ .-])(copy|final|draft|newest|new|old|backup|archive|deprecated)(?:[_ .-]|$)",
        "_",
        stem,
    )
    stem = re.sub(r"(?:^|[_ .-])v(?:ersion)?\d+(?:[_ .-]|$)", "_", stem)
    stem = re.sub(r"(?:^|[_ .-])\d{8}(?:t\d{6}z?)?(?:[_ .-]|$)", "_", stem)
    stem = re.sub(r"\s*\(\d+\)$", "", stem)
    return re.sub(r"[^a-z0-9]+", "", stem)


def write_duplicate_conflict_register(path: Path, candidates: List[Candidate]) -> None:
    exact: Dict[str, List[Candidate]] = {}
    probable: Dict[Tuple[str, str, int], List[Candidate]] = {}
    families: Dict[Tuple[str, str], List[Candidate]] = {}
    for candidate in candidates:
        if candidate.sha256:
            exact.setdefault(candidate.sha256, []).append(candidate)
        family = normalized_family_name(candidate.relative_path)
        if family:
            probable.setdefault((family, candidate.extension, candidate.size_bytes), []).append(candidate)
            families.setdefault((family, candidate.extension), []).append(candidate)

    exact_groups = [group for group in exact.values() if len(group) > 1]
    probable_groups = [
        group
        for group in probable.values()
        if len(group) > 1 and any(candidate.scan_mode == "metadata" for candidate in group)
    ]
    version_marker = re.compile(
        r"(?i)(?:\bv\d+\b|copy|final|draft|newest|old|backup|archive|deprecated|\(\d+\)|\d{8})"
    )
    conflict_groups = [
        group
        for group in families.values()
        if len(group) > 1
        and len({candidate.relative_path.lower() for candidate in group}) > 1
        and any(version_marker.search(candidate.relative_path) for candidate in group)
    ]
    for groups in (exact_groups, probable_groups, conflict_groups):
        groups.sort(
            key=lambda group: (
                -max(candidate.priority_score for candidate in group),
                -len(group),
                group[0].relative_path.lower(),
            )
        )
    archived = sorted(
        (candidate for candidate in candidates if candidate.archive_or_backup),
        key=lambda item: (-item.priority_score, item.root_alias, item.relative_path.lower()),
    )

    lines = [
        "# Duplicate, Archive, and Conflict Register",
        "",
        "Exact duplicate means matching public content SHA-256. Probable duplicate means metadata-only normalized name, extension, and size match; it is not content proof. Conflict families require human canonical selection.",
        "",
        f"- Exact public duplicate groups: `{len(exact_groups)}`",
        f"- Probable metadata duplicate groups: `{len(probable_groups)}`",
        f"- Version/conflict families: `{len(conflict_groups)}`",
        f"- Archive/backup candidates: `{len(archived)}`",
        "",
        "## Highest-Priority Exact Public Duplicates",
        "",
    ]
    for group in exact_groups[:30]:
        lines.append(f"- SHA-256 `{group[0].sha256}`")
        for candidate in group[:12]:
            lines.append(f"  - `{candidate.root_alias}:{candidate.relative_path}`")
    lines.extend(["", "## Highest-Priority Probable Metadata Duplicates", ""])
    for group in probable_groups[:30]:
        lines.append(
            f"- Probable family `{normalized_family_name(group[0].relative_path)}`; size `{group[0].size_bytes}` bytes"
        )
        for candidate in group[:12]:
            lines.append(f"  - `{candidate.root_alias}:{candidate.relative_path}`")
    lines.extend(["", "## Highest-Priority Version or Conflict Families", ""])
    for group in conflict_groups[:30]:
        lines.append(f"- Family `{normalized_family_name(group[0].relative_path)}`")
        for candidate in group[:12]:
            lines.append(f"  - `{candidate.root_alias}:{candidate.relative_path}`")
    lines.extend(["", "## Highest-Priority Archive or Backup Candidates", ""])
    for candidate in archived[:50]:
        lines.append(
            f"- `{candidate.root_alias}:{candidate.relative_path}`; priority `{candidate.priority_score}`"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_proof_capsules(output: Path, candidates: List[Candidate], top_n: int) -> None:
    capsule_dir = output / "proof_capsule_stubs"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    for index, candidate in enumerate(candidates[:top_n], start=1):
        capsule = {
            "status": "unexecuted_validation_plan",
            "candidate_rank": index,
            "architecture_source": {
                "root_alias": candidate.root_alias,
                "relative_path": candidate.relative_path,
                "sha256": candidate.sha256,
                "content_hash_status": candidate.content_hash_status,
            },
            "category": candidate.category,
            "hypothesis": "To be written as a bounded, falsifiable statement before execution.",
            "baseline": candidate.recommended_baselines,
            "locked_metrics": candidate.locked_metrics,
            "proposed_experiments": candidate.proposed_experiments,
            "dataset_or_simulator": None,
            "configuration_hash": None,
            "seed_manifest": [],
            "results": {},
            "negative_results": [],
            "failure_envelope": {},
            "claim_boundary": candidate.claim_boundary,
            "external_review": None,
            "next_gate": "human review and patent/disclosure check",
        }
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate.relative_path)[:120]
        (capsule_dir / f"{index:02d}_{safe_name}.json").write_text(
            json.dumps(capsule, indent=2, sort_keys=True), encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--additional-root", action="append", type=Path, default=[])
    parser.add_argument("--external-content-scan", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--constants", type=Path)
    parser.add_argument("--lexicon", type=Path)
    parser.add_argument("--max-files", type=int, default=20_000)
    parser.add_argument("--top-candidates", type=int, default=30)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    repo_root = args.repo_root.resolve()
    candidates = scan_root(repo_root, "repo", "content", args.max_files)

    external_mode = "content" if args.external_content_scan else "metadata"
    external_roots: List[Dict[str, Any]] = []
    for index, root in enumerate(args.additional_root, start=1):
        if not root.exists() or not root.is_dir():
            continue
        alias = f"authorized_external_{index}"
        candidates.extend(scan_root(root.resolve(), alias, external_mode, args.max_files))
        external_roots.append({"alias": alias, "scan_mode": external_mode})

    candidates.sort(key=lambda item: item.priority_score, reverse=True)

    inventory = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "claim_level": "static discovery and validation planning only",
        "candidate_count": len(candidates),
        "external_roots": external_roots,
        "constants_sha256": sha256_file(args.constants),
        "lexicon_sha256": sha256_file(args.lexicon),
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    inventory_path = args.output / "architecture_inventory.json"
    inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_csv(args.output / "architecture_inventory.csv", candidates)
    write_backlog(args.output / "validation_backlog.md", candidates, args.top_candidates)
    write_risk_register(args.output / "claim_risk_register.md", candidates)
    write_canonical_path_candidates(args.output / "canonical_path_candidates.md", candidates)
    write_duplicate_conflict_register(args.output / "duplicate_conflict_register.md", candidates)
    write_proof_capsules(args.output, candidates, min(args.top_candidates, 15))

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine_sha256": sha256_file(Path(__file__).resolve()),
        "repo_root_alias": "repo",
        "candidate_count": len(candidates),
        "constants_sha256": sha256_file(args.constants),
        "lexicon_sha256": sha256_file(args.lexicon),
        "outputs": {},
        "boundaries": [
            "No discovered code was executed.",
            "No canonical source or constants were modified.",
            "No claim was promoted automatically.",
            "External roots defaulted to metadata-only scanning unless explicitly enabled.",
        ],
    }
    for path in sorted(args.output.rglob("*")):
        if path.is_file() and path.name != "run_manifest.json":
            manifest["outputs"][path.relative_to(args.output).as_posix()] = sha256_file(path)
    (args.output / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(json.dumps({
        "candidate_count": len(candidates),
        "top_candidates": [
            {
                "path": candidate.relative_path,
                "category": candidate.category,
                "priority_score": candidate.priority_score,
                "risk_score": candidate.disclosure_risk_score,
            }
            for candidate in candidates[:10]
        ],
        "output": str(args.output.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
