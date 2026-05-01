import os, math, json
import numpy as np
import pandas as pd

SCAN_ROOT = r"C:\LumaTrader"
OUT_DIR   = r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\out"
os.makedirs(OUT_DIR, exist_ok=True)

MIN_LEN = 750

BANNED_PATH_PARTS = [
    "\\env311\\",
    "\\venv\\",
    "\\site-packages\\",
    "\\numpy\\",
    "\\Lib\\",
    "\\Scripts\\",
    "\\INSTITUTIONAL_STACK\\",
    "\\INSTITUTIONAL_STACK_V2\\",
    "\\__pycache__\\"
]

PRICE_HINTS = ["close","adj_close","adj close","price","last","settle","value","px_last"]

def safe_ret(series):
    r = pd.Series(series, dtype=float).pct_change()
    r = r.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return r

def sharpe(r, periods=252):
    r = pd.Series(r, dtype=float).dropna()
    if len(r) < 5:
        return np.nan
    sd = float(r.std(ddof=1))
    if sd == 0 or not np.isfinite(sd):
        return np.nan
    return float((r.mean() / sd) * np.sqrt(periods))

def sortino(r, periods=252):
    r = pd.Series(r, dtype=float).dropna()
    if len(r) < 5:
        return np.nan
    downside = r[r < 0]
    if len(downside) < 2:
        return np.nan
    dd = float(downside.std(ddof=1))
    if dd == 0 or not np.isfinite(dd):
        return np.nan
    return float((r.mean() / dd) * np.sqrt(periods))

def max_dd(eq):
    eq = pd.Series(eq, dtype=float).dropna()
    if len(eq) < 2:
        return np.nan
    peak = eq.cummax()
    dd = eq / peak - 1.0
    return float(dd.min())

def cagr(eq, periods=252):
    eq = pd.Series(eq, dtype=float).dropna()
    if len(eq) < 2:
        return np.nan
    if eq.iloc[0] <= 0 or eq.iloc[-1] <= 0:
        return np.nan
    years = len(eq) / periods
    if years <= 0:
        return np.nan
    return float((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1.0)

def calmar(eq, periods=252):
    cg = cagr(eq, periods)
    dd = abs(max_dd(eq))
    if not np.isfinite(cg) or not np.isfinite(dd) or dd == 0:
        return np.nan
    return float(cg / dd)

def expectancy(r):
    r = pd.Series(r, dtype=float).dropna()
    r = r[r != 0]
    if len(r) == 0:
        return np.nan
    w = r[r > 0]
    l = r[r < 0]
    pw = len(w) / len(r)
    pl = len(l) / len(r)
    aw = float(w.mean()) if len(w) else 0.0
    al = float(l.mean()) if len(l) else 0.0
    return float((pw * aw) + (pl * al))

def win_rate(r):
    r = pd.Series(r, dtype=float).dropna()
    r = r[r != 0]
    if len(r) == 0:
        return np.nan
    return float((r > 0).mean())

def turnover(sig):
    s = pd.Series(sig, dtype=float).fillna(0.0)
    return float(s.diff().abs().fillna(0.0).sum())

def profit_factor(r):
    r = pd.Series(r, dtype=float).dropna()
    pos = float(r[r > 0].sum()) if len(r[r > 0]) else 0.0
    neg = float(abs(r[r < 0].sum())) if len(r[r < 0]) else 0.0
    if neg == 0:
        return np.nan
    return float(pos / neg)

def split_series(px, frac=0.7):
    n = len(px)
    cut = int(n * frac)
    return px.iloc[:cut].copy(), px.iloc[cut:].copy()

def zscore(x, win):
    mu = x.rolling(win, min_periods=win).mean()
    sd = x.rolling(win, min_periods=win).std(ddof=0)
    z = (x - mu) / sd.replace(0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan).fillna(0.0)

def harmonic_wave(n, freq=8.0, phase=0.0, amp=1.0):
    t = np.linspace(0.0, 2.0 * np.pi, n)
    return pd.Series(amp * np.sin(freq * t + phase), dtype=float)

def flowform_library(n):
    t = np.linspace(0.0, 2.0 * np.pi, n)

    return {
        "sine_primary": pd.Series(np.sin(5*t), dtype=float),
        "sine_secondary": pd.Series(np.sin(8*t + np.pi/4), dtype=float),
        "helix_dual": pd.Series(np.sin(5*t) + 0.5*np.cos(11*t), dtype=float),
        "golden_wave": pd.Series(np.sin(1.618*6*t) + 0.35*np.sin(6*t), dtype=float),
        "spiral_phase": pd.Series(np.sin(7*t + np.linspace(0, np.pi, n)), dtype=float),
        "braid_wave": pd.Series(np.sin(4*t) * np.cos(9*t), dtype=float),
        "vortex_shift": pd.Series(np.sin(6*t) + np.cos(13*t + np.pi/6), dtype=float),
    }

def load_csv_files(root):
    found = []
    for base, _, files in os.walk(root):
        lowbase = base.lower()
        if any(part.lower().strip("\\") in lowbase for part in [x.strip("\\").lower() for x in BANNED_PATH_PARTS]):
            continue
        for f in files:
            if not f.lower().endswith(".csv"):
                continue
            p = os.path.join(base, f)
            pl = p.lower()
            if any(b.lower() in pl for b in BANNED_PATH_PARTS):
                continue
            found.append(p)
    return found

def extract_price_series(path):
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    cols = {c.lower(): c for c in df.columns}
    picked = None
    for c in PRICE_HINTS:
        if c in cols:
            picked = cols[c]
            break

    if picked is None:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not numeric_cols:
            return None
        picked = numeric_cols[-1]

    s = pd.to_numeric(df[picked], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < MIN_LEN:
        return None
    if float(s.std()) == 0:
        return None

    return pd.Series(s.astype(float).reset_index(drop=True))

def strategy_signals(px, flow):
    px = pd.Series(px, dtype=float).reset_index(drop=True)
    flow = pd.Series(flow, dtype=float).reset_index(drop=True)

    # 🔒 HARD ALIGNMENT (this is the fix)
    n = min(len(px), len(flow))
    px = px.iloc[:n]
    flow = flow.iloc[:n]

    ret = safe_ret(px)

    ema12 = px.ewm(span=12, adjust=False).mean()
    ema24 = px.ewm(span=24, adjust=False).mean()
    ema48 = px.ewm(span=48, adjust=False).mean()

    z20 = zscore(px, 20)
    vol20 = ret.rolling(20, min_periods=20).std(ddof=0).fillna(0.0)

    trend_core = np.sign(ema12 - ema48).fillna(0.0)
    trend_mid  = np.sign(ema24 - ema48).fillna(0.0)

    mr_core = pd.Series(
        np.where(z20 > 1.25, -1.0,
        np.where(z20 < -1.25, 1.0, 0.0)),
        dtype=float
    )

    breakout = pd.Series(
        np.where(ret > 1.25*vol20, 1.0,
        np.where(ret < -1.25*vol20, -1.0, 0.0)),
        dtype=float
    )

    regime = pd.Series(
        np.where(
            vol20 > vol20.rolling(60, min_periods=20).median().fillna(0.0),
            1.0, 0.0
        ),
        dtype=float
    )

    flow_sign = np.sign(flow).fillna(0.0)

    out = {}

    out["trend"] = np.sign(0.80*trend_core + 0.20*flow_sign)

    out["mean_revert"] = np.sign(0.80*mr_core + 0.20*flow_sign)

    out["breakout"] = np.sign(0.75*breakout + 0.25*trend_mid)

    # 🔥 FIXED REGIME SWITCH (aligned inputs)
    out["regime_switch"] = pd.Series(
        np.where(
            regime > 0.5,
            np.sign(0.85*mr_core + 0.15*flow_sign),
            np.sign(0.85*trend_core + 0.15*flow_sign)
        ),
        dtype=float
    )

    blend_score = (
        0.30*trend_core +
        0.20*trend_mid +
        0.20*mr_core +
        0.20*breakout +
        0.10*flow_sign
    )

    out["blend"] = np.sign(blend_score)

    return {
        k: pd.Series(v, dtype=float).shift(1).fillna(0.0)
        for k, v in out.items()
    }

def admissible(metrics_train, metrics_test):
    if not np.isfinite(metrics_train["sharpe"]) or not np.isfinite(metrics_test["sharpe"]):
        return False
    if metrics_train["sharpe"] < 0.75:
        return False
    if metrics_test["sharpe"] < 0.50:
        return False
    if not np.isfinite(metrics_test["max_dd"]) or metrics_test["max_dd"] < -0.35:
        return False
    if not np.isfinite(metrics_test["vs_baseline"]) or metrics_test["vs_baseline"] <= 0:
        return False
    if not np.isfinite(metrics_test["profit_factor"]) or metrics_test["profit_factor"] <= 1.02:
        return False
    return True

def institutional_score(m):
    vals = [
        6.0 * (m["sharpe"] if np.isfinite(m["sharpe"]) else -99),
        3.5 * (m["sortino"] if np.isfinite(m["sortino"]) else -99),
        4.0 * (m["calmar"] if np.isfinite(m["calmar"]) else -99),
        7.0 * (m["vs_baseline"] if np.isfinite(m["vs_baseline"]) else -99),
        3.0 * (m["expectancy"] if np.isfinite(m["expectancy"]) else -99),
        2.0 * (m["profit_factor"] if np.isfinite(m["profit_factor"]) else -99),
        1.5 * (m["win_rate"] if np.isfinite(m["win_rate"]) else -99),
        -8.0 * abs(m["max_dd"]) if np.isfinite(m["max_dd"]) else -99,
        -0.0005 * m["turnover"] if np.isfinite(m["turnover"]) else -99,
    ]
    return float(np.nansum(vals))

def main():
    files = load_csv_files(SCAN_ROOT)
    results = []

    for f in files:
        px = extract_price_series(f)
        if px is None:
            continue

        train_px, test_px = split_series(px, 0.7)
        if len(train_px) < MIN_LEN*0.5 or len(test_px) < MIN_LEN*0.2:
            continue

        train_flows = flowform_library(len(train_px))
        test_flows  = flowform_library(len(test_px))

        for flow_name in train_flows.keys():
            train_sigs = strategy_signals(train_px, train_flows[flow_name])
            test_sigs  = strategy_signals(test_px,  test_flows[flow_name])

            for strat_name in train_sigs.keys():
                mt = evaluate_strategy(train_px, train_sigs[strat_name])
                mv = evaluate_strategy(test_px, test_sigs[strat_name])

                if not admissible(mt, mv):
                    continue

                results.append({
                    "file": f,
                    "flowform": flow_name,
                    "strategy": strat_name,

                    "train_sharpe": mt["sharpe"],
                    "test_sharpe": mv["sharpe"],

                    "train_sortino": mt["sortino"],
                    "test_sortino": mv["sortino"],

                    "train_max_dd": mt["max_dd"],
                    "test_max_dd": mv["max_dd"],

                    "train_cagr": mt["cagr"],
                    "test_cagr": mv["cagr"],

                    "train_calmar": mt["calmar"],
                    "test_calmar": mv["calmar"],

                    "train_expectancy": mt["expectancy"],
                    "test_expectancy": mv["expectancy"],

                    "train_win_rate": mt["win_rate"],
                    "test_win_rate": mv["win_rate"],

                    "train_profit_factor": mt["profit_factor"],
                    "test_profit_factor": mv["profit_factor"],

                    "train_turnover": mt["turnover"],
                    "test_turnover": mv["turnover"],

                    "train_final": mt["final"],
                    "test_final": mv["final"],

                    "train_baseline_final": mt["baseline_final"],
                    "test_baseline_final": mv["baseline_final"],

                    "train_vs_baseline": mt["vs_baseline"],
                    "test_vs_baseline": mv["vs_baseline"],

                    "institutional_score": institutional_score(mv)
                })

    if len(results) == 0:
        print("NO VALID INSTITUTIONAL HARMONIC WINNERS")
        return

    df = pd.DataFrame(results).sort_values(
        ["institutional_score", "test_sharpe", "test_calmar", "test_vs_baseline"],
        ascending=False
    ).reset_index(drop=True)

    df.to_csv(os.path.join(OUT_DIR, "institutional_harmonic_leaderboard.csv"), index=False)

    champs = df.groupby(["flowform","strategy"], as_index=False).first()
    champs.to_csv(os.path.join(OUT_DIR, "institutional_flow_strategy_champions.csv"), index=False)

    top10 = df.head(10).copy()
    top10.to_csv(os.path.join(OUT_DIR, "institutional_top10.csv"), index=False)

    summary = {
        "files_scanned": int(len(files)),
        "validated_winners": int(len(df)),
        "top_file": str(top10.iloc[0]["file"]),
        "top_flowform": str(top10.iloc[0]["flowform"]),
        "top_strategy": str(top10.iloc[0]["strategy"]),
        "top_test_sharpe": float(top10.iloc[0]["test_sharpe"]),
        "top_test_calmar": float(top10.iloc[0]["test_calmar"]),
        "top_test_max_dd": float(top10.iloc[0]["test_max_dd"]),
        "top_test_vs_baseline": float(top10.iloc[0]["test_vs_baseline"]),
        "top_institutional_score": float(top10.iloc[0]["institutional_score"])
    }

    with open(os.path.join(OUT_DIR, "institutional_summary.json"), "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    print("=== INSTITUTIONAL HARMONIC SUITE COMPLETE ===")
    print(df.head(20).to_string(index=False))
    print("")
    print("Saved:")
    print(os.path.join(OUT_DIR, "institutional_harmonic_leaderboard.csv"))
    print(os.path.join(OUT_DIR, "institutional_flow_strategy_champions.csv"))
    print(os.path.join(OUT_DIR, "institutional_top10.csv"))
    print(os.path.join(OUT_DIR, "institutional_summary.json"))

if __name__ == "__main__":
    main()
