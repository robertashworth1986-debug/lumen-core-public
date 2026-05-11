from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
CONFIG = ROOT / "config"

# Auto-load env keys if not already set in environment
_ENV_FILE = CONFIG / "luma_live_keys.env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

INFRA_DELTA_FILE = OUT / "infra_frozen_deltas.jsonl"
FAILURE_PRED_FILE = OUT / "cross_sector_failure_predictions.jsonl"
INFRA_AUDIT_FILE = OUT / "infra_audit_ledger.jsonl"
LOSS_LADDER_FILE = ROOT / "infrastructure_money_loss_ladder.csv"
EVIDENCE_FILE = OUT / "investor_and_grant_evidence.json"
RUNTIME_FILE = CONFIG / "system_overlord_runtime.json"
OUT_FILE = EXEC_OUT / "system_overlord_20s.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    row = json.loads(text)
                except Exception:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except Exception:
        return []
    return rows


def latest_by_sector(rows: Iterable[Dict[str, Any]], sector_key: str = "sector") -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        sector = str(row.get(sector_key, "unknown")).strip().lower()
        if not sector:
            sector = "unknown"
        out[sector] = row
    return out


def read_latest_eia_kw(iso: str) -> Dict[str, Any]:
    path = ROOT / f"live_eia_{iso.upper()}.csv"
    if not path.exists():
        return {
            "iso": iso.upper(),
            "source_file": str(path),
            "ok": False,
            "reason": "missing_file",
            "site_kw": 0.0,
            "site_mwh": 0.0,
            "period": None,
        }

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            first = next(reader, None)
        if not first:
            raise ValueError("empty csv")
        mwh = float(first.get("value", 0.0) or 0.0)
        # File stores hourly demand in MWh, so average kW for the hour is MWh * 1000.
        kw = mwh * 1000.0
        return {
            "iso": iso.upper(),
            "source_file": str(path),
            "ok": True,
            "site_kw": round(kw, 2),
            "site_mwh": round(mwh, 4),
            "period": first.get("period"),
            "unit": first.get("value-units", "megawatthours"),
        }
    except Exception as exc:
        return {
            "iso": iso.upper(),
            "source_file": str(path),
            "ok": False,
            "reason": f"parse_error: {exc}",
            "site_kw": 0.0,
            "site_mwh": 0.0,
            "period": None,
        }


def read_loss_ladder() -> Dict[str, Any]:
    if not LOSS_LADDER_FILE.exists():
        return {
            "historical_outage_events": 0,
            "historical_outage_hours": 0.0,
            "historical_outage_cost_usd": 0.0,
            "historical_avoided_loss_usd": 0.0,
        }

    events = 0
    total_hours = 0.0
    total_loss = 0.0
    total_avoided = 0.0
    try:
        with LOSS_LADDER_FILE.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                loss_per_hour = float(row.get("loss_per_hour_usd", 0.0) or 0.0)
                hours = float(row.get("hours", 0.0) or 0.0)
                avoided = float(row.get("avoided_loss_usd", 0.0) or 0.0)
                events += 1
                total_hours += hours
                total_loss += loss_per_hour * hours
                total_avoided += avoided
    except Exception:
        pass

    return {
        "historical_outage_events": int(events),
        "historical_outage_hours": round(total_hours, 2),
        "historical_outage_cost_usd": round(total_loss, 2),
        "historical_avoided_loss_usd": round(total_avoided, 2),
    }


_NATIONAL_AVG_CACHE: Dict[str, Any] = {}
_NATIONAL_AVG_FALLBACK = 0.1436  # EIA EPM Table 5.6.A — US all-sectors Feb 2026: 14.36 ¢/kWh
_EIA_EPM_URL = "https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_a"


def fetch_national_avg_rate() -> Dict[str, Any]:
    """
    Fetch live US national average retail electricity price (all sectors) from EIA.
    Tries EIA Electric Power Monthly Table 5.6.A web scrape first, then EIA API v1,
    then falls back to $0.1436/kWh (Feb 2026 confirmed US all-sectors average from EIA).
    Caches result for 6 hours.
    """
    cache = _NATIONAL_AVG_CACHE
    now_ts = time.time()
    if cache.get("ts", 0) and now_ts - cache["ts"] < 21600:
        return cache

    # --- Attempt 1: scrape EIA EPM Table 5.6.A ---
    try:
        req = urllib.request.Request(
            _EIA_EPM_URL,
            headers={"Accept": "text/html", "User-Agent": "Mozilla/5.0 LumaTrader/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Look for the "U.S. Total" row and extract the all-sectors figure (9th pipe-delimited value)
        for line in html.splitlines():
            if "U.S. Total" in line and "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                # columns: Res26 Res25 Com26 Com25 Ind26 Ind25 Trans26 Trans25 All26 All25
                if len(parts) >= 9:
                    try:
                        # "U.S. Total" is parts[0]; all-sectors 2026 is parts[8] (0-indexed)
                        all_sectors_cents = float(parts[8].replace(",", ""))
                        if 5.0 < all_sectors_cents < 60.0:
                            rate = all_sectors_cents / 100.0
                            cache.update({"rate": rate, "source": "eia_epm_scrape", "period": "latest_monthly", "ts": now_ts})
                            return cache
                    except (ValueError, IndexError):
                        pass
    except Exception:
        pass

    # --- Attempt 2: EIA API v1 series ---
    api_key = os.environ.get("EIA_API_KEY", "")
    if api_key:
        try:
            url = f"https://api.eia.gov/series/?api_key={api_key}&series_id=ELEC.PRICE.US-98.M&num=1"
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            series_data = data.get("series", [{}])[0].get("data", [])
            if series_data:
                period, price_cents = series_data[0][0], series_data[0][1]
                if price_cents and float(price_cents) > 0:
                    cache.update({"rate": float(price_cents) / 100.0, "source": "eia_api_v1", "period": str(period), "ts": now_ts})
                    return cache
        except Exception:
            pass

    # --- Fallback: confirmed EIA Feb 2026 national average ---
    cache.update({"rate": _NATIONAL_AVG_FALLBACK, "source": "eia_epm_confirmed_feb2026", "period": "2026-02", "ts": now_ts})
    return cache


def build_snapshot() -> Dict[str, Any]:
    runtime = load_json(
        RUNTIME_FILE,
        {
            "selected_iso": "MISO",
            "electricity_cost_per_kwh_usd": None,
            "use_live_national_avg": True,
            "site_kw_override": 0.0,
        },
    )
    selected_iso = str(runtime.get("selected_iso", "MISO") or "MISO")

    # Prefer live national average from EIA; fall back to config override, then hardcoded default.
    use_live = bool(runtime.get("use_live_national_avg", True))
    config_rate = runtime.get("electricity_cost_per_kwh_usd")
    if use_live or config_rate is None:
        nat_avg = fetch_national_avg_rate()
        cost_per_kwh = float(nat_avg["rate"])
        rate_source = nat_avg["source"]
        rate_period = nat_avg.get("period")
    else:
        cost_per_kwh = float(config_rate or _NATIONAL_AVG_FALLBACK)
        rate_source = "config_override"
        rate_period = None
    site_kw_override = float(runtime.get("site_kw_override", 0.0) or 0.0)

    eia = read_latest_eia_kw(selected_iso)
    raw_site_kw = float(eia.get("site_kw", 0.0) or 0.0)
    site_kw = site_kw_override if site_kw_override > 0 else raw_site_kw
    kw_basis = "override" if site_kw_override > 0 else "live_iso"
    site_cost_per_hour = site_kw * cost_per_kwh

    failure_rows = list(iter_jsonl(FAILURE_PRED_FILE))
    latest_pred_by_sector = latest_by_sector(failure_rows)

    frozen_rows = list(iter_jsonl(INFRA_DELTA_FILE))
    latest_frozen_by_sector = latest_by_sector(frozen_rows)

    outage_count = len(failure_rows)
    predicted_hourly_loss = sum(float(r.get("hourly_failure_cost_usd", 0.0) or 0.0) for r in latest_pred_by_sector.values())
    predicted_run_loss = sum(float(r.get("projected_failure_cost_usd", 0.0) or 0.0) for r in latest_pred_by_sector.values())
    predicted_run_avoided = sum(float(r.get("avoided_cost_usd", 0.0) or 0.0) for r in latest_pred_by_sector.values())

    # Convert frozen optimization percentages into immediate per-hour gain estimates.
    gain_now_per_hour = 0.0
    for row in latest_frozen_by_sector.values():
        hourly_value = float(row.get("estimated_hourly_value_usd", 0.0) or 0.0)
        gain_pct = float(row.get("optimization_gain_pct", 0.0) or 0.0) / 100.0
        gain_now_per_hour += max(0.0, hourly_value * gain_pct)

    scale_annual_gain = gain_now_per_hour * 24.0 * 365.0
    scale_monthly_gain = gain_now_per_hour * 24.0 * 30.0

    affected_asset_total = sum(float(r.get("affected_asset_value_usd", 0.0) or 0.0) for r in latest_pred_by_sector.values())
    ladder = read_loss_ladder()

    evidence = load_json(EVIDENCE_FILE, {})
    prevented_pct = float(evidence.get("prevented_pct", 0.0) or 0.0)

    roi_vs_energy_pct = (gain_now_per_hour / site_cost_per_hour * 100.0) if site_cost_per_hour > 0 else 0.0

    return {
        "generated_utc": now_utc(),
        "schema": "system_overlord_20s_v1",
        "runtime": {
            "selected_iso": selected_iso.upper(),
            "electricity_cost_per_kwh_usd": round(cost_per_kwh, 6),
            "rate_source": rate_source,
            "rate_period": rate_period,
            "refresh_target_seconds": 20,
        },
        "site_live": {
            "period_utc": eia.get("period"),
            "site_kw": round(site_kw, 2),
            "raw_live_iso_kw": round(raw_site_kw, 2),
            "kw_basis": kw_basis,
            "energy_cost_per_hour_usd": round(site_cost_per_hour, 2),
            "source_ok": bool(eia.get("ok", False)),
            "source_file": eia.get("source_file"),
            "unit": "kW",
        },
        "outage_and_downtime": {
            "predicted_event_count_total": int(outage_count),
            "predicted_hourly_loss_usd": round(predicted_hourly_loss, 2),
            "predicted_run_loss_usd": round(predicted_run_loss, 2),
            "predicted_run_avoided_usd": round(predicted_run_avoided, 2),
            "historical_events": int(ladder["historical_outage_events"]),
            "historical_hours": float(ladder["historical_outage_hours"]),
            "historical_cost_usd": float(ladder["historical_outage_cost_usd"]),
            "historical_avoided_usd": float(ladder["historical_avoided_loss_usd"]),
            "prevented_pct_from_evidence": round(prevented_pct, 4),
        },
        "gain_potential": {
            "immediate_gain_per_hour_usd": round(gain_now_per_hour, 2),
            "monthly_gain_usd": round(scale_monthly_gain, 2),
            "annual_gain_usd": round(scale_annual_gain, 2),
            "affected_asset_value_usd": round(affected_asset_total, 2),
            "roi_vs_site_energy_cost_pct": round(roi_vs_energy_pct, 4),
        },
        "source_paths": {
            "infra_frozen_deltas": str(INFRA_DELTA_FILE),
            "failure_predictions": str(FAILURE_PRED_FILE),
            "infra_audit_ledger": str(INFRA_AUDIT_FILE),
            "money_loss_ladder": str(LOSS_LADDER_FILE),
            "investor_evidence": str(EVIDENCE_FILE),
        },
        "status": "green" if site_kw > 0 else "warning",
    }


def run_once() -> Dict[str, Any]:
    payload = build_snapshot()
    atomic_write_json(OUT_FILE, payload)
    return payload


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="System Overlord 20-second economics snapshot")
    p.add_argument("--loop", action="store_true", help="Run continuously every 20 seconds")
    p.add_argument("--interval", type=int, default=20, help="Refresh interval in seconds")
    args = p.parse_args(argv)

    interval = max(5, int(args.interval))

    if not args.loop:
        payload = run_once()
        print(json.dumps(payload, indent=2))
        return 0

    while True:
        payload = run_once()
        print(
            f"[{payload.get('generated_utc')}] "
            f"kW={payload['site_live']['site_kw']:.2f} "
            f"$/h={payload['site_live']['energy_cost_per_hour_usd']:.2f} "
            f"gain/h={payload['gain_potential']['immediate_gain_per_hour_usd']:.2f}"
        )
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
