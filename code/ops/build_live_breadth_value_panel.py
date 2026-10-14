from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOURS_PER_DAY = 24.0
DAYS_PER_YEAR = 365.0
MODEL_BOUNDARY = (
    "Unvalidated model context: baseline loss rate * explicit signed metric gain / 100, "
    "annualized at 8,760 constant hours. A metric gain is not an accepted cost or energy effect. "
    "Equivalent service, causal attribution, overhead, persistence, uncertainty and overlap "
    "have not been established. Totals are arithmetic scenario sums, not additive savings, "
    "revenue, measured electricity reductions or permission to scale."
)


def finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def complete_sum(values: list[Any]) -> float | None:
    numbers = [finite_number(value) for value in values]
    if not numbers or any(value is None for value in numbers):
        return None
    try:
        return finite_number(math.fsum(numbers))
    except OverflowError:
        return None


def rounded_number(value: Any, digits: int = 4) -> float | None:
    number = finite_number(value)
    return round(number, digits) if number is not None else None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_float(value: Any, default: float = 0.0) -> float:
    number = finite_number(value)
    return number if number is not None else default


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


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_nonfinite_constant(value: str) -> Any:
    raise ValueError(f"Nonfinite JSON number: {value}")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=reject_duplicate_members, parse_constant=reject_nonfinite_constant)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw, object_pairs_hook=reject_duplicate_members, parse_constant=reject_nonfinite_constant)
        if not isinstance(row, dict):
            raise ValueError("Frozen delta rows must be JSON objects")
        rows.append(row)
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
    serialized = json.dumps(payload, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")


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

        try:
            ts = datetime.fromisoformat(str(row.get("generated_utc")).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Frozen row needs a valid generated_utc timestamp") from exc
        if ts.tzinfo is None:
            raise ValueError("Frozen row generated_utc must contain a timezone")
        ts = ts.astimezone(timezone.utc)
        prev = latest_ts.get(key)
        if prev is None or ts > prev:
            latest[key] = row
            latest_ts[key] = ts
        elif ts == prev and row != latest[key]:
            raise ValueError("Conflicting frozen rows share an identity and timestamp")

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

                    enabled = raw.get("enabled") is True
                    if not isinstance(raw.get("enabled"), bool):
                        enabled = bool(env_name) or status in {
                            "LIVE_KEY_PRESENT",
                            "LIVE",
                            "ENABLED",
                            "OK",
                            "HEALTHY",
                        }

                    measured = raw.get("measured") is True
                    if not isinstance(raw.get("measured"), bool):
                        measured = row_count > 0 or status in {
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

    enabled_rows = [r for r in rows if isinstance(r, dict) and r.get("enabled") is True]
    measured_rows = [r for r in enabled_rows if r.get("measured") is True]

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
    translations = [r.get("translated_value") if isinstance(r.get("translated_value"), dict) else {} for r in measured_rows]
    measured_sources = len(measured_rows)
    coverage_pct = (float(measured_sources) / float(enabled_sources) * 100.0) if enabled_sources else 0.0

    return {
        "generated_utc": str(registry.get("generated_utc") or ""),
        "rows_total": len(rows),
        "enabled_sources": enabled_sources,
        "measured_sources": measured_sources,
        "measured_coverage_pct": coverage_pct,
        "measured_sectors": sorted(sectors),
        "translated_hourly_value_usd": None,
        "translated_daily_value_usd": None,
        "translated_annual_value_usd": None,
        "reported_translated_hourly_value_usd": complete_sum([r.get("hour") for r in translations]),
        "reported_translated_daily_value_usd": complete_sum([r.get("day") for r in translations]),
        "reported_translated_annual_value_usd": complete_sum([r.get("year") for r in translations]),
        "evidence_status": "REGISTRY_REPORTED_INTAKE_NOT_EFFECT_VALIDATION",
        "source_lookup": source_lookup,
    }


def classify_action(weighted_gain_pct: float | None, *, invalid_input: bool = False) -> str:
    if invalid_input or finite_number(weighted_gain_pct) is None:
        return "review_invalid_input"
    return "retain_baseline" if weighted_gain_pct <= 0 else "review_evidence"


def build_sector_rollup(
    latest_rows: list[dict[str, Any]],
    source_lookup: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for raw in latest_rows:
        source = str(raw.get("source") or "UNKNOWN")
        sector = str(raw.get("sector") or "unknown")
        registry = source_lookup.get(normalize_token(source), {})
        baseline = finite_number(raw.get("baseline_loss_rate_usd_per_hour"))
        gain = finite_number(raw.get("optimization_gain_pct"))
        reported = finite_number(raw.get("estimated_hourly_value_usd"))
        issues = []
        if baseline is None or baseline < 0:
            issues.append("missing_invalid_or_negative_baseline")
        if gain is None:
            issues.append("missing_or_invalid_explicit_gain")
        if "estimated_hourly_value_usd" in raw and reported is None:
            issues.append("invalid_reported_hourly_value")
        modeled = finite_number(baseline * (gain / 100)) if baseline is not None and baseline >= 0 and gain is not None else None
        daily = finite_number(modeled * HOURS_PER_DAY) if modeled is not None else None
        annual = finite_number(modeled * HOURS_PER_DAY * DAYS_PER_YEAR) if modeled is not None else None
        if not issues and any(value is None for value in (modeled, daily, annual)):
            issues.append("modeled_value_overflow")
        conflict = not math.isclose(reported, modeled, rel_tol=1e-9, abs_tol=1e-9) if reported is not None and modeled is not None else None
        if conflict:
            issues.append("reported_value_conflicts_with_signed_model")
        if gain is not None and gain > 100:
            issues.append("gain_exceeds_100_pct_loss_reduction_bound")
        row = {
            "generated_utc": str(raw.get("generated_utc") or ""),
            "source": source, "sector": sector,
            "constraint": str(raw.get("constraint") or "default"),
            "baseline_loss_rate_usd_per_hour": baseline,
            "optimization_gain_pct": gain,
            "estimated_hourly_value_usd": None,
            "estimated_daily_value_usd": None,
            "estimated_annual_value_usd": None,
            "reported_estimated_hourly_value_usd": reported,
            "modeled_hourly_value_usd": modeled,
            "modeled_daily_value_usd": daily,
            "modeled_annual_value_usd": annual,
            "reported_hourly_value_conflict": conflict,
            "predicted_failure_cost_usd": None,
            "estimated_avoided_loss_usd": None,
            "estimated_residual_loss_usd": None,
            "translated_source_yearly_value_usd": None,
            "trust_tier": str(raw.get("trust_tier") or ""),
            "key_present": raw.get("key_present") if isinstance(raw.get("key_present"), bool) else None,
            "enabled_source": registry.get("enabled") is True,
            "measured_source": registry.get("measured") is True,
            "registry_reported_intake": registry.get("measured") is True,
            "primary_live_evidence": False, "effect_validated": False,
            "evidence_source": "infra_frozen_delta_ledger",
            "evidence_status": "INVALID_INPUT_REVIEW" if issues else "UNVALIDATED_MODEL_INPUT",
            "effect_uncertainty": None, "source_freshness": "UNASSESSED",
            "input_issues": issues,
            "recommended_action": classify_action(gain, invalid_input=bool(issues)),
            "model_boundary": MODEL_BOUNDARY,
        }
        for name in ("predicted_failure_cost_usd", "estimated_avoided_loss_usd", "estimated_residual_loss_usd"):
            row["reported_" + name] = finite_number(raw.get(name))
        source_rows.append(row)
        groups.setdefault(sector, []).append(row)

    sector_rows = []
    for sector, rows in groups.items():
        baseline = complete_sum([row["baseline_loss_rate_usd_per_hour"] for row in rows])
        modeled = complete_sum([row["modeled_hourly_value_usd"] for row in rows])
        daily = complete_sum([row["modeled_daily_value_usd"] for row in rows])
        annual = complete_sum([row["modeled_annual_value_usd"] for row in rows])
        weighted = finite_number(modeled / baseline * 100) if modeled is not None and baseline is not None and baseline > 0 else None
        invalid_count = sum(bool(row["input_issues"]) for row in rows)
        sector_rows.append({
            "sector": sector, "source_count": len(rows),
            "unique_source_count": len({row["source"] for row in rows}),
            "measured_source_count": sum(row["measured_source"] for row in rows),
            "total_baseline_loss_rate_usd_per_hour": baseline,
            "weighted_optimization_gain_pct": weighted,
            "total_estimated_hourly_value_usd": None,
            "total_estimated_daily_value_usd": None,
            "total_estimated_annual_value_usd": None,
            "modeled_hourly_value_usd": modeled,
            "modeled_daily_value_usd": daily,
            "modeled_annual_value_usd": annual,
            "primary_live_evidence": False, "effect_validated": False,
            "invalid_input_count": invalid_count,
            "positive_gain_count": sum(row["optimization_gain_pct"] is not None and row["optimization_gain_pct"] > 0 for row in rows),
            "nonpositive_gain_count": sum(row["optimization_gain_pct"] is not None and row["optimization_gain_pct"] <= 0 for row in rows),
            "recommended_action": classify_action(weighted, invalid_input=bool(invalid_count)),
            "latest_generated_utc": max((row["generated_utc"] for row in rows), key=parse_utc),
            "sample_sources": ", ".join(sorted({row["source"] for row in rows})[:6]),
            "trust_tiers": ", ".join(sorted({row["trust_tier"] for row in rows if row["trust_tier"]})),
            "model_boundary": MODEL_BOUNDARY,
        })
    sector_rows.sort(key=lambda row: (row["modeled_hourly_value_usd"] is not None, row["modeled_hourly_value_usd"] or 0), reverse=True)
    source_rows.sort(key=lambda row: (row["modeled_hourly_value_usd"] is not None, row["modeled_hourly_value_usd"] or 0), reverse=True)
    return sector_rows, source_rows


def fallback_sectors_from_reference(reference_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sectors, _ = build_sector_rollup(reference_rows, {})
    for row in sectors:
        row["evidence_source"] = "UNVERIFIED_REFERENCE_MODEL_CONTEXT"
    return sectors


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

    total_baseline = complete_sum([r.get("total_baseline_loss_rate_usd_per_hour") for r in sector_rows])
    total_hourly = complete_sum([r.get("modeled_hourly_value_usd") for r in sector_rows])
    total_daily = complete_sum([r.get("modeled_daily_value_usd") for r in sector_rows])
    total_annual = complete_sum([r.get("modeled_annual_value_usd") for r in sector_rows])
    top_sector_row = sector_rows[0] if sector_rows else {}
    top_sector_rows = [dict(row, rank=index) for index, row in enumerate(sector_rows[: max(1, top_n)], start=1)]

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
        "total_baseline_loss_rate_usd_per_hour": rounded_number(total_baseline, 2),
        "total_estimated_hourly_value_usd": None,
        "total_estimated_daily_value_usd": None,
        "total_estimated_annual_value_usd": None,
        "modeled_hourly_value_usd": rounded_number(total_hourly, 2),
        "modeled_daily_value_usd": rounded_number(total_daily, 2),
        "modeled_annual_value_usd": rounded_number(total_annual, 2),
        "translated_source_hourly_value_usd": None,
        "translated_source_daily_value_usd": None,
        "translated_source_annual_value_usd": None,
        "reported_translated_source_annual_value_usd": registry_summary.get("reported_translated_annual_value_usd"),
        "evidence_status": "UNVALIDATED_MODEL_AND_REPORTED_INTAKE_CONTEXT",
        "primary_live_evidence": False,
        "model_boundary": MODEL_BOUNDARY,
        "invalid_input_count": sum(r["invalid_input_count"] for r in sector_rows),
        "enabled_sources": to_int(registry_summary.get("enabled_sources"), 0),
        "measured_sources": to_int(registry_summary.get("measured_sources"), 0),
        "measured_coverage_pct": round(to_float(registry_summary.get("measured_coverage_pct"), 0.0), 2),
        "live_sector_count": None,
        "modeled_sector_count": len(sector_rows),
        "top_sector": str(top_sector_row.get("sector") or "n/a"),
        "top_sector_hourly_value_usd": None,
        "top_sector_modeled_hourly_value_usd": rounded_number(top_sector_row.get("modeled_hourly_value_usd"), 2),
        "cross_sector_recommended_prevented_pct": None,
        "reported_cross_sector_prevented_pct": finite_number(recommended.get("prevented_pct")),
        "cross_sector_recommended_avoided_cost_usd": None,
        "reported_cross_sector_avoided_cost_usd": finite_number(recommended.get("avoided_cost_usd")),
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
            "accepted_annual_savings_usd": None,
            "boundary": MODEL_BOUNDARY,
            "trading_performance_validated": False,
            "field_performance_validated": False,
            "external_validation_status": "not_performed",
            "live_capital_increase_recommended": False,
        },
        "headline": headline,
        "lanes": {
            "cross_sector_intel": {
                "recommended_prevented_pct": None,
                "reported_prevented_pct": finite_number(recommended.get("prevented_pct")),
                "recommended_avoided_cost_usd": None,
                "reported_avoided_cost_usd": finite_number(recommended.get("avoided_cost_usd")),
                "recommended_residual_cost_usd": None,
                "reported_residual_cost_usd": finite_number(recommended.get("residual_cost_usd")),
                "recommended_efficiency_score": round(to_float(recommended.get("efficiency_score"), 0.0), 2),
            },
            "live_source_translation": {
                "enabled_sources": to_int(registry_summary.get("enabled_sources"), 0),
                "measured_sources": to_int(registry_summary.get("measured_sources"), 0),
                "measured_coverage_pct": round(to_float(registry_summary.get("measured_coverage_pct"), 0.0), 2),
                "translated_hourly_value_usd": None,
                "reported_translated_hourly_value_usd": registry_summary.get("reported_translated_hourly_value_usd"),
                "translated_annual_value_usd": None,
                "reported_translated_annual_value_usd": registry_summary.get("reported_translated_annual_value_usd"),
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
                "hourly_value_usd": None,
                "modeled_hourly_value_usd": rounded_number(market_lane.get("modeled_hourly_value_usd"), 2),
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
                "estimated_hourly_value_usd": None,
                "reported_estimated_hourly_value_usd": finite_number(r.get("estimated_hourly_value_usd")),
                "evidence_status": "UNVERIFIED_REFERENCE_CONTEXT",
            }
            for r in reference_rows[: max(1, top_n)]
        ],
        "source_rows": source_rows,
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
    for rank, source in enumerate(sector_rows, start=1):
        row = dict(source, rank=rank)
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
                "modeled_hourly_value_usd": row.get("modeled_hourly_value_usd"),
                "modeled_annual_value_usd": row.get("modeled_annual_value_usd"),
                "model_boundary": MODEL_BOUNDARY,
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
