import ast
import json
import os
import re
from pathlib import Path

import pandas as pd

try:
    import requests
except Exception:
    requests = None


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


def hydrate_env_from_files() -> None:
    paths = [
        Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\luma_live_keys.env"),
        Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\luma_market_keys.env"),
        Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\config\live_breadth_keys.env"),
    ]
    external = os.environ.get("LUMA_LIVE_KEYS_FILE") or os.environ.get("LUMA_MARKET_KEYS_FILE")
    if external:
        paths.append(Path(external))

    for path in paths:
        for key, value in parse_env_file(path).items():
            if value and not os.environ.get(key):
                os.environ[key] = value


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT = ROOT / "out"
CFG = ROOT / "config"

OUT.mkdir(parents=True, exist_ok=True)
CFG.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = CFG / "live_sources.json"
STATUS_PATH = OUT / "live_source_status.json"
REGISTRY_PATH = OUT / "full_beast_registry.json"
SUMMARY_PATH = OUT / "live_registry_summary.json"

DEFAULT_CFG = {
    "eia": {
        "enabled": True,
        "api_key_env": "EIA_API_KEY",
        "route": "electricity/rto/region-data/data",
        "frequency": "hourly",
        "data_fields": ["value"],
        "facets": {
            "type": ["D"],
            "respondent": ["MISO", "PJM", "ERCOT", "CISO", "NYIS", "ISNE"],
        },
        "sort": [{"column": "period", "direction": "desc"}],
        "length": 240,
    },
    "twelve_data": {"enabled": False, "api_key_env": "TWELVE_DATA_API_KEY"},
    "polygon": {"enabled": False, "api_key_env": "POLYGON_API_KEY"},
    "finnhub": {"enabled": False, "api_key_env": "FINNHUB_API_KEY"},
    "alpaca": {"enabled": False, "api_key_env": "ALPACA_API_KEY"},
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CFG, indent=2), encoding="utf-8")
        return DEFAULT_CFG.copy()
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


hydrate_env_from_files()
cfg = load_config()


def scan_dict_keys(py_text: str, dict_name: str):
    keys = set()
    try:
        tree = ast.parse(py_text)
    except Exception:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id != dict_name:
                continue

            if isinstance(node.value, ast.Dict):
                for k in node.value.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        keys.add(k.value)
                    elif isinstance(k, ast.Str):
                        keys.add(k.s)

    return sorted(keys)


def scan_function_names(py_text: str, prefix: str):
    names = re.findall(rf"def\s+({prefix}[A-Za-z0-9_]+)\s*\(", py_text)
    clean = []
    for name in names:
        suffix = name[len(prefix):]
        if suffix:
            clean.append(suffix)
    return sorted(set(clean))


def collect_registry():
    flowforms = set()
    algos = set()
    strategies = set()
    profiles = set()

    py_files = list(CODE.rglob("*.py"))
    for path in py_files:
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for k in scan_dict_keys(txt, "FLOWFORMS"):
            flowforms.add(k)
        for k in scan_dict_keys(txt, "ALGOS"):
            algos.add(k)
        for k in scan_dict_keys(txt, "ALGORITHMS"):
            algos.add(k)
        for k in scan_dict_keys(txt, "STRATEGIES"):
            strategies.add(k)
        for k in scan_dict_keys(txt, "METRIC_PROFILES"):
            profiles.add(k)
        for k in scan_dict_keys(txt, "PROFILES"):
            profiles.add(k)

        for k in scan_function_names(txt, "ff_"):
            flowforms.add(k)
        for k in scan_function_names(txt, "algo_"):
            algos.add(k)
        for k in scan_function_names(txt, "strat_"):
            strategies.add(k)
        for k in scan_function_names(txt, "profile_"):
            profiles.add(k)
        for k in scan_function_names(txt, "metric_profile_"):
            profiles.add(k)

    registry = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "flowforms": sorted(flowforms),
        "algos": sorted(algos),
        "strategies": sorted(strategies),
        "metric_profiles": sorted(profiles),
        "flowforms_count": len(flowforms),
        "algos_count": len(algos),
        "strategies_count": len(strategies),
        "metric_profiles_count": len(profiles),
        "files_scanned": len(py_files),
    }

    REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


def pull_eia():
    status = {
        "enabled": bool(cfg.get("eia", {}).get("enabled", False)),
        "api_key_present": False,
        "rows_written": 0,
        "files_written": [],
        "error": "",
    }

    if not status["enabled"]:
        return status

    if requests is None:
        status["error"] = "requests_not_installed"
        return status

    eia_cfg = cfg["eia"]
    api_key = os.environ.get(eia_cfg.get("api_key_env", "EIA_API_KEY"), "").strip()
    status["api_key_present"] = bool(api_key)
    if not api_key:
        status["error"] = "missing_eia_api_key_env"
        return status

    url = f"https://api.eia.gov/v2/{eia_cfg['route']}"
    params = {
        "api_key": api_key,
        "frequency": eia_cfg.get("frequency", "hourly"),
        "length": int(eia_cfg.get("length", 240)),
    }

    data_fields = eia_cfg.get("data_fields", ["value"])
    for i, field_name in enumerate(data_fields):
        params[f"data[{i}]"] = field_name

    facets = eia_cfg.get("facets", {})
    for facet_name, values in facets.items():
        for i, value in enumerate(values):
            params[f"facets[{facet_name}][{i}]"] = value

    sorters = eia_cfg.get("sort", [])
    for i, sorter in enumerate(sorters):
        params[f"sort[{i}][column]"] = sorter.get("column", "period")
        params[f"sort[{i}][direction]"] = sorter.get("direction", "desc")

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        obj = r.json()
    except Exception as e:
        status["error"] = f"eia_request_failed: {e}"
        return status

    data = (((obj or {}).get("response") or {}).get("data")) or []
    if not data:
        status["error"] = "eia_no_data_returned"
        return status

    df = pd.DataFrame(data)
    if df.empty:
        status["error"] = "eia_dataframe_empty"
        return status

    if "respondent" in df.columns:
        for respondent, group in df.groupby("respondent"):
            safe = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(respondent))
            out_path = OUT / f"live_eia_{safe}.csv"
            group.to_csv(out_path, index=False)
            status["files_written"].append(str(out_path))
            status["rows_written"] += int(len(group))
    else:
        out_path = OUT / "live_eia_generic.csv"
        df.to_csv(out_path, index=False)
        status["files_written"].append(str(out_path))
        status["rows_written"] = int(len(df))

    return status


def build_status():
    source_status = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "sources": {},
    }

    source_status["sources"]["eia"] = pull_eia()

    for name in ["twelve_data", "polygon", "finnhub", "alpaca"]:
        sc = cfg.get(name, {})
        source_status["sources"][name] = {
            "enabled": bool(sc.get("enabled", False)),
            "api_key_present": bool(os.environ.get(sc.get("api_key_env", f"{name.upper()}_API_KEY"), "").strip()),
            "rows_written": 0,
            "files_written": [],
            "error": "" if not sc.get("enabled", False) else "not_wired_yet",
        }

    STATUS_PATH.write_text(json.dumps(source_status, indent=2), encoding="utf-8")
    return source_status


def main():
    registry = collect_registry()
    status = build_status()

    summary = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "registry_counts": {
            "flowforms": registry.get("flowforms_count", 0),
            "algos": registry.get("algos_count", 0),
            "strategies": registry.get("strategies_count", 0),
            "metric_profiles": registry.get("metric_profiles_count", 0),
        },
        "live_sources": status,
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("=== LIVE SOURCE + REGISTRY PATCH COMPLETE ===")
    print("Registry:", REGISTRY_PATH)
    print("Status:", STATUS_PATH)
    print("Summary:", SUMMARY_PATH)
    print("Flowforms:", registry.get("flowforms_count", 0))
    print("Algos:", registry.get("algos_count", 0))
    print("Strategies:", registry.get("strategies_count", 0))
    print("Profiles:", registry.get("metric_profiles_count", 0))


if __name__ == "__main__":
    main()
