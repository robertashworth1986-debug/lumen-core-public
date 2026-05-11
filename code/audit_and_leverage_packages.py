from __future__ import annotations

import ast
import importlib
import json
import math
import os
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT = ROOT / "out" / "execution"
AUDIT_JSON = OUT / "package_leverage_audit.json"
SUMMARY_TXT = OUT / "package_leverage_summary.txt"
PREMIUM_MESH_FILE = OUT / "premium_stack_runtime.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_")


def extract_close_series(df):
    # yfinance can return either simple columns or multi-index columns.
    if df is None:
        return None
    try:
        import pandas as pd  # local import to keep startup lightweight

        if isinstance(df.columns, pd.MultiIndex):
            for key in ["Adj Close", "Close"]:
                if key in df.columns.get_level_values(0):
                    part = df[key]
                    if hasattr(part, "iloc") and len(part.columns) >= 1:
                        return part.iloc[:, 0].dropna()
            return None
        if "Adj Close" in df.columns:
            return df["Adj Close"].dropna()
        if "Close" in df.columns:
            return df["Close"].dropna()
    except Exception:
        return None
    return None


def list_installed_packages() -> dict[str, str]:
    packages: dict[str, str] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name", "")
        if not name:
            continue
        packages[name] = dist.version
    return dict(sorted(packages.items(), key=lambda kv: kv[0].lower()))


def scan_imported_modules() -> dict[str, int]:
    import_counts: dict[str, int] = {}
    py_files = [
        p
        for p in CODE.rglob("*.py")
        if "__pycache__" not in p.parts and ".venv" not in p.parts and "archive" not in p.parts
    ]
    for p in py_files:
        try:
            src = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except Exception:
            continue
        mods: set[str] = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    top = (a.name or "").split(".")[0]
                    if top:
                        mods.add(normalize(top))
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    top = (n.module or "").split(".")[0]
                    if top:
                        mods.add(normalize(top))
        for m in mods:
            import_counts[m] = import_counts.get(m, 0) + 1
    return import_counts


def package_usage(
    installed: dict[str, str],
    imports: dict[str, int],
    active_modules: set[str] | None = None,
    active_packages: set[str] | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    active_modules = active_modules or set()
    active_packages = active_packages or set()
    alias = {
        "alpaca_py": "alpaca",
        "alpaca_trade_api": "alpaca_trade_api",
        "prometheus_fastapi_instrumentator": "prometheus_fastapi_instrumentator",
        "pyportfolioopt": "pypfopt",
        "python_dotenv": "dotenv",
        "scikit_learn": "sklearn",
        "pillow": "PIL",
    }

    used = []
    unused = []
    active = []
    for pkg_name, ver in installed.items():
        n = normalize(pkg_name)
        mod_guess = alias.get(n, n)
        count = imports.get(normalize(mod_guess), 0)
        probe_hit = normalize(mod_guess) in active_modules
        mesh_pkg_hit = n in active_packages
        row = {
            "package": pkg_name,
            "version": ver,
            "module_guess": mod_guess,
            "imported_in_files": int(count),
            "active_in_probe": bool(probe_hit),
            "active_in_mesh": bool(mesh_pkg_hit),
        }
        if count > 0:
            used.append(row)
        else:
            unused.append(row)
        if count > 0 or probe_hit or mesh_pkg_hit:
            active.append(row)

    used.sort(key=lambda r: (-r["imported_in_files"], r["package"].lower()))
    unused.sort(key=lambda r: r["package"].lower())
    active.sort(key=lambda r: (-r["imported_in_files"], r["package"].lower()))
    return used, unused, active


def hard_science_actions() -> tuple[dict[str, dict], set[str]]:
    actions: dict[str, dict] = {}
    active: set[str] = set()

    modules = [
        "numpy", "scipy", "sympy", "networkx", "sklearn", "statsmodels",
        "numba", "jax", "torch", "cvxpy", "mpmath", "qiskit", "pennylane",
    ]
    loaded: dict[str, object] = {}
    for mod in modules:
        try:
            loaded[mod] = importlib.import_module(mod)
            active.add(normalize(mod))
            actions[f"module_{mod}"] = {"status": "ok"}
        except Exception as exc:
            actions[f"module_{mod}"] = {"status": "missing", "detail": str(exc)}

    # Euclidean + spectral/physics baseline
    try:
        np = loaded.get("numpy")
        if np is not None:
            rng = np.random.default_rng(42)
            a = rng.normal(size=(1024,))
            b = rng.normal(size=(1024,))
            euclid = float(np.linalg.norm(a - b))
            signal = np.sin(np.linspace(0, 10 * np.pi, 2048)) + 0.2 * rng.normal(size=(2048,))
            fft_mag = np.abs(np.fft.rfft(signal))
            dominant_hz = int(np.argmax(fft_mag))
            actions["geometry_euclidean_probe"] = {
                "status": "ok",
                "distance": round(euclid, 6),
                "dominant_fft_bin": dominant_hz,
            }
        else:
            actions["geometry_euclidean_probe"] = {"status": "skipped", "detail": "numpy unavailable"}
    except Exception as exc:
        actions["geometry_euclidean_probe"] = {"status": "error", "detail": str(exc)}

    # Non-Euclidean (Poincare disk hyperbolic distance)
    try:
        np = loaded.get("numpy")
        if np is not None:
            x = np.array([0.20, 0.15])
            y = np.array([0.45, -0.10])
            x2 = float(np.dot(x, x))
            y2 = float(np.dot(y, y))
            d2 = float(np.dot(x - y, x - y))
            arg = 1.0 + (2.0 * d2) / max((1.0 - x2) * (1.0 - y2), 1e-9)
            arg = max(arg, 1.0)
            hyperbolic = float(math.acosh(arg))
            actions["geometry_noneuclidean_probe"] = {
                "status": "ok",
                "poincare_distance": round(hyperbolic, 6),
            }
        else:
            actions["geometry_noneuclidean_probe"] = {"status": "skipped", "detail": "numpy unavailable"}
    except Exception as exc:
        actions["geometry_noneuclidean_probe"] = {"status": "error", "detail": str(exc)}

    # Symbolic physics/math derivation
    try:
        sympy = loaded.get("sympy")
        if sympy is not None:
            x = sympy.symbols("x")
            expr = sympy.integrate(sympy.sin(x) ** 2 + sympy.cos(x) ** 2, (x, 0, sympy.pi))
            actions["symbolic_math_probe"] = {"status": "ok", "integral_result": str(expr)}
        else:
            actions["symbolic_math_probe"] = {"status": "skipped", "detail": "sympy unavailable"}
    except Exception as exc:
        actions["symbolic_math_probe"] = {"status": "error", "detail": str(exc)}

    # Graph topology probe
    try:
        nx = loaded.get("networkx")
        if nx is not None:
            g = nx.barabasi_albert_graph(120, 2, seed=7)
            pr = nx.pagerank(g)
            top = sorted(pr.items(), key=lambda kv: kv[1], reverse=True)[:3]
            actions["topology_probe"] = {
                "status": "ok",
                "nodes": g.number_of_nodes(),
                "edges": g.number_of_edges(),
                "top_pagerank_nodes": top,
            }
        else:
            actions["topology_probe"] = {"status": "skipped", "detail": "networkx unavailable"}
    except Exception as exc:
        actions["topology_probe"] = {"status": "error", "detail": str(exc)}

    # Optional quantum circuit readiness
    if "qiskit" in loaded:
        try:
            from qiskit import QuantumCircuit
            qc = QuantumCircuit(1)
            qc.h(0)
            qc.z(0)
            actions["quantum_probe"] = {
                "status": "ok",
                "framework": "qiskit",
                "depth": int(qc.depth()),
                "size": int(qc.size()),
            }
        except Exception as exc:
            actions["quantum_probe"] = {"status": "error", "framework": "qiskit", "detail": str(exc)}
    elif "pennylane" in loaded:
        actions["quantum_probe"] = {"status": "ok", "framework": "pennylane", "detail": "module import ready"}
    else:
        actions["quantum_probe"] = {"status": "skipped", "detail": "qiskit/pennylane unavailable"}

    return actions, active


def leverage_actions() -> tuple[dict[str, dict], set[str]]:
    actions: dict[str, dict] = {}
    active_modules: set[str] = set()
    offline_mode = os.getenv("PACKAGE_AUDIT_OFFLINE", "0").strip() == "1"

    # 1) yfinance quick quote snapshot
    if offline_mode:
        actions["yfinance_probe"] = {"status": "skipped", "detail": "offline mode"}
    else:
        try:
            import yfinance as yf

            closes = {}
            for t in ["SPY", "QQQ", "BTC-USD", "ETH-USD"]:
                data = yf.download(tickers=t, period="5d", interval="1d", progress=False, auto_adjust=False)
                close = extract_close_series(data)
                if close is not None and len(close):
                    closes[t] = float(close.iloc[-1])
            actions["yfinance_probe"] = {"status": "ok", "latest_close": closes}
            active_modules.update({"yfinance", "pandas"})
        except Exception as exc:
            actions["yfinance_probe"] = {"status": "error", "detail": str(exc)}

    # 2) fredapi macro probe (requires key)
    try:
        from fredapi import Fred

        fred_key = os.getenv("FRED_API_KEY") or os.getenv("FRED_KEY")
        if fred_key:
            key_clean = str(fred_key).strip()
            if len(key_clean) != 32 or not key_clean.isalnum() or key_clean.lower() != key_clean:
                actions["fredapi_probe"] = {
                    "status": "skipped",
                    "detail": "FRED key present but format is invalid; expected 32-char lowercase alphanumeric",
                }
            else:
                if offline_mode:
                    actions["fredapi_probe"] = {"status": "skipped", "detail": "offline mode"}
                else:
                    fred = Fred(api_key=fred_key)
                    s = fred.get_series_latest_release("UNRATE")
                    latest = float(s.dropna().iloc[-1]) if hasattr(s, "dropna") and len(s.dropna()) else None
                    actions["fredapi_probe"] = {"status": "ok", "unrate_latest": latest}
                    active_modules.add("fredapi")
        else:
            actions["fredapi_probe"] = {"status": "skipped", "detail": "FRED_API_KEY/FRED_KEY not set"}
    except Exception as exc:
        actions["fredapi_probe"] = {"status": "error", "detail": str(exc)}

    # 3) PyPortfolioOpt optimize quick weights
    try:
        import pandas as pd
        import yfinance as yf
        from pypfopt import expected_returns, risk_models
        from pypfopt.efficient_frontier import EfficientFrontier
        if offline_mode:
            actions["pyportfolioopt_probe"] = {"status": "skipped", "detail": "offline mode"}
        else:
            px = yf.download(["SPY", "QQQ", "TLT", "GLD"], period="6mo", interval="1d", progress=False, auto_adjust=True)
            if isinstance(px.columns, pd.MultiIndex):
                px = px["Close"]
            mu = expected_returns.mean_historical_return(px)
            s = risk_models.sample_cov(px)
            ef = EfficientFrontier(mu, s)
            _ = ef.max_sharpe()
            cleaned = ef.clean_weights()
            actions["pyportfolioopt_probe"] = {"status": "ok", "weights": cleaned}
            active_modules.update({"pypfopt", "pandas", "yfinance"})
    except Exception as exc:
        actions["pyportfolioopt_probe"] = {"status": "error", "detail": str(exc)}

    # 4) quantstats quick sharpe metric on SPY returns
    try:
        import quantstats as qs
        import yfinance as yf
        if offline_mode:
            actions["quantstats_probe"] = {"status": "skipped", "detail": "offline mode"}
        else:
            px = yf.download("SPY", period="6mo", interval="1d", progress=False, auto_adjust=True)
            close = extract_close_series(px)
            ret = close.pct_change().dropna() if close is not None else []
            sharpe = float(qs.stats.sharpe(ret)) if len(ret) else 0.0
            actions["quantstats_probe"] = {"status": "ok", "spy_sharpe_6mo": sharpe}
            active_modules.update({"quantstats", "yfinance"})
    except Exception as exc:
        actions["quantstats_probe"] = {"status": "error", "detail": str(exc)}

    # 5) pyzmq local capability check
    try:
        import zmq

        actions["pyzmq_probe"] = {
            "status": "ok",
            "zmq_version": zmq.zmq_version(),
            "pyzmq_version": zmq.__version__,
        }
        active_modules.add("zmq")
    except Exception as exc:
        actions["pyzmq_probe"] = {"status": "error", "detail": str(exc)}

    # 6) openai sdk ready check
    try:
        import openai  # noqa: F401

        has_key = bool(os.getenv("OPENAI_API_KEY"))
        if offline_mode:
            actions["openai_probe"] = {"status": "ok", "detail": "sdk import ready (offline mode)"}
            active_modules.add("openai")
        elif has_key:
            actions["openai_probe"] = {"status": "ok", "detail": "sdk import ready"}
            active_modules.add("openai")
        else:
            actions["openai_probe"] = {"status": "skipped", "detail": "OPENAI_API_KEY not set"}
    except Exception as exc:
        actions["openai_probe"] = {"status": "error", "detail": str(exc)}

    sci_actions, sci_modules = hard_science_actions()
    actions["hard_science_lab"] = sci_actions
    active_modules.update(sci_modules)

    return actions, active_modules


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    installed = list_installed_packages()
    imports = scan_imported_modules()
    probes, probe_modules = leverage_actions()

    premium_mesh = {}
    mesh_modules: set[str] = set()
    mesh_packages: set[str] = set()
    if PREMIUM_MESH_FILE.exists():
        try:
            premium_mesh = json.loads(PREMIUM_MESH_FILE.read_text(encoding="utf-8"))
            for mod in premium_mesh.get("active_modules", []) or []:
                mesh_modules.add(normalize(str(mod)))
            for row in premium_mesh.get("rows", []) or []:
                if row.get("ok"):
                    mesh_packages.add(normalize(str(row.get("package", ""))))
        except Exception:
            premium_mesh = {}

    all_active_modules = set(probe_modules) | mesh_modules
    used, unused, active = package_usage(installed, imports, all_active_modules, mesh_packages)

    installed_count = len(installed)
    used_count = len(used)
    active_count = len(active)

    report = {
        "generated_utc": now_utc(),
        "workspace": str(ROOT),
        "python_files_scanned": len([p for p in CODE.rglob("*.py") if "archive" not in p.parts and ".venv" not in p.parts]),
        "installed_package_count": installed_count,
        "used_package_count": used_count,
        "active_package_count": active_count,
        "unused_package_count": len(unused),
        "static_import_utilization_pct": round((used_count / max(installed_count, 1)) * 100.0, 2),
        "active_utilization_pct": round((active_count / max(installed_count, 1)) * 100.0, 2),
        "top_used_packages": used[:60],
        "top_active_packages": active[:120],
        "underused_packages": unused[:120],
        "active_probe_modules": sorted(probe_modules),
        "active_mesh_modules": sorted(mesh_modules),
        "active_mesh_packages": sorted(mesh_packages),
        "premium_mesh": premium_mesh if isinstance(premium_mesh, dict) else {},
        "leverage_probes": probes,
    }

    AUDIT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "LumaTrader Premium Package Leverage Audit",
        f"Generated: {report['generated_utc']}",
        f"Installed packages: {report['installed_package_count']}",
        f"Detected in imports: {report['used_package_count']}",
        f"Active via imports+probes: {report['active_package_count']} ({report['active_utilization_pct']}%)",
        f"Not detected in imports: {report['unused_package_count']}",
        "",
        "Leverage probe status:",
    ]
    for name, result in probes.items():
        lines.append(f"- {name}: {result.get('status', 'unknown')}")
    lines.append("")
    lines.append(f"JSON report: {AUDIT_JSON}")
    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")

    print(f"WROTE_JSON={AUDIT_JSON}")
    print(f"WROTE_SUMMARY={SUMMARY_TXT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
