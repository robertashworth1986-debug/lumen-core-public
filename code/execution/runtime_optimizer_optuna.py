import argparse
import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import optuna

try:
    import orjson
except Exception:
    orjson = None


ROOT = Path(r"c:/LumaTrader/INSTITUTIONAL_STACK_V2")
TRADE_LOG_DEFAULT = ROOT / "out" / "execution" / "trade_log.json"
OUT_FILE_DEFAULT = ROOT / "out" / "execution" / "runtime_optimizer_recommendation.json"


def load_json(path: Path) -> Any:
    if not path.exists():
        return []
    raw = path.read_bytes()
    if orjson is not None:
        return orjson.loads(raw)
    import json
    return json.loads(raw.decode("utf-8"))


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if orjson is not None:
        path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
        return
    import json
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def closed_trades(trade_log: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in trade_log:
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).upper() != "CLOSED":
            continue
        if row.get("net_pnl_pct") is None:
            continue
        if row.get("gate_score") is None:
            continue
        out.append(row)
    return out


def objective_factory(rows: List[Dict[str, Any]], min_kept: int):
    def objective(trial: optuna.Trial) -> float:
        min_gate_score = trial.suggest_float("min_gate_score_for_entry", 0.94, 0.999)
        kept = [r for r in rows if float(r.get("gate_score", 0.0) or 0.0) >= min_gate_score]

        if len(kept) < min_kept:
            return -1e6 + len(kept)

        returns = np.array([float(r.get("net_pnl_pct", 0.0) or 0.0) for r in kept], dtype=float)
        mean_ret = float(np.mean(returns))
        pnl_sum = float(np.sum(returns))
        downside = float(np.mean(np.minimum(returns, 0.0)))

        # Reward positive expectancy and enough usable opportunities; penalize downside.
        score = (mean_ret * 6.0) + (pnl_sum * 0.25) + (len(kept) * 0.02) + (downside * 2.5)
        return float(score)

    return objective


def heuristic_recommendation(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    gate_scores = np.array([float(r.get("gate_score", 0.0) or 0.0) for r in rows], dtype=float) if rows else np.array([])
    if gate_scores.size == 0:
        gate_floor = 0.996
    else:
        gate_floor = float(np.quantile(gate_scores, 0.65))
        gate_floor = float(max(0.94, min(0.999, gate_floor)))

    return {
        "min_gate_score_for_entry": round(gate_floor, 3),
        "selection_min_edge_bps": 10.0,
        "min_expected_net_edge_bps": 32.0,
        "edge_fee_coverage_multiplier": 0.60,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize runtime thresholds from historical trade log.")
    parser.add_argument("--trade-log", default=str(TRADE_LOG_DEFAULT))
    parser.add_argument("--out", default=str(OUT_FILE_DEFAULT))
    parser.add_argument("--trials", type=int, default=80)
    parser.add_argument("--min-kept", type=int, default=5)
    args = parser.parse_args()

    trade_log_path = Path(args.trade_log)
    out_path = Path(args.out)

    payload = load_json(trade_log_path)
    rows = closed_trades(payload if isinstance(payload, list) else [])

    rec = heuristic_recommendation(rows)
    optimization_meta: Dict[str, Any] = {
        "used_optuna": False,
        "reason": "insufficient_data",
        "closed_trade_count": len(rows),
    }

    if len(rows) >= max(8, int(args.min_kept)):
        study = optuna.create_study(direction="maximize")
        study.optimize(objective_factory(rows, int(args.min_kept)), n_trials=max(10, int(args.trials)))
        best = study.best_params
        rec["min_gate_score_for_entry"] = round(float(best.get("min_gate_score_for_entry", rec["min_gate_score_for_entry"])), 3)
        optimization_meta = {
            "used_optuna": True,
            "closed_trade_count": len(rows),
            "best_value": float(study.best_value),
            "trials": int(len(study.trials)),
        }

    output = {
        "timestamp_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "recommendation": rec,
        "meta": optimization_meta,
        "source_trade_log": str(trade_log_path),
    }
    dump_json(out_path, output)

    print("runtime optimizer complete")
    print(f"closed_trades={len(rows)}")
    print(f"recommendation={rec}")
    print(f"out={out_path}")


if __name__ == "__main__":
    main()
