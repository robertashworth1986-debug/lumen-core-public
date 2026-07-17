from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "config" / "founder_lexicon_v1.json"
KEY_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
VERIFIED_STATES = {"verified_current_repo", "verified_pr_history"}
PUBLIC_STATES = {
    "public_safe",
    "research_only",
    "concept_or_prototype",
    "simulation_only",
    "hold",
    "private",
}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    term_key: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.term_key:
            payload["term_key"] = self.term_key
        return payload


class RegistryError(ValueError):
    """Raised when the registry cannot be parsed as an object."""


def load_registry(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"registry is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegistryError("registry root must be an object")
    return payload


def _required_text(
    obj: Mapping[str, Any],
    field: str,
    findings: list[Finding],
    *,
    term_key: str | None = None,
) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        findings.append(
            Finding("error", "missing_text", f"{field} must be non-empty text", term_key)
        )
        return ""
    return value.strip()


def _validate_source(
    source: Any,
    *,
    index: int,
    term_key: str,
    root: Path | None,
    findings: list[Finding],
) -> None:
    if not isinstance(source, dict):
        findings.append(
            Finding(
                "error",
                "invalid_source",
                f"sources[{index}] must be an object",
                term_key,
            )
        )
        return

    source_type = _required_text(source, "type", findings, term_key=term_key)
    locator = _required_text(source, "locator", findings, term_key=term_key)
    if source_type == "repo_path" and locator and root is not None:
        target = (root / locator).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError:
            findings.append(
                Finding(
                    "error",
                    "source_path_escape",
                    f"repo source escapes root: {locator}",
                    term_key,
                )
            )
        else:
            if not target.exists():
                findings.append(
                    Finding(
                        "error",
                        "missing_repo_source",
                        f"repo source does not exist: {locator}",
                        term_key,
                    )
                )


def validate_registry(
    payload: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> list[Finding]:
    findings: list[Finding] = []

    schema = _required_text(payload, "schema", findings)
    if schema and schema != "lumencore_founder_lexicon_v1":
        findings.append(
            Finding("error", "schema_mismatch", f"unexpected schema: {schema}")
        )

    _required_text(payload, "owner", findings)
    boundary = _required_text(payload, "boundary", findings)
    if boundary and "does not establish" not in boundary.lower():
        findings.append(
            Finding(
                "error",
                "boundary_incomplete",
                "boundary must explicitly state what the registry does not establish",
            )
        )

    rules = payload.get("publication_rules")
    if not isinstance(rules, dict):
        findings.append(
            Finding("error", "missing_publication_rules", "publication_rules must be an object")
        )
    else:
        for field in (
            "raw_private_chats_public",
            "raw_private_notebooks_public",
            "credentials_or_private_portal_records_public",
            "founder_origin_assertion_requires_source",
            "pending_terms_may_be_promoted",
        ):
            if field not in rules or not isinstance(rules[field], bool):
                findings.append(
                    Finding(
                        "error",
                        "invalid_publication_rule",
                        f"publication_rules.{field} must be boolean",
                    )
                )
        for forbidden_true in (
            "raw_private_chats_public",
            "raw_private_notebooks_public",
            "credentials_or_private_portal_records_public",
            "pending_terms_may_be_promoted",
        ):
            if rules.get(forbidden_true) is True:
                findings.append(
                    Finding(
                        "error",
                        "unsafe_publication_rule",
                        f"publication_rules.{forbidden_true} must remain false",
                    )
                )

    terms = payload.get("terms")
    if not isinstance(terms, list) or not terms:
        findings.append(Finding("error", "missing_terms", "terms must be a non-empty list"))
        return findings

    seen_keys: set[str] = set()
    seen_terms: set[str] = set()

    for index, term in enumerate(terms):
        if not isinstance(term, dict):
            findings.append(
                Finding("error", "invalid_term", f"terms[{index}] must be an object")
            )
            continue

        key = _required_text(term, "key", findings)
        display = _required_text(term, "term", findings, term_key=key or None)
        _required_text(term, "family", findings, term_key=key or None)
        _required_text(term, "first_documented_date", findings, term_key=key or None)
        evidence_state = _required_text(
            term, "evidence_state", findings, term_key=key or None
        )
        public_state = _required_text(
            term, "public_state", findings, term_key=key or None
        )
        definition = _required_text(
            term, "public_definition", findings, term_key=key or None
        )

        if key:
            if not KEY_RE.fullmatch(key):
                findings.append(
                    Finding(
                        "error",
                        "invalid_key",
                        "key must use lowercase snake_case",
                        key,
                    )
                )
            if key in seen_keys:
                findings.append(Finding("error", "duplicate_key", "duplicate key", key))
            seen_keys.add(key)

        display_key = display.casefold()
        if display_key:
            if display_key in seen_terms:
                findings.append(
                    Finding("error", "duplicate_term", "duplicate display term", key or None)
                )
            seen_terms.add(display_key)

        if term.get("founder_origin_asserted") is not True:
            findings.append(
                Finding(
                    "error",
                    "origin_flag",
                    "founder_origin_asserted must be true for registry terms",
                    key or None,
                )
            )

        if public_state and public_state not in PUBLIC_STATES:
            findings.append(
                Finding(
                    "error",
                    "invalid_public_state",
                    f"unsupported public_state: {public_state}",
                    key or None,
                )
            )

        sources = term.get("sources")
        if not isinstance(sources, list):
            findings.append(
                Finding("error", "invalid_sources", "sources must be a list", key or None)
            )
            sources = []

        if evidence_state in VERIFIED_STATES and not sources:
            findings.append(
                Finding(
                    "error",
                    "verified_without_source",
                    "verified terms require at least one source",
                    key or None,
                )
            )

        if evidence_state.startswith("pending") and public_state not in {"hold", "private"}:
            findings.append(
                Finding(
                    "error",
                    "pending_promoted",
                    "pending terms must remain hold or private",
                    key or None,
                )
            )

        lower_definition = definition.lower()
        if any(
            forbidden in lower_definition
            for forbidden in (
                "registered trademark",
                "patented",
                "patent priority established",
                "externally validated",
                "certified performance",
                "guaranteed",
            )
        ):
            findings.append(
                Finding(
                    "error",
                    "unsafe_definition_claim",
                    "public definition contains a prohibited legal or performance assertion",
                    key or None,
                )
            )

        for source_index, source in enumerate(sources):
            _validate_source(
                source,
                index=source_index,
                term_key=key or f"terms[{index}]",
                root=root,
                findings=findings,
            )

    return findings


def build_summary(payload: Mapping[str, Any], findings: Sequence[Finding]) -> dict[str, Any]:
    terms = payload.get("terms") if isinstance(payload.get("terms"), list) else []
    evidence_counts: dict[str, int] = {}
    public_counts: dict[str, int] = {}
    for term in terms:
        if not isinstance(term, dict):
            continue
        evidence = str(term.get("evidence_state", "unknown"))
        public = str(term.get("public_state", "unknown"))
        evidence_counts[evidence] = evidence_counts.get(evidence, 0) + 1
        public_counts[public] = public_counts.get(public, 0) + 1

    errors = [finding.as_dict() for finding in findings if finding.level == "error"]
    warnings = [finding.as_dict() for finding in findings if finding.level == "warning"]
    return {
        "schema": "lumencore_founder_lexicon_validation_v1",
        "valid": not errors,
        "term_count": len(terms),
        "evidence_state_counts": dict(sorted(evidence_counts.items())),
        "public_state_counts": dict(sorted(public_counts.items())),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the public-safe LumenCore founder lexicon registry."
    )
    parser.add_argument(
        "registry",
        nargs="?",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Path to founder_lexicon_v1.json",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root used to verify repo_path sources",
    )
    parser.add_argument(
        "--no-source-check",
        action="store_true",
        help="Validate schema and claim boundaries without checking repo_path existence",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = load_registry(args.registry)
    except RegistryError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2))
        return 2

    root = None if args.no_source_check else args.root.resolve()
    findings = validate_registry(payload, root=root)
    summary = build_summary(payload, findings)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
