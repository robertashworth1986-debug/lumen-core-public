from __future__ import annotations

import argparse
import importlib
import json
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution" / "premium_stack_runtime.json"

ALIASES = {
    "pyportfolioopt": ["pypfopt"],
    "python-dotenv": ["dotenv"],
    "scikit-learn": ["sklearn"],
    "prometheus-fastapi-instrumentator": ["prometheus_fastapi_instrumentator"],
    "pillow": ["PIL"],
    "alpaca-py": ["alpaca"],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_")


def _top_level_modules(dist: metadata.Distribution) -> list[str]:
    mods: list[str] = []
    try:
        text = dist.read_text("top_level.txt")
        if text:
            mods.extend([m.strip() for m in text.splitlines() if m.strip()])
    except Exception:
        pass
    return mods


def _candidate_modules(pkg_name: str, dist: metadata.Distribution) -> list[str]:
    candidates: list[str] = []
    candidates.extend(ALIASES.get(pkg_name.lower(), []))
    candidates.extend(_top_level_modules(dist))
    candidates.append(normalize(pkg_name))

    # dedupe preserve order
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        c = c.strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _try_import(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _high_level_probe() -> dict[str, Any]:
    probe: dict[str, Any] = {"status": "ok", "checks": {}}

    checks = [
        "numpy", "pandas", "scipy", "sklearn", "xgboost", "lightgbm", "shap",
        "pypfopt", "quantstats", "sympy", "networkx", "cvxpy", "statsmodels",
        "polars", "duckdb", "plotly", "matplotlib", "fastapi", "orjson", "ccxt",
        "yfinance", "fredapi", "openai", "optuna", "numba",
    ]

    ok = 0
    for mod in checks:
        succ, detail = _try_import(mod)
        probe["checks"][mod] = {"ok": succ, "detail": detail if not succ else "ok"}
        if succ:
            ok += 1

    probe["ok_count"] = ok
    probe["total_count"] = len(checks)
    probe["coverage_pct"] = round(ok / max(len(checks), 1) * 100.0, 2)
    return probe


def run_once(max_packages: int = 0) -> dict[str, Any]:
    dists = sorted(list(metadata.distributions()), key=lambda d: (d.metadata.get("Name", "").lower()))
    if max_packages > 0:
        dists = dists[:max_packages]

    rows: list[dict[str, Any]] = []
    active_modules: set[str] = set()
    ok_count = 0

    for dist in dists:
        pkg_name = (dist.metadata.get("Name", "") or "").strip()
        if not pkg_name:
            continue

        started = time.time()
        picked_module = ""
        success = False
        err = ""

        for candidate in _candidate_modules(pkg_name, dist):
            success, detail = _try_import(candidate)
            picked_module = candidate
            if success:
                active_modules.add(candidate)
                ok_count += 1
                break
            err = detail

        rows.append({
            "package": pkg_name,
            "version": dist.version,
            "module": picked_module,
            "ok": success,
            "error": "" if success else err,
            "duration_ms": round((time.time() - started) * 1000.0, 2),
        })

    fail_count = len(rows) - ok_count
    high_level = _high_level_probe()

    payload = {
        "generated_utc": now_utc(),
        "schema": "premium_package_mesh_v1",
        "installed_package_count": len(rows),
        "import_ok_count": ok_count,
        "import_fail_count": fail_count,
        "import_ok_pct": round(ok_count / max(len(rows), 1) * 100.0, 2),
        "active_modules": sorted(active_modules),
        "high_level_probe": high_level,
        "rows": rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Premium package mesh runner (live import coverage)")
    p.add_argument("--loop", action="store_true")
    p.add_argument("--interval", type=int, default=300)
    p.add_argument("--max-packages", type=int, default=0)
    args = p.parse_args(argv)

    if args.loop:
        while True:
            out = run_once(max_packages=args.max_packages)
            print(json.dumps({
                "ts": out["generated_utc"],
                "installed": out["installed_package_count"],
                "import_ok": out["import_ok_count"],
                "import_ok_pct": out["import_ok_pct"],
                "high_level_probe_pct": out["high_level_probe"]["coverage_pct"],
            }, indent=2))
            time.sleep(max(args.interval, 30))
    else:
        out = run_once(max_packages=args.max_packages)
        print(json.dumps({
            "ts": out["generated_utc"],
            "installed": out["installed_package_count"],
            "import_ok": out["import_ok_count"],
            "import_ok_pct": out["import_ok_pct"],
            "high_level_probe_pct": out["high_level_probe"]["coverage_pct"],
            "output": str(OUT),
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
