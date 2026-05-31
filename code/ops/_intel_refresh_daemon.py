"""
LUMA INTEL REFRESH DAEMON
Continuously keeps symbol_flip_intel_top5.json fresh from the latest Kraken alpha map.

Cycle behaviour:
  - Every DERIVE_INTERVAL_SEC (default 300 = 5 min): re-derive intel from latest alpha map.
  - Every SCAN_INTERVAL_SEC (default 1800 = 30 min): trigger a fresh quick alpha map scan
    before deriving, so we always have live market data.
  - Writes heartbeat to out/execution/intel_refresh_daemon_heartbeat.json each cycle.
  - All writes are atomic (tmp file + rename) so the executor never reads a partial file.
"""
import json
import os
import sys
import time
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────────────
STACK_ROOT   = r"C:\LumaTrader\INSTITUTIONAL_STACK_V2"
ALPHA_LATEST = os.path.join(STACK_ROOT, "out", "ops", "kraken_multi_tf_alpha_map_latest.json")
INTEL_OUT    = os.path.join(STACK_ROOT, "out", "execution", "symbol_flip_intel_top5.json")
HB_OUT       = os.path.join(STACK_ROOT, "out", "execution", "intel_refresh_daemon_heartbeat.json")
SCANNER_PY   = os.path.join(STACK_ROOT, "code", "ops", "build_kraken_multi_tf_alpha_map.py")

# ── Config (tunable at runtime via env vars) ────────────────────────────────────
DERIVE_INTERVAL_SEC     = int(os.environ.get("INTEL_DERIVE_INTERVAL", "300"))   # 5 min
SCAN_INTERVAL_SEC       = int(os.environ.get("INTEL_SCAN_INTERVAL",   "900"))   # 15 min (was 30)
EMERGENCY_STALE_SEC     = int(os.environ.get("INTEL_EMERGENCY_STALE", "2700")) # force rescan if > 45 min stale
TOP_N               = int(os.environ.get("INTEL_TOP_N",           "12"))
MAX_SPREAD_BPS      = float(os.environ.get("INTEL_MAX_SPREAD_BPS", "80"))   # filter wide-spread pairs
SCAN_TOP_LIQUID     = int(os.environ.get("INTEL_SCAN_TOP_LIQUID", "100"))   # quick scan
SCAN_LIMIT          = int(os.environ.get("INTEL_SCAN_LIMIT",      "60"))

# ── Python exe discovery ────────────────────────────────────────────────────────
def find_python():
    candidates = [
        os.path.join("C:\\LumaTrader", "venv3.11", "Scripts", "python.exe"),
        os.path.join("C:\\LumaTrader", ".venv",    "Scripts", "python.exe"),
        sys.executable,
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "python"


# ── Utilities ──────────────────────────────────────────────────────────────────
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_atomic(path: str, data: dict):
    """Write JSON atomically via tmp file to avoid partial reads by executor."""
    dir_ = os.path.dirname(path)
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False,
                                    suffix=".tmp", encoding="utf-8") as tf:
        json.dump(data, tf, indent=2, ensure_ascii=False)
        tmp_path = tf.name
    shutil.move(tmp_path, path)


def alpha_age_sec(alpha: dict) -> float:
    """Seconds since the alpha map was generated."""
    gen = alpha.get("generated_utc", "")
    if not gen:
        return float("inf")
    try:
        # Handle both offset-aware and naive ISO strings
        dt = datetime.fromisoformat(gen)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return float("inf")


def strip_usd(altname: str) -> str:
    """ALLOUSD → ALLO, XBTUSD → XBT, ETHUSD → ETH"""
    for suffix in ("USD", "USDT", "USDC"):
        if altname.upper().endswith(suffix):
            return altname[: -len(suffix)]
    return altname


def derive_intel(alpha: dict) -> dict | None:
    """
    Convert alpha_leaderboard → symbol_flip_intel_top5.json format.
    Returns None if the alpha map has no leaderboard data.
    """
    leaderboard = alpha.get("alpha_leaderboard", [])
    if not leaderboard:
        return None

    # Sort by alpha_edge_score descending, filter out wide-spread pairs
    ranked = sorted(leaderboard, key=lambda x: float(x.get("alpha_edge_score", 0)), reverse=True)

    candidates = []
    seen_symbols = set()
    skipped_spread = 0
    for entry in ranked:
        spread = float(entry.get("spread_bps", 0))
        if spread > MAX_SPREAD_BPS:
            skipped_spread += 1
            continue
        sym = strip_usd(entry.get("altname", "") or entry.get("pair", ""))
        if not sym or sym in seen_symbols:
            continue
        seen_symbols.add(sym)
        candidates.append({
            "symbol":           sym,
            "alpha_long_score": round(float(entry.get("alpha_edge_score", 0)), 6),
            "strategy_mode":    entry.get("strategy_mode", "watch"),
            "return_1h_pct":    round(float(entry.get("r_1h_pct",  0)), 6),
            "return_24h_pct":   round(float(entry.get("r_24h_pct", 0)), 6),
            "return_7d_pct":    round(float(entry.get("r_7d_pct",  0)), 6),
            "momentum_score":   round(float(entry.get("momentum_score", 0)), 4),
            "spread_bps":       round(float(entry.get("spread_bps", 0)), 2),
        })
        if len(candidates) >= TOP_N:
            break

    focus = [c["symbol"] for c in candidates[:5]]
    return {
        "generated_utc":  utcnow_iso(),
        "source":         "kraken_multi_tf_alpha_map",
        "alpha_map_age_sec": round(alpha_age_sec(alpha), 1),
        "long_candidates": candidates,
        "focus_symbols":   focus,
    }


def trigger_scan(python_exe: str) -> bool:
    """Run the quick alpha map scan synchronously. Returns True on success."""
    print(f"  [SCAN] Triggering fresh quick alpha map scan "
          f"(top_liquid={SCAN_TOP_LIQUID}, limit={SCAN_LIMIT}) ...", flush=True)
    try:
        result = subprocess.run(
            [
                python_exe, SCANNER_PY,
                "--stack-root",       STACK_ROOT,
                "--top-liquid",       str(SCAN_TOP_LIQUID),
                "--limit",            str(SCAN_LIMIT),
                "--min-turnover-usd", "100000",
                "--max-spread-bps",   "120",
                "--quotes",           "ZUSD,USDT",
            ],
            timeout=300,   # 5-minute hard cap
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("  [SCAN] Scan complete ✓", flush=True)
            return True
        else:
            print(f"  [SCAN] Scan exited {result.returncode}: "
                  f"{result.stderr[-400:] if result.stderr else '(no stderr)'}", flush=True)
            return False
    except subprocess.TimeoutExpired:
        print("  [SCAN] Scan timed out after 5 min — using cached alpha map", flush=True)
        return False
    except Exception as e:
        print(f"  [SCAN] Scan error: {e}", flush=True)
        return False


# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    python_exe      = find_python()
    last_scan_utc   = 0.0   # epoch seconds of last scan trigger
    last_derive_utc = 0.0
    cycle           = 0

    print("=" * 68, flush=True)
    print("  LUMA INTEL REFRESH DAEMON", flush=True)
    print(f"  derive every {DERIVE_INTERVAL_SEC}s  |  scan every {SCAN_INTERVAL_SEC}s  |  top_n={TOP_N}", flush=True)
    print(f"  python: {python_exe}", flush=True)
    print(f"  alpha:  {ALPHA_LATEST}", flush=True)
    print(f"  intel:  {INTEL_OUT}", flush=True)
    print("=" * 68, flush=True)
    print(flush=True)

    while True:
        now = time.time()
        cycle += 1
        ts = datetime.now().strftime("%H:%M:%S")

        # ── Decide whether to scan ──────────────────────────────────────────
        do_scan = False
        alpha_check = load_json(ALPHA_LATEST)
        _cur_age = alpha_age_sec(alpha_check)
        if (now - last_scan_utc) >= SCAN_INTERVAL_SEC and _cur_age > SCAN_INTERVAL_SEC:
            do_scan = True
        elif _cur_age > EMERGENCY_STALE_SEC:
            # Emergency re-scan: alpha map is dangerously stale regardless of interval
            print(f"[{ts}] #{cycle:04d}  ⚠ EMERGENCY RESCAN — alpha_age={_cur_age/60:.1f} min > {EMERGENCY_STALE_SEC//60} min threshold", flush=True)
            do_scan = True

        if do_scan:
            scan_ok = trigger_scan(python_exe)
            last_scan_utc = now
            if not scan_ok:
                print(f"[{ts}] #{cycle:04d}  scan failed — will retry next scan window", flush=True)

        # ── Derive intel from latest alpha map ──────────────────────────────
        alpha = load_json(ALPHA_LATEST)
        if not alpha:
            print(f"[{ts}] #{cycle:04d}  ⚠ alpha map not found at {ALPHA_LATEST}", flush=True)
            status = "no_alpha_map"
        else:
            age_sec = alpha_age_sec(alpha)
            intel   = derive_intel(alpha)
            if intel:
                write_atomic(INTEL_OUT, intel)
                last_derive_utc = now
                top3 = ", ".join(
                    f"{c['symbol']}({c['alpha_long_score']:.1f})"
                    for c in intel["long_candidates"][:3]
                )
                print(f"[{ts}] #{cycle:04d}  OK intel refreshed  "
                      f"alpha_age={age_sec/60:.1f}min  top3=[{top3}]", flush=True)
                status = "ok"
            else:
                print(f"[{ts}] #{cycle:04d}  WARN alpha leaderboard empty "
                      f"(alpha_age={age_sec/60:.1f}min)", flush=True)
                status = "empty_leaderboard"

        # ── Heartbeat ───────────────────────────────────────────────────────
        _hb_alpha = load_json(ALPHA_LATEST)
        write_atomic(HB_OUT, {
            "generated_utc":       utcnow_iso(),
            "cycle":               cycle,
            "status":              status,
            "last_derive_utc":     datetime.fromtimestamp(last_derive_utc, tz=timezone.utc).isoformat() if last_derive_utc else None,
            "last_scan_utc":       datetime.fromtimestamp(last_scan_utc,   tz=timezone.utc).isoformat() if last_scan_utc   else None,
            "alpha_map_age_sec":   round(alpha_age_sec(_hb_alpha), 1),
            "derive_interval_sec": DERIVE_INTERVAL_SEC,
            "scan_interval_sec":   SCAN_INTERVAL_SEC,
            "emergency_stale_sec": EMERGENCY_STALE_SEC,
            "top_n":               TOP_N,
        })

        # ── Sleep until next derive cycle ───────────────────────────────────
        elapsed = time.time() - now
        sleep_for = max(0.0, DERIVE_INTERVAL_SEC - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTEL DAEMON] Stopped by user.", flush=True)
