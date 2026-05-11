import numpy as np
import pandas as pd
import statistics
import inspect
from datetime import datetime, timezone
from typing import Any, Dict

class MetaEngine:
    """
    Bounded Infinity Meta-Engine: Dynamically routes capital between engines (trading, sports, hybrid/harmonic)
    based on real-time KPIs for maximum compounding and risk-adjusted returns.
    """
    def __init__(self, engines: Dict[str, Any]):
        """
        engines: dict of {name: engine_instance}
        """
        self.engines = engines
        self.history = []
        self._fallback_metrics = {
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "energy": 0.0,
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _extract_metrics(self, engine: Any, context: Any = None) -> Dict[str, float]:
        if hasattr(engine, "evaluate_kpis"):
            try:
                metrics = engine.evaluate_kpis(context)
                if isinstance(metrics, dict):
                    return metrics
            except Exception:
                pass

        if hasattr(engine, "get_metrics"):
            try:
                metrics = engine.get_metrics()
                if isinstance(metrics, dict):
                    return metrics
            except Exception:
                pass

        if hasattr(engine, "summary") and isinstance(engine.summary, dict):
            return self._summary_to_kpis(engine.summary)

        if hasattr(engine, "build_summary"):
            try:
                summary = engine.build_summary()
                if isinstance(summary, dict):
                    return self._summary_to_kpis(summary)
            except Exception:
                pass

        return dict(self._fallback_metrics)

    def _summary_to_kpis(self, summary: Dict[str, Any]) -> Dict[str, float]:
        metrics = dict(self._fallback_metrics)
        if "sharpe" in summary:
            metrics["sharpe"] = self._safe_float(summary.get("sharpe"))
        if "max_drawdown" in summary:
            metrics["max_drawdown"] = self._safe_float(summary.get("max_drawdown"))
        if "win_rate" in summary:
            metrics["win_rate"] = self._safe_float(summary.get("win_rate"))
        if "overall_karmuk" in summary:
            metrics["sharpe"] = max(metrics["sharpe"], self._safe_float(summary.get("overall_karmuk")) / 10.0)
        if "burst_energy" in summary:
            metrics["energy"] = self._safe_float(summary.get("burst_energy"))
        if "case_strength" in summary:
            metrics["sharpe"] = max(metrics["sharpe"], self._safe_float(summary.get("case_strength")))
        return metrics

    def _score_metrics(self, metrics: Dict[str, float]) -> float:
        sharpe = self._safe_float(metrics.get("sharpe"), 0.0)
        drawdown = self._safe_float(metrics.get("max_drawdown", 0.0))
        win_rate = self._safe_float(metrics.get("win_rate", 0.0))
        energy = self._safe_float(metrics.get("energy", 0.0))
        return round(sharpe + 0.15 * win_rate + 0.1 * energy - 0.5 * abs(drawdown), 6)

    def allocate(self, context: Any = None) -> Dict[str, float]:
        """
        Selects engine(s) with the best real-time KPIs.
        Returns allocation dict: {engine_name: weight}
        """
        scores = {}
        for name, engine in self.engines.items():
            metrics = self._extract_metrics(engine, context)
            scores[name] = self._score_metrics(metrics)

        total = sum(max(0.0, score) for score in scores.values())
        if total <= 0.0:
            count = len(scores) if scores else 1
            return {name: 1.0 / count for name in scores}

        return {name: max(0.0, score) / total for name, score in scores.items()}

    def run(self, data: Any, context: Any = None) -> Dict[str, Any]:
        """
        Routes data/capital to engines according to allocation, collects results.
        """
        alloc = self.allocate(context)
        results = {}
        for name, weight in alloc.items():
            engine = self.engines[name]
            if hasattr(engine, "run"):
                try:
                    run_fn = getattr(engine, "run")
                    try:
                        sig = inspect.signature(run_fn)
                        params = list(sig.parameters.values())
                        param_names = {p.name for p in params}
                        has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
                        has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)

                        args = []
                        kwargs = {}

                        if "data" in param_names:
                            kwargs["data"] = data
                        else:
                            positional_params = [
                                p
                                for p in params
                                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                            ]
                            if positional_params:
                                first_name = positional_params[0].name
                                if first_name not in {"weight", "context"}:
                                    args.append(data)
                            elif has_var_positional:
                                args.append(data)

                        if "weight" in param_names or has_var_keyword:
                            kwargs["weight"] = weight
                        if "context" in param_names or has_var_keyword:
                            kwargs["context"] = context

                        results[name] = run_fn(*args, **kwargs)
                    except (TypeError, ValueError):
                        # Fallback for dynamic/c-extension callables that do not expose a reliable signature.
                        try:
                            results[name] = run_fn(data, context=context)
                        except TypeError:
                            results[name] = run_fn(data)
                except Exception as e:
                    results[name] = {"error": str(e), "weight": weight}
            else:
                results[name] = {
                    "weight": weight,
                    "metrics": self._extract_metrics(engine, context),
                }

        self.history.append({"alloc": alloc, "results": results, "timestamp": datetime.now(timezone.utc).isoformat()})
        return results
