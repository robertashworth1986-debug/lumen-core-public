from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STACK_ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://api.kraken.com/0/public"
DEFAULT_HISTORY_ROOT = STACK_ROOT / "data" / "kraken_hourly_history"
DEFAULT_OUT_FILE = STACK_ROOT / "out" / "ops" / "kraken_history_collector_latest.json"
DEFAULT_ALPHA_MAP = STACK_ROOT / "out" / "ops" / "kraken_multi_tf_alpha_map_latest.json"
DEFAULT_TIMING_SCRIPT = Path(__file__).with_name("build_symbol_timing_edge_model.py")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def pair_token(value: Any) -> str:
    return str(value or "").upper().replace("/", "").replace("-", "").strip()


def http_json(path: str, params: dict[str, Any] | None, timeout_sec: float) -> dict[str, Any]:
    query = urllib.parse.urlencode(params or {})
    url = f"{BASE_URL}/{path}" + (f"?{query}" if query else "")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "LumaKrakenHistoryCollector/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    errors = payload.get("error") or []
    if errors:
        raise RuntimeError(f"Kraken {path} error: {errors}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Kraken {path} returned invalid result")
    return result


def fetch_pairs(timeout_sec: float) -> list[dict[str, Any]]:
    payload = http_json("AssetPairs", None, timeout_sec)
    rows: list[dict[str, Any]] = []
    for pair_id, meta in payload.items():
        if not isinstance(meta, dict):
            continue
        if str(meta.get("status") or "") != "online":
            continue
        quote = str(meta.get("quote") or "")
        if quote not in {"ZUSD", "USD", "USDT"}:
            continue
        altname = str(meta.get("altname") or pair_id)
        wsname = str(meta.get("wsname") or altname)
        if ".d" in altname or ".d" in wsname:
            continue
        rows.append(
            {
                "pair_id": str(pair_id),
                "altname": altname,
                "wsname": wsname,
                "quote": quote,
            }
        )
    return rows


def fetch_tickers(
    pairs: list[dict[str, Any]],
    timeout_sec: float,
    pause_sec: float,
) -> dict[str, dict[str, Any]]:
    pair_ids = [row["pair_id"] for row in pairs]
    out: dict[str, dict[str, Any]] = {}
    for start in range(0, len(pair_ids), 20):
        chunk = pair_ids[start : start + 20]
        try:
            payload = http_json(
                "Ticker",
                {"pair": ",".join(chunk)},
                timeout_sec,
            )
        except Exception:
            payload = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                out[str(key)] = value
        if pause_sec > 0.0:
            time.sleep(pause_sec)
    return out


def alpha_priority(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = payload.get("alpha_leaderboard") or []
    tokens: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("pair", "wsname", "altname"):
            token = pair_token(row.get(key))
            if token:
                tokens.append(token)
                break
    return list(dict.fromkeys(tokens))


def select_pairs(
    pairs: list[dict[str, Any]],
    tickers: dict[str, dict[str, Any]],
    alpha_tokens: list[str],
    pair_limit: int,
) -> list[dict[str, Any]]:
    token_map: dict[str, dict[str, Any]] = {}
    enriched: list[dict[str, Any]] = []
    for row in pairs:
        ticker = tickers.get(row["pair_id"]) or tickers.get(row["altname"]) or {}
        last = safe_float((ticker.get("c") or [0.0])[0])
        volume = safe_float((ticker.get("v") or [0.0, 0.0])[1])
        turnover = last * volume if last > 0.0 and volume > 0.0 else 0.0
        item = {**row, "turnover_24h_usd": turnover}
        enriched.append(item)
        for value in (row["pair_id"], row["altname"], row["wsname"]):
            token_map[pair_token(value)] = item

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for token in alpha_tokens:
        row = token_map.get(token)
        if row is None:
            continue
        identity = row["pair_id"]
        if identity in seen:
            continue
        selected.append(row)
        seen.add(identity)
        if len(selected) >= pair_limit:
            return selected
    for row in sorted(
        enriched,
        key=lambda item: safe_float(item.get("turnover_24h_usd")),
        reverse=True,
    ):
        identity = row["pair_id"]
        if identity in seen:
            continue
        selected.append(row)
        seen.add(identity)
        if len(selected) >= pair_limit:
            break
    return selected


def fetch_ohlc(
    pair_id: str,
    interval_min: int,
    timeout_sec: float,
    retries: int,
) -> list[list[Any]]:
    for attempt in range(max(1, retries)):
        try:
            payload = http_json(
                "OHLC",
                {"pair": pair_id, "interval": interval_min},
                timeout_sec,
            )
            for key, value in payload.items():
                if key != "last" and isinstance(value, list):
                    return value
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError):
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    return []


def file_pair(row: dict[str, Any]) -> tuple[str, str]:
    wsname = str(row.get("wsname") or "")
    if "/" in wsname:
        base, quote = wsname.split("/", 1)
    else:
        altname = str(row.get("altname") or row.get("pair_id") or "")
        quote = "USDT" if altname.endswith("USDT") else "USD"
        base = altname[: -len(quote)] if altname.endswith(quote) else altname
    if base == "XBT":
        base = "BTC"
    if base == "XDG":
        base = "DOGE"
    return base.upper(), quote.upper()


def read_existing(path: Path) -> dict[int, list[str]]:
    rows: dict[int, list[str]] = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                parsed = datetime.fromisoformat(
                    str(row.get("time") or "").replace("Z", "+00:00")
                )
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                ts = int(parsed.astimezone(timezone.utc).timestamp())
            except Exception:
                continue
            rows[ts] = [
                parsed.astimezone(timezone.utc).isoformat(),
                str(row.get("open") or ""),
                str(row.get("high") or ""),
                str(row.get("low") or ""),
                str(row.get("close") or ""),
                str(row.get("vwap") or ""),
                str(row.get("volume") or ""),
                str(row.get("count") or ""),
            ]
    return rows


def merge_rows(
    existing: dict[int, list[str]],
    fetched: list[list[Any]],
    interval_min: int,
) -> tuple[dict[int, list[str]], int]:
    merged = dict(existing)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    completed_before = now_ts - interval_min * 60
    before = len(merged)
    for raw in fetched:
        if not isinstance(raw, list) or len(raw) < 8:
            continue
        ts = safe_int(raw[0])
        if ts <= 0 or ts > completed_before:
            continue
        merged[ts] = [
            datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            str(raw[1]),
            str(raw[2]),
            str(raw[3]),
            str(raw[4]),
            str(raw[5]),
            str(raw[6]),
            str(raw[7]),
        ]
    return merged, max(0, len(merged) - before)


def write_history(path: Path, rows: dict[int, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "open", "high", "low", "close", "vwap", "volume", "count"])
        for ts in sorted(rows):
            writer.writerow(rows[ts])
    temp.replace(path)


def run_timing_model(args: argparse.Namespace) -> dict[str, Any]:
    if not args.rebuild_timing:
        return {"requested": False}
    command = [
        sys.executable,
        str(Path(args.timing_script).resolve()),
        "--data-root",
        str(Path(args.history_root).resolve()),
        "--out-root",
        str((STACK_ROOT / "out" / "ops").resolve()),
    ]
    completed = subprocess.run(
        command,
        cwd=STACK_ROOT,
        capture_output=True,
        text=True,
        timeout=max(120, int(args.timing_timeout_sec)),
    )
    return {
        "requested": True,
        "return_code": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def collect_once(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    history_root = Path(args.history_root).resolve()
    pairs = fetch_pairs(args.timeout_sec)
    tickers = fetch_tickers(pairs, args.timeout_sec, args.request_pause_sec)
    selected = select_pairs(
        pairs,
        tickers,
        alpha_priority(Path(args.alpha_map).resolve()),
        args.pair_limit,
    )
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for index, pair in enumerate(selected, start=1):
        fetched = fetch_ohlc(
            pair["pair_id"],
            args.interval_min,
            args.timeout_sec,
            args.retries,
        )
        base, quote = file_pair(pair)
        path = history_root / f"ohlc_{base}_{quote}.csv"
        if not fetched:
            errors.append({"pair": pair["pair_id"], "error": "empty_ohlc"})
            continue
        existing = read_existing(path)
        merged, added = merge_rows(existing, fetched, args.interval_min)
        write_history(path, merged)
        coverage_days = 0.0
        if len(merged) >= 2:
            keys = sorted(merged)
            coverage_days = (keys[-1] - keys[0]) / 86400.0
        results.append(
            {
                "pair_id": pair["pair_id"],
                "pair": f"{base}/{quote}",
                "path": str(path),
                "rows_total": len(merged),
                "rows_added": added,
                "coverage_days": round(coverage_days, 6),
                "turnover_24h_usd": round(
                    safe_float(pair.get("turnover_24h_usd")),
                    2,
                ),
            }
        )
        if args.request_pause_sec > 0.0:
            time.sleep(args.request_pause_sec)
        if index % 20 == 0:
            print(
                f"HISTORY_PROGRESS {index}/{len(selected)} "
                f"ok={len(results)} errors={len(errors)}",
                flush=True,
            )

    timing = run_timing_model(args)
    payload = {
        "generated_utc": now_iso(),
        "scope": "kraken_hourly_history_collector",
        "execution_authorized": False,
        "pairs_discovered": len(pairs),
        "pairs_selected": len(selected),
        "pairs_updated": len(results),
        "pair_errors": len(errors),
        "rows_added": sum(row["rows_added"] for row in results),
        "history_root": str(history_root),
        "interval_min": args.interval_min,
        "pair_limit": args.pair_limit,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "coverage": {
            "min_days": round(min((row["coverage_days"] for row in results), default=0.0), 6),
            "median_days": round(
                statistics_median([row["coverage_days"] for row in results]),
                6,
            ),
            "max_days": round(max((row["coverage_days"] for row in results), default=0.0), 6),
        },
        "results": results,
        "errors": errors[:200],
        "timing_rebuild": timing,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp.replace(output)
    return payload


def statistics_median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Persist Kraken's rolling hourly OHLC window into deduplicated per-pair "
            "CSV history and optionally rebuild the shadow timing model."
        )
    )
    parser.add_argument("--history-root", default=str(DEFAULT_HISTORY_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUT_FILE))
    parser.add_argument("--alpha-map", default=str(DEFAULT_ALPHA_MAP))
    parser.add_argument("--timing-script", default=str(DEFAULT_TIMING_SCRIPT))
    parser.add_argument("--pair-limit", type=int, default=80)
    parser.add_argument("--interval-min", type=int, default=60)
    parser.add_argument("--timeout-sec", type=float, default=16.0)
    parser.add_argument("--request-pause-sec", type=float, default=0.20)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--rebuild-timing", action="store_true")
    parser.add_argument("--timing-timeout-sec", type=int, default=300)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--cycle-sec", type=float, default=21_600.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    while True:
        try:
            payload = collect_once(args)
            print(f"KRAKEN_HISTORY_OUTPUT={Path(args.output).resolve()}", flush=True)
            print(
                "KRAKEN_HISTORY_COUNTS "
                f"selected={payload['pairs_selected']} "
                f"updated={payload['pairs_updated']} "
                f"rows_added={payload['rows_added']} "
                f"errors={payload['pair_errors']}",
                flush=True,
            )
        except Exception as exc:
            print(f"KRAKEN_HISTORY_ERROR={exc}", flush=True)
            if not args.daemon:
                return 2
        if not args.daemon:
            return 0
        time.sleep(max(900.0, float(args.cycle_sec)))


if __name__ == "__main__":
    raise SystemExit(main())
