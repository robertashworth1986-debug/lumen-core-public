import importlib.util
import pathlib
import sys

_THIS_DIR = pathlib.Path(__file__).resolve().parent
_SUITE_PATH = _THIS_DIR / "institutional_harmonic_suite.py"

if not _SUITE_PATH.exists():
    raise FileNotFoundError(f"Canonical suite file missing: {_SUITE_PATH}")

_spec = importlib.util.spec_from_file_location("institutional_harmonic_suite_canonical", str(_SUITE_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

def _pick(*names, default=None):
    for n in names:
        if hasattr(_mod, n):
            return getattr(_mod, n)
    return default

# shared constants / registries
FLOWS = _pick("FLOWS", "FLOWFORMS", default={})
FLOWFORMS = FLOWS
STRATEGIES = _pick("STRATEGIES", "STRATS", default={})
STRATS = STRATEGIES

# shared helpers
sharpe               = _pick("sharpe")
max_drawdown         = _pick("max_drawdown", "max_dd")
cagr                 = _pick("cagr")
calmar               = _pick("calmar")
win_rate             = _pick("win_rate")
expectancy           = _pick("expectancy")
annual_vol           = _pick("annual_vol")
stability_score      = _pick("stability_score", "stability")
institutional_score  = _pick("institutional_score", "metric_score")
get_price_series     = _pick("get_price_series")
evaluate_combo       = _pick("evaluate_combo")
evaluate             = _pick("evaluate")
run_engine           = _pick("run_engine")

def available_symbols():
    return sorted([k for k in dir(_mod) if not k.startswith("_")])

def sanity():
    return {
        "suite_path": str(_SUITE_PATH),
        "flow_count": len(FLOWS) if isinstance(FLOWS, dict) else 0,
        "strategy_count": len(STRATEGIES) if isinstance(STRATEGIES, dict) else 0,
        "has_get_price_series": callable(get_price_series),
        "has_evaluate_combo": callable(evaluate_combo),
        "has_run_engine": callable(run_engine),
    }