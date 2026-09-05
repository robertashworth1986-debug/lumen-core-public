"""Stage 6: frozen-point interval assurance on reused 2025 observations.

Research diagnostics only. No independence, exchangeability, safety, novelty,
energy-yield or commercial-benefit guarantee. All labels have explicit latency.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import platform
import stat
import zipfile
import numpy as np

DAY = 86400
ALPHA = .10
METHODS = ['legacy_pooled_28d', 'activity_scaled_28d', 'signed_scaled_28d', 'adaptive_scaled_28d']
MODELS = ['delayed_router_v01', 'delayed_blend_v01']
STATIONS = ['41002', '42001', '44025', '46050', '46237']
HORIZONS = [60, 180, 360]
DELAYS = [30, 90]
SOURCE_SHA = 'a0c693328a3a614ee7646731b81497f7d5f4b33b5338c9fab0595797d1017a2d'
SOURCE_BYTES = 20736097
PROTOCOL_COMMIT = '65d45b1a7ef9f21a42c10c684cdcf38c5287d06f'
END = int(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp())
START = int(dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).timestamp())


def digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def safe_extract(path: Path, destination: Path) -> None:
    with zipfile.ZipFile(path) as z:
        seen = set()
        if len(z.infolist()) > 10000 or sum(i.file_size for i in z.infolist()) > 300_000_000:
            raise ValueError('Archive resource bound')
        for i in z.infolist():
            p = PurePosixPath(i.filename)
            if (p.is_absolute() or '..' in p.parts or '\\' in i.filename or ':' in i.filename
                    or i.filename in seen or stat.S_ISLNK(i.external_attr >> 16)):
                raise ValueError('Unsafe archive member')
            seen.add(i.filename)
        if z.testzip() is not None:
            raise ValueError('ZIP integrity failure')
        z.extractall(destination)


def finite_quantile(values: np.ndarray, probability: float, lower: bool = False) -> float:
    a = np.asarray(values, float)
    if not len(a) or not np.all(np.isfinite(a)) or not 0 < probability < 1:
        raise ValueError('Invalid finite-rank quantile input')
    rank = math.floor((len(a) + 1) * probability) if lower else math.ceil((len(a) + 1) * probability)
    return float(np.partition(a, min(len(a), max(1, rank)) - 1)[min(len(a), max(1, rank)) - 1])


def interval_score(y: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    if np.any(lo > hi) or not (np.all(np.isfinite(lo)) and np.all(np.isfinite(hi))):
        raise ValueError('Invalid interval bounds')
    return hi - lo + (2 / ALPHA) * (np.maximum(lo - y, 0) + np.maximum(y - hi, 0))


def validate_series(at: np.ndarray, target: np.ndarray, y: np.ndarray,
                    prediction: np.ndarray, current: np.ndarray) -> None:
    if len(at) == 0 or not all(len(v) == len(at) for v in [target, y, prediction, current]):
        raise ValueError('Empty or mismatched arrays')
    if (not np.all(np.isfinite(at)) or not np.all(np.isfinite(target))
            or np.any(at != at.astype(np.int64)) or np.any(target != target.astype(np.int64))
            or np.any(np.diff(at) <= 0) or np.any(target <= at)):
        raise ValueError('Invalid issue or target timestamps')
    if (not np.all(np.isfinite(prediction)) or not np.all(np.isfinite(current))
            or np.any(prediction < 0) or np.any(current < 0) or np.any(np.isinf(y))
            or np.any(y[np.isfinite(y)] < 0)):
        raise ValueError('Invalid wave observations or forecasts')


def wrappers(at: np.ndarray, target: np.ndarray, y: np.ndarray, prediction: np.ndarray,
             current: np.ndarray, cfg: dict, delay: int) -> dict:
    """Generate all bounds before using their outcomes. Daily chronological replay."""
    validate_series(at, target, y, prediction, current)
    if (delay < 0 or not math.isfinite(cfg['interval_initial_q90']) or cfg['interval_initial_q90'] < 0
            or not math.isfinite(cfg['ridge']['mean'][0]) or cfg['ridge']['mean'][0] <= 0):
        raise ValueError('Negative delay or initial radius')
    n = len(at)
    initial = float(cfg['interval_initial_q90'])
    mean = max(float(cfg['ridge']['mean'][0]), 1e-9)
    scale = np.sqrt(1 + current / mean)
    lo = np.maximum(0, prediction[:, None] - initial) * np.ones((1, 4))
    hi = (prediction[:, None] + initial) * np.ones((1, 4))
    cold = np.ones(n, bool)
    latest = np.full(n, -1, np.int64)
    levels = np.full(n, ALPHA)
    clipped = np.zeros(n, bool)
    maturity = target + delay
    residual = y - prediction
    normalized = residual / scale
    days = at.astype(np.int64) // DAY
    alpha_state = ALPHA
    previous_boundary = -1
    for day in np.unique(days):
        boundary = int(day) * DAY
        ix = np.flatnonzero(days == day)
        # Only the prior intervals' errors, resolved strictly before this update.
        fresh = np.flatnonzero((maturity < boundary) & (maturity >= previous_boundary) & np.isfinite(y))
        for j in fresh[np.argsort(maturity[fresh], kind='stable')]:
            missed = float(y[j] < lo[j, 3] or y[j] > hi[j, 3])
            alpha_state = float(np.clip(alpha_state + .005 * (ALPHA - missed), .02, .25))
        previous_boundary = boundary
        levels[ix] = alpha_state
        clipped[ix] = alpha_state <= .02 or alpha_state >= .25
        hist = np.flatnonzero((at >= boundary - 28 * DAY) & (maturity < boundary) & np.isfinite(y))
        if len(hist):
            latest[ix] = int(maturity[hist].max())
            assert latest[ix[0]] < boundary
        if len(hist) < 96:
            continue
        cold[ix] = False
        raw_q = float(np.quantile(np.abs(residual[hist]), .9))
        radii = [np.full(len(ix), raw_q),
                 finite_quantile(np.abs(normalized[hist]), .9) * scale[ix],
                 None,
                 finite_quantile(np.abs(normalized[hist]), 1 - alpha_state) * scale[ix]]
        for m in [0, 1, 3]:
            lo[ix, m] = np.maximum(0, prediction[ix] - radii[m])
            hi[ix, m] = prediction[ix] + radii[m]
        left = finite_quantile(normalized[hist], .05, lower=True)
        right = finite_quantile(normalized[hist], .95)
        lo[ix, 2] = np.maximum(0, prediction[ix] + left * scale[ix])
        hi[ix, 2] = np.maximum(0, prediction[ix] + right * scale[ix])
    return {'lo': lo, 'hi': hi, 'cold': cold, 'latest': latest, 'alpha': levels, 'clipped': clipped, 'scale': scale}


def metrics(y: np.ndarray, lo: np.ndarray, hi: np.ndarray, mask: np.ndarray) -> dict:
    k = int(mask.sum())
    if not k:
        return {'n': 0, 'coverage': None, 'mean_width': None, 'interval_score': None,
                'lower_miss_rate': None, 'upper_miss_rate': None}
    v, l, u = y[mask], lo[mask], hi[mask]
    return {'n': k, 'coverage': float(np.mean((l <= v) & (v <= u))),
            'mean_width': float(np.mean(u - l)), 'interval_score': float(np.mean(interval_score(v, l, u))),
            'lower_miss_rate': float(np.mean(v < l)), 'upper_miss_rate': float(np.mean(v > u))}


def bootstrap_scores(at: np.ndarray, baseline: np.ndarray, candidate: np.ndarray,
                     block: int, seed: int) -> list[float]:
    """Paired calendar-day sufficient-statistic moving-block diagnostic interval."""
    days = at // DAY
    start, end = int(days.min()), int(days.max())
    n = end - start + 1
    if n < 2 * block or len(at) != len(baseline) or len(at) != len(candidate):
        raise ValueError('Insufficient paired calendar history')
    b = np.bincount(days - start, weights=baseline, minlength=n)
    c = np.bincount(days - start, weights=candidate, minlength=n)
    count = int(math.ceil(n / block))
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block + 1, size=(2000, count))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(2000, -1)[:, :n]
    bb = b[idx].sum(axis=1)
    cc = c[idx].sum(axis=1)
    good = bb > 0
    if good.sum() < 1900:
        raise ValueError('Degenerate bootstrap denominators')
    return np.quantile(100 * (bb[good] - cc[good]) / bb[good], [.025, .975]).tolist()


def analyze_cell(prior: Path, out: Path, sid: str, horizon: int) -> tuple[list, list, dict]:
    file = prior / 'results' / f'predictions_{sid}_{horizon}m.csv'
    d = np.genfromtxt(file, delimiter=',', names=True, dtype=float)
    cfg = json.loads((prior / 'results' / f'calibration_{sid}_{horizon}m.json').read_text())
    at, target, y = d['issue_epoch'].astype(np.int64), d['target_epoch'].astype(np.int64), d['truth']
    if np.any(target - at != horizon * 60):
        raise ValueError('Elapsed-time target mismatch')
    good = np.isfinite(y) & (at >= START) & (target < END)
    threshold = cfg['high_activity_threshold']
    month = np.array([dt.datetime.fromtimestamp(int(v), dt.timezone.utc).month for v in at])
    origin_sha = hashlib.sha256(np.column_stack([at[good], target[good]]).astype('<i8').tobytes()).hexdigest()
    packed = {'issue_epoch': at, 'target_epoch': target, 'truth': y, 'scored_mask': good,
              'current_proxy': d['persistence']}
    records, comparisons = [], []
    baseline_errors = []
    for pi, model in enumerate(MODELS):
        p = d[model]
        packed[model] = p
        for delay in DELAYS:
            result = wrappers(at, target, y, p, d['persistence'], cfg, delay * 60)
            if delay == 30:
                expected = d['router_radius' if pi == 0 else 'blend_radius']
                if not np.allclose(result['hi'][:, 0] - p, expected, atol=1e-10, rtol=1e-10):
                    raise ValueError('Legacy radius replay mismatch')
                baseline_errors.append(float(np.max(np.abs(result['hi'][:, 0] - p - expected))))
            prefix = f'{model}_{delay}m'
            for name in ['lo', 'hi', 'cold', 'latest', 'alpha', 'clipped']:
                packed[prefix + '_' + name] = result[name]
            for mi, method in enumerate(METHODS):
                l, u = result['lo'][:, mi], result['hi'][:, mi]
                item = {'station': sid, 'horizon_minutes': horizon, 'point_model': model,
                        'interval_method': method, 'feedback_delay_minutes': delay,
                        'paired_origin_sha256': origin_sha, 'eligible_origins': int(((at >= START) & (target < END)).sum()),
                        'overall': metrics(y, l, u, good),
                        'high_at_issue': metrics(y, l, u, good & (d['persistence'] >= threshold)),
                        'high_realized_target': metrics(y, l, u, good & (y >= threshold)),
                        'quarters': {str(q): metrics(y, l, u, good & (((month - 1) // 3 + 1) == q)) for q in range(1, 5)},
                        'months': {str(m): metrics(y, l, u, good & (month == m)) for m in range(1, 13)},
                        'initial_radius_fraction': float(result['cold'][good].mean()),
                        'alpha_at_bound_fraction': float(result['clipped'][good].mean()) if mi == 3 else None,
                        'current_activity_threshold': threshold, 'promotion_allowed': False}
                records.append(item)
                if delay == 30 and mi > 0:
                    bscore = interval_score(y[good], result['lo'][good, 0], result['hi'][good, 0])
                    cscore = interval_score(y[good], l[good], u[good])
                    seed = 20260906 + STATIONS.index(sid) * 100 + HORIZONS.index(horizon) * 10 + pi * 4 + mi
                    base = metrics(y, result['lo'][:, 0], result['hi'][:, 0], good)
                    comparisons.append({'station': sid, 'horizon_minutes': horizon, 'point_model': model,
                        'interval_method': method, 'n': int(good.sum()), 'paired_origin_sha256': origin_sha,
                        'interval_score_gain_pct': float(100 * (bscore.mean() - cscore.mean()) / bscore.mean()),
                        'ci7_day_pct': bootstrap_scores(at[good], bscore, cscore, 7, seed),
                        'ci14_day_pct': bootstrap_scores(at[good], bscore, cscore, 14, seed),
                        'coverage': item['overall']['coverage'], 'baseline_coverage': base['coverage'],
                        'width_change_pct': float(100 * (item['overall']['mean_width'] / base['mean_width'] - 1)),
                        'high_at_issue_n': item['high_at_issue']['n'],
                        'high_at_issue_coverage': item['high_at_issue']['coverage'],
                        'promotion_allowed': False})
    np.savez_compressed(out / f'intervals_{sid}_{horizon}m.npz', **packed)
    return records, comparisons, {'station': sid, 'horizon_minutes': horizon,
        'paired_origins': int(good.sum()), 'paired_origin_sha256': origin_sha,
        'maximum_legacy_radius_replay_error': max(baseline_errors)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--prior-zip', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.prior_zip.stat().st_size != SOURCE_BYTES or digest(args.prior_zip) != SOURCE_SHA:
        raise ValueError('Frozen source archive identity mismatch')
    args.out.mkdir(parents=True, exist_ok=True)
    prior = args.out / 'verified_prior'
    safe_extract(args.prior_zip, prior)
    source_manifest = json.loads((prior / 'results/SHA256_MANIFEST.json').read_text())
    for row in source_manifest['files']:
        if Path(row['file']).name != row['file']:
            raise ValueError('Invalid manifest file path')
        p = prior / 'results' / row['file']
        if p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
            raise ValueError('Input result manifest mismatch')
    records, comparisons, audits = [], [], []
    for sid in STATIONS:
        for h in HORIZONS:
            r, c, a = analyze_cell(prior, args.out, sid, h)
            records.extend(r); comparisons.extend(c); audits.append(a)
            print(f'Completed {sid} {h}m; {len(records)}/240 interval records', flush=True)
    assert len(records) == 240 and len(comparisons) == 90
    write_json(args.out / 'interval_metrics.json', records)
    write_json(args.out / 'comparisons.json', comparisons)
    with (args.out / 'summary.csv').open('w', newline='') as f:
        cols = ['station', 'horizon_minutes', 'point_model', 'interval_method', 'feedback_delay_minutes',
                'n', 'coverage', 'mean_width', 'interval_score', 'high_at_issue_n', 'high_at_issue_coverage']
        writer = csv.DictWriter(f, fieldnames=cols); writer.writeheader()
        for r in records:
            row = {c: r[c] for c in cols[:5]}
            row.update({k: r['overall'][k] for k in cols[5:9]})
            row.update(high_at_issue_n=r['high_at_issue']['n'], high_at_issue_coverage=r['high_at_issue']['coverage'])
            writer.writerow(row)
    summary = {'schema_version': '1.0', 'experiment': 'stage6_interval_assurance_diagnostic_20260905',
        'protocol_commit': PROTOCOL_COMMIT, 'source_sha256': SOURCE_SHA,
        'classification': 'REUSED_2025_ENGINEERING_DIAGNOSTIC', 'promotion_allowed': False,
        'interval_records': len(records), 'descriptive_comparisons': len(comparisons),
        'methods': METHODS, 'point_models': MODELS, 'cell_audits': audits,
        'paired_station_horizon_targets': sum(a['paired_origins'] for a in audits),
        'source_hold': '46042 2025 unavailable; not substituted',
        'versions': {'numpy': np.__version__, 'python': platform.python_version()},
        'claim_boundary': 'Internal interval-assurance diagnostic. Same point forecasts, not new forecast accuracy or electricity gain. Prior 2025 record already examined. Delay stress changes interval feedback only. No formal coverage, safety, novelty, independent validation, revenue or production claim.',
        'bootstrap_boundary': 'Exploratory paired calendar blocks; dependent forecasts are not independent replications. No familywise intervals or discovery claims.',
        'next_gate': 'Choose an auditable method based on these diagnostics, then register a fresh period and independent review before any promotion.'}
    write_json(args.out / 'summary.json', summary)
    write_json(args.out / 'SHA256_MANIFEST.json', {'files': [
        {'file': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(args.out.iterdir())
        if p.is_file() and p.name != 'SHA256_MANIFEST.json']})
    print(json.dumps({'complete': True, 'interval_records': 240, 'promotion_allowed': False}))

if __name__ == '__main__':
    main()
