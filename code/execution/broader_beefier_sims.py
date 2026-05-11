from __future__ import annotations

import argparse
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution" / "broader_beefier_sims.json"


@dataclass
class SimConfig:
    workers: int
    rounds: int
    gbm_paths: int
    gbm_steps: int
    matrix_dim: int
    matrix_rounds: int
    graph_nodes: int
    graph_steps: int
    seed: int


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sim_gbm(cfg: dict[str, Any], task_idx: int) -> dict[str, Any]:
    rng = np.random.default_rng(cfg["seed"] + 101 + task_idx)
    paths = int(cfg["gbm_paths"])
    steps = int(cfg["gbm_steps"])
    dt = 1.0 / steps
    mu = 0.11
    sigma = 0.32
    s0 = 1.0

    z = rng.standard_normal((paths, steps), dtype=np.float64)
    increments = (mu - 0.5 * sigma * sigma) * dt + sigma * np.sqrt(dt) * z
    log_s = np.log(s0) + np.cumsum(increments, axis=1)
    terminal = np.exp(log_s[:, -1])
    pnl = terminal - 1.0

    var_95 = float(np.quantile(pnl, 0.05))
    es_95 = float(pnl[pnl <= var_95].mean()) if np.any(pnl <= var_95) else var_95
    sharpe = float(np.mean(pnl) / (np.std(pnl) + 1e-12))

    return {
        "sim": "gbm_monte_carlo",
        "task_idx": task_idx,
        "paths": paths,
        "steps": steps,
        "mean_pnl": float(np.mean(pnl)),
        "std_pnl": float(np.std(pnl)),
        "var_95": var_95,
        "es_95": es_95,
        "sharpe_like": sharpe,
    }


def _sim_random_matrix(cfg: dict[str, Any], task_idx: int) -> dict[str, Any]:
    rng = np.random.default_rng(cfg["seed"] + 211 + task_idx)
    dim = int(cfg["matrix_dim"])
    rounds = int(cfg["matrix_rounds"])

    max_eval = -1e18
    min_eval = 1e18
    trace_avg = 0.0

    for _ in range(rounds):
        a = rng.normal(0.0, 1.0, size=(dim, dim))
        cov = (a.T @ a) / max(dim, 1)
        eig = np.linalg.eigvalsh(cov)
        max_eval = max(max_eval, float(eig[-1]))
        min_eval = min(min_eval, float(eig[0]))
        trace_avg += float(np.trace(cov))

    trace_avg /= max(rounds, 1)
    cond = float(max_eval / max(min_eval, 1e-12))

    return {
        "sim": "random_matrix_stress",
        "task_idx": task_idx,
        "dim": dim,
        "rounds": rounds,
        "eig_max": max_eval,
        "eig_min": min_eval,
        "condition_number": cond,
        "trace_avg": trace_avg,
    }


def _sim_graph_diffusion(cfg: dict[str, Any], task_idx: int) -> dict[str, Any]:
    rng = np.random.default_rng(cfg["seed"] + 307 + task_idx)
    n = int(cfg["graph_nodes"])
    steps = int(cfg["graph_steps"])

    p = min(8.0 / max(n, 1), 0.15)
    adj = (rng.random((n, n)) < p).astype(np.float64)
    np.fill_diagonal(adj, 0.0)
    adj = np.maximum(adj, adj.T)

    deg = adj.sum(axis=1)
    deg[deg == 0] = 1.0
    w = adj / deg[:, None]

    x = rng.random(n)
    x[: max(3, n // 100)] = 1.0

    for _ in range(steps):
        x = 0.85 * (w @ x) + 0.15 * x
        x = np.clip(x, 0.0, 1.0)

    hot = int((x > 0.75).sum())
    mean_state = float(x.mean())
    entropy = float(-np.mean(x * np.log(x + 1e-12) + (1 - x) * np.log(1 - x + 1e-12)))

    return {
        "sim": "graph_diffusion_contagion",
        "task_idx": task_idx,
        "nodes": n,
        "steps": steps,
        "hot_nodes": hot,
        "mean_state": mean_state,
        "state_entropy": entropy,
    }


def _run_task(kind: str, cfg: dict[str, Any], task_idx: int) -> dict[str, Any]:
    t0 = time.perf_counter()
    if kind == "gbm":
        out = _sim_gbm(cfg, task_idx)
    elif kind == "matrix":
        out = _sim_random_matrix(cfg, task_idx)
    else:
        out = _sim_graph_diffusion(cfg, task_idx)
    out["duration_sec"] = round(time.perf_counter() - t0, 4)
    return out


def run_once(config: SimConfig) -> dict[str, Any]:
    cfg = {
        "workers": config.workers,
        "rounds": config.rounds,
        "gbm_paths": config.gbm_paths,
        "gbm_steps": config.gbm_steps,
        "matrix_dim": config.matrix_dim,
        "matrix_rounds": config.matrix_rounds,
        "graph_nodes": config.graph_nodes,
        "graph_steps": config.graph_steps,
        "seed": config.seed,
    }

    tasks: list[tuple[str, int]] = []
    for i in range(config.rounds):
        tasks.append(("gbm", i))
        tasks.append(("matrix", i))
        tasks.append(("graph", i))

    results: list[dict[str, Any]] = []
    started = time.perf_counter()

    with ProcessPoolExecutor(max_workers=config.workers) as ex:
        futs = [ex.submit(_run_task, k, cfg, i) for (k, i) in tasks]
        for fut in as_completed(futs):
            results.append(fut.result())

    total_sec = time.perf_counter() - started

    gbm = [r for r in results if r["sim"] == "gbm_monte_carlo"]
    matrix = [r for r in results if r["sim"] == "random_matrix_stress"]
    graph = [r for r in results if r["sim"] == "graph_diffusion_contagion"]

    summary = {
        "gbm_mean_sharpe_like": float(np.mean([r["sharpe_like"] for r in gbm])) if gbm else 0.0,
        "matrix_avg_condition": float(np.mean([r["condition_number"] for r in matrix])) if matrix else 0.0,
        "graph_avg_hot_nodes": float(np.mean([r["hot_nodes"] for r in graph])) if graph else 0.0,
        "tasks_total": len(results),
        "throughput_tasks_per_sec": float(len(results) / max(total_sec, 1e-9)),
    }

    payload = {
        "generated_utc": now_utc(),
        "schema": "broader_beefier_sims_v1",
        "machine": {
            "cpu_count": os.cpu_count() or 1,
            "workers": config.workers,
            "python": sys.version,
        },
        "config": cfg,
        "runtime_sec": round(total_sec, 3),
        "summary": summary,
        "results": results,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def default_workers() -> int:
    c = os.cpu_count() or 8
    return max(2, c - 2)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Broader/Beefier multi-core simulation runner")
    p.add_argument("--workers", type=int, default=default_workers())
    p.add_argument("--rounds", type=int, default=8)
    p.add_argument("--gbm-paths", type=int, default=20000)
    p.add_argument("--gbm-steps", type=int, default=240)
    p.add_argument("--matrix-dim", type=int, default=220)
    p.add_argument("--matrix-rounds", type=int, default=5)
    p.add_argument("--graph-nodes", type=int, default=1200)
    p.add_argument("--graph-steps", type=int, default=180)
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--loop", action="store_true")
    p.add_argument("--interval", type=int, default=120)
    args = p.parse_args(argv)

    cfg = SimConfig(
        workers=max(1, args.workers),
        rounds=max(1, args.rounds),
        gbm_paths=max(1000, args.gbm_paths),
        gbm_steps=max(60, args.gbm_steps),
        matrix_dim=max(32, args.matrix_dim),
        matrix_rounds=max(1, args.matrix_rounds),
        graph_nodes=max(100, args.graph_nodes),
        graph_steps=max(20, args.graph_steps),
        seed=args.seed,
    )

    if args.loop:
        while True:
            out = run_once(cfg)
            print(json.dumps({
                "ts": out["generated_utc"],
                "runtime_sec": out["runtime_sec"],
                "tasks": out["summary"]["tasks_total"],
                "throughput": round(out["summary"]["throughput_tasks_per_sec"], 2),
                "workers": out["machine"]["workers"],
            }, indent=2))
            time.sleep(max(30, args.interval))
    else:
        out = run_once(cfg)
        print(json.dumps({
            "ts": out["generated_utc"],
            "runtime_sec": out["runtime_sec"],
            "tasks": out["summary"]["tasks_total"],
            "throughput": round(out["summary"]["throughput_tasks_per_sec"], 2),
            "output": str(OUT),
        }, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
