"""Canonical modular engine primitives used across modular_* wrappers."""

from typing import Any, Callable, Dict, List, Optional

import json
import pandas as pd


class SignalModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        out = self.func(df, self.params)
        if not isinstance(out, pd.Series):
            raise TypeError(f"Signal '{self.name}' did not return a pandas Series")
        return out.reindex(df.index)


class StrategyEngine:
    def __init__(self):
        self.signal_modules: List[SignalModule] = []
        self.capital_allocator: Optional[Callable[[pd.DataFrame, Dict[str, Any]], pd.Series]] = None
        self.timescales: List[str] = []

    def add_signal(self, module: SignalModule) -> None:
        self.signal_modules.append(module)

    def set_capital_allocator(self, allocator: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series]) -> None:
        self.capital_allocator = allocator

    def set_timescales(self, timescales: List[str]) -> None:
        self.timescales = list(timescales)

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        results = pd.DataFrame(index=df.index)
        for module in self.signal_modules:
            results[module.name] = module.compute(df).fillna(0.0)
        if self.capital_allocator is not None:
            alloc = self.capital_allocator(results, {"source": df})
            if not isinstance(alloc, pd.Series):
                raise TypeError("Capital allocator must return a pandas Series")
            results["capital"] = alloc.reindex(df.index).fillna(0.0)
        return results


def moving_average_signal(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("moving_average_signal requires a 'close' column")
    window = max(int(params.get("window", 20)), 1)
    ma = df["close"].rolling(window=window, min_periods=window).mean()
    return (df["close"] > ma).astype(float).mul(2.0).sub(1.0).fillna(0.0)


def equal_weight_allocator(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    width = max(int(len(df.columns) or 1), 1)
    return pd.Series(1.0 / width, index=df.index, dtype=float)


class FeatureModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        out = self.func(df, self.params)
        if not isinstance(out, pd.Series):
            raise TypeError(f"Feature '{self.name}' did not return a pandas Series")
        return out.reindex(df.index)


class FeatureEngine:
    def __init__(self):
        self.modules: List[FeatureModule] = []

    def add_feature(self, module: FeatureModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for module in self.modules:
            out[module.name] = module.compute(df).fillna(0.0)
        return out


def returns_feature(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("returns_feature requires a 'close' column")
    return df["close"].pct_change().fillna(0.0)


def volatility_feature(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("volatility_feature requires a 'close' column")
    window = max(int(params.get("window", 20)), 1)
    return df["close"].pct_change().rolling(window=window, min_periods=window).std().fillna(0.0)


class TimescaleModule:
    def __init__(
        self,
        name: str,
        resample_rule: str,
        agg_func: Dict[str, str],
        timestamp_col: Optional[str] = None,
    ):
        self.name = name
        self.resample_rule = resample_rule
        self.agg_func = agg_func
        self.timestamp_col = timestamp_col

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        work = df
        if self.timestamp_col is not None:
            if self.timestamp_col not in df.columns:
                raise KeyError(f"Missing timestamp column: {self.timestamp_col}")
            work = df.copy()
            work[self.timestamp_col] = pd.to_datetime(work[self.timestamp_col], utc=True, errors="coerce")
            work = work.dropna(subset=[self.timestamp_col]).set_index(self.timestamp_col)

        if not isinstance(work.index, pd.DatetimeIndex):
            raise TypeError("TimescaleModule requires a DatetimeIndex or a valid timestamp_col")

        return work.resample(self.resample_rule).agg(self.agg_func).dropna(how="all")


class TimescaleEngine:
    def __init__(self):
        self.modules: List[TimescaleModule] = []

    def add_timescale(self, module: TimescaleModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        out: Dict[str, pd.DataFrame] = {}
        for module in self.modules:
            out[module.name] = module.apply(df)
        return out


class ExecutionModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def execute(self, df: pd.DataFrame) -> pd.Series:
        out = self.func(df, self.params)
        if not isinstance(out, pd.Series):
            raise TypeError(f"Execution module '{self.name}' did not return a pandas Series")
        return out.reindex(df.index)


class ExecutionEngine:
    def __init__(self):
        self.modules: List[ExecutionModule] = []

    def add_execution(self, module: ExecutionModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for module in self.modules:
            out[module.name] = module.execute(df).fillna(0.0)
        return out


def market_order(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    fill_ratio = float(params.get("fill_ratio", 1.0))
    fill_ratio = max(0.0, min(fill_ratio, 1.0))
    return pd.Series(fill_ratio, index=df.index, dtype=float)


def twap_order(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("twap_order requires a 'close' column")
    window = max(int(params.get("n", 5)), 1)
    return df["close"].rolling(window=window, min_periods=1).mean().bfill()


class AnalyticsModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], Any],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def compute(self, df: pd.DataFrame) -> Any:
        return self.func(df, self.params)


class AnalyticsEngine:
    def __init__(self):
        self.modules: List[AnalyticsModule] = []

    def add_analytics(self, module: AnalyticsModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for module in self.modules:
            out[module.name] = module.compute(df)
        return out


def _returns(df: pd.DataFrame) -> pd.Series:
    if "pnl" in df.columns:
        return df["pnl"].fillna(0.0)
    if "close" in df.columns:
        return df["close"].pct_change().fillna(0.0)
    raise KeyError("Expected either 'pnl' or 'close' column")


def sharpe_ratio(df: pd.DataFrame, params: Dict[str, Any]) -> float:
    annualization = float(params.get("annualization", 252.0))
    ret = _returns(df)
    return float((ret.mean() / (ret.std(ddof=0) + 1e-12)) * (annualization ** 0.5))


def max_drawdown(df: pd.DataFrame, params: Dict[str, Any]) -> float:
    ret = _returns(df)
    equity = (1.0 + ret).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return float(drawdown.min())


class RiskModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        out = self.func(df, self.params)
        if not isinstance(out, pd.Series):
            raise TypeError(f"Risk module '{self.name}' did not return a pandas Series")
        return out.reindex(df.index)


class RiskEngine:
    def __init__(self):
        self.modules: List[RiskModule] = []

    def add_risk(self, module: RiskModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for module in self.modules:
            out[module.name] = module.compute(df).fillna(0.0)
        return out


def volatility_target(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("volatility_target requires a 'close' column")
    target_vol = float(params.get("target_vol", 0.02))
    lookback = max(int(params.get("lookback", 20)), 1)
    realized_vol = df["close"].pct_change().rolling(lookback, min_periods=lookback).std().fillna(0.0)
    scale = target_vol / (realized_vol + 1e-12)
    return scale.clip(lower=0.0, upper=float(params.get("max_scale", 2.0)))


def stop_loss(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("stop_loss requires a 'close' column")
    threshold = abs(float(params.get("stop", 0.05)))
    ret = df["close"].pct_change().fillna(0.0)
    return (ret > -threshold).astype(float)


class PortfolioModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def compute(self, df: pd.DataFrame) -> pd.Series:
        out = self.func(df, self.params)
        if not isinstance(out, pd.Series):
            raise TypeError(f"Portfolio module '{self.name}' did not return a pandas Series")
        return out.reindex(df.index)


class PortfolioEngine:
    def __init__(self):
        self.modules: List[PortfolioModule] = []

    def add_portfolio(self, module: PortfolioModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        for module in self.modules:
            out[module.name] = module.compute(df).fillna(0.0)
        return out


def equal_weight_portfolio(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return pd.Series(1.0, index=df.index, dtype=float)


def volatility_weighted_portfolio(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("volatility_weighted_portfolio requires a 'close' column")
    lookback = max(int(params.get("lookback", 20)), 1)
    vol = df["close"].pct_change().rolling(lookback, min_periods=lookback).std().fillna(0.0)
    inv_vol = 1.0 / (vol + 1e-12)
    return (inv_vol / (inv_vol.mean() + 1e-12)).fillna(0.0)


class AlphaComposer:
    SUPPORTED_METHODS = {"linear", "rank", "zscore"}

    def __init__(self):
        self.weights: Dict[str, float] = {}
        self.methods: Dict[str, str] = {}

    def set_weight(self, name: str, weight: float, method: str = "linear") -> None:
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unsupported compose method '{method}'")
        self.weights[name] = float(weight)
        self.methods[name] = method

    def compose(self, signals: pd.DataFrame) -> pd.Series:
        out = pd.Series(0.0, index=signals.index, dtype=float)
        total_weight = 0.0

        for name, weight in self.weights.items():
            if name not in signals.columns:
                continue
            method = self.methods.get(name, "linear")
            col = signals[name].astype(float).fillna(0.0)

            if method == "rank":
                col = col.rank(pct=True)
            elif method == "zscore":
                col = (col - col.mean()) / (col.std(ddof=0) + 1e-12)

            out = out + weight * col
            total_weight += abs(weight)

        if total_weight > 0:
            out = out / total_weight
        return out.fillna(0.0)


class ReportModule:
    def __init__(
        self,
        name: str,
        func: Callable[[Any, Dict[str, Any]], str],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def render(self, data: Any) -> str:
        return str(self.func(data, self.params))


class ReportingEngine:
    def __init__(self):
        self.modules: List[ReportModule] = []

    def add_report(self, module: ReportModule) -> None:
        self.modules.append(module)

    def run(self, data: Any) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for module in self.modules:
            out[module.name] = module.render(data)
        return out


def json_report(data: Any, params: Dict[str, Any]) -> str:
    indent = int(params.get("indent", 2))
    return json.dumps(data, indent=indent, default=str)


def markdown_report(data: Any, params: Dict[str, Any]) -> str:
    if isinstance(data, dict):
        lines = []
        for key in sorted(data.keys()):
            lines.append(f"- **{key}**: {data[key]}")
        return "\n".join(lines)
    if isinstance(data, list):
        return "\n".join([f"- {x}" for x in data])
    return str(data)


class MonitorModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], Any],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def check(self, df: pd.DataFrame) -> Any:
        return self.func(df, self.params)


class MonitoringEngine:
    def __init__(self):
        self.modules: List[MonitorModule] = []

    def add_monitor(self, module: MonitorModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for module in self.modules:
            out[module.name] = module.check(df)
        return out


def drawdown_alert(df: pd.DataFrame, params: Dict[str, Any]) -> str:
    threshold = float(params.get("threshold", -0.10))
    if "pnl" in df.columns:
        ret = df["pnl"].fillna(0.0)
    elif "close" in df.columns:
        ret = df["close"].pct_change().fillna(0.0)
    else:
        return "SKIPPED: missing pnl/close"

    equity = (1.0 + ret).cumprod()
    dd = float((equity / equity.cummax() - 1.0).min())
    if dd < threshold:
        return f"ALERT: drawdown {dd:.2%} breached {threshold:.2%}"
    return "OK"


def latency_monitor(df: pd.DataFrame, params: Dict[str, Any]) -> str:
    if "latency_ms" not in df.columns:
        return "SKIPPED: missing latency_ms"
    p95_limit = float(params.get("p95_ms", 250.0))
    p95 = float(df["latency_ms"].dropna().quantile(0.95)) if len(df) else 0.0
    if p95 > p95_limit:
        return f"ALERT: p95 latency {p95:.1f}ms exceeded {p95_limit:.1f}ms"
    return "OK"


class ComplianceModule:
    def __init__(
        self,
        name: str,
        func: Callable[[pd.DataFrame, Dict[str, Any]], Any],
        params: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.params = params or {}

    def check(self, df: pd.DataFrame) -> Any:
        return self.func(df, self.params)


class ComplianceEngine:
    def __init__(self):
        self.modules: List[ComplianceModule] = []

    def add_compliance(self, module: ComplianceModule) -> None:
        self.modules.append(module)

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for module in self.modules:
            out[module.name] = module.check(df)
        return out


def position_limit_check(df: pd.DataFrame, params: Dict[str, Any]) -> str:
    if "position" not in df.columns:
        return "SKIPPED: missing position"
    limit = float(params.get("limit", 1_000_000.0))
    peak = float(df["position"].abs().max()) if len(df) else 0.0
    if peak > limit:
        return f"ALERT: position limit exceeded ({peak:.2f} > {limit:.2f})"
    return "OK"


def wash_sale_check(df: pd.DataFrame, params: Dict[str, Any]) -> str:
    req = {"symbol", "side", "timestamp"}
    if not req.issubset(set(df.columns)):
        return "SKIPPED: missing symbol/side/timestamp"

    cooldown_days = int(params.get("cooldown_days", 30))
    work = df[["symbol", "side", "timestamp"]].copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], utc=True, errors="coerce")
    work = work.dropna(subset=["timestamp"]).sort_values(["symbol", "timestamp"])
    if work.empty:
        return "SKIPPED: no valid timestamps"

    violations = 0
    window = pd.Timedelta(days=cooldown_days)
    for _, group in work.groupby("symbol"):
        last_sell = None
        for _, row in group.iterrows():
            side = str(row["side"]).lower()
            ts = row["timestamp"]
            if side == "sell":
                last_sell = ts
            elif side == "buy" and last_sell is not None and (ts - last_sell) <= window:
                violations += 1

    if violations > 0:
        return f"ALERT: potential wash-sale patterns detected ({violations})"
    return "OK"


class HyperCompounderFilter:
    def __init__(
        self,
        score_func: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series],
        params: Optional[Dict[str, Any]] = None,
        threshold: float = 0.95,
    ):
        self.score_func = score_func
        self.params = params or {}
        self.threshold = float(min(max(threshold, 0.0), 1.0))

    def filter(self, df: pd.DataFrame) -> List[str]:
        scores = self.score_func(df, self.params)
        if not isinstance(scores, pd.Series) or scores.empty:
            return []
        cutoff = float(scores.quantile(self.threshold))
        return [str(k) for k, v in scores.items() if float(v) >= cutoff]


def momentum_breakout_score(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    if "close" not in df.columns:
        raise KeyError("momentum_breakout_score requires a 'close' column")

    window = max(int(params.get("window", 20)), 1)

    if "symbol" in df.columns:
        def _score_group(group: pd.DataFrame) -> float:
            close = group["close"].astype(float)
            roll_min = close.rolling(window, min_periods=window).min()
            roll_max = close.rolling(window, min_periods=window).max()
            breakout = ((close - roll_min) / (roll_max - roll_min + 1e-12)).fillna(0.0)
            return float(breakout.iloc[-1]) if len(breakout) else 0.0

        return df.groupby("symbol", sort=False).apply(_score_group)

    close = df["close"].astype(float)
    roll_min = close.rolling(window, min_periods=window).min()
    roll_max = close.rolling(window, min_periods=window).max()
    breakout = ((close - roll_min) / (roll_max - roll_min + 1e-12)).fillna(0.0)
    return pd.Series({"asset": float(breakout.iloc[-1]) if len(breakout) else 0.0})