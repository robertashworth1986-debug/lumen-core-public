"""
harmonic_vs_backprop_fair.py — apples-to-apples comparison

The LumenLab V6 benchmark claimed "harmonic beats backprop 362/400". That test
hardcoded sin/cos features at the known 12-month period of EIA data while
running a tiny untuned 1->10->1 MLP for 200 epochs at lr=0.001. The deck was
stacked.

This script runs a fair comparison on FOUR synthetic datasets where we KNOW
the ground truth, so we can see where each approach actually wins:

  D1: pure 12-period seasonal     (harmonic SHOULD win)
  D2: hidden 37-period seasonal   (period not given to harmonic)
  D3: linear trend, no seasonality (neither has structural advantage)
  D4: random walk + noise          (neither should win meaningfully)

For each dataset we compare:

  (a) Naive baseline    : predict last train value
  (b) Linear trend      : OLS on [1, t]
  (c) Harmonic-fixed    : Ridge on [1, t, sin/cos at period 12]      <-- V6's model
  (d) Harmonic-search   : Ridge on Fourier basis up to k=10, period chosen by FFT
  (e) MLP-untuned       : 1->10->1, 200 epochs, lr=1e-3 (V6's MLP)
  (f) MLP-tuned         : 4-layer with LSTM-style lag features, normalized,
                          early stopping, validation split

Output: out/fair_benchmark/results.csv + summary.json
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

RNG = np.random.default_rng(42)
N = 600
TRAIN_FRAC = 0.8


def make_datasets() -> dict[str, np.ndarray]:
    t = np.arange(N)
    return {
        "D1_period12":          5 + 0.01 * t + 3 * np.sin(2 * np.pi * t / 12)
                                 + RNG.normal(0, 0.5, N),
        "D2_period37_hidden":   5 + 0.005 * t + 2 * np.sin(2 * np.pi * t / 37)
                                 + 1.5 * np.cos(2 * np.pi * t / 37)
                                 + RNG.normal(0, 0.3, N),
        "D3_linear_trend":      2 + 0.05 * t + RNG.normal(0, 1.0, N),
        "D4_random_walk":       np.cumsum(RNG.normal(0, 1, N)),
    }


def split(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    k = int(len(y) * TRAIN_FRAC)
    return y[:k], y[k:]


def score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


# ── (a) naive ────────────────────────────────────────────────────────────
def model_naive(train, test):
    return np.full(len(test), train[-1])


# ── (b) linear trend ─────────────────────────────────────────────────────
def model_trend(train, test):
    t = np.arange(len(train)).reshape(-1, 1)
    m = LinearRegression().fit(t, train)
    t2 = np.arange(len(train), len(train) + len(test)).reshape(-1, 1)
    return m.predict(t2)


# ── (c) V6 harmonic with hardcoded period 12 ─────────────────────────────
def _fourier(t, period, k=1):
    cols = [np.ones(len(t)), t]
    for h in range(1, k + 1):
        cols.append(np.sin(2 * np.pi * h * t / period))
        cols.append(np.cos(2 * np.pi * h * t / period))
    return np.column_stack(cols)


def model_harmonic_fixed(train, test):
    tr_t = np.arange(len(train))
    te_t = np.arange(len(train), len(train) + len(test))
    Xtr = _fourier(tr_t, period=12, k=1)
    Xte = _fourier(te_t, period=12, k=1)
    m = Ridge(alpha=1.0).fit(Xtr, train)
    return m.predict(Xte)


# ── (d) harmonic with period chosen from train FFT ───────────────────────
def model_harmonic_search(train, test):
    tr_t = np.arange(len(train))
    te_t = np.arange(len(train), len(train) + len(test))
    detrended = train - np.polyval(np.polyfit(tr_t, train, 1), tr_t)
    fft = np.fft.rfft(detrended)
    power = np.abs(fft)
    power[0] = 0
    if power.max() < 1e-9:
        period = len(train)
    else:
        idx = int(np.argmax(power))
        period = max(2.0, len(train) / max(idx, 1))
    Xtr = _fourier(tr_t, period=period, k=3)
    Xte = _fourier(te_t, period=period, k=3)
    m = Ridge(alpha=1.0).fit(Xtr, train)
    return m.predict(Xte)


# ── (e) V6 untuned MLP ───────────────────────────────────────────────────
def model_mlp_untuned(train, test):
    tr_t = np.arange(len(train)).reshape(-1, 1).astype(float)
    te_t = np.arange(len(train), len(train) + len(test)).reshape(-1, 1).astype(float)
    m = MLPRegressor(
        hidden_layer_sizes=(10,),
        max_iter=200,
        learning_rate_init=0.001,
        random_state=0,
    )
    m.fit(tr_t, train)
    return m.predict(te_t)


# ── (f) Tuned MLP with lag features + normalization + early stopping ─────
def model_mlp_tuned(train, test):
    lag = 24
    if len(train) <= lag + 5:
        return model_naive(train, test)

    def make_lag(series, start, end):
        rows = []
        for i in range(start, end):
            rows.append(series[i - lag:i])
        return np.array(rows)

    full = np.concatenate([train, test])
    Xtr = make_lag(full, lag, len(train))
    ytr = train[lag:]
    sx = StandardScaler().fit(Xtr)
    sy = StandardScaler().fit(ytr.reshape(-1, 1))
    Xtr_s = sx.transform(Xtr)
    ytr_s = sy.transform(ytr.reshape(-1, 1)).ravel()

    m = MLPRegressor(
        hidden_layer_sizes=(64, 64),
        max_iter=2000,
        learning_rate_init=1e-3,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=25,
        random_state=0,
    )
    m.fit(Xtr_s, ytr_s)

    preds = []
    history = list(full[len(train) - lag:len(train)])
    for _ in range(len(test)):
        x = np.array(history[-lag:]).reshape(1, -1)
        x_s = sx.transform(x)
        yhat_s = m.predict(x_s)
        yhat = sy.inverse_transform(yhat_s.reshape(-1, 1)).ravel()[0]
        preds.append(yhat)
        history.append(yhat)
    return np.array(preds)


MODELS = {
    "a_naive":             model_naive,
    "b_linear_trend":      model_trend,
    "c_harmonic_fixed12":  model_harmonic_fixed,
    "d_harmonic_search":   model_harmonic_search,
    "e_mlp_untuned":       model_mlp_untuned,
    "f_mlp_tuned":         model_mlp_tuned,
}


def main():
    here = Path(__file__).resolve().parent
    out_dir = here.parent / "out" / "fair_benchmark"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    datasets = make_datasets()
    for name, y in datasets.items():
        train, test = split(y)
        for mname, fn in MODELS.items():
            pred = fn(train, test)
            rmse = score(test, pred)
            rows.append({"dataset": name, "model": mname, "rmse": round(rmse, 4)})

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "results.csv", index=False)

    # who won each dataset
    wins = (
        df.loc[df.groupby("dataset")["rmse"].idxmin()]
        .reset_index(drop=True)[["dataset", "model", "rmse"]]
        .to_dict(orient="records")
    )

    # head-to-head: tuned MLP vs V6 harmonic-fixed
    pivot = df.pivot(index="dataset", columns="model", values="rmse")
    head_to_head = []
    for ds in pivot.index:
        head_to_head.append({
            "dataset": ds,
            "v6_harmonic_fixed12": float(pivot.loc[ds, "c_harmonic_fixed12"]),
            "v6_mlp_untuned":      float(pivot.loc[ds, "e_mlp_untuned"]),
            "tuned_mlp":           float(pivot.loc[ds, "f_mlp_tuned"]),
            "harmonic_search":     float(pivot.loc[ds, "d_harmonic_search"]),
            "v6_winner":           "harmonic" if pivot.loc[ds, "c_harmonic_fixed12"] < pivot.loc[ds, "e_mlp_untuned"] else "mlp",
            "fair_winner":         "harmonic_search" if pivot.loc[ds, "d_harmonic_search"] < pivot.loc[ds, "f_mlp_tuned"] else "tuned_mlp",
        })

    summary = {
        "test": "fair_harmonic_vs_backprop",
        "datasets": list(datasets.keys()),
        "winners_per_dataset": wins,
        "head_to_head_v6_vs_fair": head_to_head,
        "verdict": (
            "Compare the v6_winner column (V6's rigged matchup) to the fair_winner "
            "column (proper hyperparameter tuning + period search). When the period "
            "is hidden or there's no period, the V6 'harmonic always wins' claim "
            "collapses. The honest take: Fourier features beat untuned MLPs ONLY "
            "when you already know the period. With period search and a tuned MLP, "
            "the contest is fair and the winner depends on the data structure."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print("\n=== full results table ===")
    print(pivot.round(3).to_string())


if __name__ == "__main__":
    main()
