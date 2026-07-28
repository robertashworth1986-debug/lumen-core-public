from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "lumencore_engine_commercialization_v1.json"
DEFAULT_JSON = ROOT / "dashboard" / "data" / "lumencore_engine_commercialization_audit.json"
DEFAULT_MD = ROOT / "docs" / "LUMENCORE_ENGINE_COMMERCIALIZATION_AUDIT_2026-07-27.md"

EVIDENCE_CLASSES = (
    "source",
    "entrypoint",
    "test",
    "sample",
    "documentation",
    "artifact",
    "public_surface",
)


def parse_utc(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--as-of-utc must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_record(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    exists = path.is_file()
    return {
        "path": relative_path,
        "exists": exists,
        "bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path) if exists else None,
    }


def observed_maturity(present: dict[str, bool]) -> str:
    evidence_backed = (
        present["source"]
        and present["entrypoint"]
        and present["test"]
        and present["documentation"]
        and present["artifact"]
        and present["public_surface"]
    )
    if evidence_backed:
        return "evidence_backed_candidate"
    runnable = present["source"] and present["entrypoint"] and present["documentation"]
    if runnable:
        return "runnable_candidate"
    if present["source"]:
        return "component_prototype"
    return "concept_only"


def commercial_posture(engine_id: str, maturity: str) -> str:
    if engine_id in {
        "lumengov_grant_factory",
        "lumen_infrastructure_sentinel",
        "lumascout",
        "lumacore_orchestrator",
    } and maturity in {"evidence_backed_candidate", "runnable_candidate"}:
        return "design_partner_ready"
    if maturity == "concept_only":
        return "concept_only"
    return "research_only"


def audit_engine(engine: dict[str, Any]) -> dict[str, Any]:
    evidence = engine.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError(f"{engine.get('id')}: evidence must be an object")

    audited: dict[str, list[dict[str, Any]]] = {}
    present: dict[str, bool] = {}
    missing_paths: list[str] = []

    for evidence_class in EVIDENCE_CLASSES:
        paths = evidence.get(evidence_class, [])
        if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
            raise ValueError(f"{engine.get('id')}: {evidence_class} must be a list of paths")
        records = [path_record(path) for path in paths]
        audited[evidence_class] = records
        present[evidence_class] = any(record["exists"] for record in records)
        missing_paths.extend(record["path"] for record in records if not record["exists"])

    maturity = observed_maturity(present)
    posture = commercial_posture(str(engine["id"]), maturity)
    present_count = sum(present.values())

    return {
        "id": engine["id"],
        "name": engine["name"],
        "safe_description": engine["safe_description"],
        "observed_maturity": maturity,
        "commercial_posture": posture,
        "evidence_classes_present": present_count,
        "evidence_classes_total": len(EVIDENCE_CLASSES),
        "present": present,
        "missing_paths": sorted(missing_paths),
        "payer": engine["payer"],
        "bounded_offer": engine["bounded_offer"],
        "revenue_route": engine["revenue_route"],
        "contract_or_grant_route": engine["contract_or_grant_route"],
        "acceptance_gate": engine["acceptance_gate"],
        "claim_boundary": engine["claim_boundary"],
        "next_build": engine["next_build"],
        "evidence": audited,
    }


def audit_supplemental_discovery(
    config: dict[str, Any], primary_engine_ids: set[str]
) -> dict[str, Any]:
    supplemental = config.get("supplemental_discovery")
    if not isinstance(supplemental, dict):
        raise ValueError("supplemental_discovery must be an object")

    records = supplemental.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("supplemental_discovery.records must be a non-empty list")

    required_fields = {
        "id",
        "name",
        "evidence_scope",
        "disposition",
        "maps_to",
        "verification",
        "evidence",
        "claim_boundary",
        "next_action",
    }
    allowed_dispositions = {
        "add_to_portfolio",
        "branch_candidate",
        "private_prototype",
        "map_to_existing",
        "supporting_material_only",
        "archive_only",
    }
    distinct_dispositions = {
        "add_to_portfolio",
        "branch_candidate",
        "private_prototype",
    }

    ids = [record.get("id") for record in records if isinstance(record, dict)]
    if len(ids) != len(records) or len(ids) != len(set(ids)):
        raise ValueError("Supplemental discovery ids must be unique strings")
    if primary_engine_ids.intersection(ids):
        raise ValueError("Supplemental discovery ids must not duplicate primary engine ids")

    audited: list[dict[str, Any]] = []
    for record in records:
        missing_fields = required_fields.difference(record)
        if missing_fields:
            raise ValueError(
                f"{record.get('id')}: missing supplemental fields {sorted(missing_fields)}"
            )
        if record["disposition"] not in allowed_dispositions:
            raise ValueError(f"{record['id']}: unsupported supplemental disposition")

        maps_to = record["maps_to"]
        if maps_to not in primary_engine_ids and maps_to not in {None, "multiple_existing_lanes"}:
            raise ValueError(f"{record['id']}: maps_to must reference a primary engine")

        evidence_paths = record["evidence"]
        if not isinstance(evidence_paths, list) or any(
            not isinstance(path, str) or Path(path).is_absolute() for path in evidence_paths
        ):
            raise ValueError(f"{record['id']}: evidence must contain relative repository paths")
        evidence = [path_record(path) for path in evidence_paths]
        if record["evidence_scope"] == "origin_main":
            if not evidence:
                raise ValueError(f"{record['id']}: origin_main records require evidence paths")
            missing = [item["path"] for item in evidence if not item["exists"]]
            if missing:
                raise ValueError(f"{record['id']}: origin_main evidence missing: {missing}")

        audited.append({**record, "evidence": evidence})

    distinct_count = sum(
        record["disposition"] in distinct_dispositions for record in audited
    )
    configured_distinct = supplemental.get("distinct_additions_count")
    if configured_distinct != distinct_count:
        raise ValueError(
            "supplemental_discovery.distinct_additions_count does not match dispositions"
        )

    combined_count = len(primary_engine_ids) + distinct_count
    if supplemental.get("combined_candidate_system_count") != combined_count:
        raise ValueError(
            "supplemental_discovery.combined_candidate_system_count is inconsistent"
        )

    return {
        "audited_at_utc": supplemental["audited_at_utc"],
        "scope_note": supplemental["scope_note"],
        "distinct_additions_count": distinct_count,
        "combined_candidate_system_count": combined_count,
        "disposition_counts": dict(
            sorted(Counter(record["disposition"] for record in audited).items())
        ),
        "evidence_scope_counts": dict(
            sorted(Counter(record["evidence_scope"] for record in audited).items())
        ),
        "records": audited,
    }


def build_payload(config: dict[str, Any], as_of_utc: str) -> dict[str, Any]:
    engines = config.get("engines")
    if not isinstance(engines, list) or len(engines) != 15:
        raise ValueError("Registry must define exactly 15 engines")

    ids = [engine.get("id") for engine in engines]
    if len(ids) != len(set(ids)):
        raise ValueError("Engine ids must be unique")

    supplemental = audit_supplemental_discovery(config, set(ids))
    audited = [audit_engine(engine) for engine in engines]
    maturity_counts = Counter(engine["observed_maturity"] for engine in audited)
    commercial_counts = Counter(engine["commercial_posture"] for engine in audited)

    priority_order = {
        "design_partner_ready": 0,
        "research_only": 1,
        "concept_only": 2,
    }
    ranked = sorted(
        audited,
        key=lambda engine: (
            priority_order[engine["commercial_posture"]],
            -engine["evidence_classes_present"],
            engine["name"].lower(),
        ),
    )

    return {
        "schema": "lumencore_engine_commercialization_audit_v1",
        "generated_at_utc": as_of_utc,
        "source_registry": DEFAULT_CONFIG.relative_to(ROOT).as_posix(),
        "source_note": config["source_note"],
        "boundaries": config["boundaries"],
        "summary": {
            "engine_count": len(audited),
            "maturity_counts": dict(sorted(maturity_counts.items())),
            "commercial_posture_counts": dict(sorted(commercial_counts.items())),
            "design_partner_ready_ids": [
                engine["id"] for engine in ranked if engine["commercial_posture"] == "design_partner_ready"
            ],
            "subscription_ready_count": 0,
            "subscription_ready_reason": (
                "No engine is labeled subscription-ready until tenant isolation, authentication, billing, "
                "support, data-rights, deployment health, and buyer acceptance are evidenced."
            ),
            "supplemental_distinct_additions": supplemental["distinct_additions_count"],
            "combined_candidate_system_count": supplemental[
                "combined_candidate_system_count"
            ],
        },
        "engines": ranked,
        "supplemental_discovery": supplemental,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    maturity = summary["maturity_counts"]
    commercial = summary["commercial_posture_counts"]

    lines = [
        "# LumenCore Engine Commercialization Audit",
        "",
        f"Generated at: `{payload['generated_at_utc']}`",
        "",
        "## Decision",
        "",
        "The founder email names 15 engines. Repository evidence supports a mixed portfolio, not 15 finished products.",
        "This audit separates implementation evidence from what can honestly be offered to a buyer.",
        "",
        f"- Engine names audited: `{summary['engine_count']}`",
        f"- Evidence-backed candidates: `{maturity.get('evidence_backed_candidate', 0)}`",
        f"- Runnable candidates: `{maturity.get('runnable_candidate', 0)}`",
        f"- Component prototypes: `{maturity.get('component_prototype', 0)}`",
        f"- Concept-only lanes: `{maturity.get('concept_only', 0)}`",
        f"- Design-partner-ready lanes: `{commercial.get('design_partner_ready', 0)}`",
        f"- Subscription-ready lanes: `{summary['subscription_ready_count']}`",
        f"- Distinct supplemental candidates after deduplication: `{summary['supplemental_distinct_additions']}`",
        f"- Named candidate systems after deduplication: `{summary['combined_candidate_system_count']}`",
        "",
        summary["subscription_ready_reason"],
        "",
        "## First Revenue Sequence",
        "",
        "1. LumenGov Grant Factory: sell a controlled 30-day workflow pilot.",
        "2. Lumen Infrastructure Sentinel: sell a bounded baseline and drift assessment.",
        "3. LumaCore Orchestrator: sell governed workflow integration after public gateway health is restored.",
        "4. LumaScout: sell a private forward-tracked discovery sprint after data-rights review.",
        "5. Keep trading, sports, hardware, XR, identity, energy, and world-model lanes in research or grant mode until their stated gates pass.",
        "",
        "## Supplemental Drive Discovery",
        "",
        payload["supplemental_discovery"]["scope_note"],
        "",
        "The scan found four distinct additions, but they are not four finished products: one is in "
        "`origin/main`, two are tested branch-only candidates, and one is a private synthetic prototype.",
        "Names that are older lineages, specializations, or supporting documents stay mapped into the "
        "existing 15 lanes instead of inflating the portfolio.",
        "",
        "| Candidate | Evidence scope | Disposition | Maps to | Verification |",
        "|---|---|---|---|---|",
    ]

    for record in payload["supplemental_discovery"]["records"]:
        maps_to = record["maps_to"] or "new candidate"
        verification = record["verification"].replace("|", "/")
        lines.append(
            f"| {record['name']} | `{record['evidence_scope']}` | "
            f"`{record['disposition']}` | `{maps_to}` | {verification} |"
        )

    lines.extend(
        [
        "",
        "## Portfolio Matrix",
        "",
        "| Engine | Repo maturity | Commercial posture | Evidence | Buyer-safe next offer |",
        "|---|---|---|---:|---|",
        ]
    )

    for engine in payload["engines"]:
        offer = engine["bounded_offer"].replace("|", "/")
        lines.append(
            f"| {engine['name']} | `{engine['observed_maturity']}` | "
            f"`{engine['commercial_posture']}` | "
            f"{engine['evidence_classes_present']}/{engine['evidence_classes_total']} | {offer} |"
        )

    lines.extend(
        [
            "",
            "## Engine Gates",
            "",
        ]
    )

    for engine in payload["engines"]:
        lines.extend(
            [
                f"### {engine['name']}",
                "",
                f"- Safe description: {engine['safe_description']}",
                f"- Payer: {engine['payer']}",
                f"- Revenue route: {engine['revenue_route']}",
                f"- Contract or grant route: {engine['contract_or_grant_route']}",
                f"- Acceptance gate: {engine['acceptance_gate']}",
                f"- Claim boundary: {engine['claim_boundary']}",
                f"- Next build: {engine['next_build']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Shared Productization Gate",
            "",
            "Before any lane is sold as a recurring software subscription, require:",
            "",
            "- healthy production deployment and rollback receipt;",
            "- tenant isolation, authentication, authorization, and audit logging;",
            "- billing and cancellation flow with no hidden autonomous spend;",
            "- source rights, privacy terms, retention rules, and customer data boundary;",
            "- support ownership, service levels, incident response, and backup recovery test;",
            "- buyer-defined baseline, metric, acceptance threshold, and limitation statement;",
            "- claim review that distinguishes local, replay, simulation, prospective, and external evidence.",
            "",
            "## Boundaries",
            "",
        ]
    )
    lines.extend(f"- {boundary}" for boundary in payload["boundaries"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the founder engine inventory and supplemental discovery."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    as_of_utc = args.as_of_utc
    if args.check and as_of_utc is None and args.json_out.exists():
        as_of_utc = read_json(args.json_out).get("generated_at_utc")

    payload = build_payload(read_json(args.config), parse_utc(as_of_utc))
    rendered_json = json.dumps(payload, indent=2) + "\n"
    rendered_md = render_markdown(payload)

    if args.check:
        mismatches = []
        if not args.json_out.exists() or args.json_out.read_text(encoding="utf-8") != rendered_json:
            mismatches.append(str(args.json_out))
        if not args.md_out.exists() or args.md_out.read_text(encoding="utf-8") != rendered_md:
            mismatches.append(str(args.md_out))
        if mismatches:
            raise SystemExit("Stale engine commercialization outputs: " + ", ".join(mismatches))
        return 0

    write_outputs(payload, args.json_out, args.md_out)
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
