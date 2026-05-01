from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

try:
    import cvxpy as cp
except Exception:
    cp = None


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def optimize_candidate_weights(
    candidates: List[Dict[str, Any]],
    available_heat_pct: float,
    max_single_position_pct: float,
    turnover_reference: Dict[str, float] | None,
    risk_aversion: float,
    turnover_penalty: float,
) -> Dict[str, Any]:
    if not candidates:
        return {"ok": True, "status": "no_candidates", "weights": {}, "solver": None}

    fallback_scores: Dict[str, float] = {}
    for candidate in candidates:
        sym = str(candidate.get("symbol", ""))
        fallback_scores[sym] = max(_f(candidate.get("expected_return"), 0.0), 1e-9)

    total_score = sum(fallback_scores.values())
    if total_score <= 0.0:
        total_score = float(len(candidates))
        for sym in fallback_scores:
            fallback_scores[sym] = 1.0

    def _fallback(status: str) -> Dict[str, Any]:
        weights: Dict[str, float] = {}
        remaining = max(available_heat_pct, 0.0)
        for candidate in sorted(candidates, key=lambda item: item.get("expected_return", 0.0), reverse=True):
            sym = str(candidate.get("symbol", ""))
            score_weight = fallback_scores[sym] / total_score
            proposed = min(
                available_heat_pct * score_weight,
                _f(candidate.get("max_weight_cap_pct"), max_single_position_pct),
                remaining,
            )
            weights[sym] = max(proposed, 0.0)
            remaining = max(remaining - weights[sym], 0.0)
        return {"ok": False, "status": status, "weights": weights, "solver": None}

    if cp is None:
        return _fallback("cvxpy_unavailable")

    mu = np.array([max(_f(candidate.get("expected_return"), 0.0), 1e-9) for candidate in candidates], dtype=float)
    sigma_diag = np.array([max(_f(candidate.get("estimated_vol"), 0.0), 0.005) ** 2 for candidate in candidates], dtype=float)
    caps = np.array([
        min(_f(candidate.get("max_weight_cap_pct"), max_single_position_pct), max_single_position_pct)
        for candidate in candidates
    ], dtype=float)
    prev = np.array([
        max(_f((turnover_reference or {}).get(str(candidate.get("symbol", ""))), 0.0), 0.0)
        for candidate in candidates
    ], dtype=float)

    try:
        w = cp.Variable(len(candidates), nonneg=True)
        objective = cp.Maximize(
            (mu @ w)
            - (risk_aversion * cp.sum(cp.multiply(sigma_diag, cp.square(w))))
            - (turnover_penalty * cp.sum_squares(w - prev))
        )
        constraints = [cp.sum(w) <= max(available_heat_pct, 0.0), w <= caps]
        problem = cp.Problem(objective, constraints)

        solver_used = None
        for solver in [cp.OSQP, cp.SCS, cp.CLARABEL]:
            try:
                problem.solve(solver=solver, warm_start=True, verbose=False)
                solver_used = str(solver)
                if problem.status in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
                    break
            except Exception:
                continue

        if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE} or w.value is None:
            return _fallback(f"optimizer_status={problem.status}")

        return {
            "ok": True,
            "status": str(problem.status),
            "weights": {
                str(candidate.get("symbol", "")): max(float(w.value[idx]), 0.0)
                for idx, candidate in enumerate(candidates)
            },
            "solver": solver_used,
        }
    except Exception as exc:
        return _fallback(f"optimizer_exception={exc}")