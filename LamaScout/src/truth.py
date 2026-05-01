from __future__ import annotations
import json
import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .settings import CFG, OUT, utc_now
from .delta import DeltaEngine


@dataclass
class Strategy:
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    weight: float = 1.0
    evaluator: Callable[[pd.DataFrame], pd.Series] = field(default=None)


class TruthEngine:
    def __init__(self, config: dict | None = None):
        self.config = config or CFG.get("truth_engine", {})
        self.registry: Dict[str, Strategy] = {}
        self.history: List[dict] = []
        self.register_default_strategies()

    def register_strategy(self, strategy: Strategy) -> None:
        self.registry[strategy.name] = strategy

    def register_flowform(
        self,
        name: str,
        description: str,
        evaluator: Callable[[pd.DataFrame], pd.Series],
        tags: Iterable[str] | None = None,
        weight: float = 1.0,
        enabled: bool = True,
    ) -> None:
        self.register_strategy(
            Strategy(
                name=name,
                description=description,
                tags=list(tags or []),
                enabled=enabled,
                weight=weight,
                evaluator=evaluator,
            )
        )

    def register_default_strategies(self) -> None:
        self.register_flowform(
            name="hot_urgency",
            description="Ranks artists by urgency and breakout momentum from live signals.",
            evaluator=lambda df: df["hot_urgency"].fillna(0.0).astype(float),
            tags=["live", "urgency", "momentum"],
            weight=1.0,
        )
        self.register_flowform(
            name="breakout_forecast",
            description="Estimates breakout potential using follower, view and trend growth.",
            evaluator=lambda df: df["predicted_breakout"].fillna(0.0).astype(float),
            tags=["forecast", "breakout"],
            weight=0.9,
        )
        self.register_flowform(
            name="cross_platform_strength",
            description="Measures balance and strength across expected platform coverage.",
            evaluator=lambda df: df["cross_platform_strength"].fillna(0.0).astype(float),
            tags=["platform", "reach"],
            weight=0.75,
        )
        self.register_flowform(
            name="portfolio_diversity",
            description="Rewards portfolios with genre and geography diversity.",
            evaluator=lambda df: df["genre_signal"].fillna(0.0).astype(float) + df["location_signal"].fillna(0.0).astype(float),
            tags=["diversity", "portfolio"],
            weight=0.6,
        )
        self.register_flowform(
            name="audit_fidelity",
            description="Tracks proof-grade signals and evidence consistency across the run.",
            evaluator=lambda df: df["posting_consistency"].fillna(0.0).astype(float) if "posting_consistency" in df.columns else pd.Series(np.zeros(len(df)), index=df.index),
            tags=["proof", "audit"],
            weight=0.4,
            enabled=False,
        )

    def _evaluate_strategy(self, strategy: Strategy, df: pd.DataFrame) -> pd.Series:
        if not strategy.enabled:
            return pd.Series([], dtype=float)
        try:
            return strategy.evaluator(df).astype(float).fillna(0.0)
        except Exception:
            return pd.Series([0.0] * len(df), index=df.index)

    def strategy_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for name, strategy in self.registry.items():
            if not strategy.enabled:
                continue
            series = self._evaluate_strategy(strategy, df)
            if series.empty:
                scores[name] = 0.0
                continue
            scores[name] = float(series.mean())
        return scores

    def strategy_ranking(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for name, strategy in self.registry.items():
            scores = self._evaluate_strategy(strategy, df)
            rows.append({
                "strategy": name,
                "description": strategy.description,
                "tags": ", ".join(strategy.tags),
                "mean_score": float(scores.mean()) if not scores.empty else 0.0,
                "weight": float(strategy.weight),
                "enabled": bool(strategy.enabled),
            })
        return pd.DataFrame(rows).sort_values(["mean_score", "weight"], ascending=[False, False])

    def run_monte_carlo(self, df: pd.DataFrame, runs: int | None = None) -> dict:
        runs = runs or min(max(200, self.config.get("monte_carlo_runs", 1000)), 3000)
        candidates = df.copy()
        if candidates.empty:
            return {"runs": runs, "best_value": 0.0, "portfolio": [], "best_score": 0.0}

        if len(candidates) == 1:
            label = str(candidates.iloc[0].get("artist_name", ""))
            raw_score = float(candidates.iloc[0].get("champion_score", 0.0))
            return {"runs": runs, "best_value": raw_score, "portfolio": [label], "best_score": raw_score, "portfolio_size": 1}

        best_value = -float("inf")
        best_portfolio: List[str] = []
        portfolio_stats = []

        for _ in range(runs):
            size = random.randint(2, min(10, len(candidates)))
            subset = candidates.sample(n=size)
            raw_score = float(subset["champion_score"].sum())
            diversity = float(subset["genre"].nunique() + subset["state"].nunique())
            live_boost = float((subset["source_origin"] == "live").sum())
            penalty = float((subset["platform_count"] <= 1).sum()) * 2.0
            value = raw_score + diversity * 4.0 + live_boost * 3.0 - penalty
            portfolio_stats.append(value)
            if value > best_value:
                best_value = value
                best_portfolio = list(subset["artist_name"].astype(str))

        return {
            "runs": runs,
            "best_value": float(best_value if best_value != -float("inf") else 0.0),
            "portfolio": best_portfolio,
            "best_score": float(np.mean(portfolio_stats) if portfolio_stats else 0.0),
            "portfolio_size": len(best_portfolio),
        }

    def run_evolutionary(self, df: pd.DataFrame, generations: int | None = None, population: int | None = None) -> dict:
        generations = generations or int(self.config.get("evolutionary_generations", 30))
        population = population or int(self.config.get("evolutionary_population", 50))
        candidates = df.copy()
        if candidates.empty:
            return {"generations": generations, "population": population, "best_value": 0.0, "portfolio": []}

        indexed = candidates.reset_index(drop=True)
        if len(indexed) == 1:
            return {
                "generations": generations,
                "population": population,
                "best_value": float(indexed.iloc[0].get("champion_score", 0.0)),
                "portfolio": [str(indexed.iloc[0].get("artist_name", ""))],
                "portfolio_size": 1,
            }

        current_population: List[List[int]] = [random.sample(range(len(indexed)), min(5, len(indexed))) for _ in range(population)]
        best_portfolio: List[int] = []
        best_value = -float("inf")

        def score_portfolio(indexes: list[int]) -> float:
            subset = indexed.loc[indexes]
            raw_score = float(subset["champion_score"].sum())
            diversity = float(subset["genre"].nunique() + subset["state"].nunique())
            concentration = float((subset["platform_count"] <= 1).sum())
            return raw_score + diversity * 3.0 - concentration * 2.0

        for _ in range(generations):
            scored_population = sorted(current_population, key=score_portfolio, reverse=True)
            winners = scored_population[: max(1, population // 4)]
            current_population = winners.copy()
            while len(current_population) < population:
                parent_a = random.choice(winners)
                parent_b = random.choice(winners)
                child = list(dict.fromkeys(parent_a[: len(parent_a) // 2] + parent_b[len(parent_b) // 2 :]))
                if random.random() < 0.3 and len(child) > 1:
                    i = random.randrange(len(child))
                    child[i] = random.randrange(len(indexed))
                current_population.append(child)
            for portfolio in current_population:
                value = score_portfolio(portfolio)
                if value > best_value:
                    best_value = value
                    best_portfolio = portfolio.copy()

        return {
            "generations": generations,
            "population": population,
            "best_value": float(best_value if best_value != -float("inf") else 0.0),
            "portfolio": list(indexed.loc[best_portfolio, "artist_name"].astype(str).values),
            "portfolio_size": len(best_portfolio),
        }

    def compute_rolling_metrics(self, metrics: dict) -> dict:
        self.history.append(metrics)
        if len(self.history) > int(self.config.get("rolling_history_length", 20)):
            self.history = self.history[-int(self.config.get("rolling_history_length", 20)) :]

        windows = [h.get("truth_confidence", 0.0) for h in self.history]
        return {
            "rolling_truth_mean": float(statistics.mean(windows)) if windows else 0.0,
            "rolling_truth_stdev": float(statistics.stdev(windows)) if len(windows) > 1 else 0.0,
            "history_length": len(windows),
        }

    def assess(self, scored: pd.DataFrame) -> dict:
        base_summary = {
            "generated_utc": utc_now(),
            "total_artists": int(len(scored)),
            "live_artists": int((scored["source_origin"] == "live").sum()) if "source_origin" in scored.columns else 0,
            "champions": int((scored["tier"] == "CHAMPION").sum()) if "tier" in scored.columns else 0,
            "watchlist": int((scored["tier"] == "WATCHLIST").sum()) if "tier" in scored.columns else 0,
            "portfolio_size": int((scored["champion_portfolio"] == "PORTFOLIO").sum()) if "champion_portfolio" in scored.columns else 0,
        }

        strategy_scores = self.strategy_scores(scored)
        weighted_truth = sum(strategy_scores.get(k, 0.0) * self.registry[k].weight for k in strategy_scores) / max(
            1.0, sum(self.registry[k].weight for k in strategy_scores)
        )

        monte = self.run_monte_carlo(scored)
        evo = self.run_evolutionary(scored)

        truth_confidence = min(max(weighted_truth * 100.0, 0.0), 100.0)
        rolling = self.compute_rolling_metrics({"truth_confidence": truth_confidence})

        sort_keys = [key for key in ["champion_score", "hot_priority"] if key in scored.columns]
        delta_engine = DeltaEngine()
        delta_snapshot = delta_engine.freeze({
            **base_summary,
            "truth_confidence": truth_confidence,
            "strategy_scores": strategy_scores,
            "monte_carlo": monte,
            "evolutionary": evo,
        }, entity="truth")
        rolling_deltas = delta_engine.rolling_stats()

        summary = {
            **base_summary,
            "truth_engine_version": 1,
            "strategy_count": len([s for s in self.registry.values() if s.enabled]),
            "strategy_scores": strategy_scores,
            "truth_confidence": truth_confidence,
            "rolling_truth_mean": rolling["rolling_truth_mean"],
            "rolling_truth_stdev": rolling["rolling_truth_stdev"],
            "rolling_history_length": rolling["history_length"],
            "monte_carlo": monte,
            "evolutionary": evo,
            "active_strategies": [name for name, strat in self.registry.items() if strat.enabled],
            "top_truth_artists": scored.sort_values(sort_keys, ascending=[False] * len(sort_keys)).head(10)["artist_name"].astype(str).tolist() if sort_keys else scored["artist_name"].astype(str).head(10).tolist(),
            "delta_checksum": delta_snapshot["checksum"],
            "previous_delta_checksum": delta_snapshot["previous_checksum"],
            "delta_size": delta_snapshot["delta_size"],
            "delta_energy": delta_snapshot["truth_energy"],
            "delta_stability": delta_snapshot["stability_score"],
            "rolling_delta_history_length": rolling_deltas["history_length"],
            "rolling_delta_energy": rolling_deltas["average_energy"],
            "rolling_delta_stability": rolling_deltas["average_stability"],
            "notes": "Modular rolling truth engine for LumaScout strategy registry and live metric pulse.",
        }

        (OUT / "truth_engine_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
