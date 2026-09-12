"""Same-origin missingness engineering diagnostic; previously inspected 2025 data.

No promotion is possible in this stage. No network, secrets or production writes.
Reuses hash-verified Stage 3/4 code and frozen Stage 4 source/calibration artifacts.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PROTOCOL_COMMIT = 'b7c5a01cf4eddbb9451963dba482cf0154b1444c'
P4 = HERE.parent / 'stage4' / 'run_stage4.py'
if hashlib.sha256(P4.read_bytes()).hexdigest() != '08268884689415bb14ac5f36b5922a3885809d3bddd7c55a3af5abffc66729e7':
    raise RuntimeError('Stage 4 code identity mismatch')
spec = importlib.util.spec_from_file_location('stage4_for_stage5', P4)
assert spec is not None and spec.loader is not None
s4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s4)
s3 = s4.s3
STATIONS = ['41002', '42001', '44025', '46050', '46237']
SCENARIOS = ['clean', 'missing_10pct', 'missing_30pct', 'block_missing_3h_per_14d']
COMPARATORS = ['persistence', 'selected_rolling', 'complete_lag_ridge', 'static_champion']


def corrupt(t: np.ndarray, x: np.ndarray, scenario: str, seed: int, year: int) -> np.ndarray:
    z = x.copy()
    if scenario in ('missing_10pct', 'missing_30pct'):
        rate = .1 if scenario == 'missing_10pct' else .3
        z[np.random.default_rng(seed).random(len(z)) < rate] = np.nan
    elif scenario == 'block_missing_3h_per_14d':
        z[(t - s4.stamp(year)) % (14 * s4.DAY) < 10800] = np.nan
    elif scenario != 'clean':
        raise ValueError('Unknown corruption scenario')
    return z


def partial_mean(t: np.ndarray, x: np.ndarray, at: np.ndarray, width: int, cadence: float) -> tuple:
    if width <= 0 or not np.isfinite(cadence) or cadence <= 0:
        raise ValueError('Invalid elapsed-time window or cadence')
    good = s3.valid(x)
    sums = np.r_[0., np.cumsum(np.where(good, x, 0.))]
    counts = np.r_[0, np.cumsum(good)]
    left = np.searchsorted(t, at - width, side='right')
    right = np.searchsorted(t, at, side='right')
    n = counts[right] - counts[left]
    avg = np.divide(sums[right] - sums[left], n, out=np.full(len(at), np.nan), where=n > 0)
    return avg, np.minimum(1., n / max(1., width / cadence))


def short_features(t: np.ndarray, x: np.ndarray, at: np.ndarray, cadence: float) -> np.ndarray:
    p = s3.exact_target(t, x, at, 0)
    m1, c1 = partial_mean(t, x, at, 3600, cadence)
    m3, c3 = partial_mean(t, x, at, 10800, cadence)
    l1 = s3.exact_target(t, x, at, -1800)
    l2 = s3.exact_target(t, x, at, -3600)
    return np.column_stack([p, m1-p, m3-p, np.where(np.isfinite(l1), l1-p, 0.),
                            np.where(np.isfinite(l2), l2-p, 0.), c1, c3,
                            ~np.isfinite(l1), ~np.isfinite(l2)])


def train_short(t: np.ndarray, x: np.ndarray, h: int, cadence: float) -> dict:
    at = t[s3.issue_indices(t, x, 1800)]
    truth = s3.exact_target(t, x, at, h)
    Xs, ys, lengths = [], [], []
    for scenario in SCENARIOS:
        X = short_features(t, corrupt(t, x, scenario, 20260905, 2023), at, cadence)
        use = (at+h < s4.stamp(2023, 9)) & np.isfinite(truth) & np.all(np.isfinite(X), axis=1)
        if use.sum() < 100:
            raise ValueError('Insufficient augmented training data')
        Xs.append(X[use]); ys.append(truth[use]-X[use, 0]); lengths.append(int(use.sum()))
    X, y = np.vstack(Xs), np.concatenate(ys)
    weights = np.concatenate([np.full(n, len(X)/(len(lengths)*n)) for n in lengths])
    mu = np.average(X, axis=0, weights=weights)
    scale = np.sqrt(np.average((X-mu)**2, axis=0, weights=weights))
    scale[scale < 1e-12] = 1.
    A = np.column_stack([np.ones(len(X)), (X-mu)/scale])
    penalty = np.eye(A.shape[1])*10.; penalty[0, 0] = 0.
    beta = np.linalg.solve(A.T @ (weights[:, None]*A)+penalty, A.T @ (weights*y))
    return {'mean': mu.tolist(), 'scale': scale.tolist(), 'beta': beta.tolist(),
            'training_rows_per_view': lengths, 'equal_view_total_weight': True,
            'last_training_target_exclusive': s4.stamp(2023, 9)}


def predict_short(X: np.ndarray, model: dict) -> np.ndarray:
    pred = np.full(len(X), np.nan)
    use = np.all(np.isfinite(X), axis=1)
    A = np.column_stack([np.ones(use.sum()), (X[use]-model['mean'])/model['scale']])
    pred[use] = np.maximum(0., X[use, 0]+A@np.asarray(model['beta']))
    return pred


def common_origins(truth: np.ndarray, views: list[np.ndarray], eligible: np.ndarray) -> np.ndarray:
    use = eligible & np.isfinite(truth)
    for view in views:
        use &= np.all(np.isfinite(view), axis=1)
    return use


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--prior', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    s4.verify_sources(a.prior/'sources')
    # Authenticate every previously frozen result/calibration file before reuse.
    manifest = json.loads((a.prior/'results/SHA256_MANIFEST.json').read_text())
    for row in manifest['files']:
        p = a.prior/'results'/row['file']
        if p.parent.resolve() != (a.prior/'results').resolve() or s3.digest(p) != row['sha256']:
            raise ValueError('Prior result/calibration checksum mismatch')
    records = []
    for sid in STATIONS:
        t1, x1, _ = s3.read_ndbc(a.prior/'sources'/f'{sid}h2023.txt.gz', 2023)
        t, x, _ = s3.read_ndbc(a.prior/'sources'/f'{sid}h2025.txt.gz', 2025)
        at = t[s3.issue_indices(t, x, 1800)]
        for h in s4.HORIZONS:
            cfg = json.loads((a.prior/'results'/f'calibration_{sid}_{h//60}m.json').read_text())
            model = train_short(t1, x1, h, cfg['cadence_seconds'])
            s3.jwrite(a.out/f'model_{sid}_{h//60}m.json', model)
            truth = s3.exact_target(t, x, at, h)
            eligible = (at >= s4.stamp(2025)) & (at+h < s4.stamp(2026))
            for seed in range(10):
                views, fallback, available = [], [], []
                for scenario in SCENARIOS:
                    z = corrupt(t, x, scenario, seed, 2025)
                    E, _ = s4.expert_matrix(t, z, at, h, cfg['cadence_seconds'], cfg['ridge'])
                    X = short_features(t, z, at, cfg['cadence_seconds'])
                    candidate = predict_short(X, model)
                    preds = np.column_stack([candidate, E[:, 0], E[:, cfg['rolling']], E[:, 6], E[:, cfg['champion']]])
                    views.append(preds)
                    longX = s4.features(t, z, at, cfg['cadence_seconds'])[3]
                    fallback.append(~np.all(np.isfinite(longX), axis=1))
                    available.append(int(np.sum(eligible & np.isfinite(E[:, 0]))))
                use = common_origins(truth, views, eligible)
                if use.sum() < 100:
                    raise ValueError('Insufficient fair common-origin support')
                for si, scenario in enumerate(SCENARIOS):
                    pred = views[si][use]; y = truth[use]
                    errors = np.abs(y[:, None]-pred)
                    means = errors.mean(axis=0)
                    rec = {'station': sid, 'horizon_minutes': h//60, 'seed': seed, 'scenario': scenario,
                           'common_pairs': int(use.sum()), 'common_origin_sha256': hashlib.sha256(at[use].astype('<i8').tobytes()).hexdigest(),
                           'original_eligible_origins': int(eligible.sum()), 'scenario_available_origins': available[si],
                           'available_fraction_of_clean': available[si]/max(1, available[0]),
                           'candidate_mae': float(means[0]),
                           'complete_lag_fallback_fraction_on_common_pairs': float(fallback[si][use].mean()),
                           'candidate_coverage_on_common_pairs': float(np.isfinite(pred[:, 0]).mean()),
                           'promotion_allowed': False}
                    for j, name in enumerate(COMPARATORS, 1):
                        rec[name+'_mae'] = float(means[j])
                        rec['gain_pct_vs_'+name] = float(100*(means[j]-means[0])/means[j]) if means[j] > 0 else None
                    records.append(rec)
                    if sid == '46237' and h == 3600 and seed == 0:
                        np.savetxt(a.out/f'paired_predictions_{scenario}.csv', np.column_stack([at[use], at[use]+h, y, pred]),
                                   delimiter=',', fmt='%.17g', header=','.join(['issue_epoch','target_epoch','truth','short_candidate']+COMPARATORS), comments='')
            print(f'{sid} {h//60}m: 40 paired diagnostics complete', flush=True)
    if len(records) != 600:
        raise ValueError('Predeclared diagnostic matrix incomplete')
    with (a.out/'diagnostics.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(records[0])); w.writeheader(); w.writerows(records)
    groups = []
    for sid in STATIONS:
        for h in s4.HORIZONS:
            for scenario in SCENARIOS:
                rr = [r for r in records if r['station']==sid and r['horizon_minutes']==h//60 and r['scenario']==scenario]
                groups.append({'station':sid, 'horizon_minutes':h//60, 'scenario':scenario, 'seeds':len(rr),
                    **{k:float(np.mean([r[k] for r in rr])) for k in records[0] if k.startswith('gain_pct_')},
                    'mean_complete_lag_fallback_fraction':float(np.mean([r['complete_lag_fallback_fraction_on_common_pairs'] for r in rr]))})
    result = {'schema_version':'1.0', 'classification':'DESCRIPTIVE_ENGINEERING_ONLY_PREVIOUSLY_EXAMINED_2025',
              'protocol_commit':PROTOCOL_COMMIT, 'diagnostic_records':len(records), 'station_horizon_cells':15,
              'scenarios':SCENARIOS, 'seeds_reuse_same_outcomes':True, 'promotion_allowed':False,
              'all_negative_results_retained':True, 'groups':groups,
              'source_manifest_sha256':s3.digest(a.prior/'sources/SOURCE_MANIFEST.json'),
              'code_sha256':s3.digest(Path(__file__)), 'numpy_version':np.__version__,
              'claim_boundary':'Internal retrospective diagnostics, not new holdout confirmation, novelty, plant operation, electricity gain or commercial validation.'}
    s3.jwrite(a.out/'summary.json', result)
    s3.jwrite(a.out/'SHA256_MANIFEST.json', {'files':[{'file':p.name,'sha256':s3.digest(p),'bytes':p.stat().st_size}
        for p in sorted(a.out.iterdir()) if p.is_file() and p.name!='SHA256_MANIFEST.json']})

if __name__ == '__main__':
    main()
