from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "config" / "lumencore_story_value_policy_v1.json"
DEFAULT_OUTPUT = ROOT / "out" / "social" / "lumencore_story_value_engine_v1_20260716"
SUPPORTED_EXTENSIONS = {
    ".avi",
    ".heic",
    ".jpeg",
    ".jpg",
    ".json",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".png",
    ".webm",
    ".wmv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def discover_external_assets(inputs: Iterable[Path]) -> list[Path]:
    discovered: list[Path] = []
    for raw_path in inputs:
        path = raw_path.expanduser().resolve()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            discovered.append(path)
            continue
        if path.is_dir():
            discovered.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
            )
    return sorted(set(discovered), key=lambda value: str(value).lower())


def _default_metrics() -> dict[str, float]:
    return {
        "proof_binding": 0.0,
        "narrative_strength": 0.0,
        "visual_strength": 0.0,
        "conversion_alignment": 0.0,
        "rights_confidence": 0.0,
        "reusability": 0.0,
        "freshness": 0.0,
        "privacy_risk": 1.0,
        "unsupported_claim_risk": 1.0,
        "provenance_ambiguity": 1.0,
    }


def _normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(spec)
    metrics = _default_metrics()
    metrics.update({key: clamp(value) for key, value in spec.get("metrics", {}).items()})
    normalized["metrics"] = metrics
    normalized.setdefault("asset_id", "unclassified_asset")
    normalized.setdefault("content_role", "unclassified")
    normalized.setdefault("rights_status", "unknown")
    normalized.setdefault("negative_or_null_result", False)
    normalized.setdefault("public_label", normalized["asset_id"].replace("_", " ").title())
    return normalized


def score_asset(spec: dict[str, Any], profile: dict[str, Any]) -> tuple[float, str, list[str]]:
    metrics = spec["metrics"]
    positive = sum(clamp(metrics.get(name, 0.0)) * float(weight) for name, weight in profile["weights"].items())
    penalty = sum(clamp(metrics.get(name, 0.0)) * float(weight) for name, weight in profile["penalties"].items())
    score = round(clamp(positive - penalty) * 100.0, 2)

    gates = profile["hard_gates"]
    reasons: list[str] = []
    if spec["rights_status"] not in gates["allowed_rights_statuses"]:
        reasons.append("rights_status_not_allowed")
    if metrics["privacy_risk"] > float(gates["privacy_risk_max"]):
        reasons.append("privacy_risk_above_profile_limit")
    if metrics["unsupported_claim_risk"] > float(gates["unsupported_claim_risk_max"]):
        reasons.append("unsupported_claim_risk_above_profile_limit")
    if (
        spec["content_role"] == "proof_claim"
        and metrics["proof_binding"] < float(gates["proof_binding_min_for_proof_claim"])
    ):
        reasons.append("proof_claim_not_bound_to_required_evidence")

    if reasons:
        return score, "FREEZE_PUBLIC_SURFACE", reasons

    thresholds = profile["thresholds"]
    if score >= float(thresholds["feature_min"]):
        disposition = "FEATURE"
    elif score >= float(thresholds["support_min"]):
        disposition = "SUPPORT"
    elif score >= float(thresholds["hold_min"]):
        disposition = "HOLD"
    else:
        disposition = "FREEZE_LOW_VALUE"
        reasons.append("score_below_profile_hold_threshold")
    return score, disposition, reasons


def _select_canonical(paths: list[Path]) -> Path:
    return min(paths, key=lambda path: (0 if is_within(path, ROOT) else 1, len(str(path)), str(path).lower()))


def collect_asset_records(
    policy: dict[str, Any],
    profile_name: str,
    external_inputs: Iterable[Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if profile_name not in policy["profiles"]:
        raise ValueError(f"unknown profile: {profile_name}")
    profile = policy["profiles"][profile_name]
    candidates: list[tuple[Path, dict[str, Any]]] = []

    for raw_spec in policy.get("repo_assets", []):
        spec = _normalize_spec(raw_spec)
        path = (ROOT / raw_spec["path"]).resolve()
        if not path.is_file():
            continue
        candidates.append((path, spec))

    external_rules = {
        key.lower(): _normalize_spec(value)
        for key, value in policy.get("external_asset_rules_by_sha256", {}).items()
    }
    for path in discover_external_assets(external_inputs):
        digest = sha256(path)
        rule = external_rules.get(digest, _normalize_spec({"asset_id": f"unclassified_{digest[:12]}"}))
        candidates.append((path, rule))

    grouped: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path, spec in candidates:
        grouped.setdefault(sha256(path), []).append((path, spec))

    private_records: list[dict[str, Any]] = []
    public_records: list[dict[str, Any]] = []
    for digest in sorted(grouped):
        group = grouped[digest]
        paths = sorted({path for path, _ in group}, key=lambda path: str(path).lower())
        canonical = _select_canonical(paths)
        spec = next(spec for path, spec in group if path == canonical)
        score, disposition, reasons = score_asset(spec, profile)
        stat = canonical.stat()
        record = {
            "asset_id": spec["asset_id"],
            "sha256": digest,
            "bytes": stat.st_size,
            "canonical_name": canonical.name,
            "extension": canonical.suffix.lower(),
            "content_role": spec["content_role"],
            "public_label": spec["public_label"],
            "negative_or_null_result": bool(spec["negative_or_null_result"]),
            "rights_status": spec["rights_status"],
            "metrics": spec["metrics"],
            "score": score,
            "disposition": disposition,
            "disposition_reasons": reasons,
            "custody_copy_count": len(paths),
            "freeze_is_reversible": disposition.startswith("FREEZE"),
            "source_bytes_mutated": False,
        }
        private_record = dict(record)
        private_record["canonical_path"] = str(canonical)
        private_record["custody_paths"] = [str(path) for path in paths]
        private_records.append(private_record)
        public_records.append(record)
    return private_records, public_records


def build_chain(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    previous = "0" * 64
    chain: list[dict[str, str]] = []
    for record in sorted(records, key=lambda item: (item["asset_id"], item["sha256"])):
        record_hash = hashlib.sha256(canonical_json(record)).hexdigest()
        chain_hash = hashlib.sha256(f"{previous}:{record_hash}".encode("ascii")).hexdigest()
        chain.append({"asset_id": record["asset_id"], "record_sha256": record_hash, "chain_sha256": chain_hash})
        previous = chain_hash
    return chain


def public_summary(records: list[dict[str, Any]], profile_name: str, policy: dict[str, Any]) -> dict[str, Any]:
    chain = build_chain(records)
    disposition_counts: dict[str, int] = {}
    for record in records:
        disposition_counts[record["disposition"]] = disposition_counts.get(record["disposition"], 0) + 1
    return {
        "schema": "lumencore_story_value_public_manifest_v1",
        "generated_utc": utc_now(),
        "profile": profile_name,
        "profile_purpose": policy["profiles"][profile_name].get(
            "purpose", "Deterministic story and conversion triage."
        ),
        "interpretation_boundary": {
            "score_is_financial_forecast": False,
            "score_is_valuation": False,
            "score_is_expected_return": False,
            "score_is_story_and_conversion_triage": True,
            "freeze_deletes_or_moves_source": False,
        },
        "asset_count": len(records),
        "disposition_counts": disposition_counts,
        "assets": sorted(records, key=lambda item: (-item["score"], item["asset_id"])),
        "chain": chain,
        "terminal_chain_sha256": chain[-1]["chain_sha256"] if chain else "0" * 64,
    }


def _write_markdown(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# LumenCore Story Selection",
        "",
        f"- Profile: `{manifest['profile']}`",
        f"- Assets scored: `{manifest['asset_count']}`",
        f"- Terminal chain: `{manifest['terminal_chain_sha256']}`",
        "- Boundary: this is story and conversion triage, not a valuation or return forecast.",
        "- Freeze rule: no source file was moved, deleted, renamed, or rewritten.",
        "",
        "## Selected Story Assets",
        "",
        "| Disposition | Score | Asset | Role | Evidence note |",
        "|---|---:|---|---|---|",
    ]
    for asset in manifest["assets"]:
        note = "negative/null evidence retained" if asset["negative_or_null_result"] else asset["public_label"]
        lines.append(
            f"| {asset['disposition']} | {asset['score']:.2f} | {asset['asset_id']} | "
            f"{asset['content_role']} | {note} |"
        )
    lines.extend(
        [
            "",
            "## Film Spine",
            "",
            "1. Hook: What if the important proof is that an AI can refuse its own best-looking result?",
            "2. Human drive: a founder keeps asking for stronger tests, not prettier claims.",
            "3. The gauntlet: a positive diagnostic result meets the stricter reviewer protocol.",
            "4. The turn: every promotion gate closes and economic action remains disabled.",
            "5. The invitation: an independent reviewer receives the blind kit and tries to break it.",
            "",
            "## Public-Safe Conversation Motifs",
            "",
            "- \"We only claim facts.\"",
            "- \"I love integrity checks.\"",
            "- \"Can we do an independent result receipt yet?\"",
            "- \"Failure is data.\"",
            "",
            "The existing 32-second `Truth Over Hype` cut is the teaser. The longer documentary should add the human build story, notebook/equation custody, and the outside-review handoff without promoting unvalidated performance.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(
    output_dir: Path,
    private_records: list[dict[str, Any]],
    public_manifest: dict[str, Any],
    policy_path: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    private_payload = {
        "schema": "lumencore_story_value_private_manifest_v1",
        "generated_utc": utc_now(),
        "policy_path": str(policy_path.resolve()),
        "records": private_records,
        "non_destructive_rule": "No source file was moved, deleted, renamed, or rewritten.",
    }
    private_path = output_dir / "PRIVATE_ASSET_LEDGER.json"
    public_path = output_dir / "PUBLIC_STORY_VALUE_MANIFEST.json"
    selection_path = output_dir / "STORY_SELECTION.md"
    private_path.write_text(json.dumps(private_payload, indent=2) + "\n", encoding="utf-8")
    public_path.write_text(json.dumps(public_manifest, indent=2) + "\n", encoding="utf-8")
    _write_markdown(selection_path, public_manifest)

    checksummed = [private_path, public_path, selection_path]
    rows = [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in checksummed]
    receipt = {
        "schema": "lumencore_story_value_output_receipt_v1",
        "generated_utc": utc_now(),
        "profile": public_manifest["profile"],
        "terminal_chain_sha256": public_manifest["terminal_chain_sha256"],
        "source_mutation_performed": False,
        "artifacts": rows,
    }
    receipt_path = output_dir / "OUTPUT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank LumenCore media and proof assets without deleting sources.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--profile", default="public_documentary")
    parser.add_argument("--external", action="append", type=Path, default=[])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    private_records, public_records = collect_asset_records(policy, args.profile, args.external)
    manifest = public_summary(public_records, args.profile, policy)
    write_outputs(args.output_dir, private_records, manifest, args.policy)
    print(json.dumps({
        "output_dir": str(args.output_dir.resolve()),
        "asset_count": manifest["asset_count"],
        "disposition_counts": manifest["disposition_counts"],
        "terminal_chain_sha256": manifest["terminal_chain_sha256"],
        "source_mutation_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
