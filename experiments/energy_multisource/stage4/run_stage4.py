"""Frozen 2025 prequential test of two delayed-feedback routing heuristics.

Research only. Standard expert aggregation, not a novelty/valuation claim.
Reuse Stage 3 exact-time parser, rolling windows and paired block bootstrap.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
S3_PATH = BASE.parent / 'stage3' / 'run_stage3.py'
S3_BLOB = 'd878cc6e764ecbdafdeeed98fe5e7ff71153d9ad'
raw = S3_PATH.read_bytes()
if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != S3_BLOB:
    raise RuntimeError('Stage 3 dependency hash mismatch')
spec = importlib.util.spec_from_file_location('stage3_base', S3_PATH)
assert spec is not None and spec.loader is not None
s3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s3)
DAY = 86400
SEED = 20260905
PROTOCOL_COMMIT = '80bac1f947122c7c4753f7116d42163e07d3b9d2'
STATIONS = ['41002', '42001', '44025', '46042', '46050', '46237']
HORIZONS = [3600, 10800, 21600]
WINDOWS = [3600, 7200, 10800, 21600]
EXPERTS = ['persistence', 'rolling_60m', 'rolling_120m', 'rolling_180m',
           'rolling_360m', 'half_damped_60m_trend', 'direct_residual_ridge_alpha10']
CANDIDATES = ['delayed_router_v01', 'delayed_blend_v01']
COMPARATORS = ['persistence', 'calibration_best_rolling', 'calibration_static_champion']
FAMILY = 108


def stamp(year: int, month: int = 1, day: int = 1) -> int:
    return int(dt.datetime(year, month, day, tzinfo=dt.timezone.utc).timestamp())


def features(t: np.ndarray, x: np.ndarray, at: np.ndarray, cadence: float) -> tuple:
    """All inputs occur at or before the forecast issue time."""
    p = s3.exact_target(t, x, at, 0)
    lag = [s3.exact_target(t, x, at, -v * 3600) for v in [1, 3, 6, 12, 24]]
    rolls = [s3.rolling(t, x, at, w, cadence) for w in WINDOWS]
    X = np.column_stack([p] + lag + rolls)
    return p, lag, rolls, X


def fit_ridge(X: np.ndarray, delta: np.ndarray, mask: np.ndarray) -> dict:
    """Fixed alpha; train-only feature scaling and no imputed labels."""
    use = mask & np.all(np.isfinite(X), axis=1) & np.isfinite(delta)
    if int(use.sum()) < 100:
        raise ValueError('Insufficient early-2023 ridge training pairs')
    mu = X[use].mean(axis=0)
    scale = X[use].std(axis=0)
    scale[scale < 1e-12] = 1.0
    A = np.column_stack([np.ones(use.sum()), (X[use] - mu) / scale])
    penalty = np.eye(A.shape[1]) * 10.0
    penalty[0, 0] = 0
    beta = np.linalg.solve(A.T @ A + penalty, A.T @ delta[use])
    return {'mean': mu.tolist(), 'scale': scale.tolist(), 'beta': beta.tolist(),
            'training_pairs': int(use.sum())}


def expert_matrix(t: np.ndarray, x: np.ndarray, at: np.ndarray, h: int,
                  cadence: float, ridge: dict) -> tuple[np.ndarray, dict]:
    p, lag, rolls, X = features(t, x, at, cadence)
    trend = np.maximum(0, p + .5 * min(h / 3600, 1.0) * (p - lag[0]))
    pred = p.copy()
    complete = np.all(np.isfinite(X), axis=1)
    A = np.column_stack([np.ones(complete.sum()),
                         (X[complete] - np.array(ridge['mean'])) / np.array(ridge['scale'])])
    pred[complete] = np.maximum(0, p[complete] + A @ np.array(ridge['beta']))
    cols = [p] + rolls + [trend, pred]
    fallback = {}
    for i, c in enumerate(cols):
        bad = ~np.isfinite(c)
        fallback[EXPERTS[i]] = int(bad.sum()) if i != 6 else int((~complete).sum())
        cols[i] = np.where(bad, p, c)
    return np.column_stack(cols), fallback


def calibrate(t: np.ndarray, x: np.ndarray, h: int) -> dict:
    at = t[s3.issue_indices(t, x, 1800)]
    tt = t[(t < stamp(2023, 9)) & s3.valid(x)]
    cadence = float(np.median(np.diff(tt)))
    if not np.isfinite(cadence) or cadence <= 0:
        raise ValueError('Invalid calibration cadence')
    p, _, _, X = features(t, x, at, cadence)
    truth = s3.exact_target(t, x, at, h)
    train = at + h < stamp(2023, 9)
    ridge = fit_ridge(X, truth - p, train)
    E, _ = expert_matrix(t, x, at, h, cadence, ridge)
    val = (at >= stamp(2023, 9)) & (at + h < stamp(2024)) & np.isfinite(truth)
    if val.sum() < 100:
        raise ValueError('Insufficient late-2023 calibration pairs')
    losses = np.abs(truth[val, None] - E[val])
    prior = losses.mean(axis=0)
    champion = int(np.argmin(prior))
    rm = int(1 + np.argmin(prior[1:5]))
    return {'cadence_seconds': cadence, 'ridge': ridge, 'prior_mae': prior.tolist(),
            'champion': champion, 'rolling': rm, 'calibration_pairs': int(val.sum()),
            'last_selection_target': int((at[val] + h).max()),
            'interval_initial_q90': float(np.quantile(losses[:, champion], .9)),
            'high_activity_threshold': float(np.quantile(truth[val], .95))}


def adaptive(at: np.ndarray, truth: np.ndarray, E: np.ndarray, h: int,
             cfg: dict, latency: int = 1800) -> dict:
    """Update at day start. Current day's unresolved labels cannot affect routing.

    Public source observation time is an availability proxy. The explicit
    label latency is a test assumption, not measured NOAA dissemination delay.
    """
    if len(at) == 0 or np.any(np.diff(at) <= 0):
        raise ValueError('Empty or nonmonotone forecast origins')
    if E.shape != (len(at), 7) or not np.all(np.isfinite(E)):
        raise ValueError('Invalid expert forecasts')
    champion = int(cfg['champion'])
    prior = np.asarray(cfg['prior_mae'], float)
    mat = np.column_stack([E[:, champion], E[:, champion]])
    radii = np.full((len(at), 2), cfg['interval_initial_q90'], float)
    choices = np.full(len(at), champion, int)
    active = np.zeros(len(at), bool)
    last_labels = np.full(len(at), -1, np.int64)
    Eerr = np.abs(truth[:, None] - E)
    maturity = at + h + latency
    days = at // DAY
    for day in np.unique(days):
        ix = np.flatnonzero(days == day)
        boundary = int(day) * DAY
        # at+h+latency must be strictly before day start, not <=.
        hist = np.flatnonzero((at >= boundary - 14 * DAY) & (maturity < boundary)
                             & np.isfinite(truth))
        if len(hist) >= 96 and len(np.unique(days[hist])) >= 5:
            score = (Eerr[hist].sum(axis=0) + 48 * prior) / (len(hist) + 48)
            chosen = int(np.argmin(score))
            if not score[chosen] <= .98 * score[champion]:
                chosen = champion
            weight = np.exp(-4 * (score - score.min()) / max(float(np.median(score)), 1e-12))
            weight /= weight.sum()
            mat[ix, 0] = E[ix, chosen]
            mat[ix, 1] = .5 * E[ix, champion] + .5 * (E[ix] @ weight)
            choices[ix] = chosen
            active[ix] = True
            last_labels[ix] = int(maturity[hist].max())
        # Candidate residuals were generated at their original issue times.
        hist28 = np.flatnonzero((at >= boundary - 28 * DAY) & (maturity < boundary)
                               & np.isfinite(truth))
        if len(hist28) >= 96:
            radii[ix] = np.quantile(np.abs(truth[hist28, None] - mat[hist28]), .9, axis=0)
    return {'pred': mat, 'radius': radii, 'chosen': choices, 'active': active,
            'latest_feedback_available': last_labels}


def diagnostics(at: np.ndarray, truth: np.ndarray, pred: np.ndarray,
                radius: np.ndarray, baseline: np.ndarray, threshold: float) -> dict:
    err = np.abs(truth - pred)
    be = np.abs(truth - baseline)
    high = truth >= threshold
    quarters = {}
    for q in range(4):
        a = stamp(2025, 1 + 3 * q)
        b = stamp(2025, 4 + 3 * q) if q < 3 else stamp(2026)
        m = (at >= a) & (at < b)
        if m.any():
            quarters[str(q + 1)] = {'n': int(m.sum()), 'mae': float(err[m].mean()),
                                    'baseline_mae': float(be[m].mean())}
    return {'nominal_interval_coverage': .9,
            'empirical_interval_coverage': float(np.mean((truth >= np.maximum(0, pred - radius))
                                                        & (truth <= pred + radius))),
            'mean_interval_width': float(np.mean(pred + radius - np.maximum(0, pred - radius))),
            'calibration_high_activity_threshold': threshold,
            'high_activity_n': int(high.sum()),
            'high_activity_mae': float(err[high].mean()) if high.any() else None,
            'high_activity_baseline_mae': float(be[high].mean()) if high.any() else None,
            'quarters': quarters}


def score_cell(sid: str, t: np.ndarray, x: np.ndarray, h: int,
               cfg: dict, out: Path) -> tuple[list, dict]:
    ii = s3.issue_indices(t, x, 1800)
    at = t[ii]
    E, fallback = expert_matrix(t, x, at, h, cfg['cadence_seconds'], cfg['ridge'])
    truth = s3.exact_target(t, x, at, h)
    online = adaptive(at, truth, E, h, cfg)
    eligible = (at >= stamp(2025)) & (at + h < stamp(2026))
    good = eligible & np.isfinite(truth)
    if good.sum() < 100:
        raise ValueError('Too few exact-time evaluation pairs')
    coverage = float(good.sum() / max(1, eligible.sum()))
    baselines = [0, cfg['rolling'], cfg['champion']]
    result = []
    for ci, candidate in enumerate(CANDIDATES):
        pred = online['pred'][:, ci]
        for bi, comparator in enumerate(COMPARATORS):
            seed = SEED + STATIONS.index(sid) * 100 + HORIZONS.index(h) * 10 + ci * 3 + bi
            b = E[:, baselines[bi]]
            r = s3.boot_compare(at[good], truth[good], b[good], pred[good], 7, seed)
            sensitivity = s3.boot_compare(at[good], truth[good], b[good], pred[good], 14, seed)
            r.update(station=sid, horizon_minutes=h // 60, candidate=candidate, comparator=comparator,
                     comparator_expert=EXPERTS[baselines[bi]], common_pair_coverage=coverage,
                     eligible_origins=int(eligible.sum()), ci14_days=sensitivity['ci95_pct'])
            result.append(r)
    diag = {'station': sid, 'horizon_minutes': h // 60, 'calibration': cfg,
            'fallback_counts_all_origins': fallback, 'eligible_origins': int(eligible.sum()),
            'matched_origins': int(good.sum()), 'common_pair_coverage': coverage,
            'adaptive_active_fraction': float(online['active'][good].mean()),
            'router_expert_fractions': {e: float(np.mean(online['chosen'][good] == i))
                                        for i, e in enumerate(EXPERTS)}, 'candidates': {}}
    for ci, c in enumerate(CANDIDATES):
        diag['candidates'][c] = diagnostics(at[good], truth[good], online['pred'][good, ci],
            online['radius'][good, ci], E[good, cfg['champion']], cfg['high_activity_threshold'])
    records = np.column_stack([at, at + h, truth, E, online['pred'], online['radius'],
                                online['chosen'], online['active'], online['latest_feedback_available']])
    np.savetxt(out / f'predictions_{sid}_{h//60}m.csv', records, delimiter=',', fmt='%.17g',
               header=','.join(['issue_epoch', 'target_epoch', 'truth'] + EXPERTS + CANDIDATES +
               ['router_radius', 'blend_radius', 'chosen_expert', 'adaptive_active', 'latest_feedback_available']), comments='')
    return result, diag


def stress(t: np.ndarray, x: np.ndarray, cfg: dict) -> dict:
    """Descriptive only, preselected station/horizon. Clean truth kept separate."""
    result = {}
    original_at = t[s3.issue_indices(t, x, 1800)]
    original_eligible = int(np.sum(original_at + 3600 < stamp(2026)))
    for scenario in ['clean', 'random_missing_10pct', 'block_missing_3h_per_14d', 'label_latency_90m']:
        corrupted = x.copy()
        latency = 1800
        if scenario == 'random_missing_10pct':
            corrupted[np.random.default_rng(42).random(len(x)) < .1] = np.nan
        elif scenario == 'block_missing_3h_per_14d':
            corrupted[(t - stamp(2025)) % (14 * DAY) < 10800] = np.nan
        elif scenario == 'label_latency_90m':
            latency = 5400
        at = t[s3.issue_indices(t, corrupted, 1800)]
        E, fallback = expert_matrix(t, corrupted, at, 3600, cfg['cadence_seconds'], cfg['ridge'])
        truth = s3.exact_target(t, x, at, 3600)
        online = adaptive(at, truth, E, 3600, cfg, latency)
        eligible = at + 3600 < stamp(2026)
        use = eligible & np.isfinite(truth)
        result[scenario] = {'eligible_origins': int(eligible.sum()), 'matched_pairs': int(use.sum()),
            'eligible_count_ratio_to_clean': float(eligible.sum() / max(1, original_eligible)),
            'input_values_withheld': int(np.sum(np.isfinite(x) & ~np.isfinite(corrupted))),
            'persistence_mae': float(np.abs(truth[use] - E[use, 0]).mean()),
            'static_champion_mae': float(np.abs(truth[use] - E[use, cfg['champion']]).mean()),
            'router_mae': float(np.abs(truth[use] - online['pred'][use, 0]).mean()),
            'blend_mae': float(np.abs(truth[use] - online['pred'][use, 1]).mean()),
            'fallback_counts': fallback}
    return result


def adjust(rows: list[dict]) -> None:
    running = 0.0
    for rank, i in enumerate(sorted(range(len(rows)), key=lambda j: rows[j]['p_one_sided'])):
        r = rows[i]
        running = max(running, min(1., r['p_one_sided'] * (FAMILY - rank)))
        r['holm_p'] = running
        r['screen_pass'] = bool(r['n'] >= 2000 and r['scored_days'] >= 120
            and r['common_pair_coverage'] >= .8 and r.get('improvement_pct') is not None
            and r['improvement_pct'] >= 5 and running < .05
            and r['ci95_pct'][0] > 0 and r['ci14_days'][0] > 0)


def verify_sources(root: Path) -> dict:
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    for r in manifest['files']:
        if r['status'] == 'ACQUIRED':
            p = root / r['file']
            if p.parent.resolve() != root.resolve() or s3.digest(p) != r['sha256']:
                raise ValueError('Source checksum/path mismatch')
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--sources', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    manifest = verify_sources(a.sources)
    acquired = {r['file'] for r in manifest['files'] if r['status'] == 'ACQUIRED'}
    scores, cells, holds, sources = [], [], [], []
    stress_result = {}
    for sid in STATIONS:
        p1, p2 = a.sources / f'{sid}h2023.txt.gz', a.sources / f'{sid}h2025.txt.gz'
        if p1.name not in acquired or p2.name not in acquired:
            holds.append({'station': sid, 'reason': 'Missing predeclared calibration/evaluation source',
                          'withheld_comparisons': 18})
            continue
        t1, x1, m1 = s3.read_ndbc(p1, 2023)
        t2, x2, m2 = s3.read_ndbc(p2, 2025)
        sources.extend([m1, m2])
        for h in HORIZONS:
            cfg = calibrate(t1, x1, h)
            s3.jwrite(a.out / f'calibration_{sid}_{h//60}m.json', cfg)
            r, d = score_cell(sid, t2, x2, h, cfg, a.out)
            scores.extend(r)
            cells.append(d)
            print(f'{sid} {h//60}m finished', flush=True)
            if sid == '46237' and h == 3600:
                stress_result = stress(t2, x2, cfg)
    adjust(scores)
    promoted = []
    for sid in STATIONS:
        for h in HORIZONS:
            for candidate in CANDIDATES:
                group = [r for r in scores if r['station'] == sid and r['horizon_minutes'] == h//60
                         and r['candidate'] == candidate]
                if len(group) == 3 and all(r['screen_pass'] for r in group):
                    promoted.append({'station': sid, 'horizon_minutes': h//60, 'candidate': candidate})
    result = {'schema_version': '1.0', 'experiment': 'stage4_delayed_feedback_router_2025',
        'protocol_commit': PROTOCOL_COMMIT, 'run_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'research_status': 'COMPLETE_WITH_SOURCE_HOLD' if holds else 'COMPLETE',
        'planned_comparisons': FAMILY, 'scored_comparisons': len(scores),
        'source_holds': holds, 'full_screen_candidates': promoted, 'comparisons': scores,
        'cells': cells, 'predeclared_stress_diagnostics': stress_result, 'sources': sources,
        'acquisition_manifest_sha256': s3.digest(a.sources/'SOURCE_MANIFEST.json'),
        'code_sha256': s3.digest(Path(__file__)), 'versions': {'python': platform.python_version(), 'numpy': np.__version__},
        'claim_boundary': 'Internal retrospective prequential research. Standard expert aggregation; no novelty, independent validation, energy production, control, safety or valuation claim.',
        'limitations': ['Public final historical observations, not as-of dissemination snapshots.',
          '2025 labels update weights only after configured maturity; this is not a static frozen-weight holdout.',
          'Bootstrap inference depends on weak temporal dependence; intervals are not familywise intervals.',
          'Forecast-availability losses and missing truths require separate coverage review.',
          'Geothermal transfer and commercial benefit not tested in this wave-only stage.']}
    s3.jwrite(a.out / 'summary.json', result)
    if scores:
        with (a.out/'comparisons.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(scores[0]))
            w.writeheader(); w.writerows(scores)
    s3.jwrite(a.out/'SHA256_MANIFEST.json', {'files': [{'file':p.name,'sha256':s3.digest(p),'bytes':p.stat().st_size}
        for p in sorted(a.out.iterdir()) if p.is_file() and p.name != 'SHA256_MANIFEST.json']})
    print(json.dumps({'scored':len(scores), 'promoted':promoted, 'holds':holds}))


if __name__ == '__main__':
    main()
