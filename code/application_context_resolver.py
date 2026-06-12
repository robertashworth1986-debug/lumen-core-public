from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT_OPS = ROOT / "out" / "ops"
CTX_DIR = OUT_OPS / "application_context"

PROFILE_PATH = DATA / "company_profile.json"
INVESTOR_READINESS_PATH = OUT_OPS / "investor_metric_readiness_latest.json"
SKIP_AUTOFILL_PATH = OUT_OPS / "skips_grant_autofill" / "skips_grant_autofill_latest.json"

CTX_LATEST = CTX_DIR / "application_context_latest.json"
CTX_MANIFEST_LATEST = CTX_DIR / "application_context_manifest_latest.json"

KNOWN_ENV_FILES = [
    ROOT / ".env",
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
]

COMPANY_ENV_MAP: dict[str, list[str]] = {
    "legal_name": ["LUMA_COMPANY_LEGAL_NAME", "COMPANY_LEGAL_NAME", "LEGAL_NAME"],
    "dba": ["LUMA_DBA", "COMPANY_DBA", "DBA_NAME"],
    "founder_pi": ["LUMA_FOUNDER_PI", "FOUNDER_NAME"],
    "founder_role": ["LUMA_FOUNDER_ROLE", "FOUNDER_ROLE"],
    "country": ["LUMA_COUNTRY", "COUNTRY", "COUNTRY_CODE"],
    "duns_or_uei": ["LUMA_UEI", "UEI", "DUNS_OR_UEI"],
    "ein": ["LUMA_EIN", "EIN", "TIN"],
    "sam_gov_status": ["LUMA_SAM_GOV_STATUS", "SAM_GOV_STATUS"],
    "address_line1": ["LUMA_ADDRESS_LINE1", "COMPANY_ADDRESS_LINE1", "ADDRESS_LINE1"],
    "city": ["LUMA_CITY", "COMPANY_CITY", "CITY"],
    "state": ["LUMA_STATE", "COMPANY_STATE", "STATE"],
    "zip": ["LUMA_ZIP", "COMPANY_ZIP", "ZIP", "ZIP_CODE"],
    "phone": ["LUMA_PHONE", "COMPANY_PHONE", "PHONE"],
    "email": ["LUMA_EMAIL", "COMPANY_EMAIL", "EMAIL"],
    "website": ["LUMA_WEBSITE", "COMPANY_WEBSITE", "WEBSITE"],
    "cage_code": ["LUMA_CAGE_CODE", "CAGE_CODE"],
    "uspto_nonprovisional": [
        "LUMA_USPTO_NONPROVISIONAL",
        "USPTO_NONPROVISIONAL",
        "USPTO_APPLICATION_NO",
    ],
}

PI_ENV_MAP: dict[str, list[str]] = {
    "name": ["LUMA_PI_NAME", "PI_NAME", "FOUNDER_NAME"],
    "title": ["LUMA_PI_TITLE", "PI_TITLE", "FOUNDER_ROLE"],
    "phone": ["LUMA_PI_PHONE", "PI_PHONE", "PHONE"],
    "email": ["LUMA_PI_EMAIL", "PI_EMAIL", "EMAIL"],
}

BOOL_FIELDS_COMPANY = {"us_owned_majority", "small_business"}
BOOL_FIELDS_PI = {"us_citizen_or_pr"}

PATENT_ENV_KEYS = [
    "LUMA_PATENT_NUMBERS",
    "PATENT_NUMBERS",
    "PATENT_APPLICATION_NUMBERS",
    "USPTO_NONPROVISIONAL",
    "LUMA_USPTO_NONPROVISIONAL",
]

REQUIRED_FIELDS = [
    "company.legal_name",
    "company.duns_or_uei",
    "company.ein",
    "company.sam_gov_status",
    "company.sam_gov_verified_utc",
    "company.sam_gov_expiration_date",
    "company.address_line1",
    "company.city",
    "company.state",
    "company.zip",
    "company.country",
    "company.phone",
    "company.email",
    "company.website",
    "company.cage_code",
    "pi.name",
    "pi.title",
    "pi.phone",
    "pi.email",
    "federal_readiness.status",
    "federal_readiness.runtime_mode",
    "identifiers.patent_numbers",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    txt = str(value or "").strip().lower()
    return txt in {"1", "true", "t", "yes", "y"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_env_file(path: Path) -> list[str]:
    loaded: list[str] = []
    if not path.exists():
        return loaded
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_key = key.strip()
        env_val = value.strip().strip('"').strip("'")
        if not env_key or not env_val:
            continue
        if env_key not in os.environ:
            os.environ[env_key] = env_val
            loaded.append(env_key)
    return loaded


def _hydrate_known_env() -> dict[str, list[str]]:
    detail: dict[str, list[str]] = {}
    for path in KNOWN_ENV_FILES:
        loaded = _load_env_file(path)
        if loaded:
            detail[str(path)] = loaded
    return detail


def _first_env(names: list[str]) -> tuple[str | None, str | None]:
    for name in names:
        value = str(os.environ.get(name) or "").strip()
        if value:
            return name, value
    return None, None


def _extract_patent_tokens(text: str) -> list[str]:
    found: list[str] = []
    if not text:
        return found
    for token in re.findall(r"\b\d{2}/\d{3},\d{3}\b", text):
        found.append(token)
    for token in re.findall(r"\bUS\s*\d{2}/\d{3},\d{3}\b", text, flags=re.I):
        cleaned = re.sub(r"\s+", " ", token.strip())
        found.append(cleaned)
    return found


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        txt = str(value or "").strip()
        if not txt:
            continue
        key = txt.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(txt)
    return out


def _collect_patent_numbers(company: dict[str, Any], profile_payload: dict[str, Any]) -> list[str]:
    patents: list[str] = []

    direct = company.get("patent_numbers")
    if isinstance(direct, list):
        patents.extend(str(x) for x in direct)

    uspto = str(company.get("uspto_nonprovisional") or "").strip()
    if uspto:
        patents.append(uspto)

    ip_status = str(profile_payload.get("ip_status") or "")
    patents.extend(_extract_patent_tokens(ip_status))

    for key in PATENT_ENV_KEYS:
        env_val = str(os.environ.get(key) or "").strip()
        if not env_val:
            continue
        parts = [p.strip() for p in re.split(r"[,;|]", env_val) if p.strip()]
        patents.extend(parts)

    return _dedupe_keep_order(patents)


def _field_value(payload: dict[str, Any], field_path: str) -> Any:
    cur: Any = payload
    for part in field_path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True


def resolve_application_context(*, strict: bool = False, write_outputs: bool = True) -> dict[str, Any]:
    env_detail = _hydrate_known_env()

    profile_payload = _load_json(PROFILE_PATH, {})
    if not isinstance(profile_payload, dict):
        profile_payload = {}

    company = profile_payload.get("company", {})
    if not isinstance(company, dict):
        company = {}
    company = dict(company)

    pi = profile_payload.get("pi", {})
    if not isinstance(pi, dict):
        pi = {}
    pi = dict(pi)

    env_overrides: dict[str, str] = {}

    for field, names in COMPANY_ENV_MAP.items():
        env_name, env_value = _first_env(names)
        if not env_name or not env_value:
            continue
        if field in BOOL_FIELDS_COMPANY:
            company[field] = _to_bool(env_value)
        elif not _is_present(company.get(field)):
            company[field] = env_value
        env_overrides[f"company.{field}"] = env_name

    for field, names in PI_ENV_MAP.items():
        env_name, env_value = _first_env(names)
        if not env_name or not env_value:
            continue
        if field in BOOL_FIELDS_PI:
            pi[field] = _to_bool(env_value)
        elif not _is_present(pi.get(field)):
            pi[field] = env_value
        env_overrides[f"pi.{field}"] = env_name

    skip_payload = _load_json(SKIP_AUTOFILL_PATH, {})
    if not isinstance(skip_payload, dict):
        skip_payload = {}
    skip_business = skip_payload.get("business_profile", {})
    if not isinstance(skip_business, dict):
        skip_business = {}

    if not _is_present(company.get("dba")):
        company["dba"] = skip_business.get("name")
    if not _is_present(company.get("website")):
        company["website"] = skip_business.get("website")
    if not _is_present(company.get("country")):
        company["country"] = skip_business.get("location") or "United States"
    if not _is_present(company.get("founder_pi")):
        company["founder_pi"] = skip_business.get("founder")

    if not _is_present(pi.get("name")):
        pi["name"] = company.get("founder_pi")
    if not _is_present(pi.get("phone")):
        pi["phone"] = company.get("phone")
    if not _is_present(pi.get("email")):
        pi["email"] = company.get("email")
    if not _is_present(pi.get("title")):
        pi["title"] = company.get("founder_role") or "Founder & Chief Scientist"

    patents = _collect_patent_numbers(company, profile_payload)

    investor_payload = _load_json(INVESTOR_READINESS_PATH, {})
    if not isinstance(investor_payload, dict):
        investor_payload = {}
    summary = investor_payload.get("summary", {}) if isinstance(investor_payload, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    signal = summary.get("signal_evidence", {}) if isinstance(summary, dict) else {}
    if not isinstance(signal, dict):
        signal = {}
    capital = summary.get("capital_and_risk_gate_evidence", {}) if isinstance(summary, dict) else {}
    if not isinstance(capital, dict):
        capital = {}

    federal_readiness = {
        "generated_utc": investor_payload.get("generated_utc"),
        "status": summary.get("status"),
        "investor_position": summary.get("investor_position"),
        "runtime_mode": capital.get("runtime_mode"),
        "allow_live_orders": bool(capital.get("allow_live_orders")) if capital else False,
        "hard_safety_only_mode": bool(capital.get("hard_safety_only_mode")) if capital else False,
        "max_notional_per_trade_usd": _safe_float(capital.get("max_notional_per_trade_usd"), 0.0),
        "annual_value_signal_usd": _safe_float(signal.get("annual_value_usd"), 0.0),
        "router_edge_pct": _safe_float(signal.get("router_edge_pct"), 0.0),
        "harmonic_win_rate_pct": _safe_float(signal.get("harmonic_win_rate_pct"), 0.0),
    }

    identifiers = {
        "uei": company.get("duns_or_uei"),
        "ein": company.get("ein"),
        "cage_code": company.get("cage_code"),
        "sam_gov_status": company.get("sam_gov_status"),
        "patent_numbers": patents,
    }

    application_profile = {
        "schema_version": str(profile_payload.get("schema_version") or "1.0"),
        "company": company,
        "pi": pi,
        "company_capabilities": profile_payload.get("company_capabilities", []),
        "broader_impacts": profile_payload.get("broader_impacts", []),
        "differentiators": profile_payload.get("differentiators", []),
        "ip_status": profile_payload.get("ip_status"),
        "team_letters_of_support": profile_payload.get("team_letters_of_support", []),
        "submission_readiness": profile_payload.get("submission_readiness", {}),
        "federal_readiness": federal_readiness,
        "identifiers": identifiers,
    }

    missing_required_fields: list[str] = []
    for field in REQUIRED_FIELDS:
        value = _field_value(application_profile, field)
        if not _is_present(value):
            missing_required_fields.append(field)

    completeness_pct = round(
        100.0 * (len(REQUIRED_FIELDS) - len(missing_required_fields)) / max(1, len(REQUIRED_FIELDS)),
        2,
    )

    status = "PASS" if not missing_required_fields else "WARN"
    payload = {
        "generated_utc": _now_iso(),
        "schema": "application_context_v1",
        "status": status,
        "completeness": {
            "required_fields_total": len(REQUIRED_FIELDS),
            "missing_required_fields": missing_required_fields,
            "score_pct": completeness_pct,
            "ready_for_autofill": len(missing_required_fields) == 0,
        },
        "application_profile": application_profile,
        "evidence_paths": {
            "company_profile": str(PROFILE_PATH),
            "investor_readiness": str(INVESTOR_READINESS_PATH),
            "skip_autofill": str(SKIP_AUTOFILL_PATH),
        },
        "variable_sources": {
            "env_file_hydration": env_detail,
            "field_env_overrides": env_overrides,
        },
    }

    if write_outputs:
        tag = _stamp()
        CTX_DIR.mkdir(parents=True, exist_ok=True)
        tagged = CTX_DIR / f"application_context_{tag}.json"
        _write_json(tagged, payload)
        _write_json(CTX_LATEST, payload)

        manifest = {
            "generated_utc": _now_iso(),
            "schema": "application_context_manifest_v1",
            "status": status,
            "strict_blockers": missing_required_fields,
            "artifact": {
                "tagged": str(tagged),
                "latest": str(CTX_LATEST),
                "latest_sha256": _sha256_file(CTX_LATEST),
                "latest_bytes": CTX_LATEST.stat().st_size,
            },
            "completeness": payload.get("completeness"),
        }
        manifest_tagged = CTX_DIR / f"application_context_manifest_{tag}.json"
        _write_json(manifest_tagged, manifest)
        _write_json(CTX_MANIFEST_LATEST, manifest)

    if strict and missing_required_fields:
        raise RuntimeError("missing required context fields: " + ", ".join(missing_required_fields))

    return payload


def load_application_profile() -> dict[str, Any]:
    source_paths = [
        PROFILE_PATH,
        INVESTOR_READINESS_PATH,
        SKIP_AUTOFILL_PATH,
        Path(__file__).resolve(),
    ]
    source_mtime = max(
        (path.stat().st_mtime for path in source_paths if path.exists()),
        default=0.0,
    )
    cache_fresh = (
        CTX_LATEST.exists()
        and CTX_LATEST.stat().st_mtime >= source_mtime
    )
    if cache_fresh:
        latest = _load_json(CTX_LATEST, {})
        if isinstance(latest, dict):
            profile = latest.get("application_profile")
            if isinstance(profile, dict) and profile.get("company") and profile.get("pi"):
                return profile
    payload = resolve_application_context(strict=False, write_outputs=True)
    profile = payload.get("application_profile")
    return profile if isinstance(profile, dict) else {"company": {}, "pi": {}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve and validate unified application context for grants/loans/jobs.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if required context fields are missing.")
    args = parser.parse_args()

    try:
        payload = resolve_application_context(strict=args.strict, write_outputs=True)
    except Exception as exc:
        print(f"APPLICATION_CONTEXT_STATUS=FAIL")
        print(f"APPLICATION_CONTEXT_ERROR={exc}")
        return 2

    completeness = payload.get("completeness", {}) if isinstance(payload, dict) else {}
    print(f"APPLICATION_CONTEXT_STATUS={payload.get('status')}")
    print(f"APPLICATION_CONTEXT_LATEST={CTX_LATEST}")
    print(f"APPLICATION_CONTEXT_MANIFEST={CTX_MANIFEST_LATEST}")
    print(f"APPLICATION_CONTEXT_SCORE_PCT={_safe_float(completeness.get('score_pct'), 0.0):.2f}")
    print(f"APPLICATION_CONTEXT_MISSING={_safe_int(len(completeness.get('missing_required_fields') or []), 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
