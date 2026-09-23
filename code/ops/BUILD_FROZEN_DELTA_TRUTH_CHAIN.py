from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
CHAIN_DIR = OUT_OPS / "frozen_delta_truth_chain"
DELTA_DIR = CHAIN_DIR / "deltas"

LEDGER_PATH = CHAIN_DIR / "frozen_delta_truth_chain_ledger.jsonl"
LEDGER_LATEST_JSON = CHAIN_DIR / "frozen_delta_truth_chain_latest.json"
SNAPSHOT_LATEST_JSON = CHAIN_DIR / "frozen_delta_snapshot_latest.json"
VERIFY_LATEST_JSON = CHAIN_DIR / "frozen_delta_truth_chain_verify_latest.json"
VERIFY_LATEST_MD = CHAIN_DIR / "frozen_delta_truth_chain_verify_latest.md"
HEARTBEAT_LATEST_JSON = CHAIN_DIR / "frozen_delta_truth_chain_heartbeat_latest.json"

LIVE_PANEL = OUT_OPS / "live_breadth_value_panel_latest.json"
MASTER_VAL = OUT_OPS / "master_valuation" / "master_valuation_latest.json"
READINESS = OUT_OPS / "investor_metric_readiness_latest.json"
PUBLIC_TRUTH = OUT_OPS / "public_truth" / "public_truth_latest.json"
GRANTS_QUEUE = ROOT / "out" / "grant_approval_queue.json"
JOBS_QUEUE = ROOT / "out" / "jobs" / "_queue" / "index.json"
OPP_TRACKER = ROOT / "out" / "opportunities" / "tracker.json"
EXEC_EVENTS_A = ROOT / "execution_events.jsonl"
EXEC_EVENTS_B = ROOT / "out" / "execution" / "execution_events.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


CLAIM_BOUNDARY = (
    "This chain verifies artifact custody, not causal effects, accepted economics, revenue or savings. "
    "Legacy dollar values remain source-specific reported context. Model deltas are not field improvements."
)


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_nonfinite_constant(value: str) -> Any:
    raise ValueError(f"Nonfinite JSON number: {value}")


def optional_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def optional_count(value: Any) -> int | None:
    number = optional_number(value)
    return int(number) if number is not None and number >= 0 and number.is_integer() else None


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        txt = raw.strip()
        if not txt:
            continue
        try:
            obj = json.loads(txt)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except Exception:
        return path.as_posix()


def find_exec_events_path() -> Path | None:
    if EXEC_EVENTS_A.exists():
        return EXEC_EVENTS_A
    if EXEC_EVENTS_B.exists():
        return EXEC_EVENTS_B
    return None


def count_any(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("total", "count", "records", "rows"):
            if key in payload:
                return safe_int(payload.get(key), len(payload))
        for key in ("items", "entries", "opportunities", "queue"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return len(payload)
    return 0


def read_prev_entry_sha(ledger_path: Path) -> str:
    if not ledger_path.exists():
        return ""
    lines = ledger_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for raw in reversed(lines):
        txt = raw.strip()
        if not txt:
            continue
        try:
            row = json.loads(txt)
        except Exception:
            continue
        if isinstance(row, dict):
            return str(row.get("entry_sha256") or "")
    return ""


def collect_state() -> dict[str, Any]:
    source_paths = {
        "live_breadth_value_panel_latest": LIVE_PANEL, "master_valuation_latest": MASTER_VAL,
        "investor_metric_readiness_latest": READINESS, "public_truth_latest": PUBLIC_TRUTH,
        "grant_approval_queue": GRANTS_QUEUE, "jobs_queue_index": JOBS_QUEUE,
        "opportunities_tracker": OPP_TRACKER,
    }
    exec_events_path = find_exec_events_path()
    if exec_events_path:
        source_paths["execution_events"] = exec_events_path
    source_hashes: dict[str, str] = {}
    source_bytes: dict[str, int] = {}
    documents: dict[str, Any] = {}
    for name, path in source_paths.items():
        if not path.exists():
            documents[name] = None
            continue
        # Bind the hash to the exact bytes parsed, rather than re-read a changing source later.
        raw = path.read_bytes()
        source_hashes[name] = hashlib.sha256(raw).hexdigest()
        source_bytes[name] = len(raw)
        try:
            text = raw.decode("utf-8-sig")
            documents[name] = [json.loads(line, object_pairs_hook=reject_duplicate_members, parse_constant=reject_nonfinite_constant) for line in text.splitlines() if line.strip()] if name == "execution_events" else json.loads(text, object_pairs_hook=reject_duplicate_members, parse_constant=reject_nonfinite_constant)
        except (UnicodeError, ValueError) as exc:
            raise ValueError(f"Invalid frozen-chain input: {name}") from exc
    live = documents.get("live_breadth_value_panel_latest")
    val = documents.get("master_valuation_latest")
    readiness = documents.get("investor_metric_readiness_latest")
    public_truth = documents.get("public_truth_latest")
    grants = documents.get("grant_approval_queue")
    jobs = documents.get("jobs_queue_index")
    tracker = documents.get("opportunities_tracker")
    events_tail = documents.get("execution_events") or []
    latest_event = events_tail[-1] if events_tail and isinstance(events_tail[-1], dict) else {}

    live_headline = (live.get("headline", {}) or {}) if isinstance(live, dict) else {}
    val_block = (val.get("valuation", {}) or {}) if isinstance(val, dict) else {}
    val_inputs = (val.get("inputs", {}) or {}) if isinstance(val, dict) else {}
    readiness_summary = (readiness.get("summary", {}) or {}) if isinstance(readiness, dict) else {}

    metrics = {
        "annual_value_signal_usd": None,
        "top_sector_hourly_value_usd": None,
        "modeled_annual_value_usd": optional_number(live_headline.get("modeled_annual_value_usd")),
        "top_sector_modeled_hourly_value_usd": optional_number(live_headline.get("top_sector_modeled_hourly_value_usd")),
        "measured_sources": optional_count(live_headline.get("measured_sources")),
        "enabled_sources": optional_count(live_headline.get("enabled_sources")),
        "measured_coverage_pct": optional_number(live_headline.get("measured_coverage_pct")),
        "benchmark_prevented_pct": None,
        "router_edge_pct": optional_number(live_headline.get("router_edge_pct")),
        "harmonic_win_rate_pct": optional_number(live_headline.get("harmonic_win_rate_pct")),
        "top_sector": str(live_headline.get("top_sector") or ""),
        "valuation_proxy_usd": None, "valuation_increment_usd": None,
        "grant_pipeline_value_usd": None, "grant_license_value_usd": None,
        "digital_scout_value_usd": None, "institutional_trading_value_usd": None,
        "validated_autonomy_value_usd": None,
        "economic_claim_status": "NO_ACCEPTED_ECONOMICS",
        "public_economic_value_claim_allowed": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "reported_economic_context": {
            "live_panel_annual_value_usd": optional_number(live_headline.get("total_estimated_annual_value_usd")),
            "master_valuation_annual_value_usd": optional_number(val_inputs.get("annual_value_signal_usd")),
            "live_panel_top_sector_hourly_value_usd": optional_number(live_headline.get("top_sector_hourly_value_usd")),
            "master_valuation_proxy_usd": optional_number(val_block.get("master_valuation_proxy_usd")),
            "valuation_increment_usd": optional_number(val_block.get("valuation_increment_usd")),
            "grant_pipeline_value_usd": optional_number(val_block.get("grant_and_opportunity_pipeline_value_usd")),
            "grant_license_value_usd": optional_number(val_block.get("grant_finding_and_ranking_system_license_value_usd")),
            "digital_scout_value_usd": optional_number(val_block.get("digital_scout_value_usd")),
            "institutional_trading_value_usd": optional_number(val_block.get("institutional_trading_system_value_usd")),
            "validated_autonomy_value_usd": optional_number(val_block.get("validated_engine_autonomy_value_usd")),
            "benchmark_prevented_pct": optional_number(live_headline.get("cross_sector_recommended_prevented_pct")),
        },
        "readiness_status": str(
            readiness_summary.get("performance_metrics_status")
            or live_headline.get("performance_metrics_status")
            or ""
        ),
        "grants_queue_total": count_any(grants),
        "jobs_queue_total": count_any(jobs),
        "opportunities_total": count_any(tracker),
        "public_truth_status": str((public_truth.get("status") if isinstance(public_truth, dict) else "") or ""),
        "latest_execution_event_type": str(latest_event.get("event_type") or latest_event.get("type") or ""),
        "latest_execution_event_utc": str(latest_event.get("generated_utc") or latest_event.get("timestamp_utc") or ""),
    }

    return {
        "metrics": metrics,
        "source_paths": {k: rel(v) for k, v in source_paths.items()},
        "source_hashes": source_hashes,
        "source_bytes": source_bytes,
    }


def build_numeric_deltas(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in current.items():
        old = previous.get(key)
        if isinstance(value, bool) or isinstance(old, bool):
            continue
        if not isinstance(value, (int, float)) or not isinstance(old, (int, float)):
            continue
        if optional_number(value) is not None and optional_number(old) is not None:
            delta = optional_number(value - old)
            if delta is not None:
                out[key] = delta
    return out


def write_delta(name: str, run_tag: str, generated_utc: str, current: dict[str, Any], previous: dict[str, Any], source_hashes: dict[str, str]) -> tuple[Path, Path]:
    payload = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "schema": "frozen_delta_payload_v1",
        "delta_name": name,
        "current": current,
        "previous": previous,
        "numeric_delta": build_numeric_deltas(current, previous),
        "source_hashes": source_hashes,
        "claim_boundary": CLAIM_BOUNDARY,
        "public_economic_value_claim_allowed": False,
    }

    DELTA_DIR.mkdir(parents=True, exist_ok=True)
    ts_path = DELTA_DIR / f"frozen_delta_{name}_{run_tag}.json"
    latest_path = DELTA_DIR / f"frozen_delta_{name}_latest.json"
    write_json(ts_path, payload)
    write_json(latest_path, payload)
    return ts_path, latest_path


def build_markdown_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Frozen Delta Truth Chain")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Run Tag: {payload.get('run_tag', '')}")
    lines.append(f"Entry SHA256: {payload.get('entry_sha256', '')}")
    lines.append(f"Previous Entry SHA256: {payload.get('previous_entry_sha256', '')}")
    lines.append("")
    lines.append(CLAIM_BOUNDARY)
    lines.append("Accepted annual savings: UNKNOWN; economic claims remain closed.")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append("")
    metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
    for key in (
        "annual_value_signal_usd",
        "modeled_annual_value_usd",
        "economic_claim_status",
        "measured_sources",
        "enabled_sources",
        "measured_coverage_pct",
        "benchmark_prevented_pct",
        "router_edge_pct",
        "harmonic_win_rate_pct",
        "valuation_proxy_usd",
        "valuation_increment_usd",
        "readiness_status",
    ):
        value = metrics.get(key)
        lines.append(f"- {key}: {'UNKNOWN' if value is None else value}")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    for row in payload.get("artifacts", []):
        lines.append(
            f"- {row.get('path_rel','')} | sha256={row.get('sha256','')} | bytes={row.get('bytes',0)} | mtime_utc={row.get('mtime_utc','')}"
        )
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append("- Recompute file hashes and compare with artifact sha256 values.")
    lines.append("- Recompute entry sha256 from canonical JSON without entry_sha256 field.")
    lines.append("- Ensure previous_entry_sha256 equals the prior ledger entry hash.")
    lines.append("")
    return "\n".join(lines)


def verify_chain(ledger_path: Path) -> dict[str, Any]:
    generated_utc = now_iso()
    rows = load_jsonl(ledger_path)
    failures: list[str] = []

    prev_sha = ""
    for idx, row in enumerate(rows):
        row_sha = str(row.get("entry_sha256") or "")
        row_prev = str(row.get("previous_entry_sha256") or "")
        if row_prev != prev_sha:
            failures.append(f"entry_{idx}: previous_entry_sha256 mismatch")

        material = dict(row)
        material.pop("entry_sha256", None)
        computed_sha = canonical_sha256(material)
        if row_sha != computed_sha:
            failures.append(f"entry_{idx}: entry_sha256 mismatch")

        artifacts = row.get("artifacts", [])
        if isinstance(artifacts, list):
            for j, art in enumerate(artifacts):
                if not isinstance(art, dict):
                    failures.append(f"entry_{idx}: artifact_{j} invalid record")
                    continue
                path_rel = str(art.get("path_rel") or "")
                expected = str(art.get("sha256") or "")
                if not path_rel:
                    failures.append(f"entry_{idx}: artifact_{j} missing path_rel")
                    continue
                target = ROOT / Path(path_rel)
                if not target.exists():
                    failures.append(f"entry_{idx}: artifact_{j} missing file {path_rel}")
                    continue
                actual = sha256_file(target)
                if actual != expected:
                    failures.append(f"entry_{idx}: artifact_{j} sha256 mismatch {path_rel}")

        prev_sha = row_sha

    return {
        "generated_utc": generated_utc,
        "schema": "frozen_delta_truth_chain_verify_v1",
        "ledger_path": rel(ledger_path),
        "entries_checked": len(rows),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
    }


def render_verify_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Frozen Delta Truth Chain Verification")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Ledger: {payload.get('ledger_path', '')}")
    lines.append(f"Entries Checked: {payload.get('entries_checked', 0)}")
    lines.append(f"Status: {payload.get('status', '')}")
    failures = payload.get("failures", [])
    if failures:
        lines.append("")
        lines.append("## Failures")
        lines.append("")
        for item in failures:
            lines.append(f"- {item}")
    else:
        lines.append("")
        lines.append("All ledger links and artifact hashes verified.")
    lines.append("")
    return "\n".join(lines)


def build_chain(strict: bool) -> int:
    generated_utc = now_iso()
    run_tag = now_tag()

    CHAIN_DIR.mkdir(parents=True, exist_ok=True)
    DELTA_DIR.mkdir(parents=True, exist_ok=True)

    state = collect_state()
    metrics = state.get("metrics", {}) if isinstance(state, dict) else {}
    source_hashes = state.get("source_hashes", {}) if isinstance(state, dict) else {}
    source_paths = state.get("source_paths", {}) if isinstance(state, dict) else {}

    prev_snapshot = load_json(SNAPSHOT_LATEST_JSON)
    prev_metrics = (prev_snapshot.get("metrics", {}) or {}) if isinstance(prev_snapshot, dict) else {}

    live_current = {
        "modeled_annual_value_usd": metrics.get("modeled_annual_value_usd"),
        "economic_claim_status": metrics.get("economic_claim_status", "LEGACY_UNVERIFIED_CONTEXT"),
        "annual_value_signal_usd": metrics.get("annual_value_signal_usd"),
        "measured_sources": metrics.get("measured_sources", 0),
        "enabled_sources": metrics.get("enabled_sources", 0),
        "measured_coverage_pct": metrics.get("measured_coverage_pct", 0.0),
        "benchmark_prevented_pct": metrics.get("benchmark_prevented_pct", 0.0),
        "router_edge_pct": metrics.get("router_edge_pct", 0.0),
        "harmonic_win_rate_pct": metrics.get("harmonic_win_rate_pct", 0.0),
        "top_sector": metrics.get("top_sector", ""),
        "top_sector_hourly_value_usd": metrics.get("top_sector_hourly_value_usd"),
    }
    live_prev = {
        "modeled_annual_value_usd": prev_metrics.get("modeled_annual_value_usd"),
        "economic_claim_status": prev_metrics.get("economic_claim_status", "LEGACY_UNVERIFIED_CONTEXT"),
        "annual_value_signal_usd": prev_metrics.get("annual_value_signal_usd"),
        "measured_sources": prev_metrics.get("measured_sources", 0),
        "enabled_sources": prev_metrics.get("enabled_sources", 0),
        "measured_coverage_pct": prev_metrics.get("measured_coverage_pct", 0.0),
        "benchmark_prevented_pct": prev_metrics.get("benchmark_prevented_pct", 0.0),
        "router_edge_pct": prev_metrics.get("router_edge_pct", 0.0),
        "harmonic_win_rate_pct": prev_metrics.get("harmonic_win_rate_pct", 0.0),
        "top_sector": prev_metrics.get("top_sector", ""),
        "top_sector_hourly_value_usd": prev_metrics.get("top_sector_hourly_value_usd"),
    }

    valuation_current = {
        "reported_economic_context": metrics.get("reported_economic_context", {}),
        "valuation_proxy_usd": metrics.get("valuation_proxy_usd"),
        "valuation_increment_usd": metrics.get("valuation_increment_usd"),
        "grant_pipeline_value_usd": metrics.get("grant_pipeline_value_usd"),
        "grant_license_value_usd": metrics.get("grant_license_value_usd"),
        "digital_scout_value_usd": metrics.get("digital_scout_value_usd"),
        "institutional_trading_value_usd": metrics.get("institutional_trading_value_usd"),
        "validated_autonomy_value_usd": metrics.get("validated_autonomy_value_usd"),
    }
    valuation_prev = {
        "reported_economic_context": prev_metrics.get("reported_economic_context", {}),
        "valuation_proxy_usd": prev_metrics.get("valuation_proxy_usd"),
        "valuation_increment_usd": prev_metrics.get("valuation_increment_usd"),
        "grant_pipeline_value_usd": prev_metrics.get("grant_pipeline_value_usd"),
        "grant_license_value_usd": prev_metrics.get("grant_license_value_usd"),
        "digital_scout_value_usd": prev_metrics.get("digital_scout_value_usd"),
        "institutional_trading_value_usd": prev_metrics.get("institutional_trading_value_usd"),
        "validated_autonomy_value_usd": prev_metrics.get("validated_autonomy_value_usd"),
    }

    ops_current = {
        "readiness_status": metrics.get("readiness_status", ""),
        "grants_queue_total": metrics.get("grants_queue_total", 0),
        "jobs_queue_total": metrics.get("jobs_queue_total", 0),
        "opportunities_total": metrics.get("opportunities_total", 0),
        "public_truth_status": metrics.get("public_truth_status", ""),
        "latest_execution_event_type": metrics.get("latest_execution_event_type", ""),
        "latest_execution_event_utc": metrics.get("latest_execution_event_utc", ""),
    }
    ops_prev = {
        "readiness_status": prev_metrics.get("readiness_status", ""),
        "grants_queue_total": prev_metrics.get("grants_queue_total", 0),
        "jobs_queue_total": prev_metrics.get("jobs_queue_total", 0),
        "opportunities_total": prev_metrics.get("opportunities_total", 0),
        "public_truth_status": prev_metrics.get("public_truth_status", ""),
        "latest_execution_event_type": prev_metrics.get("latest_execution_event_type", ""),
        "latest_execution_event_utc": prev_metrics.get("latest_execution_event_utc", ""),
    }

    delta_live_ts, _ = write_delta("live_surface", run_tag, generated_utc, live_current, live_prev, source_hashes)
    delta_val_ts, _ = write_delta("valuation_integrity", run_tag, generated_utc, valuation_current, valuation_prev, source_hashes)
    delta_ops_ts, _ = write_delta("operational_truth", run_tag, generated_utc, ops_current, ops_prev, source_hashes)

    snapshot_payload = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "schema": "frozen_delta_snapshot_v1",
        "metrics": metrics,
        "source_paths": source_paths,
        "source_hashes": source_hashes,
        "deltas": [
            rel(delta_live_ts),
            rel(delta_val_ts),
            rel(delta_ops_ts),
        ],
    }
    snapshot_ts = CHAIN_DIR / f"frozen_delta_snapshot_{run_tag}.json"
    write_json(snapshot_ts, snapshot_payload)
    write_json(SNAPSHOT_LATEST_JSON, snapshot_payload)

    artifact_paths = [delta_live_ts, delta_val_ts, delta_ops_ts, snapshot_ts]
    artifacts: list[dict[str, Any]] = []
    for path in artifact_paths:
        st = path.stat()
        artifacts.append(
            {
                "path_rel": rel(path),
                "sha256": sha256_file(path),
                "bytes": int(st.st_size),
                "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
            }
        )

    previous_sha = read_prev_entry_sha(LEDGER_PATH)
    entry_material = {
        "generated_utc": generated_utc,
        "run_tag": run_tag,
        "event_label": "frozen_delta_truth_chain_update",
        "previous_entry_sha256": previous_sha,
        "metrics": metrics,
        "artifacts": artifacts,
    }
    entry_sha = canonical_sha256(entry_material)
    ledger_row = dict(entry_material)
    ledger_row["entry_sha256"] = entry_sha
    append_jsonl(LEDGER_PATH, ledger_row)

    chain_txt_ts = CHAIN_DIR / f"frozen_delta_chain_of_custody_{run_tag}.sha256.txt"
    chain_txt_latest = CHAIN_DIR / "frozen_delta_chain_of_custody_latest.sha256.txt"
    chain_lines = [
        f"generated_utc={generated_utc}",
        f"run_tag={run_tag}",
        f"entry_sha256={entry_sha}",
        f"previous_entry_sha256={previous_sha}",
    ]
    for row in artifacts:
        chain_lines.append(f"artifact={row['path_rel']}")
        chain_lines.append(f"sha256={row['sha256']}")
    chain_text = "\n".join(chain_lines)
    write_text(chain_txt_ts, chain_text)
    write_text(chain_txt_latest, chain_text)

    latest_payload = dict(ledger_row)
    latest_payload["ledger_path"] = rel(LEDGER_PATH)
    latest_payload["snapshot_latest"] = rel(SNAPSHOT_LATEST_JSON)
    latest_payload["chain_of_custody_latest"] = rel(chain_txt_latest)
    write_json(LEDGER_LATEST_JSON, latest_payload)

    md_report_ts = CHAIN_DIR / f"frozen_delta_truth_chain_{run_tag}.md"
    md_report_latest = CHAIN_DIR / "frozen_delta_truth_chain_latest.md"
    md_text = build_markdown_report(ledger_row)
    write_text(md_report_ts, md_text)
    write_text(md_report_latest, md_text)

    verify_payload = verify_chain(LEDGER_PATH)
    verify_ts_json = CHAIN_DIR / f"frozen_delta_truth_chain_verify_{run_tag}.json"
    verify_ts_md = CHAIN_DIR / f"frozen_delta_truth_chain_verify_{run_tag}.md"
    write_json(verify_ts_json, verify_payload)
    write_json(VERIFY_LATEST_JSON, verify_payload)
    verify_md = render_verify_markdown(verify_payload)
    write_text(verify_ts_md, verify_md)
    write_text(VERIFY_LATEST_MD, verify_md)

    heartbeat = {
        "generated_utc": now_iso(),
        "scope": "frozen_delta_truth_chain",
        "status": "ok" if verify_payload.get("status") == "PASS" else "error",
        "run_tag": run_tag,
        "entry_sha256": entry_sha,
        "previous_entry_sha256": previous_sha,
        "verify_status": verify_payload.get("status", ""),
        "verify_entries_checked": verify_payload.get("entries_checked", 0),
        "artifacts": {
            "delta_live_surface_latest": rel(DELTA_DIR / "frozen_delta_live_surface_latest.json"),
            "delta_valuation_integrity_latest": rel(DELTA_DIR / "frozen_delta_valuation_integrity_latest.json"),
            "delta_operational_truth_latest": rel(DELTA_DIR / "frozen_delta_operational_truth_latest.json"),
            "snapshot_latest": rel(SNAPSHOT_LATEST_JSON),
            "ledger": rel(LEDGER_PATH),
            "ledger_latest": rel(LEDGER_LATEST_JSON),
            "verify_latest_json": rel(VERIFY_LATEST_JSON),
            "verify_latest_md": rel(VERIFY_LATEST_MD),
            "chain_of_custody_latest": rel(chain_txt_latest),
            "report_latest": rel(md_report_latest),
        },
    }
    write_json(HEARTBEAT_LATEST_JSON, heartbeat)

    print(f"FROZEN_DELTA_LIVE={DELTA_DIR / 'frozen_delta_live_surface_latest.json'}")
    print(f"FROZEN_DELTA_VALUATION={DELTA_DIR / 'frozen_delta_valuation_integrity_latest.json'}")
    print(f"FROZEN_DELTA_OPS={DELTA_DIR / 'frozen_delta_operational_truth_latest.json'}")
    print(f"FROZEN_DELTA_SNAPSHOT={SNAPSHOT_LATEST_JSON}")
    print(f"FROZEN_DELTA_LEDGER={LEDGER_PATH}")
    print(f"FROZEN_DELTA_LEDGER_LATEST={LEDGER_LATEST_JSON}")
    print(f"FROZEN_DELTA_VERIFY_JSON={VERIFY_LATEST_JSON}")
    print(f"FROZEN_DELTA_VERIFY_MD={VERIFY_LATEST_MD}")
    print(f"FROZEN_DELTA_CHAIN_TXT={chain_txt_latest}")
    print(f"FROZEN_DELTA_HEARTBEAT={HEARTBEAT_LATEST_JSON}")

    if strict and verify_payload.get("status") != "PASS":
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a SHA256-linked frozen-delta truth chain with verification.")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing ledger chain and write verification artifacts.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if verification fails.")
    args = parser.parse_args()

    if args.verify_only:
        verify_payload = verify_chain(LEDGER_PATH)
        write_json(VERIFY_LATEST_JSON, verify_payload)
        write_text(VERIFY_LATEST_MD, render_verify_markdown(verify_payload))
        print(f"FROZEN_DELTA_VERIFY_JSON={VERIFY_LATEST_JSON}")
        print(f"FROZEN_DELTA_VERIFY_MD={VERIFY_LATEST_MD}")
        if args.strict and verify_payload.get("status") != "PASS":
            return 1
        return 0

    return build_chain(strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
