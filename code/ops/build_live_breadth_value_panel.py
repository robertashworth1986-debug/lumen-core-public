from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOURS_PER_DAY = 24.0
DAYS_PER_YEAR = 365.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def clamp_pct(value: Any) -> float:
    n = to_float(value, 0.0)
    if n < 0.0:
        return 0.0
    if n > 100.0:
        return 100.0
    return n


def to_percent(value: Any) -> float:
    n = to_float(value, 0.0)
    if 0.0 <= n <= 1.0:
        return n * 100.0
    return n


def normalize_token(value: Any) -> str:
    text = str(value or "").strip().upper()
    return "".join(ch for ch in text if ch.isalnum())


def parse_utc(value: Any) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    fmts = (
        "%Y%m%dT%H%M%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S%z",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue

    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def rel_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            text = raw.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def load_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]
    except Exception:
        return []


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def resolve_existing(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def pick_latest_frozen_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    latest_ts: dict[tuple[str, str, str], datetime] = {}

    for row in rows:
        source = str(row.get("source") or "UNKNOWN")
        sector = str(row.get("sector") or "unknown")
        constraint = str(row.get("constraint") or "default")
        key = (normalize_token(source), normalize_token(sector), normalize_token(constraint))

        ts = parse_utc(row.get("generated_utc"))
        prev = latest_ts.get(key)
        if prev is None or ts >= prev:
            latest[key] = row
            latest_ts[key] = ts

    out = list(latest.values())
    out.sort(key=lambda r: parse_utc(r.get("generated_utc")), reverse=True)
    return out


def add_alias(source_lookup: dict[str, dict[str, Any]], key: str, row: dict[str, Any]) -> None:
    norm = normalize_token(key)
    if norm and norm not in source_lookup:
        source_lookup[norm] = row


def build_registry_summary(path: Path) -> dict[str, Any]:
    registry = load_json(path)
    rows: list[dict[str, Any]] = []
    if isinstance(registry, dict):
        candidate_rows = registry.get("rows", [])
        if isinstance(candidate_rows, list) and candidate_rows:
            rows = [r for r in candidate_rows if isinstance(r, dict)]
        else:
            # Compatibility path: some registries use `sources` entries with `status` + `env`.
            candidate_sources = registry.get("sources", [])
            if isinstance(candidate_sources, list):
                normalized_rows: list[dict[str, Any]] = []
                for raw in candidate_sources:
                    if not isinstance(raw, dict):
                        continue
                    status = str(raw.get("status") or "").upper()
                    env_name = str(raw.get("env") or "").strip()
                    row_count = to_int(raw.get("rows"), 0)

                    enabled = bool(raw.get("enabled", False))
                    if not enabled:
                        enabled = bool(env_name) or status in {
                            "LIVE_KEY_PRESENT",
                            "LIVE",
                            "ENABLED",
                            "OK",
                            "HEALTHY",
                        }

                    measured = bool(raw.get("measured", False))
                    if not measured:
                        measured = row_count > 0 or status in {
                            "LIVE_KEY_PRESENT",
                            "MEASURED",
                            "LIVE",
                        }

                    normalized = dict(raw)
                    normalized["enabled"] = enabled
                    normalized["measured"] = measured
                    if not isinstance(normalized.get("translated_value"), dict):
                        normalized["translated_value"] = {}
                    normalized_rows.append(normalized)

                rows = normalized_rows

    enabled_rows = [r for r in rows if isinstance(r, dict) and bool(r.get("enabled", False))]
    measured_rows = [r for r in enabled_rows if bool(r.get("measured", False))]

    source_lookup: dict[str, dict[str, Any]] = {}
    for row in enabled_rows:
        source = str(row.get("source") or "")
        norm = normalize_token(source)
        if norm:
            source_lookup[norm] = row

        if norm == "ALPACA":
            add_alias(source_lookup, "ALPACA_PAPER", row)
            add_alias(source_lookup, "ALPACAPAPER", row)
        if norm == "MASSIVE":
            add_alias(source_lookup, "POLYGON", row)
        if norm == "NOAANCEI":
            add_alias(source_lookup, "NOAA", row)

    translated_hour = 0.0
    translated_day = 0.0
    translated_year = 0.0
    sectors: set[str] = set()

    for row in measured_rows:
        translated = row.get("translated_value", {}) if isinstance(row, dict) else {}
        if not isinstance(translated, dict):
            translated = {}
        translated_hour += to_float(translated.get("hour"), 0.0)
        translated_day += to_float(translated.get("day"), 0.0)
        translated_year += to_float(translated.get("year"), 0.0)
        sectors.add(str(row.get("sector") or "unknown"))

    enabled_sources = len(enabled_rows)
    measured_sources = len(measured_rows)
    coverage_pct = (float(measured_sources) / float(enabled_sources) * 100.0) if enabled_sources else 0.0

    return {
        "generated_utc": str(registry.get("generated_utc") or ""),
        "rows_total": len(rows),
        "enabled_sources": enabled_sources,
        "measured_sources": measured_sources,
        "measured_coverage_pct": coverage_pct,
        "measured_sectors": sorted(sectors),
        "translated_hourly_value_usd": translated_hour,
        "translated_daily_value_usd": translated_day,
        "translated_annual_value_usd": translated_year,
        "source_lookup": source_lookup,
    }


def classify_action(weighted_gain_pct: float) -> str:
    if weighted_gain_pct >= 10.0:
        return "scale_now"
    if weighted_gain_pct >= 3.0:
        return "scale_guarded"
    if weighted_gain_pct >= 1.0:
        return "compound"
    return "observe"


def build_sector_rollup(
    latest_rows: list[dict[str, Any]],
    source_lookup: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sector_rollup: dict[str, dict[str, Any]] = {}
    source_rows: list[dict[str, Any]] = []

    for row in latest_rows:
        source = str(row.get("source") or "UNKNOWN")
        sector = str(row.get("sector") or "unknown")
        constraint = str(row.get("constraint") or "default")
        generated_utc = str(row.get("generated_utc") or "")

        baseline = to_float(row.get("baseline_loss_rate_usd_per_hour"), 0.0)
        gain_pct = to_float(row.get("optimization_gain_pct"), 0.0)
        est_hour = to_float(row.get("estimated_hourly_value_usd"), 0.0)

        if est_hour <= 0.0 and baseline > 0.0 and gain_pct > 0.0:
            est_hour = baseline * (gain_pct / 100.0)

        source_registry = source_lookup.get(normalize_token(source), {})
        measured_source = bool(source_registry.get("measured", False)) if isinstance(source_registry, dict) else False
        enabled_source = bool(source_registry.get("enabled", False)) if isinstance(source_registry, dict) else False

        translated = source_registry.get("translated_value", {}) if isinstance(source_registry, dict) else {}
        if not isinstance(translated, dict):
            translated = {}

        source_rows.append(
            {
                "generated_utc": generated_utc,
                "source": source,
                "sector": sector,
                "constraint": constraint,
                "baseline_loss_rate_usd_per_hour": round(baseline, 4),
                "optimization_gain_pct": round(gain_pct, 4),
                "estimated_hourly_value_usd": round(est_hour, 4),
                "estimated_daily_value_usd": round(est_hour * HOURS_PER_DAY, 4),
                "estimated_annual_value_usd": round(est_hour * HOURS_PER_DAY * DAYS_PER_YEAR, 4),
                "predicted_failure_cost_usd": round(to_float(row.get("predicted_failure_cost_usd"), 0.0), 4),
                "estimated_avoided_loss_usd": round(to_float(row.get("estimated_avoided_loss_usd"), 0.0), 4),
                "estimated_residual_loss_usd": round(to_float(row.get("estimated_residual_loss_usd"), 0.0), 4),
                "trust_tier": str(row.get("trust_tier") or ""),
                "key_present": bool(row.get("key_present", False)),
                "enabled_source": enabled_source,
                "measured_source": measured_source,
                "translated_source_yearly_value_usd": round(to_float(translated.get("year"), 0.0), 4),
            }
        )

        agg = sector_rollup.setdefault(
            sector,
            {
                "sector": sector,
                "source_count": 0,
                "measured_source_count": 0,
                "total_baseline_loss_rate_usd_per_hour": 0.0,
                "total_estimated_hourly_value_usd": 0.0,
                "weighted_gain_numerator": 0.0,
                "weighted_gain_denominator": 0.0,
                "latest_generated_utc": "",
                "sources": set(),
                "trust_tiers": set(),
            },
        )

        agg["source_count"] += 1
        if measured_source:
            agg["measured_source_count"] += 1
        agg["total_baseline_loss_rate_usd_per_hour"] += baseline
        agg["total_estimated_hourly_value_usd"] += est_hour
        agg["weighted_gain_numerator"] += gain_pct * max(baseline, 0.0)
        agg["weighted_gain_denominator"] += max(baseline, 0.0)
        agg["latest_generated_utc"] = max(str(agg["latest_generated_utc"]), generated_utc)
        agg["sources"].add(source)

        trust = str(row.get("trust_tier") or "")
        if trust:
            agg["trust_tiers"].add(trust)

    sectors: list[dict[str, Any]] = []
    for sector, agg in sector_rollup.items():
        denom = to_float(agg.get("weighted_gain_denominator"), 0.0)
        weighted_gain_pct = to_float(agg.get("weighted_gain_numerator"), 0.0) / denom if denom > 0.0 else 0.0

        est_hour = to_float(agg.get("total_estimated_hourly_value_usd"), 0.0)
        sectors.append(
            {
                "sector": sector,
                "source_count": to_int(agg.get("source_count"), 0),
                "measured_source_count": to_int(agg.get("measured_source_count"), 0),
                "total_baseline_loss_rate_usd_per_hour": round(to_float(agg.get("total_baseline_loss_rate_usd_per_hour"), 0.0), 4),
                "weighted_optimization_gain_pct": round(weighted_gain_pct, 4),
                "total_estimated_hourly_value_usd": round(est_hour, 4),
                "total_estimated_daily_value_usd": round(est_hour * HOURS_PER_DAY, 4),
                "total_estimated_annual_value_usd": round(est_hour * HOURS_PER_DAY * DAYS_PER_YEAR, 4),
                "recommended_action": classify_action(weighted_gain_pct),
                "latest_generated_utc": str(agg.get("latest_generated_utc") or ""),
                "sample_sources": ", ".join(sorted(agg.get("sources", set()))[:6]),
                "trust_tiers": ", ".join(sorted(agg.get("trust_tiers", set()))),
            }
        )

    sectors.sort(key=lambda r: to_float(r.get("total_estimated_hourly_value_usd"), 0.0), reverse=True)
    source_rows.sort(key=lambda r: to_float(r.get("estimated_hourly_value_usd"), 0.0), reverse=True)
    return sectors, source_rows


def fallback_sectors_from_reference(reference_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for row in reference_rows:
        sector = str(row.get("sector") or "unknown")
        source = str(row.get("source") or "UNKNOWN")

        gain_pct = to_float(row.get("optimization_gain_pct"), 0.0)
        est_hour = to_float(row.get("estimated_hourly_value_usd"), 0.0)

        agg = grouped.setdefault(
            sector,
            {
                "sector": sector,
                "source_count": 0,
                "measured_source_count": 0,
                "total_baseline_loss_rate_usd_per_hour": 0.0,
                "weighted_optimization_gain_pct": 0.0,
                "weighted_gain_numerator": 0.0,
                "weighted_gain_denominator": 0.0,
                "total_estimated_hourly_value_usd": 0.0,
                "latest_generated_utc": "",
                "sources": set(),
            },
        )

        agg["source_count"] += 1
        agg["total_estimated_hourly_value_usd"] += est_hour
        agg["weighted_gain_numerator"] += gain_pct * max(est_hour, 1.0)
        agg["weighted_gain_denominator"] += max(est_hour, 1.0)
        agg["sources"].add(source)

    rows: list[dict[str, Any]] = []
    for sector, agg in grouped.items():
        denom = to_float(agg.get("weighted_gain_denominator"), 0.0)
        weighted_gain_pct = to_float(agg.get("weighted_gain_numerator"), 0.0) / denom if denom > 0.0 else 0.0
        est_hour = to_float(agg.get("total_estimated_hourly_value_usd"), 0.0)
        rows.append(
            {
                "sector": sector,
                "source_count": to_int(agg.get("source_count"), 0),
                "measured_source_count": 0,
                "total_baseline_loss_rate_usd_per_hour": 0.0,
                "weighted_optimization_gain_pct": round(weighted_gain_pct, 4),
                "total_estimated_hourly_value_usd": round(est_hour, 4),
                "total_estimated_daily_value_usd": round(est_hour * HOURS_PER_DAY, 4),
                "total_estimated_annual_value_usd": round(est_hour * HOURS_PER_DAY * DAYS_PER_YEAR, 4),
                "recommended_action": classify_action(weighted_gain_pct),
                "latest_generated_utc": "",
                "sample_sources": ", ".join(sorted(agg.get("sources", set()))[:6]),
                "trust_tiers": "",
            }
        )

    rows.sort(key=lambda r: to_float(r.get("total_estimated_hourly_value_usd"), 0.0), reverse=True)
    return rows


def mission_kalisha_score(
    router_win_pct: float,
    stacker_win_rate: float,
    blender_win_pct: float,
    cov80_pct: float,
    cov95_pct: float,
    anomaly_rate_pct: float,
    regime_break_pct: float,
) -> float:
    calibration = (cov80_pct * 0.6) + (cov95_pct * 0.4)
    stability = clamp_pct(100.0 - (anomaly_rate_pct * 1.35) - (regime_break_pct * 0.95))

    score = (
        (router_win_pct * 0.27)
        + (stacker_win_rate * 0.24)
        + (blender_win_pct * 0.19)
        + (calibration * 0.18)
        + (stability * 0.12)
    )
    return clamp_pct(score)


def load_evidence_signals(evidence_roots: list[Path]) -> dict[str, Any]:
    for root in evidence_roots:
        latest_path = root / "latest.txt"
        if not latest_path.exists():
            continue

        run_utc = latest_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not run_utc:
            continue

        run_dir = root / "runs" / run_utc
        summary = load_json(run_dir / "summary.json")
        router_eval = load_json(run_dir / "router" / "eval.json")
        stacker_eval = load_json(run_dir / "stacker" / "eval.json")
        blender_eval = load_json(run_dir / "blender" / "eval.json")
        calib = load_json(run_dir / "calibration" / "summary.json")
        anom = load_json(run_dir / "anomalies" / "summary.json")
        regime = load_json(run_dir / "regime" / "summary.json")

        router_summary = router_eval.get("summary", {}) if isinstance(router_eval, dict) else {}
        if not isinstance(router_summary, dict):
            router_summary = {}

        router_edge_pct = to_float(router_summary.get("router_chose_correctly_pct"), 0.0)
        if router_edge_pct <= 0.0:
            router_rate = to_percent((router_summary.get("win_rates") or {}).get("router"))
            router_edge_pct = router_rate

        stacker_summary = stacker_eval.get("summary", {}) if isinstance(stacker_eval, dict) else {}
        if not isinstance(stacker_summary, dict):
            stacker_summary = {}
        stacker_n = to_float(stacker_summary.get("n_datasets"), 0.0)
        stacker_router_wins = to_float((stacker_summary.get("win_counts") or {}).get("router"), 0.0)
        stacker_win_rate = (stacker_router_wins / stacker_n * 100.0) if stacker_n > 0 else 0.0

        blender_summary = blender_eval.get("summary", {}) if isinstance(blender_eval, dict) else {}
        if not isinstance(blender_summary, dict):
            blender_summary = {}
        blender_n = to_float(blender_summary.get("n_datasets"), 0.0)
        blender_wins = to_float((blender_summary.get("win_counts_in_blend_plus_fams") or {}).get("blend"), 0.0)
        blender_win_pct = (blender_wins / blender_n * 100.0) if blender_n > 0 else 0.0

        overall = calib.get("overall", {}) if isinstance(calib, dict) else {}
        if not isinstance(overall, dict):
            overall = {}
        cov80_pct = to_percent(overall.get("mean_cov80"))
        cov95_pct = to_percent(overall.get("mean_cov95"))

        anom_n = to_float(anom.get("n_datasets"), 0.0)
        anom_2s = to_float(anom.get("n_with_2sigma_anomaly"), 0.0)
        anomaly_rate_pct = (anom_2s / anom_n * 100.0) if anom_n > 0 else 0.0

        regime_n = to_float(regime.get("n_datasets"), 0.0)
        regime_breaks = to_float(regime.get("n_with_any_mean_break"), 0.0)
        regime_break_pct = (regime_breaks / regime_n * 100.0) if regime_n > 0 else 0.0

        kalisha = mission_kalisha_score(
            router_win_pct=router_edge_pct,
            stacker_win_rate=stacker_win_rate,
            blender_win_pct=blender_win_pct,
            cov80_pct=cov80_pct,
            cov95_pct=cov95_pct,
            anomaly_rate_pct=anomaly_rate_pct,
            regime_break_pct=regime_break_pct,
        )

        harmonic_win_rate_pct = to_percent(summary.get("harmonic_win_rate")) if isinstance(summary, dict) else 0.0
        n_datasets_succeeded = to_int(summary.get("n_datasets_succeeded"), 0) if isinstance(summary, dict) else 0

        return {
            "evidence_root": str(root),
            "run_utc": run_utc,
            "router_edge_pct": round(router_edge_pct, 4),
            "harmonic_win_rate_pct": round(harmonic_win_rate_pct, 4),
            "stacker_router_win_rate_pct": round(stacker_win_rate, 4),
            "blender_win_rate_pct": round(blender_win_pct, 4),
            "cov80_pct": round(cov80_pct, 4),
            "cov95_pct": round(cov95_pct, 4),
            "anomaly_rate_pct": round(anomaly_rate_pct, 4),
            "regime_break_pct": round(regime_break_pct, 4),
            "kalisha_prediction_score": round(kalisha, 4),
            "datasets_succeeded": n_datasets_succeeded,
        }

    return {
        "evidence_root": "",
        "run_utc": "",
        "router_edge_pct": 0.0,
        "harmonic_win_rate_pct": 0.0,
        "stacker_router_win_rate_pct": 0.0,
        "blender_win_rate_pct": 0.0,
        "cov80_pct": 0.0,
        "cov95_pct": 0.0,
        "anomaly_rate_pct": 0.0,
        "regime_break_pct": 0.0,
        "kalisha_prediction_score": 0.0,
        "datasets_succeeded": 0,
    }


def build_metric_readiness(
    runtime_control_path: Path,
    controller_status_path: Path,
    vps_growth_proof_path: Path,
) -> dict[str, Any]:
    runtime = load_json(runtime_control_path)
    controller = load_json(controller_status_path)
    vps = load_json(vps_growth_proof_path)

    guard = controller.get("guard", {}) if isinstance(controller, dict) else {}
    if not isinstance(guard, dict):
        guard = {}

    perf = vps.get("live_trade_performance", {}) if isinstance(vps, dict) else {}
    if not isinstance(perf, dict):
        perf = {}

    runtime_allow_live = bool(runtime.get("allow_live_orders", False))
    runtime_kill_switch = bool(runtime.get("kill_switch", True))
    runtime_hard_safety = bool(runtime.get("hard_safety_only_mode", False))
    runtime_max_notional = round(to_float(runtime.get("max_notional_per_trade_usd"), 0.0), 4)
    runtime_max_daily_loss = round(to_float(runtime.get("max_daily_loss_usd"), 0.0), 4)
    runtime_symbol = str(runtime.get("symbol") or "UNIVERSE")
    runtime_mode = str(runtime.get("mode") or "paper")

    controller_mode = str(controller.get("mode") or "UNKNOWN") if isinstance(controller, dict) else "UNKNOWN"
    controller_allow_live = bool(guard.get("allow_live", False))
    controller_live_requested = bool(guard.get("live_requested", False))
    controller_trade_rows = to_int(guard.get("trade_rows_total"), 0)
    controller_portfolio_est = round(to_float(guard.get("portfolio_est_usd"), 0.0), 4)

    closed_live_trades = to_int(perf.get("closed_live_count"), controller_trade_rows)
    if closed_live_trades <= 0:
        closed_live_trades = controller_trade_rows

    win_rate_pct = round(to_float(perf.get("win_rate_pct"), 0.0), 4)
    realized_net_usd = round(to_float(perf.get("realized_net_usd"), 0.0), 4)
    max_drawdown_pct = round(to_float(perf.get("max_drawdown_pct"), 0.0), 4)

    metrics_stable_threshold = 200
    capital_mode = "micro_capitalized" if controller_portfolio_est > 0 and controller_portfolio_est < 1000 else "standard"
    stability_progress_pct = 0.0
    if metrics_stable_threshold > 0:
        stability_progress_pct = min(100.0, (100.0 * float(closed_live_trades)) / float(metrics_stable_threshold))
    provisional_label = (
        "provisional_under_guardrails"
        if closed_live_trades < metrics_stable_threshold
        else "sample_stable_for_risk_metrics"
    )

    status = "capital_and_risk_guarded"
    if runtime_allow_live and not runtime_kill_switch and controller_allow_live:
        status = "funded_live_window_active"
    elif runtime_allow_live and runtime_hard_safety:
        status = "limited_live_safety_mode"

    explanation = (
        "PnL and risk-adjusted metrics are provisional because the observed sample does not meet the "
        "predeclared stability gate. Breadth coverage, routing scores, and cross-sector estimates are "
        "first-party diagnostics; they do not validate alpha, savings, or field performance."
    )
    if closed_live_trades < metrics_stable_threshold:
        explanation += (
            f" Closed-trade sample depth is {round(stability_progress_pct, 2)}% of the institutional stability threshold "
            "required before Sharpe/CAGR/Sortino are promoted from provisional to stable reporting."
        )

    return {
        "status": status,
        "provisional_label": provisional_label,
        "explanation": explanation,
        "target_window": "thursday_readiness_window",
        "capital_mode": capital_mode,
        "closed_live_trades": closed_live_trades,
        "metrics_stable_threshold": metrics_stable_threshold,
        "stability_progress_pct": round(stability_progress_pct, 2),
        "provisional_due_to": [
            "capital_and_notional_limits",
            "risk_gates_active",
            "sample_depth_below_institutional_threshold",
        ],
        "provisional_metrics": {
            "win_rate_pct": win_rate_pct,
            "realized_net_usd": realized_net_usd,
            "max_drawdown_pct": max_drawdown_pct,
        },
        "runtime_gates": {
            "runtime_mode": runtime_mode,
            "symbol": runtime_symbol,
            "allow_live_orders": runtime_allow_live,
            "kill_switch": runtime_kill_switch,
            "hard_safety_only_mode": runtime_hard_safety,
            "max_notional_per_trade_usd": runtime_max_notional,
            "max_daily_loss_usd": runtime_max_daily_loss,
        },
        "controller_gates": {
            "mode": controller_mode,
            "live_requested": controller_live_requested,
            "allow_live": controller_allow_live,
            "trade_rows_total": controller_trade_rows,
            "portfolio_est_usd": controller_portfolio_est,
        },
        "thursday_plan": [
            "keep execution in paper/replay mode and preserve the current safety gates",
            "freeze the source registry, dataset window, baseline, metrics, costs, and failure rules",
            "obtain non-author execution or buyer-owned data before promoting performance claims",
            "publish risk-adjusted metrics only after the sample and independence gates pass",
        ],
        "evidence_refs": {
            "runtime_control_json": str(runtime_control_path),
            "controller_status_json": str(controller_status_path),
            "vps_growth_proof_json": str(vps_growth_proof_path),
        },
    }


def build_investor_metric_readiness_payload(
    report: dict[str, Any],
    workspace_root: Path,
    panel_json_primary: Path,
    panel_json_tagged: Path,
) -> dict[str, Any]:
    headline = report.get("headline", {}) if isinstance(report, dict) else {}
    if not isinstance(headline, dict):
        headline = {}

    readiness = report.get("metric_readiness", {}) if isinstance(report, dict) else {}
    if not isinstance(readiness, dict):
        readiness = {}

    runtime_gates = readiness.get("runtime_gates", {}) if isinstance(readiness, dict) else {}
    if not isinstance(runtime_gates, dict):
        runtime_gates = {}

    controller_gates = readiness.get("controller_gates", {}) if isinstance(readiness, dict) else {}
    if not isinstance(controller_gates, dict):
        controller_gates = {}

    provisional_metrics = readiness.get("provisional_metrics", {}) if isinstance(readiness, dict) else {}
    if not isinstance(provisional_metrics, dict):
        provisional_metrics = {}

    proof_refs = report.get("proof_refs", {}) if isinstance(report, dict) else {}
    if not isinstance(proof_refs, dict):
        proof_refs = {}

    payload = {
        "generated_utc": now_iso(),
        "scope": {
            "workspace_root": str(workspace_root),
            "purpose": "investor_metric_readiness",
            "source_panel_generated_utc": str(report.get("generated_utc") or ""),
            "source_panel_artifact": rel_path(panel_json_tagged, workspace_root),
        },
        "summary": {
            "status": str(readiness.get("status") or "unknown"),
            "provisional_label": str(readiness.get("provisional_label") or "unknown"),
            "investor_position": (
                "Current PnL, Sharpe, CAGR, Sortino, and MDD are not decision-grade. Source breadth and routing "
                "scores are first-party diagnostics only; they do not establish alpha, savings, or a reason to "
                "increase capital."
            ),
            "signal_evidence": {
                "evidence_class": "first_party_diagnostic_not_performance_validation",
                "economic_estimates_included": False,
                "performance_validated": False,
                "measured_sources": to_int(headline.get("measured_sources"), 0),
                "enabled_sources": to_int(headline.get("enabled_sources"), 0),
                "measured_coverage_pct": round(to_float(headline.get("measured_coverage_pct"), 0.0), 2),
                "router_edge_pct": round(to_float(headline.get("router_edge_pct"), 0.0), 2),
                "harmonic_win_rate_pct": round(to_float(headline.get("harmonic_win_rate_pct"), 0.0), 2),
                "kalisha_prediction_score": round(to_float(headline.get("kalisha_prediction_score"), 0.0), 2),
                "top_sector": str(headline.get("top_sector") or "n/a"),
            },
            "capital_and_risk_gate_evidence": {
                "runtime_mode": str(runtime_gates.get("runtime_mode") or ""),
                "allow_live_orders": bool(runtime_gates.get("allow_live_orders", False)),
                "kill_switch": bool(runtime_gates.get("kill_switch", True)),
                "hard_safety_only_mode": bool(runtime_gates.get("hard_safety_only_mode", False)),
                "max_notional_per_trade_usd": round(to_float(runtime_gates.get("max_notional_per_trade_usd"), 0.0), 4),
                "max_daily_loss_usd": round(to_float(runtime_gates.get("max_daily_loss_usd"), 0.0), 4),
                "controller_mode": str(controller_gates.get("mode") or ""),
                "controller_allow_live": bool(controller_gates.get("allow_live", False)),
                "portfolio_est_usd": round(to_float(controller_gates.get("portfolio_est_usd"), 0.0), 4),
            },
            "provisional_live_metrics": {
                "closed_live_trades": to_int(readiness.get("closed_live_trades"), 0),
                "metrics_stable_threshold": to_int(readiness.get("metrics_stable_threshold"), 0),
                "stability_progress_pct": round(to_float(readiness.get("stability_progress_pct"), 0.0), 2),
                "provisional_due_to": (
                    readiness.get("provisional_due_to")
                    if isinstance(readiness.get("provisional_due_to"), list)
                    else []
                ),
                "win_rate_pct": round(to_float(provisional_metrics.get("win_rate_pct"), 0.0), 4),
                "realized_net_usd": round(to_float(provisional_metrics.get("realized_net_usd"), 0.0), 4),
                "max_drawdown_pct": round(to_float(provisional_metrics.get("max_drawdown_pct"), 0.0), 4),
            },
            "explanation": str(readiness.get("explanation") or ""),
            "first_thursday_action": str((readiness.get("thursday_plan") or [""])[0]),
            "thursday_plan": readiness.get("thursday_plan") if isinstance(readiness.get("thursday_plan"), list) else [],
        },
        "evidence_paths": {
            "panel_json": rel_path(panel_json_primary, workspace_root),
            "panel_tagged_json": rel_path(panel_json_tagged, workspace_root),
            "runtime_control_json": str(proof_refs.get("runtime_control_json") or ""),
            "controller_status_json": str(proof_refs.get("vps_growth_controller_status_json") or ""),
            "vps_growth_proof_json": str(proof_refs.get("vps_growth_proof_json") or ""),
            "frozen_deltas_jsonl": str(proof_refs.get("frozen_deltas_jsonl") or ""),
            "optimization_report_json": str(proof_refs.get("cross_sector_optimization_report_json") or ""),
            "source_registry_json": str(proof_refs.get("live_source_registry_json") or ""),
        },
    }
    return payload


def render_investor_metric_readiness_markdown(payload: dict[str, Any]) -> str:
    scope = payload.get("scope", {}) if isinstance(payload, dict) else {}
    if not isinstance(scope, dict):
        scope = {}

    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    if not isinstance(summary, dict):
        summary = {}

    signal = summary.get("signal_evidence", {}) if isinstance(summary, dict) else {}
    if not isinstance(signal, dict):
        signal = {}

    gates = summary.get("capital_and_risk_gate_evidence", {}) if isinstance(summary, dict) else {}
    if not isinstance(gates, dict):
        gates = {}

    provisional = summary.get("provisional_live_metrics", {}) if isinstance(summary, dict) else {}
    if not isinstance(provisional, dict):
        provisional = {}

    evidence_paths = payload.get("evidence_paths", {}) if isinstance(payload, dict) else {}
    if not isinstance(evidence_paths, dict):
        evidence_paths = {}

    thursday_plan = summary.get("thursday_plan") if isinstance(summary.get("thursday_plan"), list) else []

    lines: list[str] = []
    lines.append("# Investor Metric Readiness Brief")
    lines.append("")
    lines.append(f"Timestamp (UTC): {payload.get('generated_utc', '')}")
    lines.append("Scope: investor narrative alignment")
    lines.append(f"Source panel generated UTC: {scope.get('source_panel_generated_utc', '')}")
    lines.append("")
    lines.append("## Executive Position")
    lines.append("")
    lines.append(str(summary.get("investor_position") or ""))
    lines.append("")
    lines.append("First-party diagnostic coverage:")
    lines.append("")
    lines.append(f"- Evidence class: {signal.get('evidence_class', '')}")
    lines.append(f"- Economic estimates included: {signal.get('economic_estimates_included', False)}")
    lines.append(f"- Performance validated: {signal.get('performance_validated', False)}")
    lines.append(f"- Measured coverage: {signal.get('measured_sources', 0)} of {signal.get('enabled_sources', 0)} enabled sources ({signal.get('measured_coverage_pct', 0)}%)")
    lines.append(f"- Router edge: {signal.get('router_edge_pct', 0)}%")
    lines.append(f"- Harmonic win rate: {signal.get('harmonic_win_rate_pct', 0)}%")
    lines.append(f"- Kalisha prediction score: {signal.get('kalisha_prediction_score', 0)}")
    lines.append("")
    lines.append("## Why Risk-Adjusted Metrics Are Provisional")
    lines.append("")
    lines.append(f"Readiness status: {summary.get('status', 'unknown')}")
    lines.append(f"Provisional label: {summary.get('provisional_label', 'unknown')}")
    lines.append("")
    lines.append("System gates currently enforce a constrained execution envelope:")
    lines.append("")
    lines.append(f"- runtime mode: {gates.get('runtime_mode', '')}")
    lines.append(f"- allow_live_orders: {gates.get('allow_live_orders', False)}")
    lines.append(f"- kill_switch: {gates.get('kill_switch', True)}")
    lines.append(f"- hard_safety_only_mode: {gates.get('hard_safety_only_mode', False)}")
    lines.append(f"- max_notional_per_trade_usd: {gates.get('max_notional_per_trade_usd', 0)}")
    lines.append(f"- max_daily_loss_usd: {gates.get('max_daily_loss_usd', 0)}")
    lines.append(f"- controller mode: {gates.get('controller_mode', '')}")
    lines.append(f"- controller allow live: {gates.get('controller_allow_live', False)}")
    lines.append(f"- portfolio estimate: {gates.get('portfolio_est_usd', 0)} USD")
    lines.append("")
    lines.append("Current live sample depth:")
    lines.append("")
    lines.append(f"- closed live trades: {provisional.get('closed_live_trades', 0)}")
    lines.append(f"- institutional stability threshold: {provisional.get('metrics_stable_threshold', 0)}")
    lines.append(f"- stability_progress_pct: {provisional.get('stability_progress_pct', 0)}")
    lines.append(f"- win_rate_pct: {provisional.get('win_rate_pct', 0)}")
    lines.append(f"- realized_net_usd: {provisional.get('realized_net_usd', 0)}")
    lines.append(f"- max_drawdown_pct: {provisional.get('max_drawdown_pct', 0)}")
    lines.append("")
    lines.append("Interpretation:")
    lines.append(str(summary.get("explanation") or ""))
    lines.append("")
    lines.append("## Evidence Readiness Plan")
    lines.append("")
    for idx, item in enumerate(thursday_plan, start=1):
        lines.append(f"{idx}. {item}")
    lines.append("")
    lines.append("First bounded action:")
    lines.append("")
    lines.append(f"- {summary.get('first_thursday_action', '')}")
    lines.append("")
    lines.append("## Evidence Chain")
    lines.append("")
    for key in (
        "panel_json",
        "panel_tagged_json",
        "runtime_control_json",
        "controller_status_json",
        "vps_growth_proof_json",
        "frozen_deltas_jsonl",
        "optimization_report_json",
        "source_registry_json",
    ):
        lines.append(f"- {evidence_paths.get(key, '')}")
    lines.append("")
    lines.append("## Investor Talk Track (Short)")
    lines.append("")
    lines.append(
        '"The system currently provides source-coverage and routing diagnostics. Performance, savings, and alpha '
        'remain unvalidated until a frozen protocol passes adequate-sample and non-author execution gates."'
    )
    lines.append("")
    return "\n".join(lines)


def build_panel(
    stack_root: Path,
    workspace_root: Path,
    frozen_deltas_path: Path,
    optimization_report_path: Path,
    top_sectors_csv_path: Path,
    source_registry_path: Path,
    lumascout_summary_path: Path,
    runtime_control_path: Path,
    controller_status_path: Path,
    vps_growth_proof_path: Path,
    evidence_roots: list[Path],
    top_n: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    registry_summary = build_registry_summary(source_registry_path)
    source_lookup = registry_summary.get("source_lookup", {}) if isinstance(registry_summary, dict) else {}
    if not isinstance(source_lookup, dict):
        source_lookup = {}

    frozen_all = load_jsonl(frozen_deltas_path)
    frozen_latest = pick_latest_frozen_deltas(frozen_all)

    sector_rows, source_rows = build_sector_rollup(frozen_latest, source_lookup)

    reference_rows = load_csv(top_sectors_csv_path)
    if not sector_rows and reference_rows:
        sector_rows = fallback_sectors_from_reference(reference_rows)

    optimization = load_json(optimization_report_path)
    recommended = optimization.get("recommended", {}) if isinstance(optimization, dict) else {}
    if not isinstance(recommended, dict):
        recommended = {}

    evidence = load_evidence_signals(evidence_roots)
    lumascout = load_json(lumascout_summary_path)
    metric_readiness = build_metric_readiness(
        runtime_control_path=runtime_control_path,
        controller_status_path=controller_status_path,
        vps_growth_proof_path=vps_growth_proof_path,
    )

    total_baseline = sum(to_float(r.get("total_baseline_loss_rate_usd_per_hour"), 0.0) for r in sector_rows)
    total_hourly = sum(to_float(r.get("total_estimated_hourly_value_usd"), 0.0) for r in sector_rows)
    total_daily = total_hourly * HOURS_PER_DAY
    total_annual = total_daily * DAYS_PER_YEAR

    top_sector_row = sector_rows[0] if sector_rows else {}

    top_sector_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(sector_rows[: max(1, top_n)]):
        top_sector_rows.append(
            {
                "rank": idx + 1,
                "sector": str(row.get("sector") or "unknown"),
                "source_count": to_int(row.get("source_count"), 0),
                "measured_source_count": to_int(row.get("measured_source_count"), 0),
                "weighted_optimization_gain_pct": round(to_float(row.get("weighted_optimization_gain_pct"), 0.0), 4),
                "total_baseline_loss_rate_usd_per_hour": round(to_float(row.get("total_baseline_loss_rate_usd_per_hour"), 0.0), 4),
                "total_estimated_hourly_value_usd": round(to_float(row.get("total_estimated_hourly_value_usd"), 0.0), 4),
                "total_estimated_daily_value_usd": round(to_float(row.get("total_estimated_daily_value_usd"), 0.0), 4),
                "total_estimated_annual_value_usd": round(to_float(row.get("total_estimated_annual_value_usd"), 0.0), 4),
                "recommended_action": str(row.get("recommended_action") or "observe"),
                "sample_sources": str(row.get("sample_sources") or ""),
                "trust_tiers": str(row.get("trust_tiers") or ""),
                "latest_generated_utc": str(row.get("latest_generated_utc") or ""),
            }
        )

    market_lane = next(
        (
            row
            for row in sector_rows
            if normalize_token(row.get("sector")) in {"MARKETEXECUTION", "FINANCIALMARKETINFRA", "CRYPTOEXEC", "BROKER"}
        ),
        {},
    )

    thursday_plan = metric_readiness.get("thursday_plan") if isinstance(metric_readiness, dict) else []
    if not isinstance(thursday_plan, list):
        thursday_plan = []
    first_thursday_action = str(thursday_plan[0]) if thursday_plan else ""

    headline = {
        "total_baseline_loss_rate_usd_per_hour": round(total_baseline, 2),
        "total_estimated_hourly_value_usd": round(total_hourly, 2),
        "total_estimated_daily_value_usd": round(total_daily, 2),
        "total_estimated_annual_value_usd": round(total_annual, 2),
        "translated_source_hourly_value_usd": round(to_float(registry_summary.get("translated_hourly_value_usd"), 0.0), 2),
        "translated_source_daily_value_usd": round(to_float(registry_summary.get("translated_daily_value_usd"), 0.0), 2),
        "translated_source_annual_value_usd": round(to_float(registry_summary.get("translated_annual_value_usd"), 0.0), 2),
        "enabled_sources": to_int(registry_summary.get("enabled_sources"), 0),
        "measured_sources": to_int(registry_summary.get("measured_sources"), 0),
        "measured_coverage_pct": round(to_float(registry_summary.get("measured_coverage_pct"), 0.0), 2),
        "live_sector_count": len(sector_rows),
        "top_sector": str(top_sector_row.get("sector") or "n/a"),
        "top_sector_hourly_value_usd": round(to_float(top_sector_row.get("total_estimated_hourly_value_usd"), 0.0), 2),
        "cross_sector_recommended_prevented_pct": round(to_percent(recommended.get("prevented_pct")), 2),
        "cross_sector_recommended_avoided_cost_usd": round(to_float(recommended.get("avoided_cost_usd"), 0.0), 2),
        "router_edge_pct": round(to_float(evidence.get("router_edge_pct"), 0.0), 2),
        "harmonic_win_rate_pct": round(to_float(evidence.get("harmonic_win_rate_pct"), 0.0), 2),
        "kalisha_prediction_score": round(to_float(evidence.get("kalisha_prediction_score"), 0.0), 2),
        "evidence_datasets_succeeded": to_int(evidence.get("datasets_succeeded"), 0),
        "lumascout_active_sources": to_int(lumascout.get("active_sources"), 0),
        "performance_metrics_status": str(metric_readiness.get("status") or "unknown"),
        "performance_metrics_explanation": str(metric_readiness.get("explanation") or ""),
        "first_thursday_action": first_thursday_action,
        "economic_estimates_public_claim_allowed": False,
        "trading_performance_validated": False,
        "external_validation_status": "not_performed",
    }

    patent_bridge = {
        "attribution_model": "substrate_to_value_chain",
        "thesis": (
            "The proposed harmonic flowform substrate links source sensing, routing, execution controls, and "
            "evidence capture as a testable architecture hypothesis."
        ),
        "stages": [
            {
                "stage": "sense",
                "mechanism": "live multi-source breadth measurement",
                "headline_metric": {
                    "measured_sources": headline["measured_sources"],
                    "enabled_sources": headline["enabled_sources"],
                    "measured_coverage_pct": headline["measured_coverage_pct"],
                },
                "evidence_ref": rel_path(source_registry_path, workspace_root),
            },
            {
                "stage": "route",
                "mechanism": "flowform router and harmonic lane selection",
                "headline_metric": {
                    "router_edge_pct": headline["router_edge_pct"],
                    "harmonic_win_rate_pct": headline["harmonic_win_rate_pct"],
                    "kalisha_prediction_score": headline["kalisha_prediction_score"],
                },
                "evidence_ref": "dashboard/evidence/runs/<run_utc>/{summary.json,router/eval.json,stacker/eval.json,blender/eval.json}",
            },
            {
                "stage": "execute",
                "mechanism": "trader/execution lane preservation",
                "headline_metric": {
                    "market_lane_sector": str(market_lane.get("sector") or "market_execution"),
                    "market_lane_source_count": to_int(market_lane.get("source_count"), 0),
                    "cross_sector_prevented_pct": headline["cross_sector_recommended_prevented_pct"],
                },
                "evidence_ref": rel_path(frozen_deltas_path, workspace_root),
            },
            {
                "stage": "prove",
                "mechanism": "frozen delta and optimization proof chain",
                "headline_metric": {
                    "economic_estimates_public_claim_allowed": False,
                    "top_sector": headline["top_sector"],
                    "external_validation_status": "not_performed",
                },
                "evidence_ref": rel_path(optimization_report_path, workspace_root),
            },
        ],
        "investor_message": (
            "The substrate is a testable architecture hypothesis. Economic or performance claims require a "
            "frozen protocol, accepted baseline, and non-author or buyer-owned validation."
        ),
        "legal_note": (
            "Investor attribution framing only. Final claim-family assignment and new-matter classification require patent counsel."
        ),
    }

    report = {
        "generated_utc": now_iso(),
        "scope": {
            "stack_root": str(stack_root),
            "workspace_root": str(workspace_root),
            "top_n": max(1, int(top_n)),
            "selection_mode": "latest_per_source_sector_constraint",
        },
        "inputs": {
            "frozen_deltas_jsonl": rel_path(frozen_deltas_path, workspace_root),
            "optimization_report_json": rel_path(optimization_report_path, workspace_root),
            "top_optimized_sectors_csv": rel_path(top_sectors_csv_path, workspace_root),
            "live_source_registry_json": rel_path(source_registry_path, workspace_root),
            "lumascout_summary_json": rel_path(lumascout_summary_path, workspace_root),
            "frozen_deltas_records_raw": len(frozen_all),
            "frozen_deltas_records_latest": len(frozen_latest),
            "reference_rows": len(reference_rows),
            "registry_generated_utc": str(registry_summary.get("generated_utc") or ""),
        },
        "claim_gate": {
            "public_economic_value_claim_allowed": False,
            "trading_performance_validated": False,
            "field_performance_validated": False,
            "external_validation_status": "not_performed",
            "live_capital_increase_recommended": False,
        },
        "headline": headline,
        "lanes": {
            "cross_sector_intel": {
                "recommended_prevented_pct": round(to_percent(recommended.get("prevented_pct")), 2),
                "recommended_avoided_cost_usd": round(to_float(recommended.get("avoided_cost_usd"), 0.0), 2),
                "recommended_residual_cost_usd": round(to_float(recommended.get("residual_cost_usd"), 0.0), 2),
                "recommended_efficiency_score": round(to_float(recommended.get("efficiency_score"), 0.0), 2),
            },
            "live_source_translation": {
                "enabled_sources": to_int(registry_summary.get("enabled_sources"), 0),
                "measured_sources": to_int(registry_summary.get("measured_sources"), 0),
                "measured_coverage_pct": round(to_float(registry_summary.get("measured_coverage_pct"), 0.0), 2),
                "translated_hourly_value_usd": round(to_float(registry_summary.get("translated_hourly_value_usd"), 0.0), 2),
                "translated_annual_value_usd": round(to_float(registry_summary.get("translated_annual_value_usd"), 0.0), 2),
            },
            "flowform_router": {
                "evidence_run_utc": str(evidence.get("run_utc") or ""),
                "router_edge_pct": round(to_float(evidence.get("router_edge_pct"), 0.0), 2),
                "harmonic_win_rate_pct": round(to_float(evidence.get("harmonic_win_rate_pct"), 0.0), 2),
                "kalisha_prediction_score": round(to_float(evidence.get("kalisha_prediction_score"), 0.0), 2),
                "datasets_succeeded": to_int(evidence.get("datasets_succeeded"), 0),
            },
            "trader_execution": {
                "sector": str(market_lane.get("sector") or "market_execution"),
                "hourly_value_usd": round(to_float(market_lane.get("total_estimated_hourly_value_usd"), 0.0), 2),
                "weighted_gain_pct": round(to_float(market_lane.get("weighted_optimization_gain_pct"), 0.0), 2),
                "source_count": to_int(market_lane.get("source_count"), 0),
            },
            "lumascout": {
                "active_sources": to_int(lumascout.get("active_sources"), 0),
                "champions": to_int(lumascout.get("champions"), 0),
                "watchlist": to_int(lumascout.get("watchlist"), 0),
                "generated_utc": str(lumascout.get("generated_utc") or ""),
            },
            "performance_metrics_readiness": {
                "status": str(metric_readiness.get("status") or "unknown"),
                "explanation": str(metric_readiness.get("explanation") or ""),
                "target_window": str(metric_readiness.get("target_window") or ""),
                "capital_mode": str(metric_readiness.get("capital_mode") or "unknown"),
                "closed_live_trades": to_int(metric_readiness.get("closed_live_trades"), 0),
                "metrics_stable_threshold": to_int(metric_readiness.get("metrics_stable_threshold"), 0),
                "first_thursday_action": first_thursday_action,
                "thursday_plan": thursday_plan,
                "provisional_metrics": metric_readiness.get("provisional_metrics")
                if isinstance(metric_readiness.get("provisional_metrics"), dict)
                else {},
                "runtime_mode": str((metric_readiness.get("runtime_gates") or {}).get("runtime_mode") or ""),
                "max_notional_per_trade_usd": round(
                    to_float((metric_readiness.get("runtime_gates") or {}).get("max_notional_per_trade_usd"), 0.0),
                    4,
                ),
                "max_daily_loss_usd": round(
                    to_float((metric_readiness.get("runtime_gates") or {}).get("max_daily_loss_usd"), 0.0),
                    4,
                ),
                "controller_mode": str((metric_readiness.get("controller_gates") or {}).get("mode") or ""),
                "controller_allow_live": bool((metric_readiness.get("controller_gates") or {}).get("allow_live", False)),
                "portfolio_est_usd": round(
                    to_float((metric_readiness.get("controller_gates") or {}).get("portfolio_est_usd"), 0.0),
                    4,
                ),
                "allow_live_orders": bool((metric_readiness.get("runtime_gates") or {}).get("allow_live_orders", False)),
                "kill_switch": bool((metric_readiness.get("runtime_gates") or {}).get("kill_switch", True)),
            },
        },
        "patent_substrate_bridge": patent_bridge,
        "metric_readiness": metric_readiness,
        "top_sectors": top_sector_rows,
        "top_optimized_reference": [
            {
                "source": str(r.get("source") or ""),
                "sector": str(r.get("sector") or ""),
                "optimization_gain_pct": round(to_float(r.get("optimization_gain_pct"), 0.0), 4),
                "estimated_hourly_value_usd": round(to_float(r.get("estimated_hourly_value_usd"), 0.0), 4),
            }
            for r in reference_rows[: max(1, top_n)]
        ],
        "source_rows": source_rows[: max(1, top_n * 2)],
        "proof_refs": {
            "frozen_deltas_jsonl": rel_path(frozen_deltas_path, workspace_root),
            "live_source_registry_json": rel_path(source_registry_path, workspace_root),
            "cross_sector_optimization_report_json": rel_path(optimization_report_path, workspace_root),
            "top_optimized_sectors_csv": rel_path(top_sectors_csv_path, workspace_root),
            "runtime_control_json": rel_path(runtime_control_path, workspace_root),
            "vps_growth_controller_status_json": rel_path(controller_status_path, workspace_root),
            "vps_growth_proof_json": rel_path(vps_growth_proof_path, workspace_root),
            "evidence_root": rel_path(Path(str(evidence.get("evidence_root") or "")), workspace_root)
            if str(evidence.get("evidence_root") or "")
            else "",
        },
    }

    csv_rows: list[dict[str, Any]] = []
    for row in top_sector_rows:
        csv_rows.append(
            {
                "rank": row.get("rank"),
                "sector": row.get("sector"),
                "source_count": row.get("source_count"),
                "measured_source_count": row.get("measured_source_count"),
                "weighted_optimization_gain_pct": row.get("weighted_optimization_gain_pct"),
                "total_baseline_loss_rate_usd_per_hour": row.get("total_baseline_loss_rate_usd_per_hour"),
                "total_estimated_hourly_value_usd": row.get("total_estimated_hourly_value_usd"),
                "total_estimated_daily_value_usd": row.get("total_estimated_daily_value_usd"),
                "total_estimated_annual_value_usd": row.get("total_estimated_annual_value_usd"),
                "recommended_action": row.get("recommended_action"),
                "sample_sources": row.get("sample_sources"),
                "trust_tiers": row.get("trust_tiers"),
                "latest_generated_utc": row.get("latest_generated_utc"),
            }
        )

    return report, csv_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build cross-sector live breadth value panel artifacts.")
    parser.add_argument(
        "--stack-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Stack root (default: INSTITUTIONAL_STACK_V2)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=8,
        help="Top sectors to retain in panel output and CSV (default: 8)",
    )
    parser.add_argument(
        "--frozen-deltas-file",
        default="",
        help="Override path to infra_frozen_deltas.jsonl",
    )
    parser.add_argument(
        "--optimization-report-file",
        default="",
        help="Override path to cross_sector_optimization_report.json",
    )
    parser.add_argument(
        "--top-sectors-csv",
        default="",
        help="Override path to infra_top_optimized_sectors.csv",
    )
    parser.add_argument(
        "--source-registry-file",
        default="",
        help="Override path to config/live_source_registry.json",
    )
    parser.add_argument(
        "--lumascout-summary-file",
        default="",
        help="Override path to out/lumascout_summary.json",
    )
    parser.add_argument(
        "--runtime-control-file",
        default="",
        help="Override path to config/runtime_control.json",
    )
    parser.add_argument(
        "--controller-status-file",
        default="",
        help="Override path to dashboard/data/vps_growth_controller_status.json",
    )
    parser.add_argument(
        "--vps-growth-proof-file",
        default="",
        help="Override path to dashboard/data/vps_growth_proof.json",
    )
    args = parser.parse_args()

    stack_root = Path(args.stack_root).resolve()
    workspace_root = stack_root.parent

    frozen_deltas_path = (
        Path(args.frozen_deltas_file).resolve()
        if args.frozen_deltas_file
        else resolve_existing([
            stack_root / "out" / "infra_frozen_deltas.jsonl",
            workspace_root / "INSTITUTIONAL_STACK_V2" / "out" / "infra_frozen_deltas.jsonl",
        ])
    )

    optimization_report_path = (
        Path(args.optimization_report_file).resolve()
        if args.optimization_report_file
        else resolve_existing([
            stack_root / "cross_sector_optimization_report.json",
            stack_root / "out" / "cross_sector_optimization_report.json",
        ])
    )

    top_sectors_csv_path = (
        Path(args.top_sectors_csv).resolve()
        if args.top_sectors_csv
        else resolve_existing([
            workspace_root / "clean_data" / "infra_top_optimized_sectors.csv",
            stack_root / "out" / "cross_sector_optimization_matrix.csv",
        ])
    )

    source_registry_path = (
        Path(args.source_registry_file).resolve()
        if args.source_registry_file
        else resolve_existing([
            stack_root / "config" / "live_source_registry.json",
            workspace_root / "INSTITUTIONAL_STACK_V2" / "config" / "live_source_registry.json",
        ])
    )

    lumascout_summary_path = (
        Path(args.lumascout_summary_file).resolve()
        if args.lumascout_summary_file
        else resolve_existing([
            stack_root / "out" / "lumascout_summary.json",
            workspace_root / "INSTITUTIONAL_STACK_V2" / "out" / "lumascout_summary.json",
        ])
    )

    runtime_control_path = (
        Path(args.runtime_control_file).resolve()
        if args.runtime_control_file
        else resolve_existing([
            stack_root / "config" / "runtime_control.json",
            workspace_root / "INSTITUTIONAL_STACK_V2" / "config" / "runtime_control.json",
        ])
    )

    controller_status_path = (
        Path(args.controller_status_file).resolve()
        if args.controller_status_file
        else resolve_existing([
            stack_root / "dashboard" / "data" / "vps_growth_controller_status.json",
            workspace_root / "INSTITUTIONAL_STACK_V2" / "dashboard" / "data" / "vps_growth_controller_status.json",
        ])
    )

    vps_growth_proof_path = (
        Path(args.vps_growth_proof_file).resolve()
        if args.vps_growth_proof_file
        else resolve_existing([
            stack_root / "dashboard" / "data" / "vps_growth_proof.json",
            workspace_root / "INSTITUTIONAL_STACK_V2" / "dashboard" / "data" / "vps_growth_proof.json",
        ])
    )

    evidence_roots = [
        workspace_root / "dashboard" / "evidence",
        stack_root / "dashboard" / "evidence",
    ]

    report, csv_rows = build_panel(
        stack_root=stack_root,
        workspace_root=workspace_root,
        frozen_deltas_path=frozen_deltas_path,
        optimization_report_path=optimization_report_path,
        top_sectors_csv_path=top_sectors_csv_path,
        source_registry_path=source_registry_path,
        lumascout_summary_path=lumascout_summary_path,
        runtime_control_path=runtime_control_path,
        controller_status_path=controller_status_path,
        vps_growth_proof_path=vps_growth_proof_path,
        evidence_roots=evidence_roots,
        top_n=max(1, int(args.top_n)),
    )

    out_dir = stack_root / "out" / "ops"
    tag = now_tag()

    json_tag_path = out_dir / f"live_breadth_value_panel_{tag}.json"
    csv_tag_path = out_dir / f"live_breadth_value_panel_{tag}.csv"
    json_primary = out_dir / "live_breadth_value_panel.json"
    csv_primary = out_dir / "live_breadth_value_panel.csv"
    json_latest = out_dir / "live_breadth_value_panel_latest.json"
    csv_latest = out_dir / "live_breadth_value_panel_latest.csv"
    investor_json_tag = out_dir / f"investor_metric_readiness_{tag}.json"
    investor_json_latest = out_dir / "investor_metric_readiness_latest.json"
    investor_md_tag = out_dir / f"investor_metric_readiness_{tag}.md"
    investor_md_latest = out_dir / "investor_metric_readiness_latest.md"

    report["artifacts"] = {
        "json_rel": rel_path(json_primary, workspace_root),
        "csv_rel": rel_path(csv_primary, workspace_root),
        "timestamp_json_rel": rel_path(json_tag_path, workspace_root),
        "timestamp_csv_rel": rel_path(csv_tag_path, workspace_root),
        "latest_json_rel": rel_path(json_latest, workspace_root),
        "latest_csv_rel": rel_path(csv_latest, workspace_root),
        "investor_metric_readiness_json_rel": rel_path(investor_json_tag, workspace_root),
        "investor_metric_readiness_md_rel": rel_path(investor_md_tag, workspace_root),
        "investor_metric_readiness_latest_json_rel": rel_path(investor_json_latest, workspace_root),
        "investor_metric_readiness_latest_md_rel": rel_path(investor_md_latest, workspace_root),
    }

    write_json(json_tag_path, report)
    write_csv(csv_tag_path, csv_rows)
    write_json(json_primary, report)
    write_csv(csv_primary, csv_rows)
    write_json(json_latest, report)
    write_csv(csv_latest, csv_rows)

    investor_payload = build_investor_metric_readiness_payload(
        report=report,
        workspace_root=workspace_root,
        panel_json_primary=json_primary,
        panel_json_tagged=json_tag_path,
    )
    investor_markdown = render_investor_metric_readiness_markdown(investor_payload)
    write_json(investor_json_tag, investor_payload)
    write_json(investor_json_latest, investor_payload)
    write_text(investor_md_tag, investor_markdown)
    write_text(investor_md_latest, investor_markdown)

    manifest = {
        "generated_utc": report.get("generated_utc"),
        "headline": report.get("headline"),
        "artifacts": {
            "timestamp_json": str(json_tag_path),
            "timestamp_csv": str(csv_tag_path),
            "primary_json": str(json_primary),
            "primary_csv": str(csv_primary),
            "latest_json": str(json_latest),
            "latest_csv": str(csv_latest),
            "investor_metric_readiness_json": str(investor_json_tag),
            "investor_metric_readiness_md": str(investor_md_tag),
            "investor_metric_readiness_latest_json": str(investor_json_latest),
            "investor_metric_readiness_latest_md": str(investor_md_latest),
        },
    }

    manifest_path = out_dir / f"live_breadth_value_panel_manifest_{tag}.json"
    write_json(manifest_path, manifest)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
