from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_EXEC = ROOT / "out" / "execution"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

RUNTIME_FILE = CONFIG / "runtime_control.json"
LEGACY_RUNTIME_FILE = ROOT / "code" / "execution" / "runtime_control.json"
ACCOUNT_RUNTIME_FILES = [
    CONFIG / "accounts" / "ALPACA_PRIMARY" / "runtime_control.json",
    CONFIG / "accounts" / "KRAKEN_PRIMARY" / "runtime_control.json",
]
CONTROL_FLAG_FILES = [
    ROOT / "control_flags.json",
    ROOT / "out" / "control_flags.json",
]
MULTI_ACCOUNT_POLICY_FILE = CONFIG / "multi_account_policy.json"
LIVE_MARKER_FILES = [
    ROOT / "control" / "LIVE.flag",
    CONFIG / "live_arm.confirm",
    CONFIG / "multi_live_arm.confirm",
    CONFIG / "lightning_live_arm.confirm",
]
PAPER_LEDGER_FILE = ROOT / "out" / "paper_trade_ledger.jsonl"
REAL_PAPER_LEDGER_FILE = ROOT / "out" / "paper_trade_real_api_ledger.jsonl"
PAPER_CANONICAL_LEDGER_FILE = OUT_EXEC / "paper_trade_ledger_canonical.jsonl"
REAL_PAPER_CANONICAL_LEDGER_FILE = OUT_EXEC / "paper_trade_real_api_ledger_canonical.jsonl"
PAPER_RECONCILIATION_FILE = OUT_EXEC / "paper_ledger_reconciliation.json"
STATE_WRITER_SCAN_ROOTS = [
    ROOT / "code",
    ROOT / "code" / "execution",
    ROOT / "code" / "ops",
]
EXEC_HEARTBEAT = OUT_EXEC / "live_executor_heartbeat.json"
AUTOFIRE_HEARTBEAT = OUT_EXEC / "approval_autofire_heartbeat.json"
GROWTH_STATUS = OUT_EXEC / "vps_growth_controller_status.json"
QUEUE_FILE = OUT_EXEC / "live_operator_approval_queue.json"

JSON_OUT = OUT_OPS / "trading_stack_safety_audit_latest.json"
MD_OUT = DOCS / "TRADING_STACK_SAFETY_AUDIT_2026-06-19.md"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_load_error": str(exc), "_path": str(path)}
    return default


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_dt(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def age_minutes(value: Any) -> float | None:
    dt = parse_dt(value)
    if dt is None:
        return None
    return round(max((now_utc() - dt).total_seconds() / 60.0, 0.0), 3)


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "live", "enabled"}
    return False


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def runtime_summary(path: Path) -> dict[str, Any]:
    payload = load_json(path, {})
    return {
        "path": rel(path),
        "present": path.exists(),
        "mode": str(payload.get("mode") or payload.get("runtime_mode") or "").strip().lower(),
        "allow_live_orders": truthy(payload.get("allow_live_orders")),
        "paper_enabled": truthy(payload.get("paper_enabled")),
        "kill_switch": truthy(payload.get("kill_switch")),
        "force_live_mode": truthy(payload.get("force_live_mode")),
        "strict_live_only": truthy(payload.get("strict_live_only")),
        "x1000_auto_enabled": truthy(payload.get("x1000_auto_enabled")),
        "x1000_auto_apply": truthy(payload.get("x1000_auto_apply")),
        "load_error": str(payload.get("_load_error") or ""),
    }


def control_flag_summary(path: Path) -> dict[str, Any]:
    payload = load_json(path, {})
    return {
        "path": rel(path),
        "present": path.exists(),
        "live_enabled": truthy(payload.get("live_enabled")),
        "runtime_mode": str(payload.get("runtime_mode") or payload.get("mode") or "").strip().lower(),
        "kill_switch": truthy(payload.get("kill_switch")),
        "load_error": str(payload.get("_load_error") or ""),
    }


def marker_summary(path: Path) -> dict[str, Any]:
    present = path.exists() and path.is_file()
    size = path.stat().st_size if present else 0
    return {
        "path": rel(path),
        "present": present,
        "nonempty": bool(size),
        "bytes": size,
        "content_disclosed": False,
    }


def _expr_contains_filename(node: ast.AST | None, filename: str) -> bool:
    if node is None:
        return False
    return any(isinstance(child, ast.Constant) and child.value == filename for child in ast.walk(node))


def _assigned_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return {target.id for target in targets if isinstance(target, ast.Name)}


def discover_python_path_writers(filename: str) -> list[str]:
    """Find source files that write a named path without importing discovered code."""
    writer_functions = {"write_json", "save_json", "atomic_write_json", "write_text", "write_bytes"}
    writers: set[str] = set()
    for scan_root in STATE_WRITER_SCAN_ROOTS:
        if not scan_root.exists():
            continue
        for path in scan_root.glob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, SyntaxError):
                continue
            aliases: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)) and _expr_contains_filename(
                    node.value, filename
                ):
                    aliases.update(_assigned_names(node))
            if not aliases:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Attribute):
                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id in aliases
                        and node.func.attr in {"write_text", "write_bytes"}
                    ):
                        writers.add(rel(path))
                        break
                    function_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    function_name = node.func.id
                else:
                    function_name = ""
                if function_name not in writer_functions:
                    continue
                if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in aliases:
                    writers.add(rel(path))
                    break
    return sorted(writers)


def jsonl_integrity(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": rel(path),
        "present": path.exists(),
        "is_symlink": path.is_symlink(),
        "external_target": False,
        "target_basename": "",
        "bytes": 0,
        "modified_utc": "",
        "modified_age_min": None,
        "changed_during_scan": False,
        "total_rows": 0,
        "valid_json_rows": 0,
        "invalid_json_rows": 0,
        "fill_rows": 0,
        "unique_fill_ids": 0,
        "duplicate_fill_rows": 0,
        "duplicate_fill_ratio": 0.0,
        "missing_fill_id_rows": 0,
        "snapshot_rows": 0,
        "max_snapshot_trade_count": 0,
        "latest_timestamp": "",
        "modes": [],
        "sources": [],
    }
    if not path.exists():
        return result

    before = path.stat()
    result["bytes"] = before.st_size
    modified = datetime.fromtimestamp(before.st_mtime, timezone.utc)
    result["modified_utc"] = modified.isoformat()
    result["modified_age_min"] = round(max((now_utc() - modified).total_seconds() / 60.0, 0.0), 3)
    if path.is_symlink():
        try:
            result["target_basename"] = path.readlink().name
            resolved = path.resolve(strict=False)
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                result["external_target"] = True
        except OSError:
            pass

    fill_ids: set[str] = set()
    modes: set[str] = set()
    sources: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            result["total_rows"] += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                result["invalid_json_rows"] += 1
                continue
            if not isinstance(row, dict):
                result["invalid_json_rows"] += 1
                continue
            result["valid_json_rows"] += 1
            event_type = str(row.get("event_type") or "").strip().lower()
            mode = str(row.get("mode") or "").strip()
            source = str(row.get("source") or "").strip()
            timestamp = str(row.get("timestamp") or row.get("timestamp_utc") or "").strip()
            if mode:
                modes.add(mode)
            if source:
                sources.add(source)
            if timestamp and timestamp > result["latest_timestamp"]:
                result["latest_timestamp"] = timestamp
            if event_type == "account_snapshot":
                result["snapshot_rows"] += 1
                result["max_snapshot_trade_count"] = max(
                    result["max_snapshot_trade_count"], int(safe_float(row.get("trade_count"), 0.0))
                )
            if row.get("fill_id") is not None or event_type.endswith("fill"):
                result["fill_rows"] += 1
                fill_id = str(row.get("fill_id") or "").strip()
                if fill_id:
                    fill_ids.add(fill_id)
                else:
                    result["missing_fill_id_rows"] += 1

    after = path.stat()
    result["changed_during_scan"] = before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
    result["unique_fill_ids"] = len(fill_ids)
    result["duplicate_fill_rows"] = max(result["fill_rows"] - len(fill_ids) - result["missing_fill_id_rows"], 0)
    result["duplicate_fill_ratio"] = round(
        result["duplicate_fill_rows"] / result["fill_rows"], 6
    ) if result["fill_rows"] else 0.0
    result["modes"] = sorted(modes)[:12]
    result["sources"] = sorted(sources)[:12]
    return result


def reconciliation_summary(
    raw_ledgers: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    receipt = load_json(PAPER_RECONCILIATION_FILE, {})
    receipt_ledgers = receipt.get("ledgers") if isinstance(receipt.get("ledgers"), dict) else {}
    definitions = {
        "paper_ledger": (PAPER_LEDGER_FILE, PAPER_CANONICAL_LEDGER_FILE),
        "real_api_ledger": (REAL_PAPER_LEDGER_FILE, REAL_PAPER_CANONICAL_LEDGER_FILE),
    }
    result: dict[str, Any] = {
        "path": rel(PAPER_RECONCILIATION_FILE),
        "present": PAPER_RECONCILIATION_FILE.exists(),
        "schema": receipt.get("schema"),
        "status": receipt.get("status"),
        "raw_evidence_preserved": bool(receipt.get("raw_evidence_preserved", False)),
        "ledgers": {},
        "current": False,
    }
    all_current = bool(
        result["present"]
        and result["schema"] == "paper_ledger_reconciliation_v1"
        and result["status"] == "PASS"
        and result["raw_evidence_preserved"]
    )
    for key, (source, canonical) in definitions.items():
        receipt_row = receipt_ledgers.get(key) if isinstance(receipt_ledgers.get(key), dict) else {}
        canonical_integrity = jsonl_integrity(canonical)
        source_integrity = raw_ledgers[key]
        reasons: list[str] = []
        source_sha256 = ""
        canonical_sha256 = ""
        if not source.exists():
            reasons.append("source_missing")
        else:
            source_sha256 = sha256_file(source)
            if source_sha256 != str(receipt_row.get("source_sha256") or ""):
                reasons.append("source_hash_mismatch")
        if not canonical.exists():
            reasons.append("canonical_missing")
        else:
            canonical_sha256 = sha256_file(canonical)
            if canonical_sha256 != str(receipt_row.get("canonical_sha256") or ""):
                reasons.append("canonical_hash_mismatch")
        if receipt_row.get("status") != "PASS":
            reasons.append("receipt_row_not_pass")
        if canonical_integrity["invalid_json_rows"]:
            reasons.append("canonical_invalid_json")
        if canonical_integrity["missing_fill_id_rows"]:
            reasons.append("canonical_missing_fill_id")
        if canonical_integrity["duplicate_fill_rows"]:
            reasons.append("canonical_duplicate_fill_id")
        if canonical_integrity["unique_fill_ids"] != source_integrity["unique_fill_ids"]:
            reasons.append("canonical_unique_fill_count_mismatch")
        current = not reasons
        all_current = all_current and current
        result["ledgers"][key] = {
            "current": current,
            "reasons": reasons,
            "source_sha256": source_sha256,
            "canonical_path": rel(canonical),
            "canonical_sha256": canonical_sha256,
            "canonical_rows": canonical_integrity["total_rows"],
            "canonical_fill_rows": canonical_integrity["fill_rows"],
            "canonical_unique_fill_ids": canonical_integrity["unique_fill_ids"],
            "canonical_duplicate_fill_rows": canonical_integrity["duplicate_fill_rows"],
        }
    result["current"] = all_current
    return result


def add_blocker(blockers: list[str], condition: bool, message: str) -> None:
    if condition and message not in blockers:
        blockers.append(message)


def build_audit() -> dict[str, Any]:
    runtime = load_json(RUNTIME_FILE, {})
    executor = load_json(EXEC_HEARTBEAT, {})
    autofire = load_json(AUTOFIRE_HEARTBEAT, {})
    growth = load_json(GROWTH_STATUS, {})
    queue = load_json(QUEUE_FILE, {})

    canonical_runtime = runtime_summary(RUNTIME_FILE)
    legacy_runtime = runtime_summary(LEGACY_RUNTIME_FILE)
    account_runtimes = [runtime_summary(path) for path in ACCOUNT_RUNTIME_FILES]
    control_flags = [control_flag_summary(path) for path in CONTROL_FLAG_FILES]
    multi_account_policy = load_json(MULTI_ACCOUNT_POLICY_FILE, {})
    live_markers = [marker_summary(path) for path in LIVE_MARKER_FILES]
    paper_ledger = jsonl_integrity(PAPER_LEDGER_FILE)
    real_paper_ledger = jsonl_integrity(REAL_PAPER_LEDGER_FILE)
    reconciliation = reconciliation_summary(
        {"paper_ledger": paper_ledger, "real_api_ledger": real_paper_ledger}
    )
    paper_state_writers = discover_python_path_writers("paper_trade_state.json")

    runtime_mode = str(runtime.get("mode") or runtime.get("runtime_mode") or "").strip().lower()
    allow_live_orders = truthy(runtime.get("allow_live_orders"))
    paper_enabled = truthy(runtime.get("paper_enabled"))
    kill_switch = truthy(runtime.get("kill_switch"))
    executor_age_min = age_minutes(executor.get("timestamp_utc") or executor.get("timestamp") or executor.get("generated_utc"))
    autofire_age_min = age_minutes(autofire.get("generated_utc") or autofire.get("timestamp_utc"))
    growth_guard = growth.get("guard") if isinstance(growth.get("guard"), dict) else {}
    growth_summary = growth.get("summary") if isinstance(growth.get("summary"), dict) else {}

    queue_tickets = queue.get("tickets") if isinstance(queue.get("tickets"), list) else []
    pending_operator_tickets = [
        row for row in queue_tickets
        if str(row.get("decision_state") or row.get("approval_state") or "").upper().startswith("PENDING")
    ]

    safety_blockers: list[str] = []
    operational_readiness_blockers: list[str] = []
    warnings: list[str] = []

    add_blocker(safety_blockers, runtime_mode != "paper", f"runtime mode is not paper: {runtime_mode or 'missing'}")
    add_blocker(safety_blockers, allow_live_orders, "allow_live_orders is true")
    add_blocker(safety_blockers, not paper_enabled, "paper_enabled is false")
    add_blocker(safety_blockers, bool(canonical_runtime["load_error"]), "canonical runtime control is unreadable")
    for row in account_runtimes:
        add_blocker(safety_blockers, not row["present"], f"account runtime is missing: {row['path']}")
        add_blocker(
            safety_blockers,
            row["present"] and (row["mode"] != "paper" or row["allow_live_orders"] or not row["paper_enabled"]),
            f"account runtime is not paper-only: {row['path']}",
        )
    add_blocker(
        safety_blockers,
        legacy_runtime["present"]
        and (legacy_runtime["mode"] == "live" or legacy_runtime["allow_live_orders"] or legacy_runtime["force_live_mode"]),
        f"legacy runtime contradicts canonical paper authority: {legacy_runtime['path']}",
    )
    for row in control_flags:
        add_blocker(
            safety_blockers,
            row["present"] and (row["live_enabled"] or row["runtime_mode"] == "live"),
            f"control flag contradicts canonical paper authority: {row['path']}",
        )
    add_blocker(
        safety_blockers,
        MULTI_ACCOUNT_POLICY_FILE.exists()
        and (
            truthy(multi_account_policy.get("allow_live"))
            or str(multi_account_policy.get("default_mode") or "").strip().lower() == "live"
        ),
        f"multi-account policy permits live execution: {rel(MULTI_ACCOUNT_POLICY_FILE)}",
    )
    for row in live_markers:
        add_blocker(
            safety_blockers,
            row["nonempty"] and row["path"].endswith(".confirm"),
            f"stale live-arm marker requires removal or reconciliation: {row['path']}",
        )
    add_blocker(
        operational_readiness_blockers,
        executor_age_min is None or executor_age_min > 20.0,
        f"executor heartbeat stale or missing: {executor_age_min}",
    )
    add_blocker(
        operational_readiness_blockers,
        autofire_age_min is None or autofire_age_min > 20.0,
        f"autofire heartbeat stale or missing: {autofire_age_min}",
    )
    add_blocker(
        operational_readiness_blockers,
        not bool(growth_guard.get("heartbeat_ok", False)),
        "growth controller heartbeat check is not ok",
    )
    add_blocker(safety_blockers, str(growth.get("mode") or "").upper() != "SAFE_DRY_RUN", "growth controller is not in SAFE_DRY_RUN")
    add_blocker(safety_blockers, int(growth_summary.get("auto_fired_count") or 0) != 0, "auto-fired orders were detected")
    add_blocker(safety_blockers, len(paper_state_writers) != 1, f"paper state has {len(paper_state_writers)} write-capable implementations")
    for ledger_key, ledger in (
        ("paper_ledger", paper_ledger),
        ("real_api_ledger", real_paper_ledger),
    ):
        add_blocker(safety_blockers, not ledger["present"], f"paper evidence ledger is missing: {ledger['path']}")
        add_blocker(
            safety_blockers,
            ledger["invalid_json_rows"] > 0,
            f"paper evidence ledger has invalid JSON rows: {ledger['path']}",
        )
        add_blocker(
            safety_blockers,
            ledger["duplicate_fill_rows"] > 0
            and not bool(reconciliation["ledgers"].get(ledger_key, {}).get("current", False)),
            f"paper evidence ledger has unreconciled duplicate fill identities: {ledger['path']}",
        )
        add_blocker(
            safety_blockers,
            ledger["missing_fill_id_rows"] > 0,
            f"paper evidence ledger has fill rows without fill_id: {ledger['path']}",
        )
    add_blocker(
        safety_blockers,
        real_paper_ledger["unique_fill_ids"] > 0
        and real_paper_ledger["max_snapshot_trade_count"] > 0
        and real_paper_ledger["max_snapshot_trade_count"] > real_paper_ledger["unique_fill_ids"],
        "real-API snapshot trade_count exceeds the unique fill evidence available",
    )
    add_blocker(
        safety_blockers,
        real_paper_ledger["external_target"]
        and "paused" in str(real_paper_ledger["target_basename"]).lower()
        and safe_float(real_paper_ledger["modified_age_min"], 1e9) < 20.0
        and not reconciliation["current"],
        "external paper ledger target is labeled paused but has recent writes",
    )

    if not kill_switch:
        warnings.append("kill_switch is false; acceptable only while allow_live_orders=false and runtime mode=paper")
    if truthy(runtime.get("gate_override_enabled")):
        warnings.append("gate_override_enabled is true")
    if truthy(runtime.get("auto_convert_collateral")):
        warnings.append("auto_convert_collateral is true; keep disabled for unattended paper governance")
    if pending_operator_tickets:
        warnings.append(f"operator queue has {len(pending_operator_tickets)} pending review tickets")
    if int(growth_summary.get("actionable_candidates") or 0) <= 0:
        warnings.append("no actionable candidates in latest growth controller run; this is a research result, not a safety failure")
    if real_paper_ledger["external_target"]:
        warnings.append("real-API paper ledger is an external symlink; custody depends on the external target")
    if (
        real_paper_ledger["external_target"]
        and "paused" in str(real_paper_ledger["target_basename"]).lower()
        and safe_float(real_paper_ledger["modified_age_min"], 1e9) < 20.0
        and reconciliation["current"]
    ):
        warnings.append(
            "external paper ledger target has a legacy paused basename but recent writes are covered by the current hash-bound reconciliation"
        )
    for ledger_key, ledger in (
        ("paper_ledger", paper_ledger),
        ("real_api_ledger", real_paper_ledger),
    ):
        if ledger["duplicate_fill_rows"] > 0 and reconciliation["ledgers"].get(ledger_key, {}).get("current"):
            warnings.append(
                f"raw {ledger_key} retains {ledger['duplicate_fill_rows']} duplicate historical rows; a current canonical reconciliation excludes them without rewriting evidence"
            )
    if (
        real_paper_ledger["unique_fill_ids"] > real_paper_ledger["max_snapshot_trade_count"] > 0
    ):
        warnings.append(
            "real-API snapshot trade_count is a collector checkpoint lower bound; canonical unique fills include earlier retained history"
        )
    if real_paper_ledger["changed_during_scan"]:
        warnings.append("real-API paper ledger changed during audit; counts are a moving snapshot")
    if paper_ledger["changed_during_scan"]:
        warnings.append("paper ledger changed during audit; counts are a moving snapshot")

    live_promotion_blockers = safety_blockers + [
        item for item in operational_readiness_blockers if item not in safety_blockers
    ]
    safety_posture = "PAPER_SAFE" if not safety_blockers else "UNSAFE"
    if safety_blockers:
        operational_posture = "UNSAFE"
    elif operational_readiness_blockers:
        operational_posture = "OFFLINE_SAFE"
    else:
        operational_posture = "READY_FOR_GATED_REVIEW"

    posture = "BLOCK_LIVE"
    if not live_promotion_blockers and runtime_mode == "paper" and not allow_live_orders and paper_enabled:
        posture = "PAPER_OK"

    return {
        "generated_utc": now_utc().isoformat(),
        "schema": "trading_stack_safety_audit_v3",
        "posture": posture,
        "safety_posture": safety_posture,
        "operational_posture": operational_posture,
        "execution_authorized": False,
        "claim_status": "NOT_VALIDATED_FOR_ALPHA_OR_LIVE_EXECUTION",
        "secret_handling": "The audit reads control booleans, file metadata, and non-secret ledger fields only. It never emits credentials, order identifiers, fill identifiers, or live-arm contents.",
        "runtime": {
            "mode": runtime_mode,
            "allow_live_orders": allow_live_orders,
            "paper_enabled": paper_enabled,
            "kill_switch": kill_switch,
            "max_notional_per_trade_usd": safe_float(runtime.get("max_notional_per_trade_usd"), 0.0),
            "max_daily_loss_usd": safe_float(runtime.get("max_daily_loss_usd"), 0.0),
            "max_open_positions": int(safe_float(runtime.get("max_open_positions"), 0.0)),
        },
        "evidence": {
            "executor_heartbeat_age_min": executor_age_min,
            "executor_status": executor.get("status"),
            "executor_reason": executor.get("reason"),
            "symbol_intel_stale": bool(executor.get("symbol_intel_stale", False)),
            "autofire_heartbeat_age_min": autofire_age_min,
            "autofire_status": autofire.get("status"),
            "autofire_eligible_count": int(safe_float(autofire.get("eligible_count"), 0.0)),
            "autofire_approved_buy_count": int(safe_float(autofire.get("approved_buy_count"), 0.0)),
            "growth_mode": growth.get("mode"),
            "growth_guard_reasons": growth_guard.get("reasons", []),
            "growth_actionable_candidates": int(safe_float(growth_summary.get("actionable_candidates"), 0.0)),
            "growth_emitted_count": int(safe_float(growth_summary.get("emitted_count"), 0.0)),
            "growth_auto_fired_count": int(safe_float(growth_summary.get("auto_fired_count"), 0.0)),
            "portfolio_est_usd": safe_float(growth_guard.get("portfolio_est_usd"), 0.0),
            "operator_pending_tickets": len(pending_operator_tickets),
        },
        "authority": {
            "canonical_runtime": canonical_runtime,
            "legacy_runtime": legacy_runtime,
            "account_runtimes": account_runtimes,
            "control_flags": control_flags,
            "multi_account_policy": {
                "path": rel(MULTI_ACCOUNT_POLICY_FILE),
                "present": MULTI_ACCOUNT_POLICY_FILE.exists(),
                "allow_live": truthy(multi_account_policy.get("allow_live")),
                "default_mode": str(multi_account_policy.get("default_mode") or "").strip().lower(),
            },
            "live_markers": live_markers,
            "paper_state_writer_count": len(paper_state_writers),
            "paper_state_writers": paper_state_writers,
        },
        "paper_evidence_integrity": {
            "paper_ledger": paper_ledger,
            "real_api_ledger": real_paper_ledger,
            "reconciliation": reconciliation,
            "alpha_validated": False,
            "live_execution_validated": False,
            "boundary": "Ledger presence and local consistency are necessary controls, not proof of alpha, independent validation, or live readiness.",
        },
        "safety_blockers": safety_blockers,
        "operational_readiness_blockers": operational_readiness_blockers,
        "live_promotion_blockers": live_promotion_blockers,
        "blockers": live_promotion_blockers,
        "warnings": warnings,
        "promotion_rule": "Live execution remains blocked until authority conflicts are removed, raw duplicate history has a current hash-bound canonical reconciliation, one canonical state writer remains, paper/live heartbeats are fresh, full order/fill reconciliation passes, and a human operator grants a separate short-lived action-time approval. This audit never authorizes execution.",
    }


def render_markdown(audit: dict[str, Any]) -> str:
    runtime = audit["runtime"]
    evidence = audit["evidence"]
    authority = audit["authority"]
    integrity = audit["paper_evidence_integrity"]
    canonical = authority["canonical_runtime"]
    legacy = authority["legacy_runtime"]
    paper_ledger = integrity["paper_ledger"]
    real_ledger = integrity["real_api_ledger"]
    reconciliation = integrity["reconciliation"]
    blockers = audit.get("blockers", [])
    warnings = audit.get("warnings", [])
    lines = [
        "# Trading Stack Safety Audit",
        "",
        f"Generated UTC: {audit['generated_utc']}",
        "",
        f"Posture: {audit['posture']}",
        "",
        f"Safety posture: {audit['safety_posture']}",
        "",
        f"Operational posture: {audit['operational_posture']}",
        "",
        f"Execution authorized: {audit['execution_authorized']}",
        "",
        f"Claim status: {audit['claim_status']}",
        "",
        "## Claim Boundary",
        "",
        integrity["boundary"],
        "",
        "## Secret Handling",
        "",
        audit["secret_handling"],
        "",
        "## Runtime Gates",
        "",
        f"- mode: {runtime['mode']}",
        f"- allow_live_orders: {runtime['allow_live_orders']}",
        f"- paper_enabled: {runtime['paper_enabled']}",
        f"- kill_switch: {runtime['kill_switch']}",
        f"- max_notional_per_trade_usd: {runtime['max_notional_per_trade_usd']}",
        f"- max_daily_loss_usd: {runtime['max_daily_loss_usd']}",
        f"- max_open_positions: {runtime['max_open_positions']}",
        "",
        "## Evidence Readout",
        "",
        f"- executor heartbeat age min: {evidence['executor_heartbeat_age_min']}",
        f"- executor status/reason: {evidence['executor_status']} / {evidence['executor_reason']}",
        f"- symbol intel stale: {evidence['symbol_intel_stale']}",
        f"- autofire heartbeat age min: {evidence['autofire_heartbeat_age_min']}",
        f"- autofire eligible/approved buy: {evidence['autofire_eligible_count']} / {evidence['autofire_approved_buy_count']}",
        f"- growth mode: {evidence['growth_mode']}",
        f"- growth guard reasons: {evidence['growth_guard_reasons']}",
        f"- actionable/emitted/auto-fired: {evidence['growth_actionable_candidates']} / {evidence['growth_emitted_count']} / {evidence['growth_auto_fired_count']}",
        f"- portfolio estimate USD: {evidence['portfolio_est_usd']}",
        f"- operator pending tickets: {evidence['operator_pending_tickets']}",
        "",
        "## Authority Reconciliation",
        "",
        f"- canonical runtime: {canonical['path']} mode={canonical['mode']} allow_live_orders={canonical['allow_live_orders']} paper_enabled={canonical['paper_enabled']}",
        f"- legacy runtime: {legacy['path']} present={legacy['present']} mode={legacy['mode']} allow_live_orders={legacy['allow_live_orders']}",
        f"- account runtimes: {len(authority['account_runtimes'])}",
        f"- nonempty live-arm markers: {sum(1 for row in authority['live_markers'] if row['nonempty'] and row['path'].endswith('.confirm'))}",
        f"- paper state writer count: {authority['paper_state_writer_count']}",
        f"- paper state writers: {', '.join(authority['paper_state_writers']) if authority['paper_state_writers'] else 'none'}",
        "",
        "## Paper Evidence Integrity",
        "",
        f"- local paper ledger rows/fills/unique/duplicates: {paper_ledger['total_rows']} / {paper_ledger['fill_rows']} / {paper_ledger['unique_fill_ids']} / {paper_ledger['duplicate_fill_rows']}",
        f"- real-API ledger rows/fills/unique/duplicates: {real_ledger['total_rows']} / {real_ledger['fill_rows']} / {real_ledger['unique_fill_ids']} / {real_ledger['duplicate_fill_rows']}",
        f"- real-API snapshot rows/max trade_count: {real_ledger['snapshot_rows']} / {real_ledger['max_snapshot_trade_count']}",
        f"- real-API ledger external target: {real_ledger['external_target']}",
        f"- real-API ledger changed during scan: {real_ledger['changed_during_scan']}",
        f"- reconciliation current: {reconciliation['current']}",
        f"- reconciliation receipt: {reconciliation['path']}",
        "",
        "## Safety Blockers",
        "",
    ]
    safety_blockers = audit.get("safety_blockers", [])
    operational_blockers = audit.get("operational_readiness_blockers", [])
    if safety_blockers:
        lines.extend(f"- {item}" for item in safety_blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Operational Readiness Blockers", ""])
    if operational_blockers:
        lines.extend(f"- {item}" for item in operational_blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Live Promotion Blockers", ""])
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- none")
    lines.extend(["", "## Promotion Rule", "", audit["promotion_rule"], ""])
    return "\n".join(lines)


def main() -> int:
    OUT_OPS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    JSON_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    MD_OUT.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"posture": audit["posture"], "blockers": len(audit["blockers"]), "json": str(JSON_OUT), "md": str(MD_OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
